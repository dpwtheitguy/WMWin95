#!/usr/bin/env python3
"""Reproducible CPU render benchmark; does not claim end-to-end input latency."""
import argparse,hashlib,json,statistics,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev')]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--frames',type=int,default=100);a=p.parse_args()
 import gi;gi.require_foreign('cairo');import cairo
 from win95lx.shell.app import Shell,Gtk
 from check_menu_seams import flush_draws
 runs=[]
 with TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
  shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
  surface=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);context=cairo.Context(surface)
  for state in ('desktop','computer','selection'):
   if state=='computer':shell.open('computer')
   if state=='selection':shell.item_selection=(shell.state.active,'Control Panel')
   for _ in range(5):shell.draw(shell.area,context)
   values=[]
   for _ in range(a.frames):
    start=time.perf_counter_ns();shell.draw(shell.area,context);surface.flush();values.append((time.perf_counter_ns()-start)/1e6)
   ordered=sorted(values);runs.append({'state':state,'frames':len(values),'median_ms':statistics.median(values),'p95_ms':ordered[min(len(values)-1,int(len(values)*.95))],'max_ms':max(values)})
  shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
 digest=hashlib.sha256()
 for path in sorted((ROOT/'src').rglob('*.py')):digest.update(str(path.relative_to(ROOT)).encode());digest.update(path.read_bytes())
 report={'source_sha256':digest.hexdigest(),'viewport':[shell.width,shell.height],'measurement':'Cairo shell.draw CPU time; excludes X presentation, pointer input, compositor and viewer','runs':runs}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
