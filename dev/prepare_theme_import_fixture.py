#!/usr/bin/env python3
"""Privately install original Plus media names for import validation; no execution."""
import argparse,configparser,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from win95lx.control_panel.theme_preferences import installed_names

def prepare(output,theme='NATURE.THM'):
 output=Path(output);output.mkdir(parents=True,exist_ok=False);source=ROOT/'private/cabsets/plus95';text=(source/theme).read_text(encoding='cp1252');parser=configparser.ConfigParser(interpolation=None,allow_no_value=True);parser.read_string(text)
 names=installed_names((ROOT/'private/reference/media/plus/PLUS.INF').read_text(encoding='cp1252'));copied=[]
 for section in parser.sections():
  for key,value in parser[section].items():
   if value is None or not value.casefold().startswith('%themedir%'):continue
   filename=value[10:];filename=re.sub(r',\s*0$','',filename)
   if Path(filename).name!=filename:raise ValueError('Unexpected original media path.')
   original=source/names[filename.casefold()];destination=output/filename
   if not destination.exists():shutil.copyfile(original,destination);copied.append(filename)
 definition=output/'Original.theme';definition.write_bytes((source/theme).read_bytes())
 return {'definition':str(definition),'source':str(source/theme),'installed_media':copied}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--theme',default='NATURE.THM');a=p.parse_args();print(json.dumps(prepare(a.output,a.theme),indent=2))
