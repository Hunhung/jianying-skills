import os
import json
import subprocess
from typing import Optional


def _norm_output_path(input_path: str) -> str:
    abs_in = os.path.abspath(input_path)
    parent = os.path.dirname(abs_in)
    stem, _ = os.path.splitext(os.path.basename(abs_in))
    cache_dir = os.path.join(parent, "__jycache__")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, f"{stem}.__jy_norm__.mp4")


def _is_cache_fresh(src: str, dst: str) -> bool:
    if not os.path.exists(dst):
        return False
    try:
        return os.path.getmtime(dst) >= os.path.getmtime(src)
    except OSError:
        return False


_FMT_MAP = {
    "avc": "h264", "h.264": "h264", "avc1": "h264",
    "hevc": "hevc", "h.265": "hevc",
    "vp9": "vp9", "av1": "av1", "vp8": "vp8",
}


def _mi_pix_fmt(track) -> Optional[str]:
    """把 MediaInfo 的 color_space/chroma_subsampling 映射成 ffprobe 风格的 pix_fmt。"""
    cs = (getattr(track, "color_space", "") or "").strip().upper()
    ss = (getattr(track, "chroma_subsampling", "") or "").replace(" ", "")
    if cs == "YUV" and ss == "4:2:0":
        return "yuv420p"
    return None


def _probe_video(input_path: str) -> dict:
    """探测视频编码信息。

    优先使用 pymediainfo（本项目依赖，不依赖系统 ffprobe）；
    回退到 ffprobe。**任何探测失败都返回 `{}` 而不是抛异常** —— 调用方据此
    保守跳过归一化，避免因环境缺 ffprobe 直接崩溃，也避免误判触发转码。
    """
    # 1) pymediainfo（首选）
    try:
        import pymediainfo
        if pymediainfo and pymediainfo.MediaInfo.can_parse():
            info = pymediainfo.MediaInfo.parse(input_path)
            for t in info.video_tracks:
                codec = _FMT_MAP.get((getattr(t, "format", "") or "").strip().lower())
                pix = _mi_pix_fmt(t)
                if codec is None or pix is None:
                    return {}
                return {
                    "codec_name": codec,
                    "pix_fmt": pix,
                    "width": int(t.width or 0),
                    "height": int(t.height or 0),
                }
    except Exception:
        pass

    # 2) ffprobe 回退
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=codec_name,width,height,pix_fmt",
        "-of",
        "json",
        input_path,
    ]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return {}
    if proc.returncode != 0:
        return {}
    try:
        streams = json.loads(proc.stdout or "{}").get("streams", [])
    except json.JSONDecodeError:
        return {}
    return streams[0] if streams else {}


def should_normalize_video_for_jianying(input_path: str) -> bool:
    info = _probe_video(input_path)
    if not info:
        # 探测不可用或信息不足：保守跳过归一化。
        # 归一化会把视频压成 1920x1080@30，对 4K60 素材属于破坏性操作，
        # 宁可不动，也不要因误判而悄悄降质。
        return False
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    return (
        info.get("codec_name") != "h264"
        or info.get("pix_fmt") != "yuv420p"
        or width <= 0
        or height <= 0
        or width % 16 != 0
        or height % 2 != 0
    )


def normalize_video_for_jianying(input_path: str, force: bool = False) -> Optional[str]:
    """
    Convert video to JianYing-friendly MP4 before timeline import.

    Output profile:
    - Video: H.264 (libx264), yuv420p
    - Audio: AAC (optional if source has audio)
    - Geometry: 1920x1080 with padding when needed
    """
    src = os.path.abspath(input_path)
    if not os.path.exists(src):
        return None
    if not force and not should_normalize_video_for_jianying(src):
        return src

    dst = _norm_output_path(src)
    if _is_cache_fresh(src, dst):
        return dst

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        src,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        dst,
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        print("❌ FFmpeg not found. Cannot normalize video for JianYing import.")
        return None
    except Exception as e:
        print(f"❌ Video normalization failed: {e}")
        return None

    if proc.returncode != 0 or not os.path.exists(dst):
        err = (proc.stderr or proc.stdout or "").strip()
        print(f"❌ Video normalization failed (ffmpeg={proc.returncode}): {err}")
        return None

    return dst


def normalize_webm_for_jianying(input_path: str) -> Optional[str]:
    return normalize_video_for_jianying(input_path, force=True)
