# ComfyUI-SeeThrough-HeadTags

把 SeeThrough v3 已有的头部分支单独暴露为 ComfyUI 节点，按标签保存原始透明图层。

## 能力

- 跳过身体分支，直接调用 `group_index=1`。
- 模型仍计算完整的 **11 个头部标签**；`tags=mouth` 只是筛选嘴巴输出，不能减少成单标签推理。
- 直接保存原始 RGBA PNG 和 JSON 清单，跳过 Marigold 深度、后处理、左右拆分及 PSD 导出。
- 输入应是保留原始头发和五官上下文的完整头部裁图；节点不会自动从全身图定位、裁切头部。
- 输入 batch 只处理第一张图。

## 安装

1. 先按[原版节点说明](https://github.com/jtydhr88/ComfyUI-See-through)安装原版及其依赖，目录名必须是 `ComfyUI/custom_nodes/ComfyUI-See-through`。
2. 在同一个 `custom_nodes` 目录克隆本仓库：

   ```sh
   git clone https://github.com/kq0715/ComfyUI-SeeThrough-HeadTags.git
   ```

3. 重启 ComfyUI，在 `SeeThrough/Research` 分类查找两个节点。
4. 使用 v3 标签格式的模型，例如 `layerdifforg/seethroughv0.0.2_layerdiff3d`。模型版本 `v0.0.2` 和标签格式 `v3` 是两套版本号。

本仓库依赖原版节点，不包含原版完整实现或模型权重。导入代码要求标准安装目录及原版准确文件夹名，不支持改名后的原版文件夹、带 `-main` 后缀的 ZIP 解压目录或额外 custom-node 根目录。已有可用的原版运行环境时，无需额外安装 Python 依赖。

## 使用

`LoadImage` 与原版 `SeeThrough_LoadLayerDiffModel` 接入 `SeeThrough_GenerateHeadTags`，其 `layers` 输出接 `SeeThrough_SaveRawTags`；`preview` 可接 `PreviewImage`。

节点显示名：

- **SeeThrough Generate Head Tags (Research)**
- **SeeThrough Save Raw Tags (Research)**

`tags` 使用英文逗号分隔，区分大小写：

```text
headwear,face,irides,eyebrow,eyewhite,eyelash,eyewear,ears,earwear,nose,mouth
```

只要嘴巴填写 `mouth`；嘴巴和眉毛填写 `mouth,eyebrow`；全部输出就填上面整行。

**前发、后发、完整 head、neck 属于身体分支，不在可选列表内。**

默认参数为 seed 42、1024 分辨率、12 步。模型加载器建议按示例使用 `cache_tag_embeds=true`、`group_offload=false`；此原型不支持 `cache_tag_embeds=false` 与 `group_offload=true` 同时使用。显存需求取决于原版模型及配置。

## 示例工作流

- [画布工作流](workflows/head_tags.json)：在 ComfyUI 中导入后，选择自己的头部图片和本机 v3 模型。
- [API 工作流](workflows/head_tags_api.json)：把 `head.png` 换成已经放在 ComfyUI input 中的文件名，再将整个对象放入 `POST /prompt` 的 `prompt` 字段。

示例默认只保存 `mouth`，模型自动下载关闭；根据本机加载器列表调整模型名称。仓库不附带人物图片和权重。

## 输出与限制

默认输出前缀是 `research/face-head-tags`，相对 ComfyUI output 目录。只使用不含 `..` 的相对前缀；此原型没有额外校验绝对路径或目录穿越。

每次保存带时间戳和随机 ID 的透明 PNG，以及 `*_raw_tags.json`。PNG 保留完整方形处理画布；清单记录画布尺寸、标签、文件名和 alpha 包围盒，空图层 bbox 为 `null`，右下坐标为排他边界。它不记录回到原始全身图的坐标映射，也没有原版深度后处理和左右拆层。

## 来源和验证

首个提交原样保留本机已安装的 `__init__.py`，SHA-256 为 `d9141e38407bbe24312be3f098e584e869ba66ce6c33abfca2d0f4d1df8e6fc0`，整理时新增说明和示例。本地扩展只提供独立入口和输出筛选，没有重新训练模型。

参考原版提交为 `eb6fa6f`。本次整理验证 Python 语法、示例结构与源文件一致性，没有重跑 GPU 推理。上游代码和模型各自遵循原项目许可；这个初始仓库快照没有为本地扩展另行授予开源许可证。
