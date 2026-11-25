---
name: text-subtitles
description: Rules for adding text and subtitles for the 高清直拍 workflow (SRT import, vertical layout, fade in/out, shadow).
metadata:
  tags: text, subtitles, captions, srt
---

# Text & Subtitles（高清直拍专用）

⚠️ 本专用版已移除花字功能（`add_styled_text` / `assets/artistEffect` / `cloud_text_styles.csv` 全删）。
高清直拍的字幕方案固定为：**竖排 + 左上安全区 + 渐显渐隐 + 阴影**，花字不用。

## 1. 导入歌词 SRT（主路径）

字幕内容来自剪映【歌词识别】导出的 SRT（本 skill 无 ASR，见 SKILL.md 字幕前置依赖）。

```python
project.import_srt(srt_path, track_name="Subtitles")
```

导入后再逐条套样式：动画「渐显」入场 +「渐隐」出场、阴影（黑 / 不透明度 40 / 模糊 4 / 距离 2 / 角度 -45）、左上安全区。
**竖排**：底层 `add_text_simple` 未见竖排方向参数，若无法用代码写则须在剪映手动改。

## 2. Plain Text（普通文字）

```python
project.add_text_simple(
    text="Hello World",
    start_time="0s",
    duration="3s",
    clip_settings=draft.ClipSettings(transform_y=-0.8),  # -1.0 底 / 0.0 中 / 1.0 顶
    font_size=12.0,
    color_rgb=(1, 1, 1),
    anim_in="渐显",
    anim_out="渐隐",
    shadow=...   # 阴影参数按 SKILL.md 的高清直拍规格
)
```

- **Duration** 必须显式给出。
- 动画枚举从 `data/text_animations.csv` 查。

## 3. Rich Text & Keyword Highlighting（富文本/高亮）

```python
project.add_rich_text(
    text="Wait for the 99% logic to complete.",
    highlights=[
        {"word": "99%", "color": (1, 0, 0), "bold": True, "size": 15.0},
        {"word": "logic", "italic": True}
    ],
    start_time="2s",
    duration="3s",
    font_size=12.0
)
```

## 4. Auto-Layering（防重叠）

同一逻辑轨上时间重叠的文字段，wrapper 会自动分层，不用手动算轨道。

## Data Context
- `data/text_animations.csv`: 文字入场/出场动画 ID 索引（渐显/渐隐在这里查）。
