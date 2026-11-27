---
name: media
description: Rules for importing video, audio, and image assets.
metadata:
  tags: media, video, audio, image, import
---

# Media Import

Use `project.add_media_safe()` to import assets. This method automatically detects asset type (Video/Image/Audio).

## API Signature

```python
def add_media_safe(self, file_path, start_time=None, duration=None, track_name=None):
    """
    Args:
        file_path (str): Absolute path to the asset file.
        start_time (str, optional): Timeline position (e.g., "0s"). 
                                   If None, appends to the end of the track (Smart Append).
        duration (str, optional): Duration override (recommended: "5s").
        track_name (str, optional): Logical name of the track.
    
    Returns:
        SegmentObject: The created segment instance.
    """
```

## Rules & Best Practices

1.  **Absolute Paths**: ALWAYS use absolute paths for `file_path`.
2.  **Audio**: You can also use `project.add_audio_safe(...)` which is an alias specifically for audio, ensuring it goes to an audio track.
3.  **Track Names**: Providing a `track_name` (e.g. "OverlapTrack") helps forcing media onto specific or new tracks, useful for Picture-in-Picture (PIP).
4.  **Return Value**: Capture the return value if you plan to add animations (Keyframes) to this clip.
5.  **WEBM Import**: `add_media_safe(...)` automatically normalizes `.webm` to JianYing-friendly MP4 before import. Do not add manual conversion steps unless explicitly required.

## 旋转元数据素材（2026-09-30 实测，手机竖拍 MOV 必读）

手机竖拍文件常见形态：编码 3840x2160（或 1920x1080）+ 容器级 `rotation=90/270` 元数据。
**剪映导入时会自动归一化**（从用户今晚亲建草稿的明文 `Timelines/<uuid>/template.json` 实测）：

- 素材 `width/height` 写**显示尺寸**（如 1080x1920），不是编码尺寸；
- 片段 `clip.rotation = 0`、`scale = 1`——**不要再手动旋转**；
- 画布与显示比例一致（如 2160x3840）时 `scale=1.0`（contain 基准）恰好满屏、零黑边。

脚本做法：`mat = VideoMaterial(path)` 后把 `mat.width/height` 覆写为显示尺寸
（导出后再按 path 兜底补一遍），片段用默认 `ClipSettings(scale_x=1, scale_y=1, rotation=0)`。
判断显示尺寸：pymediainfo 的 `video_track.rotation` ≠ 0 时，宽高互换。

## 视频原声（无需单独音频轨）

视频素材 `has_audio=1` 时，**声音跟随视频片段本身**（片段 `volume` 即原声音量），
不需要、也不应该再为它建 audio 素材/片段。用户亲建草稿实测：video 轨 1 段 +
audio 轨只有外挂 BGM，无对应视频的音频素材。

## 指定草稿根目录

`JyProject(name, width, height, drafts_root=r"E:/JianyingPro Drafts", overwrite=False)`
——用户可能改过草稿位置，写错根目录剪映首页看不到。判定方法见 `rules/draft_storage.md`。

## BGM 实用要点

- 云端曲库下载：`CloudManager().download_asset(id)`，首次 403 时**重试即可成功**
  （实测 7378224057998886938）。下载缓存目录 `~/cloud_cache/`。
- 建议把音频文件**复制进 `<draft>/materials/audio/`**，避免缓存清理后「媒体丢失」。
- **⚠️ 素材 path 一律写绝对路径**（正斜杠 `E:/...` 即可）。实测：脚本草稿中视频素材
  全用绝对路径全部正常加载，唯一用相对路径的音频被弹「链接媒体：媒体丢失」。
  （剪映自建草稿的相对路径能用是它有内部解析机制，脚本写的没有。）
- **⚠️⚠️ 剪映开着草稿时绝对不要改它的 JSON**：关闭草稿时会用内存状态覆盖落盘
  （实测 2026-09-30：改完文件用户关闭剪映，修改被覆盖、且 draft_content.json 被加密）。
  要改文件必须先确认剪映进程已退出（`tasklist` 查 JianyingPro.exe）。
- **⚠️ 草稿被剪映打开保存过一次后，draft_content.json 即加密、脚本路线终结**
  （备份在 `<draft>/.backup/*.close.bak`，同样加密）。此时只能：① 用户在剪映
  「链接媒体」弹窗里手动重链；② 换名字重建草稿（流水线重跑，秒级）。
- 音频素材字段对齐剪映原生本地音频：`check_flag=1`、`music_id=""`、
  `local_material_id=""`（pyJianYingDraft 默认生成的 check_flag=3/music_id=id 有风险）。
- 片段级淡出：pyJianYingDraft 无 fade API，导出后补
  `seg["fade"] = {"id":"","fade_in_duration":0,"fade_out_duration":1500000,"fade_type":0}`。
- 卡点切点：用 `scripts/beat_detect.py`（numpy 谱通量，无需 librosa）取重音时间。

## AI 视频分析优化 (AI Analysis Optimization)

在进行 AI 视频理解或分析（如 Gemini 视频模型）前，请遵循以下建议以提高效率和模型理解力：
- **最大时长**: 建议控制在 **30 分钟** 以内。
- **目标分辨率**: 建议压缩至 **360p**。这是 AI 理解的最佳平衡点（文件小且关键信息保留完整）。
- **预处理**: 若原始视频体积过大，必须先进行 **压缩** 后再传给 AI 分析，以避免上传超时或模型截断。

## 分辨率与比例 (Resolution & Ratio)

为了保证剪辑效果，**项目分辨率必须与主素材比例一致**：
- **横屏 (16:9)**: 创建项目时使用默认参数或显式指定 `width=1920, height=1080`。
- **竖屏 (9:16)**: 如果主视频是竖屏，创建项目时 **必须** 指定 `width=2160, height=3840`（4K 竖屏；1080x1920 是错的，用户成片固定 4K）。
  ```python
  # 创建竖屏项目示例
  project = JyProject("竖屏短视频项目", width=2160, height=3840)
  ```
- **自动检测**: 建议在创建项目前，先用脚本或 AI 判断视频的原始比例，确保输出不带有黑边。
- **素材比例 ≠ 画布比例时，不要靠裁剪，要旋转**（已实测）：
  `clip.scale` 的基准是 **contain**（`scale=1.0` 渲染尺寸 = `(sw·k, sh·k)`，`k = min(cw/sw, ch/sh)`），
  不是素材原始像素。横屏 16:9 素材进 9:16 画布时，`rotation = -90` + `scale = 16/9 ≈ 1.7778`
  可做到零裁剪、零黑边、源像素 1:1 落到画布。
  完整公式、验证依据与写入示例见 `SKILL.md` 的 CRITICAL 规则 6。


## Examples

```python
# Import main video
video_seg = project.add_media_safe(os.path.expanduser("~/assets/video.mp4"), start_time="0s")

# Import BGM (Audio)
project.add_audio_safe(os.path.expanduser("~/assets/bgm.mp3"), start_time="0s", track_name="BGM")

# Import Cloud Asset (NEW)
# Automatically searches, downloads, and imports from the cloud database
project.add_cloud_media("海绵宝宝", start_time="5s", duration="2s")
project.add_cloud_media("7322042077603302666", start_time="10s")

# Import PIP (Picture in Picture)
pip_seg = project.add_media_safe(os.path.expanduser("~/assets/facecam.mp4"), start_time="5s", track_name="PipLayer")
```
