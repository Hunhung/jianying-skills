"""
素材规范化 + 素材包搬运（供 rebuild_styled_draft.py / augment_draft.py 共用）。

为什么需要
----------
1. pyJianYingDraft 写出来的素材是「最小集」，缺剪映内部依赖的字段
   （如滤镜素材的 `beauty_face_auto_retouch_info` / `third_resource_id`、
   视频素材的 `has_audio` / `is_ai_generate_content` 等）。
   实测剪映 11.5 对缺字段的素材可能直接静默忽略 —— 这就是「滤镜是空的」的根因之一。

2. 滤镜/字体这类资源剪映**按 resource_id 从服务端拉取**。若本机
   `Cache/artistEffect/<resource_id>/` 下没有落地的文件，新建草稿首次打开时
   可能拉取失败。把用户自己草稿里已验证可用的元数据（含 path）整块搬过来最稳。

用法
----
    from jy_material_port import harvest_style_pool, normalize_materials, port_style_materials
    pool = harvest_style_pool(drafts)          # 扫描全库，收集模板
    port_style_materials(content, pool)        # 就地补字段
"""

import os
import glob
import json
from collections import defaultdict

# 每个容器下的「代表样本」——取字段最全的那条
CONTAINERS = (
    "videos", "effects", "texts", "audios", "canvases", "masks",
    "sticker_animations", "material_animations", "speeds", "placeholder_infos",
)


def _is_plaintext_json(path):
    """剪映 11.5 加密草稿判据：首字节不是 '{' 就是加密的。"""
    try:
        with open(path, "rb") as f:
            return f.read(1) == b"{"
    except OSError:
        return False


def _load_plaintext(path):
    if not _is_plaintext_json(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None


def harvest_style_pool(drafts_root, limit_scan=400):
    """扫描草稿库里的**明文**草稿，抽出每个 (容器, type) 下字段最全的素材作样本。

    明文草稿都是 2026-08-20 之前的老草稿 —— 正好是剪映自己写过的，
    字段完整度最高，用户收藏的滤镜/字体都真实生效过。
    """
    pool = {}          # (container, type) -> 字段最多的素材 dict
    names = defaultdict(int)

    count = 0
    for entry in sorted(glob.glob(os.path.join(drafts_root, "*"))):
        if count >= limit_scan:
            break
        if not os.path.isdir(entry):
            continue
        for cand in (os.path.join(entry, "draft_info.json"),
                     os.path.join(entry, "Timelines")):
            pass
        # 只认根目录的明文 draft_info.json
        obj = _load_plaintext(os.path.join(entry, "draft_info.json"))
        if obj is None:
            continue
        count += 1
        for container, items in (obj.get("materials") or {}).items():
            if not isinstance(items, list):
                continue
            for it in items:
                if not isinstance(it, dict):
                    continue
                key = (container, it.get("type"))
                prev = pool.get(key)
                if prev is None or len(it) > len(prev):
                    pool[key] = it
                    names[key] = os.path.basename(entry)

    return {"pool": pool, "scan_count": count, "names": dict(names)}


def _merge_into(dst, sample):
    """把样本里有、目标里缺的键补上（浅合并；嵌套 dict 也补一层）。"""
    added = []
    for k, v in sample.items():
        if k not in dst:
            dst[k] = json.loads(json.dumps(v)) if isinstance(v, (dict, list)) else v
            added.append(k)
        elif isinstance(v, dict) and isinstance(dst.get(k), dict):
            for kk, vv in v.items():
                if kk not in dst[k]:
                    dst[k][kk] = json.loads(json.dumps(vv)) if isinstance(vv, (dict, list)) else vv
                    added.append(f"{k}.{kk}")
    return added


def normalize_materials(content, pool, verbose=True):
    """给草稿里所有素材补齐字段，并把滤镜素材重指到本机可用的缓存 path。

    返回 {容器: 补键数} 报告。
    """
    report = defaultdict(int)
    mats = content.setdefault("materials", {})
    for container, items in mats.items():
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            sample = pool.get((container, it.get("type")))
            if sample is None:
                continue
            added = _merge_into(it, sample)
            if added:
                report[f"{container}/{it.get('type')}"] += len(added)

            # 滤镜/特效：把 path 指到本机 Cache 里真实存在的文件
            rid = it.get("resource_id") or it.get("effect_id")
            if it.get("type") == "filter" and rid:
                p = find_local_effect_path(str(rid), it.get("name"))
                if p:
                    it["path"] = p

    if verbose:
        for k, v in sorted(report.items()):
            print(f"      补全 {k}: +{v} 字段")
    return dict(report)


def find_local_effect_path(resource_id, name=None):
    """在本机 Cache 里找该资源已落地的文件路径。找不到返回 None。"""
    base = os.path.join(os.path.expanduser("~"), "AppData", "Local",
                        "JianyingPro", "User Data", "Cache")
    for sub in ("artistEffect", "effect", "filter", "beauty"):
        d = os.path.join(base, sub, resource_id)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                fp = os.path.join(d, f)
                if os.path.isfile(fp) and os.path.getsize(fp) > 0:
                    return fp.replace("\\", "/")
    return None


def port_style_materials(content, pool):
    """把用户已验证可用的滤镜素材（含 path）整条搬进草稿，并重指滤镜轨。

    这是「滤镜是空的」最直接的解法：素材不是缺字段，而是剪映根本拉不到资源。
    直接复用用户 7月13日 草稿里那条已经生效过的滤镜素材。
    """
    key = ("effects", "filter")
    sample = pool.get(key)
    if sample is None:
        return None

    mats = content.setdefault("materials", {})
    mats.setdefault("effects", [])

    # 干掉旧的 filter 素材（保持唯一）
    mats["effects"] = [e for e in mats["effects"]
                       if not (isinstance(e, dict) and e.get("type") == "filter")]

    fid = sample.get("id")
    if not fid or any(e.get("id") == fid for e in mats["effects"] if isinstance(e, dict)):
        import uuid
        fid = str(uuid.uuid4()).upper()

    new = json.loads(json.dumps(sample))
    new["id"] = fid
    # 实时校正 path：本机有就直接用本机的
    p = find_local_effect_path(str(new.get("resource_id") or ""), new.get("name"))
    if p:
        new["path"] = p
    mats["effects"].append(new)

    for t in content.get("tracks") or []:
        if t.get("type") != "filter":
            continue
        for s in t.get("segments") or []:
            s["material_id"] = fid

    return {"id": fid, "path": new.get("path", ""), "name": new.get("name"),
            "resource_id": new.get("resource_id")}


def harvest_font_meta(drafts_root, font_resource_id, limit_scan=400):
    """从明文草稿里捞指定字体的 text 素材，返回字段最全的那条（可含 path）。"""
    best = None
    count = 0
    for entry in sorted(glob.glob(os.path.join(drafts_root, "*"))):
        if count >= limit_scan:
            break
        if not os.path.isdir(entry):
            continue
        obj = _load_plaintext(os.path.join(entry, "draft_info.json"))
        if obj is None:
            continue
        count += 1
        for it in (obj.get("materials") or {}).get("texts") or []:
            if not isinstance(it, dict):
                continue
            if str(it.get("font_resource_id")) == str(font_resource_id):
                if best is None or len(it) > len(best):
                    best = it
    return best
