#!/usr/bin/env python3
"""Compare the pre-cache builder with cold/warm incremental private bundles."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
SEEDS=('webview-strings.json','webview-verdana-regular.json','webview-verdana-bold.json')


def snapshot(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(root.rglob('*'))if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline-commit',default='b7b7876')
    args=parser.parse_args();directory=args.output.resolve()
    if not directory.is_relative_to(ROOT/'private'):parser.error('Original assets remain private.')
    directory.mkdir(parents=True,exist_ok=False);bundle=directory/'bundle';bundle.mkdir()
    seed=directory/'seed';seed.mkdir()
    for name in SEEDS:
        source=ROOT/'private/shell-assets'/name
        if source.exists():shutil.copyfile(source,seed/name)
    def reseed():
        for source in seed.iterdir():shutil.copyfile(source,bundle/source.name)
    reseed()
    original=subprocess.check_output(['git','show',args.baseline_commit+':tools/prepare_assets.py'],cwd=ROOT,text=True)
    needle="output=ROOT/'private/shell-assets'"
    if original.count(needle)!=1:raise ValueError('Unsupported baseline builder.')
    original=original.replace(needle,'output=Path('+repr(str(bundle))+')',1).replace('stage_mouse_animation()','stage_mouse_animation(output)').replace('stage_pointer_schemes()','stage_pointer_schemes(output)')
    driver=directory/'reference_builder.py'
    driver.write_text('exec(compile('+repr(original)+','+repr(str(ROOT/'tools/prepare_assets.py'))+',"exec"),{"__file__":'+repr(str(ROOT/'tools/prepare_assets.py'))+',"__name__":"__main__"})\n')
    results=[]
    def run(label,command):
        started=time.perf_counter()
        with (directory/(label+'.log')).open('w')as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        results.append({'name':label,'seconds':round(time.perf_counter()-started,4)})
    run('legacy',[sys.executable,str(driver)])
    expected=snapshot(bundle);(directory/'expected-files.json').write_text(json.dumps(expected,indent=2)+'\n')
    shutil.copytree(bundle,directory/'legacy-files')
    shutil.rmtree(bundle);bundle.mkdir();reseed()
    common=[sys.executable,str(ROOT/'tools/prepare_assets.py'),'--output',str(bundle),'--cache-dir',str(directory/'cache')]
    run('cold',[*common,'--report',str(directory/'cold-report.json')])
    actual=snapshot(bundle)
    if actual!=expected:raise AssertionError('Cold builder differs: '+repr([name for name in set(actual)|set(expected)if actual.get(name)!=expected.get(name)][:20]))
    run('warm',[*common,'--report',str(directory/'warm-report.json')])
    if snapshot(bundle)!=expected:raise AssertionError('Warm cache changed bundle bytes.')
    warm=json.loads((directory/'warm-report.json').read_text())
    if warm['hits']!=len(warm['stages']):raise AssertionError('Not every unchanged stage was reused: '+repr(warm['stages']))
    report={'baseline_commit':args.baseline_commit,'conditions':'Same checkout, runtime, immutable original inputs and optional WebView seed metadata; all file paths and SHA256 compared.','files':len(expected),'legacy_cold_warm_equal':True,'runs':results,'warm_hits':warm['hits']}
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
