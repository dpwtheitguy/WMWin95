"""Measured Plus Display Screen Saver page; original evidence stays untouched."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def stage(output):
    from stage_command_button_assets import read_bmp
    from pixels import write
    source=ROOT/'private/theme-customization-20261127/saver-ie4-native';meta=json.loads((source/'STATE.JSN').read_text());w,h,p=read_bmp(source/'STATE.BMP')
    if meta['title']!='Display Properties'or meta['size']!=[404,448]or(w,h)!=(404,448):raise ValueError('Unverified Screen Saver frame.')
    for identity,rect in ((1000,[33,261,173,21]),(1003,[211,259,75,23]),(1004,[292,259,75,23]),(1006,[273,290,30,20])):
        if not any(c['id']==identity and c['rect']==rect and c['visible'] for c in meta['controls']):raise ValueError('Screen saver control geometry mismatch.')
    spinner=next(c for c in meta['controls']if c['id']==1007 and c['class']=='msctls_updown')
    if(spinner['range_lower'],spinner['range_upper'])!=(1,60):raise ValueError('Unverified native wait range.')
    output=Path(output);output.mkdir(parents=True,exist_ok=True);write(output/'display-screen-saver.png',w,h,p)
    selected=ROOT/'private/theme-customization-20261127/saver-nature-native';selected_meta=json.loads((selected/'STATE.JSN').read_text());sw,sh,sp=read_bmp(selected/'STATE.BMP')
    if not any(c['id']==1007 and c['class']=='msctls_updown' and c['enabled'] and c['rect']==[301,290,17,20] for c in selected_meta['controls']):raise ValueError('Unverified enabled spin control.')
    pixels=[sp[yy*sw+xx]for yy in range(290,310)for xx in range(301,318)]
    write(output/'display-screen-saver-spin-enabled.png',17,20,pixels)
    return [{'source':str(source.relative_to(ROOT)),'output':'display-screen-saver.png','type':'SCREEN_CAPTURE_CONTROL','profile':'ie4','dimensions':[w,h],'reference_sha256':hashlib.sha256((source/'STATE.BMP').read_bytes()).hexdigest(),'metadata_sha256':hashlib.sha256((source/'STATE.JSN').read_bytes()).hexdigest()},{'source':str(selected.relative_to(ROOT)),'output':'display-screen-saver-spin-enabled.png','type':'SCREEN_CAPTURE_CONTROL','profile':'plus-ie4','dimensions':[17,20],'source_rect':[301,290,17,20],'reference_sha256':hashlib.sha256((selected/'STATE.BMP').read_bytes()).hexdigest(),'metadata_sha256':hashlib.sha256((selected/'STATE.JSN').read_bytes()).hexdigest()}]
if __name__=='__main__':
    import sys;sys.path.insert(0,str(ROOT/'tools'));print(stage(ROOT/'private/shell-assets'))
