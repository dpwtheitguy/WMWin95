"""Preserve original Plus color/font/metric data in the private preset catalog."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from win95lx.control_panel.theme_import import read_legacy_appearance

def stage(output):
 output=Path(output);catalog=json.loads((output/'themes-library.json').read_text());text=(ROOT/'private/reference/media/plus/PLUS.INF').read_text(encoding='cp1252')
 labels={short.casefold():Path(long).stem for short,long in re.findall(r'([\w~]+\.THM)<([^>]+)>',text,re.I)};records=[]
 for row in catalog['provenance']:
  if 'wallpaper_source'not in row:continue
  source=ROOT/row['source'];raw=source.read_bytes();value=read_legacy_appearance(raw)
  if set(value)!={'colors','fonts','metrics'}:raise ValueError('Original theme appearance data is incomplete.')
  label=labels[source.name.casefold()];catalog['themes'][label].update(value)
  records.append({'source':row['source'],'source_sha256':hashlib.sha256(raw).hexdigest(),'type':'NATIVE_THEME_APPEARANCE','theme':label,'output':'themes-library.json','components':list(value),'scope':'Typed original INI data; no blanket art recoloring or full themed-control pixel acceptance.'})
 source=ROOT/'private/cabsets/plus95/DEFAULT.THM';raw=source.read_bytes();defaults=read_legacy_appearance(raw)
 catalog['themes']['Windows Default']={'wallpaper':{'file':'','mode':'center'},'pointers':'(None)','sounds':'Windows Default','icons':{},'screensaver':{'saver':''},**defaults}
 records.append({'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(raw).hexdigest(),'type':'NATIVE_THEME_DEFAULT','theme':'Windows Default','output':'themes-library.json','scope':'Original default appearance; default pointer/sound/icon providers; no visible Linux defaults.'})
 catalog['appearance_provenance']=records;(output/'themes-library.json').write_text(json.dumps(catalog,indent=2)+'\n');return records
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);args=p.parse_args();print(json.dumps(stage(args.output),indent=2))
