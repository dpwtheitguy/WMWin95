#!/usr/bin/env python3
"""Drive the real non-admin Date/Time applet and restore its original zone."""
import json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'dev')]
from qmp import QMP
from capture_control_panel import key,type_command
ssh=['ssh','-i',str(ROOT/'private/run/guest_ed25519'),'-o','IdentitiesOnly=yes','-o','UserKnownHostsFile='+str(ROOT/'private/run/installed_known_hosts'),'-p','22295','developer@127.0.0.1']
def state():
    text=subprocess.check_output(ssh+['timedatectl show --property=Timezone --property=NTP'],text=True)
    return dict(row.split('=',1) for row in text.splitlines())
original=state();rows=json.loads((ROOT/'private/shell-assets/native-timezones.json').read_text())['zones'];index=next(i for i,row in enumerate(rows) if row['zone']==original['Timezone']);delta=-1 if index else 1;target=rows[index+delta]['zone']
q=QMP(ROOT/'private/run/xubuntu.qmp');folder=ROOT/'private/screenshots'/('date-time-live-'+str(time.time_ns()));folder.mkdir(exist_ok=False)
try:
    key(q,'esc');key(q,'ctrl','esc');key(q,'r');key(q,'ctrl','a');type_command(q,'control timedate.cpl\n');time.sleep(1)
    key(q,'ctrl','tab');key(q,'up' if delta<0 else 'down');key(q,'shift','tab');key(q,'spc');time.sleep(1)
    applied=state();q.call('screendump',{'filename':str(folder/'timezone-applied.png'),'format':'png'})
    assert applied['Timezone']==target,(target,applied)
    assert applied['NTP']==original['NTP']
    key(q,'tab');key(q,'down' if delta<0 else 'up');key(q,'shift','tab');key(q,'spc');time.sleep(1)
    restored=state();assert restored==original,(original,restored)
    q.call('screendump',{'filename':str(folder/'timezone-restored.png'),'format':'png'})
    key(q,'esc')
    report={'original':original,'applied':applied,'restored':restored,'non_admin_visible_ui':True,'clock_edited':False}
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:
    q.close()
    if state()!=original:
        # Emergency restoration is deliberately not counted as a successful
        # UI round trip. Never leave the user's guest zone changed on failure.
        import shlex
        password=json.loads((ROOT/'private/run/development-credentials.json').read_text())['password']
        subprocess.run(ssh+['sudo -S -p "" timedatectl set-timezone '+shlex.quote(original['Timezone'])],input=password+'\n',text=True,capture_output=True,check=True)
        if state()['NTP']!=original['NTP']:
            subprocess.run(ssh+['sudo -S -p "" timedatectl set-ntp '+('true' if original['NTP']=='yes' else 'false')],input=password+'\n',text=True,capture_output=True,check=True)
        (folder/'failed-run-restored.json').write_text(json.dumps({'original':original,'restored':state(),'ui_round_trip_passed':False},indent=2)+'\n')
        raise RuntimeError('UI verification failed; original guest timezone restored using maintenance access.')
