---
name: jianying-editor-hd-fancam
description: 「高清直拍」固定栏目专用剪辑流程——把一批直拍/饭拍素材套成统一的成片规格（4K 竖屏 9:16 / 100 Mbps、固定滤镜与调节、竖排字幕与 HuHu 文字蒙版），批量产出风格一致的视频。当用户说「高清直拍」「直拍成片」「做直拍」「批量出直拍」「套直拍模板」，或要按他固定发的那类视频规格出片时使用。通用的旅游混剪、多素材整合、没有固定栏目要求的剪辑请用 jianying-editor。底层沿用 JianYing Editor Skill 的 JyWrapper API 与全部实测规则。
---

# JianYing Editor · 高清直拍专用版

Use this skill when the user wants to produce his fixed-format "高清直拍" videos. For general-purpose editing (travel clips, mixed media, one-off edits), use the sibling skill `jianying-editor` instead.

## 🎬 高清直拍：固定规格 + 完整工作流（2026-11-25 用户口述）

这一节是本 skill 独有的栏目规格与操作流程，**通用版没有**。每次出片都按这里对齐，不要每次重问。

### 成片规格
- 画布：**4K 竖屏 9:16 = 2160×3840**（不是 1080×1920；4K 素材按 `rules/media.md` 的旋转/缩放规则适配，不要靠裁剪）
- 素材：EOS R7 4K60p、`RF 100-400`/`200-800` 长焦直拍
- 导出：**H.264 / 4K60p / VBR 100 Mbps**（原来 80 Mbps 作废）
- 文件名：**`高清直拍_<主题或明星>_<YYYYMMDDHHmm>.mp4`**（时间戳取实际导出那一刻）
- ⚠️ 画布必须在 `JyProject(...)` 显式传宽高，否则会被首个素材覆盖（见下方 CRITICAL 规则 5）

### ⚠️ 这个 skill 在哪一步用（人机分工，先读这条）

**本质**：本 skill 是**剪映草稿生成器**——把"能用代码写进草稿 JSON 的参数化操作"提前搭好，生成草稿文件；**不是**能自动操作剪映全部 UI 的机器人。剪映的 GPU 实时特效、AI 识别、以及 AE 环节，代码一律调不动，必须人工。

图例：【🤖 skill】= 生成草稿自动完成　【👤 人工】= 你在剪映 / AE 里手动做

### ⚠️ 文档提到但代码里不存在的脚本（2026-11-27 核实，照抄会报错）

以下脚本在 SKILL.md / rules / docs 里被引用，但 `scripts/` 目录下**没有对应文件**。看到名字不要直接 import，先 `ls scripts/` 确认。

| 脚本 | 文档声称的作用 | 现状 | 现在该用什么 |
|---|---|---|---|
| `jy_sidecar.py` | 侧车生成 + key_value 登记 | 不存在 | 未实现，需按 `rules/draft_storage.md` 手写 |
| `jy_material_port.py` | 素材搬运 | 不存在 | 用 `core/media_ops.py` 的 `add_media_safe` |
| `asset_search.py` | 素材搜索 | 不存在 | 直接查 `data/*.csv` |
| `auto_exporter.py` | 无头自动导出 | 不存在 | 剪映 11.x 无 UIA 树，只能人工或模拟点击 |
| `api_validator.py` | 接口校验 | 不存在 | 用 `scripts/draft_inspector.py` |
| `beat_detect.py` | 卡点检测 | 不存在 | 未实现 |

**主线缺口**：`jy_sidecar.py`（滤镜不渲染的根因就在这）和 `auto_exporter.py`（批量导出的最后一步）是 L3/L4 的必需件，做批量前必须先补这两个。

**第一段 · 剪映粗剪（产出给 AE 的中间片）**
1. 【🤖】导入 R7 4K60p 素材，画布设 9:16
2. 【👤】识别歌词（剪映 AI 实时字幕，skill 调不动）
3. 【👤】选出需要的片段（创意判断）
4. 【👤】开美颜美体，预设 **zzm1**（实时特效，skill 调不动）
5. 【👤 或 🤖】导出该片段、**隐藏字幕** ← 给 AE 的中间片；用户通常自己导

**第二段 · AE（skill 完全不介入）**
6. 【👤】AE 里用**变形稳定器（Warp Stabilizer）**渲染导出，得到稳定中间片
   - **交接方式**：AE 稳定片 mp4 与歌词 SRT 放同一个文件夹，只给这一个文件夹路径（详见下方专节）
   - skill 不做稳定器、不控制 AE，也不假装能做

**第三段 · 剪映精修（🤖 主战场）**
7. 【🤖】把 AE 稳定片导入草稿
8. 【👤】防抖「裁切最少」——**已定稿（2026-11-27 用户确认，以此为准）**：稳定主要靠第二段的 AE 变形稳定器（Warp Stabilizer）；剪映这一步只开防抖「**裁切最少**」做轻量收尾。剪映防抖是实时处理，草稿层写不进去，必须人工。原 `stable_level = 3` 作废，不要再写。
9. 【🤖】滤镜：**高清增强 80**
10. 【👤】调节：锐化 **50** 由 skill 写死，其余参数用户自己调
11. 【👤】关键帧微调画面大小与位置（细微调整，用户手动）
12. 字幕（⚠️ 有前置依赖，见下方专节）：
    - 【👤/🤖】**先要有歌词内容**——skill 不会识别歌词，必须在剪映用【歌词识别】拿到文本，导出 SRT 交给 skill `import_srt`
    - 【🤖】套样式：放**左上、留安全边距（不贴边）**；动画「渐显」入场 +「渐隐」出场；**阴影** 黑色 / 不透明度 40 / 模糊度 4 / 距离 2 / 角度 -45
    - 【👤】**竖排**：**已定稿（2026-11-27 用户确认）**——底层 `add_text_simple` 没有竖排方向参数，竖排一律在剪映手动改，skill 不尝试写、也不要假装能写
13. 【👤 + 🤖】音频：声音分离（剪映 AI）人工做；音量 人声 **+3.0** / 背景音乐 **-1.0** 由 skill 写
14. 【🤖】复制视频轨，紧贴原轨上方 → 创建复合片段 → 特效【模糊 20】
15. 【🤖】文字蒙版：文字 **HuHu**，字体 **ZY INNOCENT**，不加粗 / 无下划线 / 斜体，字号 **23**，位置 **x 0 / y -2534**；蒙版阴影 不透明度 **40** / 模糊度 **3** / 距离 **1** / 角度 **-45**（⚠️ 与第 12 步字幕阴影是两套不同参数，别混）
16. 【👤】导出：**4K60p / VBR 100 Mbps**，用户自己导

### ⚠️ 字幕的前置依赖：歌词识别必须在 skill 之前

skill **不会识别歌词**（全项目无 ASR/歌词识别能力），它只能拿现成字幕文本套样式。所以字幕这一步的正确顺序是：

1. 【👤】在剪映第一段用【歌词识别】拿到歌词 → 导出 SRT 文件
2. 【🤖】skill 用 `project.script.import_srt(path, track_name="Subtitles")` 把 SRT 导进草稿 → 再加渐显/渐隐动画、阴影、位置
   - ⚠️ **2026-11-27 修正**：`import_srt` 只定义在 `pyJianYingDraft.ScriptFile` 上，`JyProject` 和四个 Mixin 都没有转发。写成 `project.import_srt(...)` 会抛 `AttributeError`，必须走 `project.script.import_srt(...)`
3. 【👤】竖排在剪映手动改（代码层不支持，已确认，不要尝试）

⚠️ 时间轴对齐：第一段识别的歌词时间戳基于**原始片段**，AE 稳定后视频时长通常不变，SRT 可直接用；若 AE 改了时长需重新对齐。

**交接目录约定（用户只需给一个路径）**：
- AE 导出的稳定片 `.mp4` 和剪映导出的歌词 `.srt` 放同一个文件夹
- 推荐同名，例如 `huhu_stable.mp4` + `huhu_stable.srt`（靠扩展名区分即可）
- 只需告诉我这个文件夹路径，我自动识别这两个文件，不用分别给路径
- 默认交接目录：`C:\Users\你的用户名\WorkBuddy\spaces\2026_11_25_08-23-45\handoff`

**一句话总结用法**：你做完粗剪（含歌词识别导出 SRT）和 AE，把「稳定片 mp4 + 歌词 SRT」放进同一个文件夹，只把文件夹路径丢给 skill → skill 生成搭好滤镜/调节/字幕样式/模糊/HuHu 蒙版的草稿 → 你在剪映打开草稿，开防抖「裁切最少」、补竖排字幕、做声音分离和动态调参 → 自己导出。无片头片尾、无额外 BGM、无卡点，原汁原味一段视频。

### ⚠️ SVIP 依赖（用户已开通剪映 SVIP）

歌词识别、字幕导出、美颜美体预设 zzm1、声音分离、高清增强滤镜、ZY INNOCENT 字体等在剪映里可能需要会员权限——用户已开 SVIP，保持登录的是 SVIP 账号即可；若会员过期这些人工步骤会失效，skill 无法绕过，遇到权限提示以剪映实际界面为准。

### 固定参数速查（实测 ID，直接用，不要猜）
- 滤镜「高清增强」：`resource_id = 7426668776491453707`，80% → `value = 0.8`
- 调节（锐化等）：挂在 `type="mixed"` 轨，10 参数共用 `resource_id = 7416258989467374091`
- 顺序陷阱：`materials.effects` 是共享键，**先写调节、后写滤镜**，否则滤镜轨空
- 字幕字体「阳煦体」`font_resource_id = 7290457267030200869`：主字幕改竖排 + 阴影，此 ID 仅作备用；蒙版文字用 ZY INNOCENT

用户说「再调整直拍规格」时，只改本节，不要动下面的 CRITICAL 实测规则。

---

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
    - 工具实现：用户项目 `scripts/jy_sidecar.py`。

0c. **素材字段要补 + 必须校验零悬空**
    - pyJianYingDraft 写出的视频素材缺 `stable`（**防抖在这里**）、`matting`、
      `video_mask_shadow`、`video_mask_stroke`、`extra_type_option`。
    - **防抖【推荐】= 视频素材的 `stable.stable_level: 3`**（实测真实草稿值，不是 0/1/2）。
    - **悬空引用**：文字段的 `extra_material_refs` 指向的 animation 素材没进 `materials`，
      100% 悬空 → 补一个 `{"id": <ref>, "type": "sticker_animation", "animations": []}` 空壳。
    - **`materials.effects` 被调节参数和滤镜素材共用** → 后写覆盖先写。
      顺序必须是**先调节、后滤镜**，否则 `material_id` 悬空、滤镜轨空。
    - 工具实现：用户项目 `scripts/jy_material_port.py`。

1.  **脚本位置**：**禁止在 Skill 内部目录创建剪辑脚本**。所有的剪辑逻辑实现代码（`.py` 脚本）必须存放在用户当前项目的**根目录**（或子目录，如 `scripts/`），以保持 Skill 库的纯净和可移植性。
2.  **版本与架构**：
    - **双平台适配**：已全面支持 MacOS (路径探测/录屏) 与 Windows。
    - **Auto-healing**：支持 v5.9+ (`draft_info.json`)。若草稿损坏或版本冲突，使用 `overwrite=True` 初始化 `JyProject` 可触发自动修复。
3.  **配乐**：高清直拍固定栏目**无 BGM、无卡点、无片头片尾**，原汁原味一段视频。云端音乐库已从本专用版移除，不要再检索或推荐 BGM。音频只做：复制一份 → 声音分离 → 人声 +3.0 / 背景音乐 -1.0（分离动作在剪映人工做）。
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
    - **`add_media_safe` 依赖系统 `ffprobe`**（用于 `media_normalizer`）。**本机 2026-11-27 已补齐**
      `E:\Program Files\ffmpeg\bin\ffprobe.exe`（9.1-essentials）。代码本身也做了安全跳过：探测失败返回 `{}`
      而不是抛异常，所以就算 PATH 里没有也不会崩。
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

## 规则指南（高清直拍专用版，已精简）

本专用版只保留高清直拍需要的规则与工具，通用版功能（录屏、影视解说、TTS、云端素材、花字、自动导出）已全部移除，需要时用通用版 jianying-editor。

- rules/setup.md — 初始化路径（指向本专用版）
- rules/core.md — 草稿创建与保存
- rules/media.md — 素材导入 / 旋转适配 9:16
- rules/text.md — 字幕：SRT 导入 + 渐显渐隐 + 阴影
- rules/keyframes.md — 关键帧微调画面大小位置
- rules/effects.md — 滤镜 / 调节 / 模糊特效
- rules/draft_storage.md — 草稿结构与侧车文件
- rules/cli.md — CLI 约定

## 保留的脚本

- scripts/jy_wrapper.py — 核心封装（JyProject）
- scripts/draft_inspector.py — 草稿检查
- scripts/core/、scripts/utils/、scripts/vendor/ — 底层依赖

## 已移除（请用通用版 jianying-editor）

录屏 / 智能变焦 / 网页动效 / 影视解说 / TTS 配音 / 云端音乐素材库 / 花字 / 自动导出 / 全部 examples / prompts。
注意：core/text_ops.py 的 add_narrated_subtitles、core/vfx_ops.py 的网页录制入口仍留有 import，但依赖脚本已删，调用会报 ImportError——本专用版不要用这两个功能。

## 字幕前置依赖（再强调）

本 skill 无歌词识别能力。字幕内容必须先由你在剪映【歌词识别】导出 SRT，再用 import_srt 导入套样式。详见上方专节。
