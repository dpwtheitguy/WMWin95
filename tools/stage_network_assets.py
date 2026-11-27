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
    # Native IPAddress uses stock System, not the dialog's MS Sans Serif.
    from win95lx.assets.bitmap import BitmapFont,word
    font_source=ROOT/'private/cabsets/windows95/vgasys.fon'
    font_data=next(data for kind,ident,lang,data,fmt in extract(font_source.read_bytes()) if kind==8 and ident==31)
    font=BitmapFont(font_data)
    if (font.face,font.height,font.ascent,word(font_data,76),word(font_data,83))!=('System',16,13,3,700):raise ValueError('Unexpected native IPAddress font metrics')
    dest=output/'network-ip-system.fnt';dest.write_bytes(font_data)
    records.append({'source':str(font_source.relative_to(ROOT)),'type':'FONT_RESOURCE','resource_id':31,'output':dest.name,'reference_sha256':hashlib.sha256(font_source.read_bytes()).hexdigest(),'resource_sha256':hashlib.sha256(font_data).hexdigest(),'metrics':{'face':font.face,'height':16,'ascent':13,'internal_leading':3,'weight':700}})
    # Original USER BUTTON radio states, independently captured at 96 dpi.
    from stage_command_button_assets import read_bmp
    radio_source=ROOT/'private/reference-tools/network-radios-native-20261126'
    state_map={0:'normal-unchecked',1:'normal-checked',4:'pressed-unchecked',5:'pressed-checked',6:'disabled-unchecked',7:'disabled-checked'}
    metadata=json.loads((radio_source/'captures/STATES.JSN').read_text())
    radio_cases=[]
    for row in metadata['states']:
        label,state=row['label_index'],row['state_index']
        if row['font_height']!=13 or row['height']!=16 or row['style']&15!=9 or not row['saved']:raise ValueError('Unexpected native Network radio profile')
        original=radio_source/'captures'/f'B0{label}{state}.BMP';rw,rh,rp=read_bmp(original)
        dest=output/f'network-radio-reference-{label}-{state}.png';write(dest,rw,rh,rp)
        radio_cases.append({**row,'file':dest.name,'source':str(original.relative_to(ROOT)),'source_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'png_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'raw_label':('&Obtain an IP address automatically','&Specify an IP address:')[label]})
        if label==0 and state in state_map:
            dest=output/f'network-radio-{state_map[state]}.png'
            write(dest,13,13,[rp[(yy+3)*rw+xx+2] for yy in range(13) for xx in range(13)])
            records.append({'source':str(original.relative_to(ROOT)),'type':'NATIVE_RADIO_GLYPH','profile':'Win95OSR2.5IE4 BS_AUTORADIOBUTTON 96dpi MS Sans Serif13','rectangle':[2,3,13,13],'output':dest.name,'reference_sha256':hashlib.sha256(original.read_bytes()).hexdigest()})
    (output/'network-radio-states.json').write_text(json.dumps({'profile':'Win95OSR2.5IE4,96dpi,standard colors,13px MS Sans Serif,16px single-line BS_AUTORADIOBUTTON','cases':radio_cases,'native_metadata_sha256':hashlib.sha256((radio_source/'captures/STATES.JSN').read_bytes()).hexdigest(),'native_harness_sha256':hashlib.sha256((radio_source/'command-buttons.c').read_bytes()).hexdigest(),'native_binary_sha256':hashlib.sha256((radio_source/'W95BTNS.EXE').read_bytes()).hexdigest(),'network_normal_equivalence':json.loads((radio_source/'equivalence.json').read_text())},indent=2)+'\n')
    dialogs=[]
    for filename in ('netdi.dll','mstcp.dll'):
        path=ROOT/'private/cabsets/windows95'/filename
        if not path.exists():continue
        for kind,ident,lang,data,fmt in extract(path.read_bytes()):
            if kind!=5 or fmt!='NE':continue
            parsed=parse_win16_dialog(data);dialogs.append({'source':filename,'id':ident,'sha256':hashlib.sha256(data).hexdigest(),**parsed})
    (output/'network-native-dialogs.json').write_text(json.dumps(dialogs,indent=2)+'\n')
    (output/'network-assets-provenance.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps({'frames':sum(record['type']=='SCREEN_CAPTURE_CONTROL' for record in records),'fonts':sum(record['type']=='FONT_RESOURCE' for record in records),'radio_glyphs':sum(record['type']=='NATIVE_RADIO_GLYPH' for record in records),'native_dialog_templates':len(dialogs)}));return records
if __name__=='__main__':stage(ROOT/'private/shell-assets')
