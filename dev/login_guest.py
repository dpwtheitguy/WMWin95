#!/usr/bin/env python3
"""Enter generated guest-only credentials at the visible guest login prompt."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));from qmp import QMP
credentials=json.loads((ROOT/'private/run/development-credentials.json').read_text());q=QMP(ROOT/'private/run/xubuntu.qmp')
try:
    for char in credentials['password']:
        if char.isalnum():key=char.lower();shift=char.isupper()
        elif char in '-_':key='minus';shift=char=='_'
        else:raise ValueError('Unsupported generated password character')
        keys=([{'type':'qcode','data':'shift'}] if shift else [])+[{'type':'qcode','data':key}];q.call('send-key',{'keys':keys,'hold-time':20});time.sleep(.04)
    q.call('send-key',{'keys':[{'type':'qcode','data':'ret'}],'hold-time':100})
finally:q.close()
print('Entered guest-only credentials; no secret output.')
