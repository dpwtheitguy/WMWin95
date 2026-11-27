#!/usr/bin/env python3
"""Private original Add/Remove frames, measured HWNDs and checklist glyphs."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from pixels import read,write
from resources import extract
from win95lx.assets.dialog_template import parse_dialog
from stage_network_assets import parse_win16_dialog

def stage(output):
 output.mkdir(parents=True,exist_ok=True);base=ROOT/'private/reference-tools/addremove-native-20261126';detail=ROOT/'private/reference-tools/addremove-details-native-20261126';records=[];layouts={}
 for name,meta,source in [('install',base/'metadata/addrem-0.JSN',base/'install.png'),('windows-setup',base/'metadata/addrem-1.JSN',base/'windows-setup.png'),('startup-disk',base/'metadata/addrem-2.JSN',ROOT/'private/screenshots/cpl-20261126/ie4-run2/addremove-startup-disk.png'),('details',detail/'metadata/ardetail-0.JSN',detail/'details.png')]:
  data=json.loads(meta.read_text());x,y=data['origin'];w,h=data['size'];sw,sh,p=read(source)
  # Fresh startup HWND metadata is correct, but its host screenshot was occluded
  # by the Win16 Details child. Use independently archived unobscured native page.
  if name=='startup-disk':x,y=22,22

  if data['dpi']!=[96,96] or x<0 or y<0 or x+w>sw or y+h>sh:raise ValueError('Unexpected native Add/Remove geometry')
  dest=output/f'addremove-{name}-frame.png';write(dest,w,h,[p[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
  layouts[name]=data;records.append({'type':'NATIVE_SCREEN_CAPTURE','profile':'OSR2.5 IE4 Desktop Update,96dpi,256colors','source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'metadata':str(meta.relative_to(ROOT)),'metadata_sha256':hashlib.sha256(meta.read_bytes()).hexdigest(),'rectangle':[x,y,w,h],'output':dest.name})
 # Exposed native ListBox trough, independent of the page's white client.
 nw,nh,np=read(output/'addremove-windows-setup-frame.png');track=(329,180,12,16)
 tx,ty,tw,th=track;colors={np[(ty+yy)*nw+tx+xx] for yy in range(th) for xx in range(tw)}
 if colors!={(255,255,255,255)}:raise ValueError('Native ListBox track no longer uniformly white')
 (output/'addremove-track-measurement.json').write_text(json.dumps({'source':'addremove-windows-setup-frame.png','rectangle':track,'pixels':tw*th,'rgba':[255,255,255,255],'source_sha256':hashlib.sha256((output/'addremove-windows-setup-frame.png').read_bytes()).hexdigest()},indent=2)+'\n')
 # Owner-drawn Windows Setup uses11px checkbox glyphs, not the13px stock BUTTON.
 w,h,p=read(output/'addremove-windows-setup-frame.png')
 for state,y in [('checked',128),('partial',146),('unchecked',182)]:
  dest=f'addremove-check-{state}.png';write(output/dest,11,11,[p[(y+yy)*w+28+xx] for yy in range(11) for xx in range(11)])
  records.append({'type':'MEASURED_OWNERDRAW_CHECKBOX','source':'addremove-windows-setup-frame.png','rectangle':[28,y,11,11],'output':dest})
 dialogs=[]
 for file,ids in [('appwiz.cpl',(101,)),('setupx.dll',(379,378,4202))]:
  path=ROOT/'private/cabsets/windows95'/file
  for kind,ident,lang,data,fmt in extract(path.read_bytes()):
   if kind==5 and ident in ids:
    parsed=(parse_dialog if fmt=='PE' else parse_win16_dialog)(data);dialogs.append({'source':file,'id':ident,'format':fmt,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'resource_sha256':hashlib.sha256(data).hexdigest(),**parsed})
 (output/'addremove-native-layout.json').write_text(json.dumps(layouts,indent=2)+'\n');(output/'addremove-native-dialogs.json').write_text(json.dumps(dialogs,indent=2)+'\n');(output/'addremove-assets-provenance.json').write_text(json.dumps(records,indent=2)+'\n')
 return records
if __name__=='__main__':print(json.dumps({'staged':len(stage(ROOT/'private/shell-assets'))}))
