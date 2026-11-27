#!/usr/bin/env python3
"""Stage reviewed Windows95 Network art and bounded Win16 dialog geometry."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from resources import extract
from pixels import read,write

def parse_win16_dialog(data):
    offset=0
    def take(fmt):
        nonlocal offset
        size=struct.calcsize(fmt)
        if offset+size>len(data):raise ValueError('Truncated Win16 dialog template')
        values=struct.unpack_from(fmt,data,offset);offset+=size;return values[0] if len(values)==1 else values
    def text(atom=False):
        nonlocal offset
        first=take('<B')
        if first==0:return ''
        if first==255:return take('<H')
        if atom and first>=128:return first
        start=offset-1
        try:end=data.index(0,start)
        except ValueError as error:raise ValueError('Unterminated Win16 dialog string') from error
        if end-start>4096:raise ValueError('Win16 dialog string exceeds limit')
        offset=end+1;return data[start:end].decode('cp1252')
    style=take('<I');count=take('<B');rect=list(take('<hhhh'))
    result={'style':style,'rect':rect,'menu':text(),'class':text(),'caption':text(),'controls':[]}
    if style&64:result['font']={'points':take('<H'),'face':text()}
    for _ in range(count):
        x,y,w,h,ident,flags=take('<hhhhHI');control={'rect':[x,y,w,h],'id':ident,'style':flags,'class':text(True),'text':text()}
        size=take('<B')
        if offset+size>len(data):raise ValueError('Truncated Win16 creation data')
        offset+=size;result['controls'].append(control)
    return result

def stage(output):
    output.mkdir(parents=True,exist_ok=True);records=[]
    source=ROOT/'private/screenshots/network-native-reviewed-20261126'
    for name in ('configuration','identification','access'):
        path=source/f'network-{name}.png';w,h,pixels=read(path);x,y,cw,ch=0,0,366,460
        image=[pixels[(y+yy)*w+x+xx] for yy in range(ch) for xx in range(cw)]
        dest=output/f'network-{name}-frame.png';write(dest,cw,ch,image)
        records.append({'source':str(path.relative_to(ROOT)),'profile':'Win95OSR2.5IE4','type':'SCREEN_CAPTURE_CONTROL','rectangle':[x,y,cw,ch],'output':dest.name,'reference_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    for index,name in enumerate(('bindings','advanced','netbios','dns','gateway','wins','ip')):
        path=source/f'tcpip-measured-page-{index}.png';w,h,pixels=read(path);x,y,cw,ch=29,67,356,437
        dest=output/f'network-tcpip-{name}-frame.png'
        write(dest,cw,ch,[pixels[(y+yy)*w+x+xx] for yy in range(ch) for xx in range(cw)])
        records.append({'source':str(path.relative_to(ROOT)),'profile':'Win95OSR2.5IE4','type':'SCREEN_CAPTURE_CONTROL','rectangle':[x,y,cw,ch],'output':dest.name,'reference_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    dialogs=[]
    for filename in ('netdi.dll','mstcp.dll'):
        path=ROOT/'private/cabsets/windows95'/filename
        if not path.exists():continue
        for kind,ident,lang,data,fmt in extract(path.read_bytes()):
            if kind!=5 or fmt!='NE':continue
            parsed=parse_win16_dialog(data);dialogs.append({'source':filename,'id':ident,'sha256':hashlib.sha256(data).hexdigest(),**parsed})
    (output/'network-native-dialogs.json').write_text(json.dumps(dialogs,indent=2)+'\n')
    (output/'network-assets-provenance.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps({'frames':len(records),'native_dialog_templates':len(dialogs)}));return records
if __name__=='__main__':stage(ROOT/'private/shell-assets')
