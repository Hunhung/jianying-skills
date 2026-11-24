# jianying-skills

剪映自动化 Skill，基于 `luoluoluo22/jianying-editor-skill` v1.7.0（MIT）的本地修改版。

当前仓库内容：

| 目录 | 状态 | 说明 |
|---|---|---|
| `jianying-editor` | 已上传 | 通用版：旅游素材混剪、一次性剪辑、多素材整合 |

高清直拍专用版（`jianying-editor-hd-fancam`）还在调整中，暂不上传。

## 通用版包含什么

上游 v1.7.0 的全部能力，加上 2026-09-30 的本地实测修复：

- 剪映 11.x 加密草稿的读写边界（被剪映打开过的草稿脚本改不动）
- `key_value.json` 素材注册（滤镜轨显示为空的根因）
- 新建草稿必须补齐的侧车文件
- 视频素材字段补齐（防抖档位、matting 等）
- 画布宽高显式传入、旋转/scale 适配规则
- 无 ffprobe 时的安全跳过

CSV 素材库来自原版，不含本机私人路径。上游 LICENSE 与致谢保留。
