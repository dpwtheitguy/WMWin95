#!/usr/bin/env python3
"""Stage reviewed native CPL art privately, retaining independent provenance."""
import hashlib
import json,re,struct
from pathlib import Path
from resources import extract
from pixels import read,write
from win95lx.assets.bitmap import icon_dib,word

ROOT=Path(__file__).resolve().parents[1]

def stage(output):
    records=[]
    registry=ROOT/'private/reference/classic-installed-versions/START.REG'
    if registry.exists():
        from win95lx.control_panel.datetime_settings import NATIVE_ZONE_MAP
        rows=[]
        for section in registry.read_text(errors='strict').split('\n\n'):
            header=section.split('\n')[0]
            if '\\Time Zones\\' not in header:continue
            key=header.rsplit('\\',1)[-1].rstrip(']')
            display=re.search(r'^"Display"="(.*)"',section,re.M)
            raw=re.search(r'^"TZI"=hex:([\da-fA-F,\\\s]+)',section,re.M)
            if key not in NATIVE_ZONE_MAP or not display or not raw:raise ValueError('Unmapped original time zone: '+key)
            encoded=bytes.fromhex(raw[1].replace(',',' ').replace('\\',' '));offset=-struct.unpack_from('<i',encoded)[0]
            zone,expected=NATIVE_ZONE_MAP[key]
            if offset!=expected:raise ValueError('Original time-zone bias differs from the mapping: '+key)
            rows.append({'id':key,'display':display[1],'zone':zone,'offset':offset})
        if len(rows)!=52:raise ValueError('Expected all 52 original time zones.')
        dest=output/'native-timezones.json';dest.write_text(json.dumps({'zones':sorted(rows,key=lambda row:(row['offset'],row['display']))},indent=2)+'\n')
        records.append({'source':str(registry.relative_to(ROOT)),'source_sha256':hashlib.sha256(registry.read_bytes()).hexdigest(),
                        'type':'TIME_ZONE_CATALOG','output':dest.name,'count':len(rows)})
    captures=ROOT/'private/screenshots/cpl-20261126'
    # Individually reviewed origins; no heuristics or cross-profile resizing.
    definitions={
        'keyboard':(('speed','language','general'),(66,66,404,448)),
        'regional':(('regional','number','currency','time','date'),(110,110,404,448)),
        'datetime':(('datetime','timezone'),(132,132,404,341)),
        'system':(('general','devices','hardware-profiles','performance'),(0,0,408,448)),
    }
    for applet,(tabs,rect) in definitions.items():
        for tab in tabs:
            source=captures/'classic-reviewed-run2'/f'{applet}-{tab}.png'
            if not source.exists():continue
            sw,sh,pixels=read(source);x,y,w,h=rect
            if x+w>sw or y+h>sh:raise ValueError('Reference crop exceeds framebuffer')
            image=[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)]
            if applet=='system' and tab=='general':
                # Never distribute a reference owner's identity or OEM key as art.
                for yy in range(66,307):
                    image[yy*w+210:yy*w+399]=[(192,192,192,255)]*189
            filename=f'{applet}-{tab}-frame.png';write(output/filename,w,h,image)
            records.append({'source':str(source.relative_to(ROOT)),'type':'SCREEN_CAPTURE_CONTROL','profile':'classic',
                            'rectangle':rect,'output':filename,'reference_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                            'dynamic_content_removed':applet=='system' and tab=='general'})
    source=captures/'plus-sounds-index1.png'
    if source.exists():
        sw,sh,pixels=read(source);x,y,w,h=66,66,366,448
        dest='sounds-sounds-frame.png'
        write(output/dest,w,h,[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
        records.append({'source':str(source.relative_to(ROOT)),'type':'SCREEN_CAPTURE_CONTROL','profile':'plus',
                        'rectangle':[x,y,w,h],'output':dest,'reference_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    from stage_sound_library import stage as stage_sounds
    records.extend(stage_sounds(output))
    groups={'keyboard':('main.cpl',200),'fonts':('main.cpl',400),'printers':('main.cpl',300),
            'datetime':('timedate.cpl',200),'regional':('intl.cpl',101),'system':('sysdm.cpl',600),
            'multimedia':('mmsys.cpl',99),'sounds':('mmsys.cpl',100),
            'network':('netcpl.cpl',100),'addremove':('appwiz.cpl',1500),
            'accessibility':('access.cpl',110),'modems':('modem.cpl',1000)}
    for name,(filename,ident) in groups.items():
        source=ROOT/'private/cabsets/windows95'/filename
        resources=list(extract(source.read_bytes()))
        group=next(data for kind,key,lang,data,fmt in resources if kind==14 and key==ident)
        entries=[group[6+i*14:20+i*14] for i in range(word(group,4))]
        for size in (16,32):
            variants=[e for e in entries if e[:2]==bytes((size,size))]
            if not variants:continue
            entry=next((e for e in variants if word(e,6)==4),variants[0]);image_id=word(entry,12)
            data=next(data for kind,key,lang,data,fmt in resources if kind==3 and key==image_id)
            w,h,pixels=icon_dib(data);dest=f'cpl-{name}-{size}.png';write(output/dest,w,h,pixels)
            records.append({'source':filename,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                            'type':'GROUP_ICON','id':ident,'image_id':image_id,'output':dest,'dimensions':[w,h]})
    for name,source_name in (('keyboard-add-language','keyboard-add-language-dialog.png'),('keyboard-language-properties','keyboard-add-language-actual.png')):
        source=captures/source_name
        if source.exists():
            sw,sh,pixels=read(source);x,y,w,h=33,55,347,171
            write(output/(name+'.png'),w,h,[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
            records.append({'source':str(source.relative_to(ROOT)),'type':'SCREEN_CAPTURE_CONTROL','output':name+'.png',
                            'rectangle':[x,y,w,h],'reference_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    descriptions={}
    for name,filename,identifier in (('Mouse','main.cpl',101),('Keyboard','main.cpl',103),('Fonts','main.cpl',107),('Printers','main.cpl',105),
                                     ('Date/Time','timedate.cpl',301),('Regional Settings','intl.cpl',2),('System','sysdm.cpl',201),
                                     ('Multimedia','mmsys.cpl',4868),('Sounds','mmsys.cpl',4870),('Passwords','password.cpl',2003),('Accessibility Options','access.cpl',5)):
        source=ROOT/'private/cabsets/windows95'/filename
        for kind,key,lang,bits,fmt in extract(source.read_bytes()):
            if kind!=6 or key!=(identifier//16)+1:continue
            offset=0
            for index in range(16):
                prefix=1 if fmt=='NE' else 2
                count=int.from_bytes(bits[offset:offset+prefix],'little');offset+=prefix
                length=count*(1 if fmt=='NE' else 2);value=bits[offset:offset+length].decode('cp1252' if fmt=='NE' else 'utf-16le');offset+=length
                if index==identifier%16:descriptions[name]=value
        records.append({'source':filename,'type':'STRING','id':identifier,'output':'cpl-descriptions.json','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    (output/'cpl-descriptions.json').write_text(json.dumps(descriptions,indent=2)+'\n')
    return records

if __name__=='__main__':
    import json
    print(json.dumps(stage(ROOT/'private/shell-assets'),indent=2))
