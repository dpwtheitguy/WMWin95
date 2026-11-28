"""Stage independently measured native Plus theme file/confirmation controls."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]

def stage(output):
    from stage_command_button_assets import read_bmp
    from pixels import write
    output=Path(output);output.mkdir(parents=True,exist_ok=True);records=[]
    cases=(('save','save-current-metadata','Save Theme'),('open','selected-nature-metadata','Open Theme'))
    for state,folder,title in cases:
        source=ROOT/'private/theme-customization-20261127'/folder
        meta=json.loads((source/'STATE.JSN').read_text());w,h,p=read_bmp(source/'STATE.BMP')
        if meta['title']!=title or meta['size']!=[426,264] or(w,h)!=(426,264):raise ValueError('Unverified native theme file dialog.')
        expected=((1152,'Edit',[84,201,233,20]),(1136,'ComboBox',[84,227,233,21]),(1,'Button',[336,201,75,23]),(2,'Button',[336,230,75,23]))
        for ident,cls,rect in expected:
            if not any(c['id']==ident and c['class']==cls and c['rect']==rect for c in meta['controls']):raise ValueError('Native theme file control geometry changed.')
        # Product template only. Dynamic names/files/fields are drawn by the
        # implementation; the untouched BMP remains independent evidence.
        for x,y,cw,ch in ((11,57,404,134),(86,203,229,16),(80,29,187,18)):
            for yy in range(y,y+ch):p[yy*w+x:yy*w+x+cw]=[(255,255,255,255)]*cw
        filename='theme-file-'+state+'-frame.png';write(output/filename,w,h,p)
        records.append({'source':str((source/'STATE.BMP').relative_to(ROOT)),'reference_sha256':hashlib.sha256((source/'STATE.BMP').read_bytes()).hexdigest(),'metadata_sha256':hashlib.sha256((source/'STATE.JSN').read_bytes()).hexdigest(),'output':filename,'type':'SCREEN_CAPTURE_CONTROL','profile':'plus-ie4','dimensions':[w,h],'scope':'Native frame; dynamic fields/list cleared in product template, never baseline.'})
    source=ROOT/'private/theme-customization-20261127/delete-owned-metadata';meta=json.loads((source/'STATE.JSN').read_text());w,h,p=read_bmp(source/'STATE.BMP')
    if meta['size']!=[366,119] or(w,h)!=(366,119):raise ValueError('Unverified native theme delete question.')
    for ident,rect in ((6,[105,82,75,23]),(7,[186,82,75,23])):
        if not any(c['id']==ident and c['rect']==rect for c in meta['controls']):raise ValueError('Unverified native theme confirmation buttons.')
    write(output/'theme-delete-frame.png',w,h,p)
    records.append({'source':str((source/'STATE.BMP').relative_to(ROOT)),'reference_sha256':hashlib.sha256((source/'STATE.BMP').read_bytes()).hexdigest(),'metadata_sha256':hashlib.sha256((source/'STATE.JSN').read_bytes()).hexdigest(),'output':'theme-delete-frame.png','type':'SCREEN_CAPTURE_CONTROL','profile':'plus-ie4','dimensions':[w,h]})
    return records

if __name__=='__main__':
    sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
    print(json.dumps(stage(ROOT/'private/theme-customization-assets'),indent=2))
