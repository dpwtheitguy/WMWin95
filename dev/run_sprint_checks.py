#!/usr/bin/env python3
"""Run the evidence-producing sprint scenarios at both acceptance resolutions."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or ROOT/'private/screenshots'/datetime.now(timezone.utc).strftime('sprint-%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True, exist_ok=False)
    reports = []
    for width, height in ((800, 600), (1280, 720)):
        destination = output/f'{width}x{height}'
        result = subprocess.run(['xvfb-run', '-a', '-s', f'-screen 0 {width}x{height}x24',
                                 args.python, str(ROOT/'dev/check_sprint_controls.py'),
                                 '--output', str(destination)], cwd=ROOT,
                                env={**os.environ, 'GDK_BACKEND': 'x11'})
        report = destination/'report.json'
        reports.append(json.loads(report.read_text()) if report.exists() else
                       {'failed': 1, 'passed': 0, 'exit_code': result.returncode})
    summary = {'runs': reports, 'passed': sum(r['passed'] for r in reports),
               'failed': sum(r['failed'] for r in reports)}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(output)
    return int(bool(summary['failed']))


if __name__ == '__main__':
    raise SystemExit(main())
