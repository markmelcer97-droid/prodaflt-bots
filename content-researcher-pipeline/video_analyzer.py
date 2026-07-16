"""
PRODAFLT Content Researcher Pipeline — Video Analyzer
Uses ffmpeg for frame extraction and OpenAI Whisper (local) for transcription.
Generates frame-level analysis: timestamps, visual hooks, pacing, CTA detection.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import config


# ---------------------------------------------------------------------------
# ffmpeg helpers
# ---------------------------------------------------------------------------

def _run_ffmpeg(args: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    """Run ffmpeg with given args."""
    cmd = [config.FFMPEG_PATH, "-y", "-hide_banner", "-loglevel", "error"] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def extract_frames(
    video_path: Path,
    output_dir: Path,
    interval_sec: float = 1.0,
    max_frames: int = 30,
) -> List[Dict]:
    """
    Extract frames at regular intervals using ffmpeg.
    Returns list of {timestamp, path} dicts.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get duration first
    probe = _run_ffmpeg([
        "-i", str(video_path),
        "-f", "null",
        "-"
    ])
    # Parse duration from stderr
    duration = 30.0  # default
    if probe.stderr:
        m = __import__("re").search(r"Duration: (\d+):(\d+):(\d+\.\d+)", probe.stderr)
        if m:
            h, mn, s = m.groups()
            duration = int(h) * 3600 + int(mn) * 60 + float(s)

    # Determine actual interval to not exceed max_frames
    actual_interval = max(interval_sec, duration / max_frames)

    # Extract frames
    template = str(output_dir / "frame_%04d.jpg")
    _run_ffmpeg([
        "-i", str(video_path),
        "-vf", f"fps=1/{actual_interval},scale=480:-1",
        "-q:v", "2",
        template,
    ])

    frames = sorted(output_dir.glob("frame_*.jpg"))
    result = []
    for i, fpath in enumerate(frames):
        ts = round(i * actual_interval, 2)
        result.append({"timestamp": ts, "path": str(fpath)})
    return result


def extract_keyframes(
    video_path: Path,
    output_dir: Path,
    scene_threshold: float = 0.3,
) -> List[Dict]:
    """
    Extract scene-change keyframes using ffmpeg scene detection.
    Better for identifying hook / CTA / transition moments.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filter_str = (
        f"select='gt(scene,{scene_threshold})',scale=480:-1"
    )
    template = str(output_dir / "keyframe_%04d.jpg")

    _run_ffmpeg([
        "-i", str(video_path),
        "-vf", filter_str,
        "-vsync", "vfr",
        "-q:v", "2",
        template,
    ])

    keyframes = sorted(output_dir.glob("keyframe_*.jpg"))
    # We don't have exact timestamps from scene detection without parsing,
    # so we'll use frame extraction with timestamps as fallback
    result = []
    for i, fpath in enumerate(keyframes):
        result.append({"timestamp": None, "path": str(fpath), "type": "scene_change"})
    return result


# ---------------------------------------------------------------------------
# Whisper transcription
# ---------------------------------------------------------------------------

def transcribe_video(video_path: Path, model: str = config.WHISPER_MODEL) -> Dict:
    """
    Transcribe video audio using faster-whisper (local, no API key).
    Returns dict with full_text, segments, language.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        # Fallback: return empty transcription
        return {
            "full_text": "",
            "segments": [],
            "language": None,
            "error": "faster-whisper not installed; run: pip install faster-whisper",
        }

    model_obj = WhisperModel(model, device="cpu", compute_type="int8")
    segments_iter, info = model_obj.transcribe(str(video_path), beam_size=5)

    segments = []
    full_text_parts = []
    for seg in segments_iter:
        segments.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
        full_text_parts.append(seg.text.strip())

    return {
        "full_text": " ".join(full_text_parts),
        "segments": segments,
        "language": info.language,
    }


# ---------------------------------------------------------------------------
# Frame-level analysis (heuristic)
# ---------------------------------------------------------------------------

def analyze_frame_sequence(frames: List[Dict], transcript_segments: List[Dict]) -> List[Dict]:
    """
    Match frames to transcript segments and tag potential hooks/CTAs.
    Returns enriched frame list with narrative role tags.
    """
    if not frames:
        return frames

    # Simple heuristic: first 3 seconds = hook, last 3 seconds = CTA
    duration = frames[-1]["timestamp"] if frames else 0
    enriched = []

    for frame in frames:
        ts = frame["timestamp"]
        tags = []

        if ts <= 3.0:
            tags.append("hook_zone")
        elif duration > 0 and ts >= duration - 3.0:
            tags.append("cta_zone")
        elif duration > 0 and ts >= duration * 0.5:
            tags.append("mid_story")
        else:
            tags.append("build_up")

        # Find overlapping transcript
        overlapping_text = ""
        for seg in transcript_segments:
            if seg["start"] <= ts <= seg["end"]:
                overlapping_text = seg["text"]
                break

        enriched.append({
            **frame,
            "tags": tags,
            "transcript_at_timestamp": overlapping_text,
        })

    return enriched


# ---------------------------------------------------------------------------
# Main video analysis entrypoint
# ---------------------------------------------------------------------------

def analyze_video(video_path: Path, output_base: Optional[Path] = None) -> Dict:
    """
    Full video analysis pipeline:
      1. Extract frames at 1s intervals
      2. Extract scene-change keyframes
      3. Transcribe audio
      4. Match frames to transcript
      5. Tag narrative zones (hook / build / CTA)

    Returns analysis dict.
    """
    output_base = output_base or config.MEDIA_DOWNLOAD_PATH / video_path.stem
    output_base.mkdir(parents=True, exist_ok=True)

    frames_dir = output_base / "frames"
    keyframes_dir = output_base / "keyframes"

    # 1. Extract frames
    frames = extract_frames(video_path, frames_dir, interval_sec=1.0, max_frames=30)

    # 2. Extract keyframes
    keyframes = extract_keyframes(video_path, keyframes_dir)

    # 3. Transcribe
    transcription = transcribe_video(video_path)

    # 4. Match frames to transcript
    enriched_frames = analyze_frame_sequence(frames, transcription.get("segments", []))

    # 5. Detect hook from transcript
    hook_text = ""
    for seg in transcription.get("segments", [])[:3]:
        hook_text += seg["text"] + " "

    # 6. Detect CTA from transcript
    cta_text = ""
    segments = transcription.get("segments", [])
    for seg in segments[-3:]:
        cta_text += seg["text"] + " "

    return {
        "video_path": str(video_path),
        "frame_count": len(frames),
        "keyframe_count": len(keyframes),
        "frames": enriched_frames,
        "keyframes": keyframes,
        "transcription": transcription,
        "hook_text": hook_text.strip(),
        "cta_text": cta_text.strip(),
        "duration_estimate": frames[-1]["timestamp"] if frames else 0,
    }
