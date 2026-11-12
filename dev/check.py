#!/usr/bin/env python3
"""Read-only development environment diagnostics."""
import ctypes.util, json, os, platform, shutil
from pathlib import Path
checks={'python':platform.python_version(),'libarchive':ctypes.util.find_library('archive'),'qemu_system_i386':shutil.which('qemu-system-i386'),'qemu_system_x86_64':shutil.which('qemu-system-x86_64'),'qemu_img':shutil.which('qemu-img'),'cabextract':shutil.which('cabextract'),'kvm_visible':Path('/dev/kvm').exists(),'kvm_accessible':os.access('/dev/kvm',os.R_OK|os.W_OK),'x11_display':bool(os.environ.get('DISPLAY')),'host_settings_modified':False}
print(json.dumps(checks,indent=2))
