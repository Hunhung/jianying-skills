---
name: jianying-editor
description: 剪映 (JianYing) 通用自动化剪辑的高级封装 API (JyWrapper)，提供开箱即用的 Python 接口，支持录屏、素材导入、字幕生成、Web 动效合成及项目导出。适用于旅游素材混剪、一次性剪辑、多素材整合等无固定栏目要求的场景；固定规格的「高清直拍」请用 jianying-editor-hd-fancam。全面适配 MacOS (Apple Silicon/Intel) 与 Windows，支持 v5.9+ (draft_info.json) 架构、工程自修复、智能配音字幕及录屏变焦。
---

# JianYing Editor Skill

Use this skill when the user wants to automate video editing, generate drafts, or manipulate media assets in JianYing Pro.

Agent execution playbook: [docs/agent-playbook.md](docs/agent-playbook.md)
Minimal command SOP: [docs/minimal-command-sop.md](docs/minimal-command-sop.md)
Natural language usage guide: [usage.md](usage.md)
Draft inspector CLI:
`python <SKILL_ROOT>/scripts/draft_inspector.py list --limit 20`
`python <SKILL_ROOT>/scripts/draft_inspector.py summary --name "DraftName"`
`python <SKILL_ROOT>/scripts/draft_inspector.py show --name "DraftName" --kind content --json`
For generic editing requests, always follow the "Quick Edit Runtime Template" and "Acceptance Checklist" in that playbook.

## 🚨 重要开发原则 (CRITICAL DEVELOPER RULES)

0.  **🚨🚨 先读这条：剪映 11.x 加密草稿，被剪映打开过的草稿不能用脚本读写**
    - `draft_content.json` 是**真加密**（base64 文本，解出后熵 7.998、无 ECB 重复块），
      `draft_meta_info.json` / `draft.extra` / `deepagent/deepagent.db` 同样加密。
      **判别方法：读首字节，只有 `b'{'` 才是明文 JSON**，不要用 `json.load` 盲试。
    - **已实测证实**：把滤镜/调节写进明文 `draft_info.json`（根 + `Timelines/<uuid>/` 双份）后，
      剪映加载该草稿仍显示为空 → **存在加密 `draft_content.json` 时明文文件被忽略**。
    - **结论**：只有「本 skill 新建、剪映尚未打开」的草稿可写；剪映打开过一次后即失去写入能力。
      剪映首次打开会把明文升级进加密文件（**升级一次性、内容保留**，旋转等参数会完整存活）。
    - **不要在 11.x 上做 UI 自动化**：主窗口类名 `HomePage_QMLTYPE_199`（QML），
      `uiautomation` 枚举后代元素全为空，界面没有 UIA 树。
    - 细节与排查顺序见 `rules/draft_storage.md`。

0b. **🚨 新建草稿必须写全「侧车文件」，否则滤镜/字体不渲染**
    - pyJianYingDraft 只产出 `draft_info.json` + 空的 `key_value.json {}`，
      但剪映加载时还要读 `key_value.json` **素材注册表**：
      资源级（键 = `resource_id`）+ 片段级（键 = `segment_id`）两条都要有，
      否则判定「资源未就绪」，**滤镜轨直接显示为空**。
      → **这就是「滤镜是空的」的根因**，不是素材缺字段。
    - 还要写：`draft_settings`（`[General]`，`real_edit_keys` 不能为 0）、
      `attachment_pc_common.json`（`recognize_tasks`，歌词识别入口）、
      `attachment_editing.json`、`draft_agency_config.json`、`timeline_layout.json`。
    - 工具实现：`scripts/jy_sidecar.py`（2026-11-27 从本地项目收进本仓库，之前只在用户项目里，clone 下来找不到）。

0c. **素材字段要补 + 必须校验零悬空**
    - pyJianYingDraft 写出的视频素材缺 `stable`（**防抖在这里**）、`matting`、
      `video_mask_shadow`、`video_mask_stroke`、`extra_type_option`。
    - **防抖【推荐】= 视频素材的 `stable.stable_level: 3`**（实测真实草稿值，不是 0/1/2）。
    - **悬空引用**：文字段的 `extra_material_refs` 指向的 animation 素材没进 `materials`，
      100% 悬空 → 补一个 `{"id": <ref>, "type": "sticker_animation", "animations": []}` 空壳。
    - **`materials.effects` 被调节参数和滤镜素材共用** → 后写覆盖先写。
      顺序必须是**先调节、后滤镜**，否则 `material_id` 悬空、滤镜轨空。
    - 工具实现：`scripts/jy_material_port.py`（同上，已随仓库提供）。

1.  **脚本位置**：**禁止在 Skill 内部目录创建剪辑脚本**。所有的剪辑逻辑实现代码（`.py` 脚本）必须存放在用户当前项目的**根目录**（或子目录，如 `scripts/`），以保持 Skill 库的纯净和可移植性。
2.  **版本与架构**：
    - **双平台适配**：已全面支持 MacOS (路径探测/录屏) 与 Windows。
    - **Auto-healing**：支持 v5.9+ (`draft_info.json`)。若草稿损坏或版本冲突，使用 `overwrite=True` 初始化 `JyProject` 可触发自动修复。
3.  **配乐选择**：
    - **简单演示使用默认音乐**。实际项目，应优先检索并推荐 `data/cloud_music_library.csv` 中的相关曲目，或根据视频主题（如“科技”、“温暖”）进行关键词过滤。
    - 询问用户：“我发现了几首符合主题的云端音乐，要不要试试？（如：`Illuminate` - 科技感）”。
4.  **🚨 数据安全：`overwrite` 默认值为 True，会永久删除同名草稿**
    - `JyProject(project_name, ...)` 的 `overwrite` 参数**默认为 `True`**。
    - 当传入的 `project_name` 与剪映里一个**已存在的正常草稿**同名时，默认行为不是“打开它”，而是 `shutil.rmtree()` 删除整个草稿文件夹后新建一个空草稿。删除不经回收站，**不可恢复**。
    - **规则**：
      - 要**修改/续编**已有草稿 → 必须显式传 `overwrite=False`（此时才会 `load_template` 打开原草稿）。
      - 要**新建**草稿 → 使用一个确认不存在的新名字，或显式 `overwrite=False`。
      - **绝不**在未确认目标名字是否已被占用的情况下依赖默认值。
    - 动手前先列出草稿确认命名：
      `python <SKILL_ROOT>/scripts/draft_inspector.py list --limit 50`
    - 处理用户已有的真实草稿前，先手工备份草稿文件夹（复制一份到别处）再操作。
5.  **素材导入的两个副作用（大文件必读）**
    - **`add_media_safe()` 会把素材复制进草稿目录**（`_stage_local_asset` → `<draft>/materials/`）。
      对一个 4GB 的素材，这意味着额外 4GB 磁盘占用 + 一次完整复制。素材已在稳定位置（非临时目录）时，
      可以直接用底层 API 建片段，让草稿引用原路径，避免复制：
      ```python
      from jy_wrapper import JyProject
      import pyJianYingDraft as draft          # 必须在 import jy_wrapper 之后
      from pyJianYingDraft import trange
      project = JyProject("新名字", width=2160, height=3840, overwrite=False)
      mat = draft.VideoMaterial(路径, crop_settings=draft.CropSettings(...))
      project._ensure_track(draft.TrackType.video, "VideoTrack")
      project.script.add_segment(
          draft.VideoSegment(mat, trange(0, mat.duration), source_timerange=trange(0, mat.duration)),
          "VideoTrack")
      project.save()
      ```
    - **画布会被首个视频素材覆盖**：`_add_video_safe` 中有
      `if not self._explicit_res: self.script.width, self.script.height = mat.width, mat.height`。
      而 `_explicit_res = (width != 1920 or height != 1080)`。
      **想得到竖屏/非 1080p 画布，必须在 `JyProject(...)` 显式传入宽高**，否则 1920x1080 会被素材比例顶掉。
    - **`add_media_safe` 依赖系统 `ffprobe`**（用于 `media_normalizer`）。若 PATH 中没有 ffprobe，
      已修复为安全跳过探测；否则历史版本会直接抛 `FileNotFoundError`。
      注意 `media_normalizer` 的归一化输出是 **1920x1080@30**，对 4K60 素材属破坏性降质，不要误触发。
    - **裁剪与 scale 的关系未经验证**：`crop` 是 0~1 归一化、以素材左上角为原点的四角坐标。
      它是否会让 contain 盒子随裁剪比例变化，**本机无样本可查**（758 个真实片段中 0 个带裁剪）。
      因此**不要假定"裁成 9:16 就会自动满屏，无需设 scale"**——若该假定不成立，
      裁剪区会被当成一张遮罩画在原有 contain 盒子里，画面只剩中间一条细窄区域。
      需要精确满屏时，改用下面第 6 条的旋转方案（已实测确定）。
6.  **🚨 画面适配：`clip.scale` 的基准是 contain，不是素材像素**
    - `segment.clip.scale = 1.0` 表示**素材等比缩放到"能放进画布的最大尺寸"**（contain），
      **不是**按素材原始像素 1:1 渲染。素材 `(sw,sh)` 进画布 `(cw,ch)` 时，
      `scale=1.0` 的渲染尺寸 = `(sw·k, sh·k)`，其中 `k = min(cw/sw, ch/sh)`。
    - 验证依据（本机真实草稿，9 例支持 contain、0 例支持"原始像素"）：
      `画布1080x1920 / 素材720x1280 / scale=1.0`（素材与画布同比例→本来就应满屏）；
      若按"原始像素"解释则应为 1.5，与实际不符。同类还有 `3544x4724 / 3072x4096`、`1080x1920 / 2160x3840`。
    - **横屏素材转竖屏：旋转，不要裁剪。** `rotation` 单位是角度、正值顺时针、可负。
      16:9 素材旋转 −90° 后在 9:16 画布上可做到**零裁剪、零黑边、1:1 像素**：
      ```python
      import math
      def fit_after_rotation(cw, ch, sw, sh, deg):
          rad = math.radians(deg)
          c, s = abs(math.cos(rad)), abs(math.sin(rad))
          k = min(cw / sw, ch / sh)          # contain 基准
          bw = sw * k * c + sh * k * s       # 旋转后包围盒宽
          bh = sw * k * s + sh * k * c       # 旋转后包围盒高
          return max(cw / bw, ch / bh)       # 铺满所需 scale
      ```
      常用结果：`3840x2160` 素材 + `2160x3840` 画布 + `rotation=-90` → `scale = 16/9 ≈ 1.777778`；
      `3840x2160` + `3840x6826` + `-90` → `≈1.7778`（与剪映自身在这些草稿里写出的 `1.78` 一致）。
      写入方式（走底层 API，不触发 `add_media_safe` 的复制与 ffprobe）：
      ```python
      mat.crop_settings = draft.CropSettings()               # 全画幅，不裁剪
      seg = draft.VideoSegment(
          mat, trange(0, dur), source_timerange=trange(0, dur),
          clip_settings=draft.ClipSettings(rotation=-90.0, scale_x=sc, scale_y=sc))
      ```
    - **`segment.uniform_scale` 只是"等比缩放"开关，不是缩放值。**
      真草稿里它恒为 `{"on": true, "value": 1}`，而 `clip.scale` 可以是 2.19 等任意值。
      改缩放改 `clip.scale`，别改 `uniform_scale`。
    - **只调参数就别重建草稿**：`JyProject(name, overwrite=True)` 会 `rmtree` 整个草稿目录。
      仅改 clip 参数时，直接就地改 `<draft>/draft_info.json` 的三处字段更安全。改前务必：
      ① 复制一份 `.bak`；② 确认草稿目录**无 `.locked`**（剪映正打开时会覆盖你的写入）；
      ③ 写回后用 JSON 全量 diff 确认只有预期字段变化。

7.  **🚨 手机竖拍素材（带 rotation 元数据）：归一化，不要再转 -90°**
    - 编码 3840x2160 + `rotation=90` 的手机竖拍 MOV，剪映导入时**自动归一化**（用户亲建
      草稿明文 template.json 实测）：素材 width/height 写**显示尺寸**、片段 `rotation=0/scale=1`。
      脚本做法：`VideoMaterial` 后覆写 `mat.width/height` 为显示尺寸（导出后按 path 兜底再补一遍），
      片段用默认 `ClipSettings(scale_x=1, scale_y=1, rotation=0)`，画布取显示比例即可满屏。
      规则 6 的「rotation=-90 + scale=16/9」只适用于**无元数据的纯横屏文件**。
    - **视频原声跟随视频片段**（`has_audio=1` + 片段 volume），不需要单独的 audio 素材。
    - **草稿根目录可被用户改到任意盘**（本机现为 `E:/JianyingPro Drafts`）：
      读 AppData 根的 `root_meta_info.json` → `all_draft_store`，按 `tm_draft_create` 最新的
      `draft_fold_path` 判定当前根，`JyProject(..., drafts_root=...)` 指定。
    - 悬空引用检查必须遍历 **materials 全部键**（videos/audios/effects/texts/placeholders/
      **speeds**/…）：11 个视频+1 个音频会产生 12 个 speed 素材 ref，漏扫 `speeds` 会误报悬空。
    - 详情：`rules/media.md`（旋转/原声/根目录/BGM/卡点）、`rules/draft_storage.md`（template.json 样本池）。

##  规则指南 (Rules)

Read the individual rule files for specific tasks and constraints:

- [rules/setup.md](rules/setup.md) - **Mandatory** initialization code for all scripts.
- [rules/core.md](rules/core.md) - Core operations: Saving, Exporting, and Draft management.
- [rules/cli.md](rules/cli.md) - CLI contracts and machine-readable output conventions.
- [rules/media.md](rules/media.md) - Importing assets & **AI Video Analysis Optimization (30m/360p)**.
- [rules/text.md](rules/text.md) - Adding Subtitles, Text, and Captions.
- [rules/keyframes.md](rules/keyframes.md) - **Advanced**: Adding Keyframe animations.
- [rules/effects.md](rules/effects.md) - Searching for and applying Filters, Effects, and Transitions.
- [rules/recording.md](rules/recording.md) - **New**: Screen Recording & Smart Zoom automation.
- [rules/web-vfx.md](rules/web-vfx.md) - Advanced: Web-to-Video generation.
- [rules/generative.md](rules/generative.md) - Chain of Thought for generative editing.
- [rules/audio-voice.md](rules/audio-voice.md) - **New**: TTS Voiceover & BGM sourcing.

## 🎯 Agent Quick Routing

- 云端视频 + 云端音乐：`rules/media.md` + `rules/audio-voice.md` -> `examples/cloud_video_music_tts_demo.py`
- 智能配音与字幕 (Script-to-Video)：`rules/text.md` + `rules/audio-voice.md` -> 核心 API `add_narrated_subtitles`
- 旁白与字幕对齐：`rules/text.md` + `rules/audio-voice.md` -> `examples/cloud_video_music_tts_demo.py`
- 录屏与智能变焦：`rules/recording.md` -> `tools/recording/recorder.py`
- 批量导出/无头导出：`rules/core.md` + `rules/cli.md` -> `examples/robust_auto_export.py`
- 影视解说生成：`rules/generative.md` -> `scripts/movie_commentary_builder.py`

## 📖 经典示例 (Examples)

Refer to these for complete workflows:
- [examples/my_first_vlog.py](examples/my_first_vlog.py) - A complete vlog creation demo with background music and animated text.
- [examples/simple_clip_demo.py](examples/simple_clip_demo.py) - Quick-start tutorial for basic cutting and track management.
- [examples/compound_clip_demo.py](examples/compound_clip_demo.py) - **New**: Professional nested project (Compound Clip) automation.
- [examples/cloud_video_music_tts_demo.py](examples/cloud_video_music_tts_demo.py) - Cloud video + cloud BGM + TTS/subtitle alignment.
- [examples/web_to_video_intro_demo.py](examples/web_to_video_intro_demo.py) - Web-to-Video intro demo (HTML animation -> timeline clip).
- [examples/robust_auto_export.py](examples/robust_auto_export.py) - Stable export workflow and failure handling.
- [examples/auto_exposure_align_demo.py](examples/auto_exposure_align_demo.py) - CV-assisted exposure alignment workflow.
- [examples/video_transcribe_and_match.py](examples/video_transcribe_and_match.py) - **Advanced**: AI-driven workflow (Transcribe Video -> Match B-Roll via AI semantics -> Assemble Draft).

## 🧠 提示词与集成工具 (Prompts & Integrated Tools)

Use these templates and scripts for complex tasks:
- **Asset Search**: Find filters, transitions, and animations by Chinese/English name:
  ```bash
  python <SKILL_ROOT>/scripts/asset_search.py "复古" -c filters
  ```
- **Movie Commentary Builder**: Generate 60s commentary videos from a storyboard JSON:
  ```bash
  python <SKILL_ROOT>/scripts/movie_commentary_builder.py --video "video.mp4" --json "storyboard.json"
  ```
- **Sync Native Assets**: Import your favorited/played BGM/Styles from JianYing App to the Skill:
  ```bash
  python <SKILL_ROOT>/scripts/sync_jy_assets.py
  # Index cloud materials from your existing drafts
  python <SKILL_ROOT>/scripts/build_cloud_music_library.py
  python <SKILL_ROOT>/scripts/build_cloud_text_styles_library.py
  ```
- **README to Tutorial**: Convert a project's README.md into a full installation tutorial video script:
  - Read prompt: `prompts/readme_to_tutorial.md`
  - Inject content into `{{README_CONTENT}}` variable
- **Screen Recorder & Smart Zoom**: Record your screen and auto-apply zoom keyframes:
  ```bash
  python <SKILL_ROOT>/tools/recording/recorder.py
  # Web preview capture (web_recorder.py 无参数，运行内置 demo)
  python <SKILL_ROOT>/scripts/web_recorder.py
  # 给已有视频套用智能变焦关键帧（位置参数，无 --flags）
  python <SKILL_ROOT>/scripts/smart_zoomer.py "ProjectName" "v.mp4" "events.json"
  ```
  ⚠️ `smart_zoomer.py` 内部调用 `JyProject(proj_name)`，**使用 overwrite 默认值 True**，
  若 ProjectName 与已有草稿同名会删除该草稿。改名前先 `draft_inspector.py list` 核对。
- **Draft Inspector**: Examine draft structure and metadata (v5.9+ support):
  ```bash
  python <SKILL_ROOT>/scripts/draft_inspector.py list --limit 20
  python <SKILL_ROOT>/scripts/draft_inspector.py summary --name "DraftName"
  ```
- **Auto Exporter**: Headless export of a draft to MP4:
  ```bash
  python <SKILL_ROOT>/scripts/auto_exporter.py "DraftName" "output.mp4" --res 1080 --fps 60
  ```
  Note: MP4 auto export uses Windows UI Automation. On macOS, generate the draft and export it manually from JianYing.
  SRT 导出没有独立 CLI；请在自己的脚本里调用导出/字幕接口。
- **Template Clone**: 🚧 **尚未实现**。`JyProject.from_template()` 与
  `jy_wrapper.py clone` 均不存在于代码库中（`jy_wrapper.py` 只有 70 行、无 argparse、无 CLI 入口）。
  需要复用模板时，请手工复制草稿文件夹后修改，或直接用 `JyProject` 重新搭建。
- **API Validator**: Run a quick diagnostic of your environment:
  ```bash
  python <SKILL_ROOT>/scripts/api_validator.py
  ```

## 🚀 快速开始示例

```python
import os
import sys

# 1. 环境初始化 (必须同步到脚本开头，支持 Win/Mac)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_root = os.getenv("JY_SKILL_ROOT", "").strip()
# 探测 Skill 路径 (支持 Antigravity, Trae, Claude 等)
skill_root = next((p for p in [
    env_root,
    os.path.join(current_dir, ".agents", "skills", "jianying-editor"),
    os.path.join(current_dir, ".agent", "skills", "jianying-editor"),
    os.path.join(current_dir, ".trae", "skills", "jianying-editor"),
    os.path.join(current_dir, ".claude", "skills", "jianying-editor"),
    os.path.join(current_dir, "skills", "jianying-editor"),
    os.path.abspath(".agents/skills/jianying-editor"),
    os.path.abspath(".agent/skills/jianying-editor"),
    os.path.abspath(".trae/skills/jianying-editor"),
    os.path.abspath(".claude/skills/jianying-editor"),
    os.path.abspath("skills/jianying-editor"),
    os.path.dirname(current_dir)
] if p and os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py"))), None)

if not skill_root: raise ImportError("Could not find jianying-editor skill root.")
sys.path.insert(0, os.path.join(skill_root, "scripts"))
from jy_wrapper import JyProject

if __name__ == "__main__":
    # 2. 初始化工程 (支持 v5.9+ 及自修复)
    project = JyProject("New AI Video", overwrite=True)
    assets_dir = os.path.join(skill_root, "assets")

    # 3. 智能配音与字幕 (One-click Script-to-Video)
    project.add_narrated_subtitles(
        text="欢迎使用剪映自动化 Skill。这是一个全面适配 MacOS 的进阶版本。",
        speaker="zh_female_xiaopengyou"
    )

    # 4. 导入额外素材
    project.add_media_safe(os.path.join(assets_dir, "video.mp4"), "0s")
    project.add_media_safe(os.path.join(assets_dir, "audio.mp3"), "0s", track_name="Audio")

    # 5. 添加带动画的标题
    project.add_text_simple("剪映自动化开启", start_time="1s", duration="3s", anim_in="复古打字机")

    project.save()
```

## 🛠️ 初始化与项目规范 (Initialization & Project Rules)

在初始化 `JyProject` 时，请务必根据主视频素材的比例设置分辨率。**默认值为横屏 (1920x1080)**。

### 🚨 脚本存放位置规范
**禁止在 Skill 安装目录下创建你的业务剪辑脚本**。
- **正确做法**：将你的剪辑 Python 脚本放在项目的根目录。
- **原因**：Skill 目录应该只包含工具集源码，便于后续 `git pull` 升级。业务代码混入会导致版本管理混乱。
