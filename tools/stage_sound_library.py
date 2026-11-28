"""Collect every WAV from verified local source sets, preserving provenance."""
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
SOURCES=(('osr25','Windows 95 OSR2.5','windows95'),('rtm','Windows 95 RTM','windows95-osr1-all'),
         ('osr2','Windows 95 OSR2','windows95-rtm-all'),('plus','Plus! 95','plus95'))

def stage(output):
    records=[];library=[];content={}
    for tag,label,folder in SOURCES:
        directory=ROOT/'private/cabsets'/folder
        if not directory.exists():continue
        aliases={}
        infs=sorted(directory.glob('*.INF'))
        if tag=='plus':infs.append(ROOT/'private/reference/media/plus/PLUS.INF')
        for inf in infs:
            aliases.update({short.casefold():long for short,long in re.findall(r'([\w~]+\.WAV)<([^>]+)>',inf.read_text(errors='replace'),re.I)})
        for path in sorted(directory.iterdir()):
            if path.suffix.casefold()!='.wav':continue
            data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
            if digest not in content:
                dest=('sound-' if tag=='osr25' else f'sound-{tag}-')+path.name.lower()
                (output/dest).write_bytes(data);content[digest]=dest
            filename=content[digest];original=aliases.get(path.name.casefold(),path.name)
            row={'source':str(path.relative_to(ROOT)),'profile':label,'original_name':original,'file':filename,'sha256':digest}
            library.append(row);records.append({**row,'type':'WAVE','output':filename})
    from win95lx.control_panel.sound_preferences import KEYS
    schemes={};plus=ROOT/'private/cabsets/plus95'
    inf=(ROOT/'private/reference/media/plus/PLUS.INF').read_text(encoding='cp1252')
    names={short.casefold():Path(long).stem for short,long in re.findall(r'([\w~]+\.THM)<([^>]+)>',inf,re.I)}
    audio={row['original_name'].casefold():row['file'] for row in library}
    audio['the microsoft sound.wav']='sound-mssound.wav'
    for theme in sorted(plus.glob('*.THM')):
        if theme.name=='DEFAULT.THM':continue
        mapping={key:'' for key in sorted(KEYS)}
        sections=re.findall(r'\[AppEvents\\Schemes\\Apps\\([^\\]+)\\([^\\]+)\\.Current\]\s*\nDefaultValue=([^\r\n]*)',theme.read_text(encoding='cp1252'),re.I)
        for app,key,value in sections:
            if key not in KEYS:continue
            if value:
                name=value.split('%')[-1].split('\\')[-1].casefold()
                if name not in audio:raise ValueError('Missing Plus theme sound: '+value)
                mapping[key]=audio[name]
        schemes['Plus! / '+names.get(theme.name.casefold(),theme.stem)]=mapping
        records.append({'source':str(theme.relative_to(ROOT)),'type':'SOUND_SCHEME','source_sha256':hashlib.sha256(theme.read_bytes()).hexdigest(),'output':'sound-library.json'})
    (output/'sound-library.json').write_text(json.dumps({'sources':library,'schemes':schemes,'unique_audio_files':len(content),
        'coverage':'Local RTM, OSR2, OSR2.5 and Plus media. No separately verified OSR1 installation/media yet.'},indent=2)+'\n')
    return records
if __name__=='__main__':
    print(json.dumps(stage(ROOT/'private/shell-assets'),indent=2))
