#!/usr/bin/env python3
"""Save a recovery checkpoint and verify it exists; never restore implicitly."""
import argparse,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from qmp import QMP

def save_checkpoint(q,name):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',name):
        raise ValueError('Use a checkpoint name of 1–80 letters, digits, dots, underscores or hyphens.')
    # A writable raw floppy prevents savevm. Report it instead of silently
    # ejecting media or claiming an unsuccessful checkpoint is recoverable.
    for block in q.call('query-block'):
        media=block.get('inserted',{})
        if media and not media.get('ro',False) and media.get('drv')=='raw':
            raise RuntimeError('Writable raw media prevents a complete checkpoint: '+block.get('device','unknown'))
    before=q.call('human-monitor-command',{'command-line':'info snapshots'})
    if any(name in line.split() for line in before.splitlines()):
        raise ValueError('Checkpoint already exists; choose a new name.')
    result=q.call('human-monitor-command',{'command-line':'savevm '+name})
    after=q.call('human-monitor-command',{'command-line':'info snapshots'})
    if result.strip() or not any(name in line.split() for line in after.splitlines()):
        raise RuntimeError('Checkpoint was not verified: '+result.strip())
    return {'checkpoint':name,'verified':True}

def main():
    import json
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--socket',type=Path,required=True);p.add_argument('name');a=p.parse_args()
    q=QMP(a.socket)
    # Saving several GiB of guest RAM can exceed the normal 15-second RPC timeout.
    q.socket.settimeout(120)
    try:print(json.dumps(save_checkpoint(q,a.name),indent=2))
    finally:q.close()
if __name__=='__main__':main()
