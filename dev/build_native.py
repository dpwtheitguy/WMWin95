#!/usr/bin/env python3
"""Compile the optional exact palette accelerator into private development output."""
import argparse,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'private/native/libpalette.so');a=p.parse_args()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run(['cc','-O3','-std=c99','-Wall','-Wextra','-Werror','-fPIC','-shared',str(ROOT/'src/win95lx/assets/palette.c'),'-o',str(a.output)],check=True)
    print('Built optional palette accelerator:',a.output)
if __name__=='__main__':main()
