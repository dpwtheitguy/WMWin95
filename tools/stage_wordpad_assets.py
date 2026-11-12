#!/usr/bin/env python3
"""Stage the original WordPad toolbar tiles from a local Windows 95 CAB set."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from pixels import write
from resources import extract

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from win95lx.assets.bitmap import rle4_bitmap

SPRITES = {
    140: ('new', 'open', 'save', 'print', 'preview', 'find', 'cut', 'copy', 'paste', 'undo', 'datetime'),
    139: ('bold', 'italic', 'underline', 'color', 'left', 'center', 'right', 'bullets'),
}


def stage(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for kind, ident, language, data, _ in extract(source.read_bytes()):
        if kind != 2 or ident not in SPRITES:
            continue
        width, height, pixels = rle4_bitmap(data)
        names = SPRITES[ident]
        if height != 16 or width < 16 * len(names):
            raise ValueError(f'Unexpected WordPad bitmap dimensions for resource {ident}')
        for index, name in enumerate(names):
            left = index * 16
            tile = [pixel for y in range(height)
                    for pixel in pixels[y * width + left:y * width + left + 16]]
            filename = f'wordpad-toolbar-{name}.png'
            write(destination / filename, 16, 16, tile)
            records.append({'source': source.name, 'id': ident, 'language': language,
                            'sha256': hashlib.sha256(data).hexdigest(), 'output': filename,
                            'rectangle': [left, 0, 16, 16]})
    if len(records) != sum(map(len, SPRITES.values())):
        raise ValueError('Missing a WordPad toolbar resource')
    (destination / 'wordpad-toolbar.json').write_text(json.dumps(records, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'private/cabsets/windows95/wordpad.exe')
    parser.add_argument('--output', type=Path, default=ROOT / 'private/shell-assets')
    args = parser.parse_args()
    stage(args.source, args.output)


if __name__ == '__main__':
    main()
