#!/usr/bin/env python3
"""Inventory original INF sound assignments; do not invent missing event sounds."""
import hashlib,json,re,shutil,wave
from pathlib import Path
root=Path(__file__).resolve().parents[1];source=root/'private/cabsets/windows95';inf=source/'motown.inf';text=inf.read_text(encoding='cp1252');strings={}
section=''
for line in text.splitlines():
    line=line.strip()
    if line.startswith('['):section=line.lower()
    if section=='[strings]' and '=' in line and not line.startswith(';'):
        key,value=line.split('=',1);strings[key.strip().lower()]=value.strip().strip('"')
def expand(value):return re.sub(r'%([^%]+)%',lambda m:strings.get(m.group(1).lower(),m.group(0)),value)
rows=[]
for n,line in enumerate(text.splitlines(),1):
    match=re.match(r'HKCU,%KEY_DEF%\\([^\\]+)\\\.(Default|Current),[^,]*,[^,]*,(.*)',line,re.I)
    if not match:continue
    event,scheme,value=match.groups();rows.append({'event':event,'scheme':scheme,'declared_path':expand(value.strip().strip('"')) or None,'assignment':'declared_silent' if not value.strip() else 'declared_file','source':'motown.inf','source_line':n,'installed_registry_verified':False})
output=root/'private/sound-assets';output.mkdir(exist_ok=True);asset=source/'mssound.wav';shutil.copyfile(asset,output/asset.name)
with wave.open(str(asset)) as w:audio={'channels':w.getnchannels(),'sample_rate':w.getframerate(),'sample_width_bytes':w.getsampwidth(),'frames':w.getnframes()}
report={'source_inf_sha256':hashlib.sha256(inf.read_bytes()).hexdigest(),'events':rows,'startup_asset':{'source':'mssound.wav','renamed_by_inf':'The Microsoft Sound.wav','sha256':hashlib.sha256(asset.read_bytes()).hexdigest(),**audio},'status':'Source assignments only; installed registry and playback validation pending'}
(output/'events.json').write_text(json.dumps(report,indent=2)+'\n');print('Inventoried',len(rows),'source event assignments; no playback enabled')
