#!/usr/bin/env python3
"""Exact RGBA comparison. Exit 0 identical, 1 differences, 2 invalid inputs."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

from pixels import read, write


def crop(image, rect):
    width, height, pixels = image
    x, y, w, h = rect
    if (not all(type(value) is int for value in rect)
            or min(x, y) < 0 or min(w, h) <= 0 or x+w > width or y+h > height):
        raise ValueError(f'Invalid rectangle {rect} for {width}x{height} image')
    return w, h, [pixel for row in range(y, y+h)
                  for pixel in pixels[row*width+x:row*width+x+w]]


def compare_images(reference, actual, masks):
    width, height, expected = reference
    aw, ah, observed = actual
    if (width, height) != (aw, ah):
        raise ValueError('Image dimensions differ')
    excluded = set()
    for mask in masks:
        if not mask.get('reason', '').strip():
            raise ValueError('Every mask requires a reason')
        x, y, w, h = mask['rect']
        if (not all(type(value) is int for value in (x, y, w, h))
                or min(x, y) < 0 or min(w, h) <= 0 or x+w > width or y+h > height):
            raise ValueError('Invalid mask rectangle')
        excluded.update(row*width+col for row in range(y, y+h) for col in range(x, x+w))
    compared = width*height-len(excluded)
    if not compared:
        raise ValueError('Masks exclude the entire image')

    rows, columns, colors = Counter(), Counter(), Counter()
    diff = []
    for index, (before, after) in enumerate(zip(expected, observed)):
        changed = index not in excluded and before != after
        if changed:
            rows[index//width] += 1
            columns[index%width] += 1
            colors[before, after] += 1
        diff.append((255, 0, 255, 255) if changed else (0, 0, 0, 255))
    differing = rows.total()
    return {
        'width': width, 'height': height,
        'differing_pixels': differing, 'compared_pixels': compared,
        'masked_pixels': len(excluded), 'differing_percent': 100*differing/compared,
        'bbox_xyxy_exclusive': [min(columns), min(rows), max(columns)+1, max(rows)+1] if differing else None,
        'rows_with_differences': dict(sorted(rows.items())),
        'columns_with_differences': dict(sorted(columns.items())),
        'top_color_changes': [{'reference_rgba': before, 'actual_rgba': after, 'pixels': count}
                              for (before, after), count in colors.most_common(12)],
        'passed': differing == 0,
    }, diff


def compare(reference, actual, masks):
    return compare_images(read(reference), read(actual), masks)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        cfg = json.loads(args.config.read_text())
        ref = (args.config.parent/cfg['reference']).resolve()
        actual = (args.config.parent/cfg['actual']).resolve()
        ref_hash = digest(ref)
        if ref_hash != cfg['reference_sha256']:
            raise ValueError('Reference hash differs from sealed configuration')
        expected, observed = read(ref), read(actual)
        if 'region' in cfg:
            region = cfg['region']
            rx, ry, w, h = region['reference_rect']
            ax, ay = region['actual_origin']
            expected = crop(expected, (rx, ry, w, h))
            observed = crop(observed, (ax, ay, w, h))
        result, diff = compare_images(expected, observed, cfg.get('masks', []))
        args.output.mkdir(parents=True, exist_ok=False)
        result.update({'reference_sha256': ref_hash, 'actual_sha256': digest(actual), 'config': cfg})
        width, height = result['width'], result['height']
        write(args.output/'diff.png', width, height, diff)
        if 'region' in cfg:
            panels = [pixel for row in range(height) for panel in (expected[2], observed[2], diff)
                      for pixel in panel[row*width:(row+1)*width]]
            write(args.output/'comparison.png', width*3, height, panels)
        shutil.copyfile(args.config, args.output/'config.json')
        (args.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
        return 0 if result['passed'] else 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, str(error)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
