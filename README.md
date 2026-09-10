# ComfyUI-SeeThrough-HeadTags

Run the existing SeeThrough v3 head branch directly in ComfyUI and save selected raw transparent layers. This repository packages the locally used HeadTags extension; it does not contain model weights or the upstream SeeThrough implementation.

[中文说明](README_CN.md)

## What it does

- Calls the v3 head branch with `group_index=1`, skipping body inference.
- Runs all **11 head tags** required by the model, then filters which outputs are returned and saved. Selecting `mouth` does **not** reduce computation to a single tag.
- Saves raw LayerDiff RGBA PNGs and a JSON manifest. Marigold depth estimation, post-processing, left/right splitting and PSD export are not run.
- Uses the existing model loader from [ComfyUI-See-through](https://github.com/jtydhr88/ComfyUI-See-through).

## Installation

1. Install [ComfyUI-See-through](https://github.com/jtydhr88/ComfyUI-See-through) and its dependencies according to its README. Keep its exact folder name: `ComfyUI/custom_nodes/ComfyUI-See-through`.
2. Clone this repository alongside it:

   ```sh
   cd ComfyUI/custom_nodes
   git clone https://github.com/kq0715/ComfyUI-SeeThrough-HeadTags.git
   ```

3. Restart ComfyUI. Search for the nodes under `SeeThrough/Research`.
4. Use a **v3** LayerDiff model, such as `layerdifforg/seethroughv0.0.2_layerdiff3d`. Model version `v0.0.2` uses tag format `v3`; these version numbers describe different things.

This is an extension of the upstream node pack, not a replacement. It imports that package using its canonical folder name and expects it under the normal `custom_nodes` directory. Renamed upstream folders, ZIP folders ending in `-main`, and alternative custom-node roots are not supported by this packaged implementation. No extra Python dependencies beyond the working upstream environment are required.

## Nodes

| Class name | Display name | Purpose |
| --- | --- | --- |
| `SeeThrough_GenerateHeadTags` | SeeThrough Generate Head Tags (Research) | Generate selected raw head layers and a preview |
| `SeeThrough_SaveRawTags` | SeeThrough Save Raw Tags (Research) | Save RGBA PNGs and a manifest |

Connect `LoadImage` and `SeeThrough_LoadLayerDiffModel` to `SeeThrough_GenerateHeadTags`, then connect its `layers` output to `SeeThrough_SaveRawTags`. The `preview` output can connect to `PreviewImage`.

### Input and settings

Use a prepared crop containing the complete head, retaining the original hair and facial context. This node pads/resizes the supplied image; it does not locate or crop a head from a full-body image. It processes only the first image of an input batch.

The comma-separated `tags` field accepts:

```text
headwear,face,irides,eyebrow,eyewhite,eyelash,eyewear,ears,earwear,nose,mouth
```

Examples: `mouth`, `mouth,eyebrow`, or the complete list above. Names are case-sensitive. `front hair`, `back hair`, `head` and `neck` belong to the body branch and are not accepted.

The packaged defaults are `seed=42`, `resolution=1024`, `num_inference_steps=12`. Use the upstream loader with `cache_tag_embeds=true` and `group_offload=false`, as in the example. The combination `cache_tag_embeds=false` and `group_offload=true` is not supported by this wrapper's manual text-encoder placement. VRAM requirements depend on the upstream model and settings.

### Workflows

- [`workflows/head_tags.json`](workflows/head_tags.json): import into the ComfyUI canvas, then choose your own head image and installed v3 model.
- [`workflows/head_tags_api.json`](workflows/head_tags_api.json): API prompt example; replace `head.png` with an existing ComfyUI input filename. The example is local-only (`auto_download=false`); adjust the loader model name to the one shown in your installation. Submit this prompt object as the `prompt` field of a `POST /prompt` request, rather than submitting the canvas workflow.

Neither example includes a character image or model weights. Defaults save only `mouth`; change `tags` to export other layers.

## Output

`filename_prefix`, defaulting to `research/face-head-tags`, is relative to the ComfyUI output directory. Use a relative path without `..`; this prototype does not validate prefix traversal or absolute paths.

Each run writes timestamp/UUID-named PNGs and a `*_raw_tags.json` manifest containing:

- `format`: `seethrough-raw-head-tags-v1`
- `width` and `height`: the processing resolution
- `layers`: selected tag names, filenames and alpha bounding boxes

PNGs retain the entire square processing canvas. Bounding boxes are `[x_min, y_min, x_max_exclusive, y_max_exclusive]`, or `null` for empty layers. The manifest does not record a mapping back to a full-body source image. Raw layers may overlap and have not undergone the original depth-based extraction pipeline.

## Provenance and validation

The initial release preserves the installed local node source byte for byte (SHA-256 `d9141e38407bbe24312be3f098e584e869ba66ce6c33abfca2d0f4d1df8e6fc0`). The surrounding documentation and workflows were prepared for repository distribution. The head branch is an existing SeeThrough v3 capability; this extension adds a separate entry point and output selection, without training a new model.

Reference upstream revision: `eb6fa6f` from `jtydhr88/ComfyUI-See-through`. Packaging checks cover Python syntax, workflow structure and preservation of the original source. GPU inference was not rerun for this release.

## Upstream projects and licensing

- [ComfyUI-See-through](https://github.com/jtydhr88/ComfyUI-See-through)
- [See-through](https://github.com/shitagaki-lab/see-through)

Upstream code and downloaded models retain their respective licenses and terms. This repository contains no upstream model weights. No new license grant is made for this local extension in this initial repository snapshot.
