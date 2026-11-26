#!/usr/bin/env python3
"""Stage basic Windows pointers and all local Plus95 pointer assets and themes."""
import configparser,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from resources import extract
from pixels import write
from win95lx.assets.bitmap import word
from win95lx.assets.cursors import decode,dib_frame

BASIC={'arrow':100,'help':112,'busy':111,'wait':102,'cross':103,'beam':101,'pen':113,'no':110,
       'size4':108,'size3':107,'size2':105,'size1':106,'move':109,'up':104}
REGISTRY={'arrow':'arrow','help':'help','appstarting':'busy','wait':'wait','crosshair':'cross','ibeam':'beam','nwpen':'pen','no':'no',
          'sizens':'size4','sizewe':'size3','sizenwse':'size2','sizenesw':'size1','sizeall':'move','uparrow':'up'}

def main():
    output=ROOT/'private/shell-assets';output.mkdir(parents=True,exist_ok=True);assets={};schemes={};source=ROOT/'private/cabsets/windows95'
    def store(key,frames,sequence,durations,origin,digest):
        info=[]
        for index,frame in enumerate(frames):
            filename=f'cursor-{key}-{index:03}.png';write(output/filename,frame.width,frame.height,frame.pixels)
            meta={'file':filename,'hotspot':frame.hotspot,'invert':frame.invert,'dimensions':[frame.width,frame.height]}
            (output/Path(filename).with_suffix('.json')).write_text(json.dumps(meta)+'\n');info.append(meta)
        assets[key]={'frames':info,'sequence':sequence,'durations_ms':durations,'source':origin,'source_sha256':digest}
        return key
    resources=list(extract((source/'user.exe').read_bytes()));basic={}
    for role,ident in BASIC.items():
        group=next(d for k,i,l,d,f in resources if k==12 and i==ident);rawid=word(group,18)
        raw=next(d for k,i,l,d,f in resources if k==1 and i==rawid)
        frame=dib_frame(raw[4:],(word(raw,0),word(raw,2)))
        basic[role]=store('basic-'+role,[frame],[0],[1000],f'USER.EXE GROUP_CURSOR {ident} / CURSOR {rawid}',hashlib.sha256(raw).hexdigest())
    schemes['(None)']=basic
    for label,suffix in (('3D Pointers','1'),('Windows Standard (large)','m'),('Windows Standard (extra large)','l')):
        schemes[label]={}
        for role in BASIC:
            path=source/f'{role}_{suffix}.cur';data=path.read_bytes();f,s,r=decode(data)
            schemes[label][role]=store(path.stem,f,s,r,path.name,hashlib.sha256(data).hexdigest())
    schemes['Animated Hourglasses']=dict(basic)
    for role,name in (('busy','appstart.ani'),('wait','hourglas.ani')):
        path=source/name;data=path.read_bytes();f,s,r=decode(data);schemes['Animated Hourglasses'][role]=store(path.stem,f,s,r,name,hashlib.sha256(data).hexdigest())
    schemes['Windows Standard']=dict(basic)
    plus=ROOT/'private/cabsets/plus95'
    if plus.is_dir():
        available={p.name.casefold():p for p in plus.iterdir()}
        inf=(ROOT/'private/reference/media/plus/PLUS.INF').read_text(encoding='cp1252')
        aliases={long.casefold():short.casefold() for short,long in re.findall(r'([\w~]+\.(?:CUR|ANI|THM))<([^>]+)>',inf,re.I)}
        plus_keys={}
        for path in sorted(plus.iterdir()):
            if path.suffix.casefold() not in ('.cur','.ani'):continue
            data=path.read_bytes();f,s,r=decode(data);plus_keys[path.name.casefold()]=store('plus-'+path.stem.lower(),f,s,r,'Plus95/'+path.name,hashlib.sha256(data).hexdigest())
        names={short.casefold():Path(long).stem for short,long in re.findall(r'([\w~]+\.THM)<([^>]+)>',inf,re.I)}
        for theme in sorted(plus.glob('*.THM')):
            if theme.name=='DEFAULT.THM':continue
            parser=configparser.ConfigParser(interpolation=None,strict=False)
            text=theme.read_text(encoding='cp1252')
            section=re.search(r'(?im)^\[Control Panel\\Cursors\]\s*\n([^\[]*)',text)
            if not section:raise ValueError('Missing theme cursor section: '+theme.name)
            parser.read_string('[Control Panel\\Cursors]\n'+section.group(1))
            mapping=dict(basic)
            for key,value in parser['Control Panel\\Cursors'].items():
                if key not in REGISTRY or not value:continue
                filename=value.split('%')[-1].split('\\')[-1].casefold();short=aliases.get(filename,filename)
                if short not in plus_keys:raise ValueError('Missing theme pointer: '+value)
                mapping[REGISTRY[key]]=plus_keys[short]
            schemes['Plus! / '+names.get(theme.name.casefold(),theme.stem)]=mapping
        # Original extra animated cursors are also directly selectable, not hidden in a file browser.
        used={asset for name,mapping in schemes.items() if name.startswith('Plus! / ') for asset in mapping.values()}
        for path in sorted(plus.glob('*.ANI')):
            key=plus_keys[path.name.casefold()]
            if key not in used:schemes['Plus! / Animated / '+path.stem.title()]={**basic,'arrow':key}
    catalog={'schemes':schemes,'assets':assets,'note':'Original private media assets; basic XOR inversion masks retained separately.'}
    (output/'pointer-schemes.json').write_text(json.dumps(catalog,indent=2)+'\n')
    print(json.dumps({'schemes':len(schemes),'cursor_assets':len(assets),'frames':sum(len(a['frames']) for a in assets.values()),'names':list(schemes)}))
if __name__=='__main__':main()
