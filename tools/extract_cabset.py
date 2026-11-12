#!/usr/bin/env python3
"""Extract a cabinet chain with explicit private-tool paths and provenance."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('cab',type=Path); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
root=Path(__file__).resolve().parents[1]; binary=root/'private/runtime/root/usr/bin/cabextract'; lib=root/'private/runtime/root/usr/lib/x86_64-linux-gnu'
a.output.mkdir(parents=True,exist_ok=False); env=os.environ.copy(); env['LD_LIBRARY_PATH']=str(lib)
result=subprocess.run([str(binary),'-d',str(a.output.resolve()),str(a.cab.resolve())],env=env,capture_output=True,text=True)
(a.output/'extraction.log').write_text(result.stdout+result.stderr)
files=[]
for f in sorted(a.output.rglob('*')):
    if f.is_file() and f.name!='extraction.log': files.append({'name':str(f.relative_to(a.output)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'size':f.stat().st_size,'extraction_status':'extracted'})
cabs=[]
for f in sorted(a.cab.parent.iterdir()):
    if f.suffix.lower()=='.cab': cabs.append({'source':str(f.resolve()),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
report={'entry_cab':str(a.cab.resolve()),'cabextract_exit_code':result.returncode,'source_directory_cabinets':cabs,'provenance_note':'Cabinet directory hashes include candidate sibling cabinets; extraction log records the actual chain.','files':files,'warnings_and_errors':result.stderr}
(a.output/'cabset-inventory.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps({'files':len(files),'returncode':result.returncode,'log':str(a.output/'extraction.log')})); raise SystemExit(result.returncode)
