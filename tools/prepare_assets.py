#!/usr/bin/env python3
"""Prepare private original assets with content-verified stage reuse."""
import argparse
import ast
from contextlib import redirect_stdout
import hashlib
import importlib
import io
import json
import platform
from pathlib import Path
import subprocess
import sys
import time
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
SEEDS=('webview-strings.json','webview-verdana-regular.json','webview-verdana-bold.json')


def code_dependencies(module):
    pending=[module];seen=set();paths=set()
    while pending:
        name=pending.pop()
        if name in seen:continue
        seen.add(name)
        path=next((p for p in (ROOT/'tools'/(name.replace('.','/')+'.py'),ROOT/'src'/(name.replace('.','/')+'.py'),ROOT/'src'/name.replace('.','/')/'__init__.py')if p.is_file()),None)
        if path is None:continue
        paths.add(path)
        tree=ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):pending.extend(a.name for a in node.names)
            elif isinstance(node,ast.ImportFrom):
                base=node.module or ''
                if node.level:
                    parent=name.split('.')[:-node.level]
                    base='.'.join(parent+([base]if base else []))
                if base:pending.append(base)
                pending.extend(base+'.'+a.name for a in node.names if a.name!='*'and base)
    return sorted(paths)


def environment():
    # Native conversion/font dependencies are conservatively part of every key.
    result={'root':str(ROOT),'python':sys.version,'platform':platform.platform(),'zlib':zlib.ZLIB_RUNTIME_VERSION}
    import cairo
    try:
        import PIL
        pillow=PIL.__version__
    except ImportError:pillow='not-installed'
    result.update(cairo=cairo.cairo_version_string(),pycairo=cairo.version,pillow=pillow)
    packages=subprocess.run(['dpkg-query','-W','-f=${binary:Package}\t${Version}\n'],capture_output=True,text=True,check=False)
    result['distribution_packages_sha256']=hashlib.sha256(packages.stdout.encode()).hexdigest()if packages.returncode==0 else 'unavailable'
    for name in ('LANG','LC_ALL','LC_CTYPE','FONTCONFIG_FILE','FONTCONFIG_PATH'):
        result[name]=__import__('os').environ.get(name)
    for name in ('/etc/fonts','/usr/share/fontconfig','/usr/share/fonts',str(Path.home()/'.local/share/fonts')):
        # Passed as explicit dependencies by main; includes existence and names.
        result.setdefault('font_environment_paths',[]).append(name)
    return result


def mouse(output):
    import stage_mouse_animation
    stage_mouse_animation.main(output)
    return [{'source':'MAIN.CPL AVI 100','type':'ANIMATION_FRAME','output':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(output.glob('mouse-test-*'))]


def pointers(output):
    import stage_pointer_schemes
    stage_pointer_schemes.main(output)
    catalog=json.loads((output/'pointer-schemes.json').read_text());records=[]
    for definition in catalog['assets'].values():
        for frame in definition['frames']:
            for filename in (frame['file'],str(Path(frame['file']).with_suffix('.json'))):
                records.append({'source':definition['source'],'type':'CURSOR_FRAME','output':filename,'source_sha256':definition['source_sha256'],'sha256':hashlib.sha256((output/filename).read_bytes()).hexdigest()})
    return records


def savers(output):
    from stage_screensaver_assets import stage_bundle
    catalog=stage_bundle(output/'screensavers');records=[]
    for profile,definition in catalog.get('font_profiles',{}).items():
        for filename,digest in definition['files'].items():records.append({'source':'private/cabsets/windows95/'+filename,'type':'SCREENSAVER_FONT_PROFILE','profile':profile,'output':'screensavers/'+definition['directory']+'/'+filename,'sha256':digest})
    for identity,presentation in catalog['presentations'].items():
        for row in presentation['provenance']:records.append({'source':row['source'],'type':'SCREENSAVER_PACKAGE','presentation':identity,'output':'screensavers/'+presentation['directory']+'/'+row['installed'],'sha256':row['sha256']})
    records.append({'source':'original Windows95 and Plus95 private assets','type':'SCREENSAVER_CATALOG','output':'screensavers/catalog.json','sha256':hashlib.sha256((output/'screensavers/catalog.json').read_bytes()).hexdigest()})
    return records


def descriptions(output):
    themes=json.loads((output/'themes-library.json').read_text());values=json.loads((output/'cpl-descriptions.json').read_text());values['Desktop Themes']=themes['description'];(output/'cpl-descriptions.json').write_text(json.dumps(values,indent=2)+'\n')
    return [{'source':'private/cabsets/plus95/THEMES.CPL','type':'STRING','id':3,'output':'cpl-descriptions.json','source_sha256':hashlib.sha256((ROOT/'private/cabsets/plus95/THEMES.CPL').read_bytes()).hexdigest()}]


def fonts(output):
    from collect_font_library import collect
    return [{'source':row['source'],'profile':row['product'],'type':'FONT_COLLECTION','output':'font-library/'+row['file'],'source_sha256':row['sha256'],'faces':len(row['faces']),'readable':row['readable']}for row in collect(output/'font-library')['fonts']]


def validate_locations(output,cache_dir,inputs):
    private=(ROOT/'private').resolve()
    for label,path in (('output',output),('cache',cache_dir)):
        if path is None:continue
        path=path.resolve()
        if not path.is_relative_to(private):raise ValueError('Original assets and cache blobs must remain private.')
        for source in inputs:
            source=source.resolve()
            if path.is_relative_to(source)or source.is_relative_to(path):
                raise ValueError('Asset '+label+' must not overlap original input paths.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'private/shell-assets')
    parser.add_argument('--cache-dir',type=Path,default=ROOT/'private/asset-stage-cache')
    parser.add_argument('--force',action='store_true',help='Rebuild every stage instead of reusing entries.')
    parser.add_argument('--no-cache',action='store_true',help='Run all stages without reading or writing the cache.')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args();output=args.output.resolve()
    if not output.is_relative_to((ROOT/'private').resolve()):parser.error('Original assets must remain inside private/.')
    dependencies=json.loads((ROOT/'config/asset-stage-dependencies.json').read_text())['stages']
    try:validate_locations(output,None if args.no_cache else args.cache_dir,[ROOT/p for stage in dependencies.values()for p in stage['private_inputs']])
    except ValueError as error:parser.error(str(error))
    output.mkdir(parents=True,exist_ok=True)
    from asset_cache import StageCache
    cache=None if args.no_cache else StageCache(output,args.cache_dir,force=args.force)
    conditions=environment();conditions['output']=str(output)
    external=[Path(p)for p in conditions['font_environment_paths']]
    jobs=[('prepare_base_assets','stage'),('stage_mouse_animation',mouse),('stage_pointer_schemes',pointers)]
    jobs += [(name,'stage')for name in ('stage_control_panel_assets','stage_multimedia_assets','stage_sound_library','stage_command_button_assets','stage_accessibility_assets','stage_namespace_drop_assets','stage_printers_assets','stage_theme_assets','stage_theme_icons','stage_theme_appearance','stage_theme_customization_assets','stage_screen_saver_ui')]
    jobs += [('stage_screensaver_assets',savers),('theme_descriptions',descriptions),('stage_fonts_assets','stage'),('collect_font_library',fonts)]
    records=[];upstream=set();report=[];started=time.perf_counter()
    for name,entry in jobs:
        if name not in dependencies:raise ValueError('Missing stage dependency declaration: '+name)
        roots=[ROOT/p for p in dependencies[name]['private_inputs']]
        module=name if name!='theme_descriptions'else 'prepare_assets'
        code=code_dependencies(module)+[Path(__file__).resolve(),ROOT/'config/asset-stage-dependencies.json']
        builder=(lambda name=name:importlib.import_module(name).stage(output))if entry=='stage'else(lambda entry=entry:entry(output))
        begin=time.perf_counter()
        with redirect_stdout(io.StringIO()):
            if cache:
                result=cache.run(name,builder,dependencies=roots+code+external,upstream=sorted(upstream)+([output/p for p in SEEDS]if name=='prepare_base_assets'else []),conditions=conditions)
                if cache.report[-1].get('reason')=='inputs-changed':
                    raise RuntimeError('Asset inputs changed during preparation; retry with stable inputs.')
                upstream.difference_update(cache.stage_deleted.get(name,[]));upstream.update(cache.stage_outputs[name])
            else:result=builder()
        records.extend(result)
        report.append(cache.report[-1]if cache else {'name':name,'status':'uncached','seconds':round(time.perf_counter()-begin,4)})
    records.append({'source':'original Windows95 and Plus95 private assets','type':'CURSOR_CATALOG','output':'pointer-schemes.json','sha256':hashlib.sha256((output/'pointer-schemes.json').read_bytes()).hexdigest()})
    (output/'manifest.json').write_text(json.dumps({'assets':records,'original_media_sha256':'c13b6bad0dcbd4f13c3d840d2b7efe939c6d4e40b1c63f086a5f92edfb1e9b77'},indent=2)+'\n')
    summary={'stages':report,'seconds':round(time.perf_counter()-started,4),'assets':len(records),'output':str(output),'hits':sum(r['status']=='hit'for r in report)}
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items()if k!='stages'}))

if __name__=='__main__':main()
