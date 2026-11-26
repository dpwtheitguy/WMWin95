#!/usr/bin/env python3
"""Capture independent native CPL tabs from prepared visible reference machines.

Never updates existing evidence or restores a VM snapshot. Saves a recovery
checkpoint before opening property sheets; leaves the final sheet visible.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from qmp import QMP

PROFILES = {'classic':'windows95-classic', 'ie4':'windows95', 'plus':'windows95-plus-reference'}
# Tab names are deliberately separate from assumed control-panel icon ordering.
APPLETS = {
    'keyboard': ('control keyboard', ('speed','language','general')),
    'regional': ('control intl.cpl', ('regional','number','currency','time','date')),
    'datetime': ('control timedate.cpl', ('datetime','timezone')),
    'system': ('control sysdm.cpl', ('general','devices','hardware-profiles','performance')),
    'multimedia': ('control mmsys.cpl', ('audio','video','midi','cd-music','advanced')),
    'sounds': ('control mmsys.cpl @1', ('sounds',)),
    'network': ('control netcpl.cpl', ('configuration','identification','access')),
    'passwords': ('control password.cpl', ('passwords','user-profiles')),
    'accessibility': ('control access.cpl', ('keyboard','sound','display','mouse','general')),
    'modems': ('control modem.cpl', ('general','diagnostics')),
    'addremove': ('control appwiz.cpl', ('install','windows-setup','startup-disk')),
}

def key(q, *keys):
    q.call('send-key', {'keys':[{'type':'qcode','data':k} for k in keys], 'hold-time':100})
    time.sleep(.55)

def type_command(q, text):
    punctuation={' ': 'spc', '.':'dot', ',':'comma', '\n':'ret','@':'2',':':'semicolon','\\':'backslash'}
    for char in text:
        name=char if char.isascii() and char.isalnum() else punctuation[char]
        keys=([{'type':'qcode','data':'shift'}] if char in ('@',':') else [])+[{'type':'qcode','data':name}]
        q.call('send-key', {'keys':keys, 'hold-time':30})
        time.sleep(.07)

def park_pointer(q):
    # Huge PS/2 deltas can overflow legacy Windows cursor save-under handling
    # and leave blue strips in captions. Small packets reach the screen edge
    # without baking those artifacts into reference artwork.
    q.call('human-monitor-command', {'command-line': 'mouse_button 0'})
    for _ in range(80):
        q.call('human-monitor-command',{'command-line':'mouse_move 16 16'})
        time.sleep(.01)
    time.sleep(.3)

def capture(profile, selected, output):
    output.mkdir(parents=True, exist_ok=False)
    q = QMP(ROOT/'private/run'/f'{PROFILES[profile]}.qmp')
    rows=[]
    try:
        checkpoint='before-cpl-capture-'+str(time.time_ns())
        q.call('human-monitor-command', {'command-line':'savevm '+checkpoint})
        for index, name in enumerate(selected):
            command, tabs = APPLETS[name]
            if index: key(q,'alt','f4')
            key(q,'ctrl','esc'); key(q,'r'); key(q,'ctrl','a')
            type_command(q,command+'\n')
            time.sleep(4)
            # Move the PS/2 pointer clear of typical fixed-size property sheets.
            park_pointer(q)
            time.sleep(.6)
            for tab_index, tab in enumerate(tabs):
                if tab_index: key(q,'ctrl','tab'); time.sleep(.8)
                path=output/f'{name}-{tab}.png'
                q.call('screendump',{'filename':str(path.resolve()),'format':'png'})
                rows.append({'applet':name,'tab':tab,'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                             'command':command,'tab_index':tab_index,'reviewed':False})
            print(profile,name,flush=True)
        (output/'capture.json').write_text(json.dumps({'profile':profile,'checkpoint':checkpoint,
            'capture_method':'QMP guest framebuffer; no resizing','pointer':'moved toward bottom-right before capture',
            'resolution':'inspect PNG dimensions','status':'raw captures; verify command result, tab names, bounds and metadata before staging',
            'captures':rows},indent=2)+'\n')
    finally:q.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',choices=PROFILES)
    p.add_argument('--applets',nargs='+',choices=APPLETS,default=list(APPLETS))
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();capture(a.profile,a.applets,a.output)
if __name__=='__main__':main()
