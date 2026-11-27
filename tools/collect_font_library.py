#!/usr/bin/env python3
"""Collect original font versions privately; inspect data without installing it."""
import argparse,hashlib,json,shutil,sys
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from win95lx.control_panel.font_catalog import EXTENSIONS,fontconfig,font_metadata
SOURCES=(('win95-rtm','Windows 95 RTM','windows95-osr1-all'),('win95-osr2','Windows 95 OSR2','windows95-rtm-all'),
 ('win95-osr25','Windows 95 OSR2.5','windows95'),('plus95','Plus! 95','plus95'),
 ('win98-se','Windows 98 Second Edition','windows98-se/base'),('plus98','Plus! 98','plus98'))

def collect(output):
    output=output.resolve()
    if not output.is_relative_to((ROOT/'private').resolve()):raise ValueError('Original font files belong in the private library.')
    output.mkdir(parents=True,exist_ok=True);rows=[];cache={};profiles=[]
    for key,label,folder in SOURCES:
        source=ROOT/'private/cabsets'/folder;count=0
        if not source.exists():continue
        for path in sorted(source.rglob('*')):
            if not path.is_file() or path.suffix.casefold() not in EXTENSIONS:continue
            digest=hashlib.sha256(path.read_bytes()).hexdigest();target=output/key/path.relative_to(source)
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise FileExistsError('Original font version would be replaced: '+str(target))
            if not target.exists():shutil.copyfile(path,target)
            if digest not in cache:
                try:
                    faces=fontconfig().query(path)
                    cache[digest]={'readable':True,'faces':[{'index':f.index,'family':f.family,'style':f.style,'format':f.format,'version_fixed_16_16':f.version,'metadata':font_metadata(path,f.index)} for f in faces]}
                except (OSError,ValueError,RuntimeError) as error:
                    reason=str(error)
                    if path.suffix.casefold()=='.fon':
                        from resources import extract
                        try:
                            if any(kind==8 and len(data)>=118 and int.from_bytes(data[66:68],'little')&1 for kind,ident,lang,data,fmt in extract(path.read_bytes())):
                                reason='Legacy Windows stroke/vector FNT font; a vector-font compatibility adapter is not implemented.'
                        except (ValueError,IndexError):pass
                    cache[digest]={'readable':False,'faces':[],'reason':reason}
            rows.append({'profile':key,'product':label,'source':str(path.relative_to(ROOT)),'original_name':str(path.relative_to(source)),'file':str(target.relative_to(output)),
                         'sha256':digest,'bytes':path.stat().st_size,**cache[digest]});count+=1
        profiles.append({'id':key,'label':label,'source_files':count})
    report={'profiles':profiles,'fonts':rows,'unique_font_files':len(cache),'readable_unique_files':sum(row['readable'] for row in cache.values()),
            'installation_performed':False,'scope':'Readability is actual FreeType/Fontconfig inspection, not global availability, identical GDI rasterization or a redistribution license. No separately verified OSR1/98-first-edition media.'}
    (output/'inventory.json').write_text(json.dumps(report,indent=2)+'\n');return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'private/font-library');a=p.parse_args();r=collect(a.output)
    print(json.dumps({'profiles':r['profiles'],'source_files':len(r['fonts']),'unique_files':r['unique_font_files'],'readable_unique_files':r['readable_unique_files'],'installed':False},indent=2))
if __name__=='__main__':main()
