"""Stage measured, independently captured native Accessibility frames privately."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from pixels import read,write

def stage(output):
    output.mkdir(parents=True,exist_ok=True);base=ROOT/'private/accessibility-20261126';records=[];layouts={}
    pairs=[(f'access-{i}',f'accessibility-{tab}',f'accessibility-{tab}-frame.png') for i,tab in enumerate(('keyboard','sound','display','mouse','general'))]
    pairs.extend((f'{name}-0',f'{name}-settings',f'accessibility-{name}-settings-frame.png') for name in ('sticky','filter','toggle','amouse','abounce','aslow'))
    for meta,name,dest in pairs:
        path=base/'metadata'/(meta+'.JSN');source=base/'native'/(name+'.png')
        if not path.exists() or not source.exists():raise ValueError('Missing reviewed native Accessibility capture: '+name)
        data=json.loads(path.read_text());x,y=data['origin'];w,h=data['size'];sw,sh,pixels=read(source)
        if x<0 or y<0 or x+w>sw or y+h>sh:raise ValueError('Native Accessibility window exceeds its capture')
        write(output/dest,w,h,[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
        layouts[meta]=data
        records.append({'source':str(source.relative_to(ROOT)),'metadata':str(path.relative_to(ROOT)),'profile':'classic-OSR2.5','type':'SCREEN_CAPTURE_CONTROL','rectangle':[x,y,w,h],'output':dest,'reference_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'metadata_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    # Both states come from genuine controls, not an invented checkmark path.
    for state,filename,rect in (('unchecked','accessibility-keyboard-frame.png',(73,122,13,13)),('checked','accessibility-sticky-settings-frame.png',(24,151,13,13))):
        w,h,pixels=read(output/filename);x,y,cw,ch=rect;dest=f'accessibility-check-{state}.png';write(output/dest,cw,ch,[pixels[(y+yy)*w+x+xx] for yy in range(ch) for xx in range(cw)])
        records.append({'source':filename,'type':'MEASURED_CONTROL_CROP','rectangle':rect,'output':dest})
    for state,rect in (('checked',(24,151,13,13)),('unchecked',(24,179,13,13))):
        filename='accessibility-filter-settings-frame.png';w,h,pixels=read(output/filename);x,y,cw,ch=rect;dest=f'accessibility-radio-{state}.png';write(output/dest,cw,ch,[pixels[(y+yy)*w+x+xx] for yy in range(ch) for xx in range(cw)])
        records.append({'source':filename,'type':'MEASURED_CONTROL_CROP','rectangle':rect,'output':dest})
    library=ROOT/'private/cabsets/windows95/access.cpl';binary=library.read_bytes();tables={}
    for name,offset,expected in (('repeat_delay_ms',5792,(300,700,1000,1500,2000)),('repeat_rate_ms',5812,(300,500,700,1000,1500,2000)),('bounce_ms',5836,(500,700,1000,1500,2000)),('slow_ms',5856,(0,300,500,700,1000,1400,2000))):
        values=struct.unpack_from('<'+'I'*len(expected),binary,offset)
        if values!=expected:raise ValueError('Original ACCESS.CPL timing data changed; review this version before staging.')
        tables[name]=values;records.append({'source':'access.cpl','source_sha256':hashlib.sha256(binary).hexdigest(),'type':'REVIEWED_TIMING_DATA','offset':offset,'format':'little-endian uint32 milliseconds','name':name,'values':values})
    (output/'accessibility-native-timings.json').write_text(json.dumps(tables,indent=2)+'\n')
    (output/'accessibility-native-layout.json').write_text(json.dumps(layouts,indent=2)+'\n')
    (output/'accessibility-provenance.json').write_text(json.dumps(records,indent=2)+'\n')
    return records
if __name__=='__main__':print(json.dumps({'staged':len(stage(ROOT/'private/shell-assets'))}))
