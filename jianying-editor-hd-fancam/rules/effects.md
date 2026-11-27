---
name: effects
description: 滤镜、调节、特效在剪映草稿中的挂载方式、资源查找与数值映射（均已在本机实测）。
metadata:
  tags: effects, filters, transitions, filter, adjust, sharpen, 滤镜, 调节
---

# 滤镜 / 调节 / 特效

## 0. 先查 ID：`asset_search.py`

```bash
python <SKILL_ROOT>/scripts/asset_search.py "高清增强" -c filters
python <SKILL_ROOT>/scripts/asset_search.py --list          # 列出可用分类
python <SKILL_ROOT>/scripts/asset_search.py "故障" -c video_scene_effects --json
```

`-c` 可用：`filters`（滤镜）、`video_scene_effects`（画面特效）、
`video_character_effects`（人物特效）、`transitions`（转场）、`text_animations`（文字动画）。
实测：`高清增强` → 分类 Filters，可用。

更省事的办法：滤镜 ID 在库内已有枚举 `pyJianYingDraft.metadata.FilterType`，
例如 `FilterType.高清增强`，可直接传给 `FilterSegment`。
**不要凭记忆猜 ID。**

## 1. 滤镜（如「高清增强」）

素材进 `materials.effects`，`type = "filter"`；挂在 **`type = "filter"` 的独立轨道**上，
由 `segment.material_id` 引用 —— **是 `material_id`，不是 `extra_material_refs`。**

```json
{
  "category_id": "100000",
  "effect_id": "7426668776491453707",
  "id": "<UUID>",
  "name": "高清增强",
  "path": ".../User Data/Cache/artistEffect/7426668776491453707/c28d7683eb3bbc58cd3b008b380ed551",
  "resource_id": "7426668776491453707",
  "source_platform": 1,
  "sub_type": "none",
  "third_resource_id": "0",
  "type": "filter",
  "value": 0.8,
  "multi_language_current": "",
  "color_match_info": {},
  "beauty_face_auto_retouch_info": {}
}
```

轨道与片段：

```json
{"id": "<TRACK_UUID>", "type": "filter", "is_default_name": true, "flag": 0,
 "attribute": 0, "name": "",
 "segments": [{
   "track_render_index": 1, "responsive_layout": {}, "render_timerange": {},
   "id": "<SEG_UUID>", "enable_adjust_mask": false, "enable_adjust": false,
   "material_id": "<滤镜素材的 id>", "enable_hsl": false,
   "source": "segmentsourcenormal",
   "target_timerange": {"start": 0, "duration": <总时长 us>},
   "enable_lut": false, "render_index": 10000, "visible": true
 }]}
```

- `value` = 强度，**0~1**（UI 百分比 ÷ 100），默认 1.0。**80% → 0.8**。
- 实测本机草稿里该滤镜的 value 分布：`1.0 / 0.87 / 0.82 / 0.76 / 0.52 …`，确认为百分比。

## 2. 调节（调色，如「锐化」）

挂在 **`type = "mixed"` 的独立轨道**上（⚠️ **2026-11-27 实测确认**：本机 4 个明文草稿的调节轨 `type` 一律是 `mixed`，`adjust` 是错的，别写）。片段 `material_id` 指向一条
`materials.placeholders` 记录，各参数经 `extra_material_refs` 逐个引用
`materials.effects`，另有一条 `materials.hsl`。

参数清单（本机实测，缺省全为 0）：

```
brightness, sharpen, highlight, shadow, white, clear,
temperature, tone, light_sensation, vignetting
```

- 每个参数一条 effect 记录，共用 `resource_id = "7416258989467374091"`（调节资源包）
  与同一 `path`，靠 `type` 区分、靠 `value` 取 0~1。
- **锐化 50 → `value = 0.5`**；实测样本 `sharpen = 0.0531` 对应 UI 约 5。
- `placeholders` 记录：`{"id": "<UUID>", "type": "adjust", "name": "调整1", "material_resource_id": ""}`。
  - ⚠️ 2026-11-27 实测：剪映 11.x 明文草稿里 `placeholders` 是**空数组**，调节素材实际落在 `materials.videos` 里（带 `enable_adjust` / `enable_color_curves` 等 flag）。上面的 placeholders 写法属旧版结构，11.x 需按 videos 结构处理，写之前先用 `draft_inspector.py show` 看真实草稿。
- 实测真草稿里 `materials.hsl[].constant_material_id` 是悬空引用，可省略。

## 3. 资源不必预下载，但**必须登记进 `key_value.json`**

草稿引用的滤镜/调节资源**可能不在本地 Cache**，剪映按 `resource_id` 按需拉取，
不要因缓存缺失就判定滤镜不可用。

但**光有素材是不够的** —— 剪映加载滤镜轨时会去 `key_value.json` 查注册项，
查不到就判定「资源未就绪」而不渲染（表现：滤镜轨显示为空）。
必须同时写两条记录（资源级用 `resource_id` 作键、片段级用 `segment_id` 作键），
字段清单见 `rules/draft_storage.md` 的「侧车文件」一节。

**这是「滤镜是空的」的真实根因**（此前误判为素材缺字段，走了弯路）。

## 4. 滤镜素材字段要与真实草稿一致

pyJianYingDraft 写出的滤镜素材只有 15 个键，真实草稿有 14 个关键键。
最稳的做法：从用户历史明文草稿里**整条搬用**素材（含已落地的 `path`），
而不是自己拼字段。工具实现见项目脚本 `scripts/jy_material_port.py`。

## 5. 写入前的硬性检查

1. 确认草稿目录**无 `.locked`**（剪映正打开时，你的写入会被覆盖）。
2. 先复制一份 `.bak`。
3. **同时改写根目录与 `Timelines/<uuid>/` 下的 `draft_info.json`**，两边保持一致。
4. 脚本要**幂等**：用固定 UUID（如 `uuid5`）生成 id，重跑时先按 id 清理旧记录再插入。
5. 写回后回读校验，打印最终轨道结构与关键数值。
6. **校验零悬空**：`material_id` 与 `extra_material_refs` 都要能在 `materials` 里解析到。

## 6. ⚠️ `draft_content.json` 是加密的 → **优先新建草稿，不要原地改**

剪映 11.5 打开草稿后会额外生成一份**加密的 `draft_content.json`**（首字节非 `{`），
**无法编辑**，且**存在加密件时明文 `draft_info.json` 会被忽略**（已实测：写入滤镜轨后
剪映加载仍显示为空）。

因此正确路线是**新建草稿**（剪映尚未打开过，只有明文），而不是原地改已有草稿。
完整落盘顺序见 `rules/draft_storage.md`。

## 7. 防抖（视频防抖 / Stabilization）

**字段已确认**，位置是**视频素材**上的 `stable`（不是片段上的 `video_algorithm`）：

```json
"stable": {"stable_level": 3, "time_range": {}}
```

实测用户真实草稿（`7月13日` / `BS9A9273.MP4`）里，「推荐」档写的是 **`stable_level: 3`**。
（此前的「本机无样本、不要猜」结论已作废。）

同时要给视频素材补 `matting` / `video_mask_shadow` / `video_mask_stroke` /
`extra_type_option`，字段形态见 `rules/draft_storage.md`。

若确实要操作 `video_algorithm.algorithms`，实测出现过
`Deflicker / QualityEnhance / ComplementFrame / MotionBlur` 四种。

## 8. 调节轨与滤镜素材**共用 `materials.effects` 这一个键**

这是最容易踩的坑：调节的 10 个参数写在 `materials.effects` 里，
滤镜素材也写在 `materials.effects` 里。**后写的一方会覆盖前者**。

落盘顺序必须是：**先写调节参数，再重建滤镜素材并重指滤镜段的 `material_id`**。
反过来的话滤镜素材会被调节参数挤掉，`material_id` 悬空 → 滤镜轨空。
