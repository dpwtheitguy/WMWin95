#!/usr/bin/env python3
"""Prepare disposable original-media fixtures for both isolated import checks."""
from pathlib import Path
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='win95lx-import-check-') as directory:
    fixture=Path(directory)/'media'
    subprocess.run([sys.executable,str(ROOT/'dev/prepare_theme_import_fixture.py'),str(fixture)],check=True)
    for size in ('800x600','1280x720'):
        subprocess.run([sys.executable,str(ROOT/'dev/check_theme_import_ui.py'),'--fixture',str(fixture),'--size',size,'--output',str(ROOT/'private/screenshots'/('theme-import-'+str(time.time_ns())+'-'+size))],check=True)
