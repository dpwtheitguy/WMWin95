#!/usr/bin/env python3
"""Start a reference visibly, preserving disk changes unless recovery is requested."""
import argparse,json,os,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROFILES={'ie4':'windows95','classic':'windows95-classic','plus':'windows95-plus-reference','rtm':'windows95-rtm','osr1':'windows95-osr1','osr2':'windows95-osr2'}

def visible_command(saved,snapshot=None):
    args=list(saved['command'] if isinstance(saved,dict) else saved)
    args[args.index('-display')+1]='gtk,show-tabs=off,zoom-to-fit=off'
    if '-daemonize' in args:args.remove('-daemonize')
    if '-icount' in args:
        index=args.index('-icount')+1;args[index]=args[index].replace('sleep=off','sleep=on')
    if '-loadvm' in args:
        index=args.index('-loadvm');del args[index:index+2]
    if snapshot:args+=['-loadvm',snapshot]
    return args

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('variant',choices=PROFILES)
    parser.add_argument('--restore-snapshot',help='Explicitly restore this recovery checkpoint, including its disk state')
    parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
    stem=PROFILES[args.variant];run=ROOT/'private/run';profile=run/(stem+'-launch.json');endpoint=run/(stem+'.qmp')
    if not profile.exists():parser.error('No prepared reference profile: '+str(profile))
    command=visible_command(json.loads(profile.read_text()),args.restore_snapshot)
    if args.dry_run:print(json.dumps(command,indent=2));return
    if endpoint.exists():
        client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:client.connect(str(endpoint));print('Reference is already running:',args.variant);return
        except ConnectionRefusedError:endpoint.unlink()
        finally:client.close()
    with (run/(stem+'-console.log')).open('ab') as log:
        process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
            start_new_session=True,env={**os.environ,'GDK_BACKEND':'x11','GDK_SCALE':'1'})
    for _ in range(50):
        if endpoint.exists():print('Opened visible reference:',args.variant);return
        if process.poll() is not None:raise SystemExit('Reference failed; inspect '+str(run/(stem+'-console.log')))
        time.sleep(.1)
    raise SystemExit('Reference did not open its control socket.')
if __name__=='__main__':main()
