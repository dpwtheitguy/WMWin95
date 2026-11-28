#!/usr/bin/env python3
"""Real XFCE daemon/cookies in an owned guest display+private D-Bus session."""
import argparse,json,os,select,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
def child(output):
 from win95lx.apps.screensaver_ownership import SaverOwnership,SessionBus,SERVICE,PATH
 address=os.environ['DBUS_SESSION_BUS_ADDRESS'];observer=SessionBus(address)
 def prop(key,value):
  subprocess.run(['xfconf-query','-c','xfce4-screensaver','-p',key,'-n','-t','bool','-s',str(value).lower()],stdout=subprocess.DEVNULL,check=True)
 def prefs():return subprocess.check_output(['xfconf-query','-c','xfce4-screensaver','-lv'])
 def wait_for(predicate):
  deadline=time.monotonic()+6
  while time.monotonic()<deadline:
   value=predicate()
   if value:return value
   time.sleep(.05)
  raise AssertionError('Owned daemon operation timed out')
 prop('/lock/enabled',False);prop('/lock/saver-activation/enabled',True)
 log=(output/'daemon.log').open('w');daemon=subprocess.Popen(['/usr/bin/xfce4-screensaver','--debug'],stdout=log,stderr=log)
 owner=None;results=[]
 try:
  unique=wait_for(observer.owner)[0];owner=SaverOwnership();before=prefs();state=owner.refresh();assert state.ready and state.mode=='Inhibit',state;assert before==prefs()
  rows=observer.inhibitors(unique);assert any(owner.reason in row for row in rows)
  results.append('Real non-locking daemon: scopedInhibit visible, allXfconfvaluesunchanged')
  # Manual activation is not suppressed; no lock/password is requested here.
  observer.call(unique,PATH,SERVICE,'SetActive','(b)',(True,));wait_for(lambda:observer.active(unique));assert owner.refresh().active
  observer.call(unique,PATH,SERVICE,'SetActive','(b)',(False,));wait_for(lambda:not observer.active(unique))
  results.append('Manualactivation bypassesinhibitor; coordinatorneverforcesdeactivation')
  external=SessionBus(address);cookie=external.acquire(unique,'Inhibit','Ownership test movie')
  assert owner.refresh().external_inhibited;external.release(unique,'Inhibit',cookie);external.close();assert not owner.refresh().external_inhibited
  results.append('Foreignmovieinhibitor respected; onlyownedcookie excluded')
  # Change only the disposable test policy, then prove coordinator preserves it.
  prop('/lock/enabled',True);before=prefs();state=owner.refresh();assert state.ready and state.mode=='Throttle',state;assert before==prefs()
  assert all(owner.reason not in row for row in observer.inhibitors(unique))
  results.append('Enablingautomaticlocking releasesInhibit, usesThrottle, preserveslockpolicy')
  owner.close();owner=None;assert not observer.inhibitors(unique);assert before==prefs()
  results.append('Close releasescookies withouttouchingprefs')
  # Crash simulation: client exits without close; service must drop its cookie.
  prop('/lock/enabled',False);before=prefs()
  source='from win95lx.apps.screensaver_ownership import SaverOwnership;import os;manager=SaverOwnership();assert manager.refresh().ready;os._exit(0)'
  subprocess.run([sys.executable,'-c',source],env={**os.environ,'PYTHONPATH':str(ROOT/'src')},check=True)
  wait_for(lambda:not observer.inhibitors(unique));assert before==prefs()
  results.append('Abruptclientexit autoreleasesInhibit ontheactualdaemon')
  owner=SaverOwnership();assert owner.refresh().ready;daemon.terminate();daemon.wait(timeout=4)
  wait_for(lambda:observer.owner()is None)
  # The first refresh can discover the old unique owner is gone; bounded retry.
  wait_for(lambda:owner.refresh().ready)
  daemon=subprocess.Popen(['/usr/bin/xfce4-screensaver','--debug'],stdout=log,stderr=log);new=wait_for(observer.owner)[0];assert new!=unique;state=owner.refresh();assert state.ready and state.mode=='Inhibit',state
  results.append('Daemonrestart reacquiresfreshcookie againstnewuniqueowner')
  (output/'report.json').write_text(json.dumps({'display':os.environ['DISPLAY'],'bus':'privateowneddbus-run-session','results':results,'config_preserved':True,'userdesktop_untouched':True},indent=2));print(json.dumps(results))
 finally:
  if owner:owner.close()
  observer.close()
  if daemon.poll()is None:daemon.terminate();daemon.wait(timeout=4)
  log.close()
def main():
 p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 assert os.uname().nodename=='win95lx-dev','Developmentguestonly.'
 if a.child:return child(a.output)
 a.output.mkdir(exist_ok=False)
 with tempfile.TemporaryDirectory(prefix='win95lx-owner-')as tmp:
  folder=Path(tmp);r,w=os.pipe();server=subprocess.Popen(['/home/developer/win95lx-ui-qa.eK9O7BgJ/Xvfb','-displayfd',str(w),'-screen','0','800x600x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stderr=subprocess.PIPE);os.close(w)
  try:
   assert select.select([r],[],[],10)[0];display=':'+os.read(r,32).decode().strip();assert display!=':0';env=os.environ.copy();env.pop('DBUS_SESSION_BUS_ADDRESS',None);env.update(DISPLAY=display,HOME=str(folder/'home'),XDG_CONFIG_HOME=str(folder/'config'),XDG_CACHE_HOME=str(folder/'cache'),XDG_DATA_HOME=str(folder/'data'));Path(env['HOME']).mkdir()
   subprocess.run(['dbus-run-session','--',sys.executable,__file__,'--child','--output',str(a.output.resolve())],env=env,check=True,timeout=45)
  finally:os.close(r);server.terminate();server.wait(timeout=10)
if __name__=='__main__':main()
