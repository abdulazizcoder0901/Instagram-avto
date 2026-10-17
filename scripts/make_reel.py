"""Carousel slaydlaridan musiqali Reel (1080x1920 MP4) yig'adi.

Ishlatish:
    python3 scripts/make_reel.py posts/2026-10-18 music/calm-01.m4a --seconds-per-slide 3.5

Papkadagi 01.png, 02.png, ... slaydlar tartib bilan, yumshoq o'tish (crossfade)
bilan ko'rsatiladi; musiqa video uzunligiga qirqiladi va oxirida so'nadi.
Natija: <papka>/reel.mp4
"""
import argparse
import subprocess
from pathlib import Path

W, H = 1080, 1920
BG = "0xF6F4EF"
FADE = 0.5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("post_dir")
    ap.add_argument("music")
    ap.add_argument("--seconds-per-slide", type=float, default=3.5)
    args = ap.parse_args()

    post_dir = Path(args.post_dir)
    slides = sorted(post_dir.glob("[0-9][0-9].png"))
    if not slides:
        raise SystemExit(f"{post_dir} ichida slayd topilmadi")
    per = args.seconds_per_slide
    total = per * len(slides) - FADE * (len(slides) - 1)

    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for s in slides:
        cmd += ["-loop", "1", "-t", str(per), "-i", str(s)]
    cmd += ["-i", args.music]

    filters = []
    for i in range(len(slides)):
        filters.append(f"[{i}:v]scale={W}:-2,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color={BG},"
                       f"format=yuv420p,fps=30,setsar=1[v{i}]")
    last = "v0"
    for i in range(1, len(slides)):
        offset = i * (per - FADE)
        filters.append(f"[{last}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[x{i}]")
        last = f"x{i}"
    a = len(slides)
    filters.append(f"[{a}:a]atrim=0:{total:.3f},afade=t=in:d=0.8,"
                   f"afade=t=out:st={max(total - 2, 0):.3f}:d=2[aout]")

    out = post_dir / "reel.mp4"
    cmd += ["-filter_complex", ";".join(filters), "-map", f"[{last}]", "-map", "[aout]",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "20",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(out)]
    subprocess.run(cmd, check=True)
    print(out)


if __name__ == "__main__":
    main()
