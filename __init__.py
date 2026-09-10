"""Thin ComfyUI wrapper for SeeThrough v3 head-tag-only inference.

This module delegates inference and data structures to the already installed
ComfyUI-See-through package.  It adds no segmentation or alpha heuristics.
"""

from __future__ import annotations

import importlib
import json
import os
import uuid
from datetime import datetime

from PIL import Image


st = importlib.import_module("custom_nodes.ComfyUI-See-through.nodes")

np = st.np
torch = st.torch
mm = st.mm
folder_paths = st.folder_paths

HEAD_TAGS_V3 = (
    "headwear",
    "face",
    "irides",
    "eyebrow",
    "eyewhite",
    "eyelash",
    "eyewear",
    "ears",
    "earwear",
    "nose",
    "mouth",
)


class SeeThroughGenerateHeadTags:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "layerdiff_model": ("SEETHROUGH_LAYERDIFF_MODEL",),
                "tags": ("STRING", {"default": "mouth", "multiline": False}),
                "seed": ("INT", {"default": 42, "min": 0, "max": 0xFFFFFFFF}),
                "resolution": ("INT", {"default": 1024, "min": 512, "max": 2048, "step": 64}),
                "num_inference_steps": ("INT", {"default": 12, "min": 1, "max": 100}),
            }
        }

    RETURN_TYPES = ("SEETHROUGH_LAYERS", "IMAGE")
    RETURN_NAMES = ("layers", "preview")
    FUNCTION = "generate"
    CATEGORY = "SeeThrough/Research"

    def generate(self, image, layerdiff_model, tags="mouth", seed=42, resolution=1024, num_inference_steps=12):
        pipeline = layerdiff_model
        if pipeline.unet.get_tag_version() != "v3":
            raise ValueError("Head-tag-only inference requires a SeeThrough v3 LayerDiff model")

        selected = []
        for tag in tags.split(","):
            tag = tag.strip()
            if tag and tag not in selected:
                selected.append(tag)
        invalid = [tag for tag in selected if tag not in HEAD_TAGS_V3]
        if not selected or invalid:
            raise ValueError(f"Invalid head tags {invalid}; valid tags: {', '.join(HEAD_TAGS_V3)}")

        device = mm.get_torch_device()
        offload = torch.device("cpu")
        st.seed_everything(seed)

        img_np = (image[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        if img_np.shape[-1] == 3:
            alpha = np.full((*img_np.shape[:2], 1), 255, dtype=np.uint8)
            img_np = np.concatenate([img_np, alpha], axis=-1)
        input_img = img_np.copy()
        fullpage, pad_size, pad_pos = st.center_square_pad_resize(
            input_img,
            resolution,
            return_pad_info=True,
        )

        # SeeThrough v3's head UNet is trained with a fixed 11-frame group and
        # reshapes conditioning with that cardinality internally.  We therefore
        # run the complete head group, but return/save only the requested tags.
        inference_tags = list(HEAD_TAGS_V3)
        cached_embeds = getattr(pipeline, "_cached_prompt_embeds", None)
        cached = bool(cached_embeds) and hasattr(pipeline, "encode_cropped_prompt_77tokens_cached")
        if cached:
            prompt_embeds, pooled_prompt_embeds = pipeline.encode_cropped_prompt_77tokens_cached(inference_tags)
        else:
            pipeline.text_encoder.to(device)
            pipeline.text_encoder_2.to(device)
            prompt_embeds, pooled_prompt_embeds = pipeline.encode_cropped_prompt_77tokens(inference_tags)
            pipeline.text_encoder.to(offload)
            pipeline.text_encoder_2.to(offload)

        group_offload = getattr(pipeline, "_st_group_offload", False)
        if not group_offload:
            pipeline.unet.to(device)
            pipeline.vae.to(device)
        pipeline.trans_vae.to(device)
        mm.soft_empty_cache()

        rng = torch.Generator(device=device).manual_seed(seed)
        out = pipeline(
            strength=1.0,
            num_inference_steps=num_inference_steps,
            batch_size=1,
            generator=rng,
            guidance_scale=1.0,
            prompt_embeds=prompt_embeds,
            pooled_prompt_embeds=pooled_prompt_embeds,
            fullpage=fullpage,
            group_index=1,
        )
        all_layers = {tag: rgba for tag, rgba in zip(inference_tags, out.images)}
        layer_dict = {tag: all_layers[tag] for tag in selected}

        if not group_offload:
            pipeline.unet.to(offload)
            pipeline.vae.to(offload)
        pipeline.trans_vae.to(offload)
        mm.soft_empty_cache()

        layers = st.SeeThrough_LayersData(
            layer_dict,
            fullpage,
            input_img,
            resolution,
            pad_size,
            pad_pos,
        )
        preview_items = {
            tag: {"img": rgba, "xyxy": [0, 0, resolution, resolution]}
            for tag, rgba in layer_dict.items()
            if np.any(rgba[..., -1] > 10)
        }
        preview = st._make_preview(preview_items, resolution)
        return (layers, preview)


class SeeThroughSaveRawTags:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "layers": ("SEETHROUGH_LAYERS",),
                "filename_prefix": ("STRING", {"default": "research/face-head-tags"}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("manifest",)
    FUNCTION = "save"
    CATEGORY = "SeeThrough/Research"
    OUTPUT_NODE = True

    def save(self, layers, filename_prefix="research/face-head-tags"):
        output_dir = folder_paths.get_output_directory()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = str(uuid.uuid4())[:8]
        entries = []

        for tag, rgba in layers.layer_dict.items():
            alpha = rgba[..., -1]
            ys, xs = np.nonzero(alpha > 0)
            bbox = None if len(xs) == 0 else [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
            filename = f"{filename_prefix}_{timestamp}_{run_id}_{tag}.png"
            path = os.path.join(output_dir, filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            Image.fromarray(rgba, mode="RGBA").save(path)
            entries.append({"name": tag, "filename": filename, "bbox": bbox})

        manifest_name = f"{filename_prefix}_{timestamp}_{run_id}_raw_tags.json"
        manifest_path = os.path.join(output_dir, manifest_name)
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "format": "seethrough-raw-head-tags-v1",
                    "width": int(layers.resolution),
                    "height": int(layers.resolution),
                    "layers": entries,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
        return (manifest_path,)


NODE_CLASS_MAPPINGS = {
    "SeeThrough_GenerateHeadTags": SeeThroughGenerateHeadTags,
    "SeeThrough_SaveRawTags": SeeThroughSaveRawTags,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SeeThrough_GenerateHeadTags": "SeeThrough Generate Head Tags (Research)",
    "SeeThrough_SaveRawTags": "SeeThrough Save Raw Tags (Research)",
}
