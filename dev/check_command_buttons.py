#!/usr/bin/env python3
"""Compare reusable button rendering to independent original Win32 controls."""
import argparse,hashlib,json,sys,time,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--assets',type=Path);parser.add_argument('--size',default='800x600');a=parser.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    try:viewport_width,viewport_height=map(int,a.size.split('x'))
    except ValueError:parser.error('Use WIDTHxHEIGHT.')
    if viewport_width<320 or viewport_height<200:parser.error('The viewport is too small.')
    import cairo
    from win95lx.shell.widgets import Painter,FACE
    from win95lx.shell.command_button import draw_command_button,resolve_default
    from win95lx.assets.bitmap import BitmapFont
    from pixels import read
    assets=a.assets or (ROOT/'private/shell-assets' if (ROOT/'private/shell-assets/command-button-references.json').exists() else ROOT/'private/command-button-assets')
    assets=assets.resolve()
    catalog=json.loads((assets/'command-button-references.json').read_text());fontfile=ROOT/'private/shell-assets/ms-sans-serif-8.fnt';font=BitmapFont(fontfile.read_bytes());comparisons=[];failures=[];timings=[]
    viewport=cairo.ImageSurface(cairo.FORMAT_RGB24,viewport_width,viewport_height);canvas=Painter(cairo.Context(viewport),font)
    for index,case in enumerate(catalog['cases']):
        source=assets/case['file']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=case['png_sha256']:raise ValueError('Native reference digest changed: '+case['file'])
        reference=read(source);w,h,pixels=reference
        ox,oy=((9,13),(viewport_width-w-9,viewport_height-h-13),((viewport_width-w)//2,(viewport_height-h)//2))[index%3]
        canvas.fill(0,0,viewport_width,viewport_height,FACE);state=case['state'];bx,by,bw,bh=case['button_rect'];started=time.perf_counter()
        geometry=draw_command_button(canvas,case['raw_label'],(ox+bx,oy+by,bw,bh),default=state in ('default','focusdefault','pressfocus','disabledefault'),focused=state in ('focused','focusdefault','pressfocus'),pressed=state in ('pressed','pressfocus'),enabled=state not in ('disabled','disabledefault'))
        timings.append((time.perf_counter()-started)*1000)
        assert geometry.contains(ox+bx,oy+by) and geometry.contains(ox+bx+bw-1,oy+by+bh-1)
        assert not geometry.contains(ox+bx-1,oy+by) and not geometry.contains(ox+bx+bw,oy+by)
        actual_surface=cairo.ImageSurface(cairo.FORMAT_RGB24,w,h);context=cairo.Context(actual_surface);context.set_source_surface(viewport,-ox,-oy);context.paint();output=a.output/case['file'];actual_surface.write_to_png(str(output));actual=read(output)
        different=sum(left!=right for left,right in zip(reference[2],actual[2]));result={'file':case['file'],'label':case['raw_label'],'state':state,'width':bw,'viewport_origin':[ox,oy],'differing_pixels':different};comparisons.append(result)
        if different:failures.append(result)
    # Independently reproduce the old default-border defect against the native
    # parent-background margin. It must fail for the reported reason.
    case=next(c for c in catalog['cases'] if c['state']=='default' and c['raw_label']=='OK' and c['button_rect'][2]==75);reference=read(assets/case['file']);w,h,_=reference
    legacy=cairo.ImageSurface(cairo.FORMAT_RGB24,w,h);p=Painter(cairo.Context(legacy),font);p.fill(0,0,w,h,FACE);p.button('OK',*case['button_rect'],default=True);legacy.write_to_png(str(a.output/'legacy-default-outside-hwnd.png'));actual=read(a.output/'legacy-default-outside-hwnd.png');bx,by,bw,bh=case['button_rect'];outside=sum(actual[2][y*w+x]!=reference[2][y*w+x] for y in range(h) for x in range(w) if not (bx<=x<bx+bw and by<=y<by+bh));assert outside==200,outside
    # Exactly one default through enabled-focus transfers; a non-command focus
    # restores OK, rather than retaining both the old and focused defaults.
    enabled={'ok':True,'cancel':True,'add':True,'apply':False}
    assert [resolve_default('ok',focus,enabled) for focus in ('add','cancel','edit','apply')]==['add','cancel','ok','ok']
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve(),[assets/c['file'] for c in catalog['cases']]),'font_sha256':hashlib.sha256(fontfile.read_bytes()).hexdigest(),'viewport':[viewport_width,viewport_height],'scope':'Offscreen native-pixel rendering at three different origins; live dialog interaction and host-viewer pointer scaling are separate integration checks.',
        'comparisons':comparisons,'failed':len(failures),'failures':failures,'native_cases':len(catalog['cases']),'legacy_outside_hwnd_pixels':outside,'render_median_ms':round(statistics.median(timings),4)}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({key:report[key] for key in ('native_cases','failed','viewport','legacy_outside_hwnd_pixels','render_median_ms')},indent=2))
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
