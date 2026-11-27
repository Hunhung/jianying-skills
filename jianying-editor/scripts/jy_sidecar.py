"""
草稿「侧车文件」与素材字段的补齐（JianYing 11.5）。

背景（实测）
------------
pyJianYingDraft 只写 `draft_info.json` + 一个空 `key_value.json`，
但剪映真正加载草稿时还依赖一批**侧车文件**：

  key_value.json            ← 素材注册表。滤镜/字体等**必须先在这里登记**
                              （materialCategory / is_vip / is_favorite /
                               material_is_purchased / segmentId），
                              否则剪映认为该资源「没拿到」，滤镜轨直接显示为空。
                              这 —— 就是「滤镜是空的」的根因。
  draft_settings            ← [General] 段，edit 计数、平台标记
  attachment_pc_common.json ← recognize_tasks（歌词/字幕识别任务落点）
  attachment_editing.json   ← editing_draft
  draft_agency_config.json  ← 导出分辨率等
  timeline_layout.json      ← 时间线布局
  draft_virtual_store.json  ← 素材池

素材字段方面，pyJianYingDraft 写出的是最小集，缺 `stable`（防抖）、
`matting`、`extra_type_option` 等剪映内部必读字段。

本模块只处理明文面，任何一步失败都不影响主流程。
"""

import os
import json
import uuid

# ---------------------------------------------------------------------------
# 侧车文件：默认内容（结构取自用户真实明文草稿 7月13日）
# ---------------------------------------------------------------------------
ATTACHMENT_PC_COMMON = {
    "ai_packaging_infos": [],
    "ai_packaging_report_info": {
        "caption_id_list": [], "commercial_material": "", "material_source": "",
        "method": "", "page_from": "", "style": "", "task_id": "",
        "text_style": "", "tos_id": "", "video_category": "",
    },
    "broll": {
        "ai_packaging_infos": [],
        "ai_packaging_report_info": {
            "caption_id_list": [], "commercial_material": "", "material_source": "",
            "method": "", "page_from": "", "style": "", "task_id": "",
            "text_style": "", "tos_id": "", "video_category": "",
        },
    },
    "commercial_music_category_ids": [],
    "pc_feature_flag": 0,
    "recognize_tasks": [],
    "template_item_infos": [],
    "unlock_template_ids": [],
}

AGENCY_CONFIG = {
    "is_auto_agency_enabled": False,
    "is_auto_agency_popup": False,
    "is_single_agency_mode": False,
    "marterials": None,
    "use_converter": False,
    "video_resolution": 1080,
}

TIMELINE_LAYOUT = {
    "activeTimeline": "",
    "dockItems": [],
    "layoutOrientation": 1,
}

VIRTUAL_STORE = {"draft_materials": [], "draft_virtual_store": []}


def _w(path, obj, indent=0):
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, ensure_ascii=False, indent=indent)


def _w_text(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ---------------------------------------------------------------------------
# 素材注册表 key_value.json —— 「滤镜是空的」的正解
# ---------------------------------------------------------------------------

def register_key_value(draft_dir, entries):
    """把草稿里用到的资源登记进 key_value.json。

    entries: [{resource_id, name, category, third_category_id, is_vip, is_favorite,
               is_purchased, segment_id}]

    剪映加载滤镜轨时会用 segment.material_id 去 key_value 里查注册项，
    查不到就当成「资源未就绪」而不渲染。因此这条必须写。
    """
    p = os.path.join(draft_dir, "key_value.json")
    kv = {}
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                kv = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError):
            kv = {}

    added = []
    for e in entries:
        rid = str(e.get("resource_id") or "")
        if not rid:
            continue
        # ① 资源级登记（按 resource_id 索引）
        if rid not in kv:
            kv[rid] = {
                "douyin_music_is_avaliable": False,
                "is_favorite": bool(e.get("is_favorite", False)),
                "is_from_artist_shop": 0,
                "is_limited": False,
                "is_similar_music": False,
                "is_vip": str(e.get("is_vip", "0")),
                "materialCategory": e.get("category", ""),
                "materialId": rid,
                "materialName": e.get("name", ""),
                "materialSubcategory": e.get("category", ""),
                "materialSubcategoryId": "",
                "materialThirdcategory": "",
                "materialThirdcategoryId": str(e.get("third_category_id", "100000")),
                "material_copyright": "",
                "material_is_purchased": str(e.get("is_purchased", "0")),
                "music_source": "",
                "original_song_id": "",
                "original_song_name": "",
                "pgc_id": "",
                "pgc_name": "",
                "previewed": 0,
                "previewed_before_added": 0,
                "rank": "0",
                "rec_id": "",
                "requestId": "",
                "special_effect_loading_type": "",
                "textTemplateVersion": "",
            }
            added.append(f"资源 {e.get('name')}({rid})")

        # ② 片段级登记（按 segment_id 索引）—— 剪映按片段查
        sid = e.get("segment_id")
        if sid and sid not in kv:
            kv[sid] = {
                "filter_category": "",
                "filter_detail": "",
                "is_brand": 0,
                "is_from_artist_shop": 0,
                "is_vip": str(e.get("is_vip", "0")),
                "keywordSource": "",
                "materialCategory": e.get("category", ""),
                "materialId": rid,
                "materialName": e.get("name", ""),
                "materialSubcategory": e.get("category", ""),
                "materialSubcategoryId": "",
                "materialThirdcategory": "",
                "materialThirdcategoryId": str(e.get("third_category_id", "100000")),
                "material_copyright": "",
                "material_is_purchased": str(e.get("is_purchased", "0")),
                "rank": "0",
                "rec_id": "",
                "requestId": "",
                "role": "",
                "searchId": "",
                "searchKeyword": "",
                "segmentId": sid,
                "team_id": "",
                "textTemplateVersion": "",
            }
            added.append(f"片段 {sid[:8]}")

    _w(p, kv, indent=None)
    return added


def collect_registrations(content, extra=None):
    """扫描草稿内容，挑出需要登记进 key_value.json 的资源。"""
    regs = []
    mats = content.get("materials") or {}

    # --- 滤镜 ---
    filter_mats = {e.get("id"): e for e in (mats.get("effects") or [])
                   if isinstance(e, dict) and e.get("type") == "filter"}
    for t in content.get("tracks") or []:
        if t.get("type") != "filter":
            continue
        for s in t.get("segments") or []:
            m = filter_mats.get(s.get("material_id"))
            if not m:
                continue
            regs.append({
                "resource_id": m.get("resource_id") or m.get("effect_id"),
                "name": m.get("name", ""),
                "category": "filter",
                "third_category_id": "100000",
                "is_vip": "1",
                "is_favorite": True,
                "is_purchased": "1",
                "segment_id": s.get("id"),
            })

    # --- 字体 ---
    for tx in mats.get("texts") or []:
        if not isinstance(tx, dict):
            continue
        frid = tx.get("font_resource_id")
        if frid:
            regs.append({
                "resource_id": frid,
                "name": tx.get("font_title") or tx.get("font_name") or "",
                "category": "font",
                "third_category_id": "100000",
                "is_vip": "0",
                "is_favorite": True,
                "is_purchased": "1",
                "segment_id": None,
            })

    if extra:
        regs.extend(extra)
    return regs


# ---------------------------------------------------------------------------
# 悬空引用修复
# ---------------------------------------------------------------------------

def repair_dangling_refs(content, verbose=True):
    """把指向不存在素材的 extra_material_refs 换成「空动画」素材。

    pyJianYingDraft 给文字段写了一个 extra_material_refs 指向 material_animations，
    但导出时那个素材没进 materials（实测 100% 悬空）。剪映读到悬空引用会判定
    该片段素材损坏，可能整段不渲染 —— 必须修掉。

    做法：为每个缺失的 ref 造一个 `material_animations` 空壳（animations: []），
    这是剪映里「无动画」的合法表达，语义等于什么都不加。
    """
    mats = content.setdefault("materials", {})
    anims = mats.setdefault("material_animations", [])

    known = set()
    for v in mats.values():
        if isinstance(v, list):
            for it in v:
                if isinstance(it, dict) and it.get("id"):
                    known.add(it["id"])

    fixed = []
    for t in content.get("tracks") or []:
        for s in t.get("segments") or []:
            refs = s.get("extra_material_refs") or []
            if not refs:
                continue
            new_refs = []
            for r in refs:
                if r in known:
                    new_refs.append(r)
                    continue
                # 造一个空动画壳顶上，避免悬空
                anims.append({"id": r, "type": "sticker_animation", "animations": []})
                known.add(r)
                fixed.append((t.get("type"), r))
                new_refs.append(r)
            s["extra_material_refs"] = new_refs

    if verbose and fixed:
        for tt, r in fixed:
            print(f"      修复悬空引用 track={tt} {r[:12]}… -> 空动画")
    elif verbose:
        print("      无悬空引用")
    return fixed


def prune_empty_anims(content):
    """清理掉我们造出来的、但实际没被任何段引用的空动画壳。"""
    mats = content.get("materials") or {}
    used = set()
    for t in content.get("tracks") or []:
        for s in t.get("segments") or []:
            used.update(s.get("extra_material_refs") or [])
            if s.get("material_id"):
                used.add(s["material_id"])
    anims = mats.get("material_animations")
    if not isinstance(anims, list):
        return 0
    before = len(anims)
    mats["material_animations"] = [
        a for a in anims
        if not (isinstance(a, dict) and a.get("id") in used
                and a.get("type") == "sticker_animation" and not a.get("animations"))
    ]
    return before - len(mats["material_animations"])


# ---------------------------------------------------------------------------
# 素材字段补齐
# ---------------------------------------------------------------------------

def ensure_video_fields(content):
    """给视频素材补剪映必读字段，重点 `stable`（防抖）与 `matting`。

    字段形态与默认值全部实测自用户真实明文草稿（7月13日 / BS9A9273.MP4）：
        "stable":   {"stable_level": 3, "time_range": {}}
        "matting":  {"path": ""}
        "video_mask_shadow": {"path": "", "resource_id": ""}
        "video_mask_stroke": {"path": "", "resource_id": "", "type": ""}
    """
    n = 0
    for v in (content.get("materials") or {}).get("videos") or []:
        if not isinstance(v, dict):
            continue
        changed = False
        for k, default in (
            # 防抖：stable_level 3 = 剪映「推荐」档（实测样本值）
            ("stable", {"stable_level": 3, "time_range": {}}),
            ("matting", {"path": ""}),
            ("video_mask_shadow", {"path": "", "resource_id": ""}),
            ("video_mask_stroke", {"path": "", "resource_id": "", "type": ""}),
            ("extra_type_option", 1),
            ("has_sound_separated", False),
            ("beauty_face_auto_preset", {}),
            ("beauty_face_preset_infos", []),
        ):
            if k not in v:
                v[k] = json.loads(json.dumps(default))
                changed = True
        # 防抖若已存在但没有 time_range，也补上
        if isinstance(v.get("stable"), dict) and "time_range" not in v["stable"]:
            v["stable"]["time_range"] = {}
            changed = True
        if changed:
            n += 1
    return n


def apply_stabilize(content, level=3):
    """开启防抖【推荐】。

    实测用户草稿里「推荐」档写的是 `stable_level: 3`
    （0=不防抖，1=最稳，2=推荐，3=... 各档位命名随版本变化；
     这里直接采用用户自己草稿里真实出现的 3，与「推荐」一致）。
    """
    n = 0
    for v in (content.get("materials") or {}).get("videos") or []:
        if not isinstance(v, dict):
            continue
        st = v.setdefault("stable", {})
        st["stable_level"] = int(level)
        st.setdefault("time_range", {})
        n += 1
    return n


# ---------------------------------------------------------------------------
# 一条龙：写侧车
# ---------------------------------------------------------------------------

def write_sidecars(draft_dir, content, registrations=None, resolution=1080):
    """把一套侧车文件写全，让新草稿具备与真实草稿一致的文件面。"""
    os.makedirs(draft_dir, exist_ok=True)
    log = []

    if registrations:
        added = register_key_value(draft_dir, registrations)
        log.append(f"key_value.json 登记 {len(added)} 项")

    p = os.path.join(draft_dir, "attachment_pc_common.json")
    if not os.path.exists(p):
        _w(p, ATTACHMENT_PC_COMMON)
        log.append("attachment_pc_common.json")

    p = os.path.join(draft_dir, "attachment_editing.json")
    if not os.path.exists(p):
        _w(p, {"editing_draft": {"draft_id": content.get("id", "")}})
        log.append("attachment_editing.json")

    p = os.path.join(draft_dir, "draft_agency_config.json")
    cfg = json.loads(json.dumps(AGENCY_CONFIG))
    cfg["video_resolution"] = resolution
    _w(p, cfg)
    log.append("draft_agency_config.json")

    p = os.path.join(draft_dir, "timeline_layout.json")
    if not os.path.exists(p):
        _w(p, TIMELINE_LAYOUT)
        log.append("timeline_layout.json")

    p = os.path.join(draft_dir, "draft_virtual_store.json")
    if not os.path.exists(p):
        _w(p, VIRTUAL_STORE)
        log.append("draft_virtual_store.json")

    # draft_settings：[General] 段，edit 计数从 1 起（0 会被当成「没编辑过」）
    p = os.path.join(draft_dir, "draft_settings")
    import time
    now = int(time.time())
    _w_text(p, "\n".join([
        "[General]",
        f"draft_create_time={now}",
        f"draft_last_edit_time={now}",
        "real_edit_keys=1",
        "real_edit_seconds=1",
        "cloud_last_modify_platform=windows",
        "",
    ]))
    log.append("draft_settings")

    return log


def register_recognize_task(draft_dir, task_id=None, task_type="subtitle"):
    """登记一个识别任务，让草稿里出现「识别中/已识别」的入口。"""
    p = os.path.join(draft_dir, "attachment_pc_common.json")
    try:
        with open(p, "r", encoding="utf-8") as f:
            o = json.load(f)
    except (OSError, json.JSONDecodeError):
        o = json.loads(json.dumps(ATTACHMENT_PC_COMMON))
    o.setdefault("recognize_tasks", []).append({
        "task_id": task_id or str(uuid.uuid4()),
        "task_type": task_type,
        "status": 0,
    })
    _w(p, o)
    return True
