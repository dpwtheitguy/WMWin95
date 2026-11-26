#!/usr/bin/env python3
"""Build a Win95-compatible, CRT-free native measurement probe privately."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    prefix=ROOT/'private/cross-tools/root';compiler=prefix/'usr/bin/i686-w64-mingw32-gcc-posix'
    output=ROOT/'private/reference-tools/W95PROBE.EXE';output.parent.mkdir(parents=True,exist_ok=True)
    env={**os.environ,'PATH':str(prefix/'usr/bin')+':'+os.environ['PATH'],'GCC_EXEC_PREFIX':str(prefix/'usr/lib/gcc')+'/'}
    command=[str(compiler),'-Os','-march=i386','-mtune=pentium','-mno-sse','-mno-sse2','-mno-mmx','-std=c99','-Wall','-Wextra','-Werror','-fno-builtin','-fno-stack-protector','-ffreestanding','-nostdlib',
             '-I'+str(prefix/'usr/i686-w64-mingw32/include'),'-L'+str(prefix/'usr/i686-w64-mingw32/lib'),
             '-Wl,--entry,_entry,--subsystem,windows,--major-subsystem-version,4,--minor-subsystem-version,0,--major-os-version,4,--minor-os-version,0,--no-insert-timestamp',
             str(ROOT/'tools/native/w95probe.c'),'-o',str(output),'-lgdi32','-luser32','-lkernel32']
    subprocess.run(command,env=env,check=True)
    print('Built native measurement probe:',output)
if __name__=='__main__':main()
