# 剪映 11.x 草稿存储格式（实测结论，必读）

**适用版本**：本机为剪映专业版 11.5.0.14471（早期版本为 10.8.7，格式不同）。

## CRITICAL：11.x 把草稿内容整体加密，明文改写路线失效

### 实测证据

| 文件 | 实际形态 |
|---|---|
| `draft_content.json` | **加密**：base64 文本，解出后熵 7.998 bit/byte，无 ECB 重复块（非纯 ECB） |
| `draft_meta_info.json` | 加密（同族） |
| `draft.extra` | 加密（base64 单串） |
| `deepagent/deepagent.db` | 加密（非 SQLite，无可用字符串） |
| `Timelines/<uuid>/draft_content.json` | 加密（与根目录同名文件同尺寸，内容为权威副本） |
| `draft_info.json` | **明文**，但只是旧格式遗留 |
| `Timelines/<uuid>/template.json` | **明文全量时间线**（仅部分草稿存在，见下） |

**判别方法**（不要再用 `json.load` 盲试）：

```python
head = open(path, 'rb').read(1)
kind = '明文JSON' if head == b'{' else '编码/加密'
```

全库统计（本机 245 个 `draft_content.json`）：**215 个加密、29 个明文**；
明文的全部是 2026-08-20 之前的老草稿。凡是 11.x 打开并保存过的草稿，一律变成加密。

> **2026-09-30 晚更新**：库内 109 个草稿的**根目录 `draft_info.json` 已全部消失**
> （109/109 无此文件），且 107 个根 `draft_content.json` 全部为加密——旧明文草稿
> 已被陆续升级完毕。**明文素材样本池只剩 `Timelines/<uuid>/template.json`**
> （每草稿 ≤1 份，全库约 160 份，含完整 materials 结构，可作滤镜/字幕样本源）。
> `jy_material_port.harvest_style_pool()` 只扫根目录 `draft_info.json`，现在必然返回
> 空池——素材 path 请改用 `find_local_effect_path(resource_id)` 直查
> `User Data/Cache/artistEffect/` 本地缓存。

### 草稿根目录可能不是默认位置（2026-09-30 实测）

用户可把草稿根目录改到任意盘（本机现为 `E:/JianyingPro Drafts`，AppData 旧根仍有 107 个历史草稿）。
**判定当前根目录**：读 `<AppData草稿根>/root_meta_info.json`（明文）→
`all_draft_store[].draft_fold_path`，取 `tm_draft_create` 最新的几条看其父目录；
今天新建的草稿落在哪个根，脚本就该往哪个根写（`JyProject(..., drafts_root=...)` 支持指定）。
新建草稿只需放进该根目录（无需登记 registry），剪映首页即可看到。

### 已证实的后果

- **写 `draft_info.json` 不会被采纳**。实测：16:10 把滤镜轨/调节轨写入
  `draft_info.json`（根 + `Timelines/<uuid>/` 双份），16:16 剪映加载该草稿后，
  用户界面上滤镜轨为空 —— 说明存在加密的 `draft_content.json` 时，明文文件被忽略。
- 因此：**剪映打开过一次的草稿，此后无法用脚本读写**。只有「脚本新建、剪映尚未打开」
  的草稿可写（此时只有 `draft_info.json`，剪映会把它当旧格式读入并升级）。
- 首次打开会把内容升级进加密文件，**升级是一次性的、内容会保留**（实测旋转参数
  `rotation=-90 / scale=1.7778` 在升级后完整保留）。

### UI 自动化同样不可行

剪映主窗口类名为 `HomePage_QMLTYPE_199`（QML/Qt Quick）。用 `uiautomation`
枚举其后代元素，**探测 60 个节点全部为空**——整个界面没有暴露 UIA 树。
所以基于 `uiautomation` 的点击方案（如 `auto_exporter.py` 依赖的导出点击）在本版本
不可靠，不要依赖。

### 仍然可用的写入面

| 路径 | 说明 |
|---|---|
| 新建草稿 | 写 `draft_info.json` + 全套侧车文件，剪映首次打开时读入（一次性） |
| `User Data/Presets/Adjust/*.json` | **明文**，用户的「调节预设」。可写自定义预设供一键套用。写入前需先退出剪映，否则会被覆盖 |

---

## CRITICAL：新建草稿必须补齐「侧车文件」，否则资源不渲染

**这是「滤镜是空的」的根因**，此前误判为素材缺字段，实际是资源没登记。

pyJianYingDraft 只产出 `draft_info.json` + 一个空的 `key_value.json {}`，
但剪映加载草稿时还依赖一批侧车文件。缺了它们，草稿能打开、轨道也在，
**但滤镜/字体这类联网资源不渲染**。

### `key_value.json` —— 素材注册表（最重要）

剪映加载滤镜轨时，会拿两把钥匙去 `key_value.json` 查注册项：

| 索引键 | 对应字段 | 用途 |
|---|---|---|
| `resource_id`（如 `7426668776491453707`） | `materialCategory` / `is_vip` / `is_favorite` / `material_is_purchased` | 资源级：判断能否使用该资源 |
| `segment_id`（片段 id） | `materialId` / `segmentId` / `materialCategory` | 片段级：绑定该片段用了什么资源 |

**两把钥匙都要有**，缺任一条滤镜就不渲染。实测用户真实草稿里
「高清增强」正是同时存在这两条记录。

必填字段（滤镜，对照真实草稿实测值）：

```json
{
  "7426668776491453707": {
    "is_favorite": true, "is_vip": "1", "materialCategory": "filter",
    "materialId": "7426668776491453707", "materialName": "高清增强",
    "materialSubcategory": "filter", "materialThirdcategoryId": "100000",
    "material_is_purchased": "1", "rank": "0", "previewed": 0
  },
  "<segment_id>": {
    "is_vip": "1", "materialCategory": "filter",
    "materialId": "7426668776491453707", "materialName": "高清增强",
    "materialSubcategory": "filter", "materialThirdcategoryId": "100000",
    "material_is_purchased": "1", "segmentId": "<segment_id>", "role": ""
  }
}
```

### 其余侧车文件

| 文件 | 作用 | 缺失后果 |
|---|---|---|
| `draft_settings` | `[General]` 段：`draft_create_time` / `draft_last_edit_time` / `real_edit_keys` | `real_edit_*` 为 0 会被当成「从未编辑」，可能被清理 |
| `attachment_pc_common.json` | `recognize_tasks` 等识别任务落点 | 歌词/字幕识别入口缺失 |
| `attachment_editing.json` | `editing_draft.draft_id` | — |
| `draft_agency_config.json` | 导出分辨率 `video_resolution` | — |
| `timeline_layout.json` | 时间线布局 | — |
| `draft_virtual_store.json` | 素材池 | — |

工具实现见项目脚本 `scripts/jy_sidecar.py`（`register_key_value` / `write_sidecars`）。

---

## 素材字段：pyJianYingDraft 写出的是「最小集」，必须补字段

对照用户真实草稿（`7月13日` / `BS9A9273.MP4`）实测，pyJianYingDraft 的视频素材
缺以下剪映必读字段：

```json
{
  "stable":   {"stable_level": 3, "time_range": {}},
  "matting":  {"path": ""},
  "video_mask_shadow": {"path": "", "resource_id": ""},
  "video_mask_stroke": {"path": "", "resource_id": "", "type": ""},
  "extra_type_option": 1,
  "has_sound_separated": false,
  "beauty_face_auto_preset": {},
  "beauty_face_preset_infos": []
}
```

**`stable.stable_level` 就是「视频防抖」档位**：实测用户草稿里
「推荐」档写的是 `3`（不是 0/1/2）。要开防抖就把这个字段写成 3。

滤镜素材同理，pyJianYingDraft 写的只有 15 个键，真实草稿有 14 个关键键、
其中 `beauty_face_auto_retouch_info` / `third_resource_id` 是它没写的。
**最稳的做法是直接从用户历史明文草稿里整条搬用素材**（含已落地的 `path`），
工具实现见 `scripts/jy_material_port.py`。

---

## 悬空引用：pyJianYingDraft 给文字段留的 animation ref 没写进 materials

实测：文字段（`TextSegment`）的 `extra_material_refs` 里有一个指向
`material_animations` 的 id，但 `script.dumps()` 导出时**那个素材没有进
`materials`**，100% 悬空。剪映读到悬空引用会判定片段素材损坏，可能导致整段不渲染。

修法：为每个缺失的 ref 造一个空动画壳顶上去，这是剪映里「无动画」的合法表达：

```python
{"id": <dangling_ref>, "type": "sticker_animation", "animations": []}
```

同理，滤镜轨段的 `material_id` 也可能悬空 —— 因为调节参数和滤镜素材
**共用 `materials.effects` 这一个键**，后写的一方会覆盖前者。顺序必须是：
先写调节参数，再重建滤镜素材并重指 `material_id`。

---

## 新建草稿的完整落盘流程（推荐顺序）

1. `script = project.script`；建视频/滤镜/字幕轨
2. `content = json.loads(script.dumps())` —— 不要用 `project.save()`，库里没有导出后钩子
3. 写视频素材字段（含防抖 `stable_level=3`）
4. 补调节轨（`_patch_adjust_into`）
5. **重建滤镜素材并重指 `material_id`**（必须在调节之后，两者共用 `materials.effects`）
6. 用历史明文草稿的素材样本规范化（补 `path` 等）
7. 修悬空引用（补空动画壳）
8. 落盘 `draft_info.json`
9. 登记 `key_value.json`（资源级 + 片段级两把钥匙）
10. 写其余侧车文件

## 排查顺序（遇到「改了没生效」）

1. 看目标草稿目录有没有加密的 `draft_content.json` → 有则直接放弃文件改写路线
2. 检查草稿是否正被剪映打开（`.locked` 文件 / 目标文件 mtime 是否被应用刷新）
3. 确认改动后是否有剪映的 `Timelines/` 升级（`Timelines/<uuid>/` 出现即代表已被应用接管）
4. **轨道在但资源不生效 → 查 `key_value.json` 有没有登记（资源级 + 片段级）**
5. **片段不渲染 → 查 `material_id` / `extra_material_refs` 有没有悬空**
