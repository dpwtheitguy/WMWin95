#!/usr/bin/env python3
"""Generate candidate XFCE settings in a project folder. Does not apply settings."""
import argparse,json
from pathlib import Path
from xml.etree.ElementTree import Element,SubElement,ElementTree
p=argparse.ArgumentParser(); p.add_argument('--output',type=Path,default=Path('private/staged-profile')); a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
channels={'xsettings':{'/Net/ThemeName':('string','Chicago95'),'/Net/IconThemeName':('string','Chicago95'),'/Xft/DPI':('int','96'),'/Xft/Antialias':('int','0'),'/Gdk/WindowScalingFactor':('int','1')},'xfwm4':{'/general/theme':('string','Chicago95'),'/general/use_compositing':('bool','false')}}
for name,properties in channels.items():
    root=Element('channel',{'name':name,'version':'1.0'})
    for key,(kind,value) in properties.items():
        node=root
        for component in key.strip('/').split('/')[:-1]:
            found=node.find(f"property[@name='{component}']")
            node=found if found is not None else SubElement(node,'property',{'name':component,'type':'empty'})
        SubElement(node,'property',{'name':key.split('/')[-1],'type':kind,'value':value})
    ElementTree(root).write(a.output/(name+'.xml'),encoding='utf-8',xml_declaration=True)
(a.output/'STATUS.json').write_text(json.dumps({'applied':False,'measured':False,'missing':['original bitmap font renderer','taskbar and menu geometry','desktop icon positions','sound mappings','accepted application allowlist'],'instruction':'Review and apply only in dedicated XFCE guest after theme availability and backup.'},indent=2)+'\n')
print(a.output)
