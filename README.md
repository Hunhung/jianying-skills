# 剪映 Skill 集合（本地维护）

这个目录同时是 GitHub 仓库根目录，只跟踪下面两个 skill。其他 skill 目录已在 `.gitignore` 中排除。

## 两个 skill 的分工

| 目录 | 用途 | 什么时候用 |
|---|---|---|
| `jianying-editor` | **通用版**：剪映自动化剪辑的完整能力 | 旅游素材混剪、一次性剪辑、任何没有固定栏目要求的场景 |
| `jianying-editor-hd-fancam` | **高清直拍专用版**：固定栏目出片流程 | 说「高清直拍」「做直拍」「批量出直拍」，或要按固定规格出片 |

两个版本的底层 API 与实测规则完全一致；专用版在 `SKILL.md` 顶部多一节「高清直拍：固定规格」，`rules/setup.md` 会优先加载自己目录下的脚本。改栏目规格时**只改专用版那一节**，不要动下面的 CRITICAL 实测规则。

## 来源与许可

- 上游：`github.com/luoluoluo22/jianying-editor-skill` v1.7.0，**MIT**（原仓库现已下线，仅存社区 v1.5.0 备份）
- 本地修改集中在 2026-09-30：加密草稿判别、`key_value.json` 素材注册、侧车文件、防抖字段、画布/scale 规则、ffprobe 兜底等，均为通用技术修复
- 内嵌依赖 `pyJianYingDraft`（`github.com/GuanYixuan/pyJianYingDraft`）
- 保留上游 `LICENSE` 与致谢，修改再发布符合 MIT 要求

## 仓库维护注意

- `data/` 里是原版的云端素材库 CSV，**不含本机私人路径**，可以安全上传
- 新装的其它 skill 不会被跟踪（见 `.gitignore`），不会误传
- 两个版本改动时保持同步：底层修复两个字目录都要改；栏目规格只改专用版
