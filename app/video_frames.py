import subprocess
import tempfile
from pathlib import Path
from typing import List

def extract_frames_from_bytes(
    video_bytes: bytes,
    fps: int = 1,
    max_frames: int = 15,
    max_seconds: int = 12,
) -> List[str]:
    """
    Tar emot video (valfritt format), konverterar till mp4 och
    extraherar JPEG-frames.
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="drill_"))

    # 1) Spara originalvideo (oavsett format)
    input_path = tmp_dir / "input_video"
    input_path.write_bytes(video_bytes)

    # 2) Konvertera ALLT till mp4
    mp4_path = tmp_dir / "normalized.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(input_path),
            "-t", str(max_seconds),
            "-movflags", "faststart",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=iw:ih",
            str(mp4_path),
        ],
        check=True,
    )

    # 3) Extrahera frames från mp4
    frames_dir = tmp_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    out_pattern = str(frames_dir / "frame_%05d.jpg")

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(mp4_path),
            "-vf", f"fps={fps}",
            "-q:v", "3",
            out_pattern,
        ],
        check=True,
    )

    frames = sorted(str(p) for p in frames_dir.glob("frame_*.jpg"))
    return frames[:max_frames]
