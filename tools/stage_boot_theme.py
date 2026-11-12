#!/usr/bin/env python3
"""Package local QEMU Windows 95 splash captures for Plymouth."""

import argparse
import os
from pathlib import Path
import re
import shutil
import tempfile

from pixels import write


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "src" / "win95lx" / "packaging" / "plymouth"
WIDTH, HEIGHT = 640, 400
RIBBON_TOP = 389


def read_frame(path):
    data = path.read_bytes()
    header = re.match(rb"P6\n640 400\n255\n", data)
    if header is None or len(data) - header.end() != WIDTH * HEIGHT * 3:
        raise ValueError(f"{path}: expected a 640×400 QEMU P6 capture")
    return data[header.end():]


def save_rows(path, rows):
    pixels = [tuple(rows[i:i + 3]) + (255,) for i in range(0, len(rows), 3)]
    write(path, WIDTH, len(pixels) // WIDTH, pixels)


def stage_theme(paths, output):
    if output.name != "win95lx":
        raise ValueError("The staged directory must be named win95lx.")
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    frames = [read_frame(path) for path in paths]
    ribbon_offset = WIDTH * RIBBON_TOP * 3
    background = frames[0][:ribbon_offset]
    if any(frame[:ribbon_offset] != background for frame in frames):
        raise ValueError("The captures differ above the animation ribbon. Select frames from one startup splash.")
    ribbons = list(dict.fromkeys(frame[ribbon_offset:] for frame in frames))
    if len(ribbons) > 20:
        raise ValueError("Select at most one cycle of the Windows 95 startup animation.")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".win95lx-", dir=output.parent) as staging:
        staged = Path(staging) / output.name
        staged.mkdir()
        shutil.copyfile(TEMPLATES / "win95lx.plymouth", staged / "win95lx.plymouth")
        script = (TEMPLATES / "win95lx.script").read_text(encoding="utf-8")
        (staged / "win95lx.script").write_text(
            script.replace("@FRAME_COUNT@", str(len(ribbons))), encoding="utf-8"
        )
        save_rows(staged / "background.png", background)
        for number, ribbon in enumerate(ribbons):
            save_rows(staged / f"ribbon-{number}.png", ribbon)
        os.rename(staged, output)
    return len(ribbons)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path, nargs="+", help="P6 captures in chronological order")
    parser.add_argument("--output", type=Path, default=ROOT / "private" / "plymouth" / "win95lx")
    options = parser.parse_args()
    try:
        frame_count = stage_theme(options.captures, options.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Staged {frame_count} animation frames in {options.output}")


if __name__ == "__main__":
    main()
