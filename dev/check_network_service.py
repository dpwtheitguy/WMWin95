#!/usr/bin/env python3
"""Maintenance-only owned-dummy integration. Never touches primary connections.

Run only as root inside recognized guest using a unique QA source copy. Creates
one nonautoconnect, nondefault dummy with a private routing table and route-only
DNS suffix. Always removes its exact UUID/device and verifies primary state.
Does not install policy; root success is not nonadmin UI acceptance.
"""
import argparse,json,os,pathlib,subprocess,sys,time,uuid
from dataclasses import replace
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from win95lx.control_panel.network_preferences import NetworkManager,NetworkState,NetworkController,NetworkError
from win95lx.guest_identity import is_development_guest
p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--owned-device',required=True);p.add_argument('--owned-uuid',required=True);a=p.parse_args()
if os.geteuid()!=0 or not is_development_guest():raise SystemExit('Recognized development guest maintenance root required')
if not a.owned_device.startswith('w95uat') or len(a.owned_device)>15 or not a.owned_device.isalnum():raise SystemExit('Only bounded owned w95uat dummy name allowed')
uuid.UUID(a.owned_uuid);a.output.mkdir(parents=True,exist_ok=False)
def run(*args,check=True):return subprocess.run(args,capture_output=True,text=True,check=check,stdin=subprocess.DEVNULL,timeout=35,env={**os.environ,'LC_ALL':'C'})
def nm(*args,check=True):return run('nmcli','--wait','12','--colors','no',*args,check=check)
def primary():
 return {'route4':run('ip','-j','route','show','table','main').stdout,'rules':run('ip','-j','rule','show').stdout,'ens2':nm('-g','IP4.ADDRESS,IP4.GATEWAY,IP4.ROUTE,IP4.DNS,IP4.DOMAIN,IP6.ADDRESS,IP6.GATEWAY,IP6.ROUTE,IP6.DNS','device','show','ens2').stdout,'dns':run('resolvectl','dns').stdout,'hostname':run('hostname').stdout,'resolv_conf':pathlib.Path('/etc/resolv.conf').read_text()}
if run('ip','link','show',a.owned_device,check=False).returncode==0:raise SystemExit('Owned device already exists; refusing')
if a.owned_uuid in nm('-g','UUID','connection','show').stdout:raise SystemExit('Owned UUID exists; refusing')
before=primary();records=[];created=False;failure=None;cleanup=[]
(a.output/'primary-before.json').write_text(json.dumps(before,indent=2)+'\n')
try:
 nm('connection','add','type','dummy','ifname',a.owned_device,'con-name',a.owned_device,'connection.uuid',a.owned_uuid,
    'connection.autoconnect','no','connection.permissions','user:win95',
    'ipv4.method','manual','ipv4.addresses','198.18.255.1/30','ipv4.never-default','yes','ipv4.route-table','49995',
    'ipv4.dns-priority','32760','ipv4.dns-search','~win95lx-uat.invalid','ipv6.method','disabled')
 created=True;nm('connection','up','uuid',a.owned_uuid)
 manager=NetworkManager();baseline_connection=manager.connection(a.owned_uuid,True,a.owned_device)
 assert baseline_connection.kind=='dummy' and baseline_connection.device==a.owned_device
 class OwnedManager(NetworkManager):
  def preferences(self):return NetworkState(before['hostname'].strip(),(self.connection(a.owned_uuid,True,a.owned_device),))
  def _write(self,connection):
   if connection.uuid!=a.owned_uuid or connection.device!=a.owned_device or connection.kind!='dummy':raise NetworkError('QA boundary rejected unrelated adapter')
   return super()._write(connection)
 backend=OwnedManager();controller=NetworkController(backend)
 controller.pending=controller.pending.change_connection(a.owned_uuid,ipv4=replace(controller.pending.connections[0].ipv4,address='198.18.255.2',dns=('192.0.2.53',),manual_dns=True))
 controller.apply();assert controller.applied.connections[0].ipv4.address=='198.18.255.2';assert controller.applied.connections[0].ipv4.dns==('192.0.2.53',)
 addr=json.loads(run('ip','-j','address','show','dev',a.owned_device).stdout)
 assert any(i.get('local')=='198.18.255.2' for row in addr for i in row['addr_info'])
 records.append('Root backend writes/activates owned dummy; authoritative NM and kernel address readback confirmed')
 (a.output/'owned-applied.json').write_text(json.dumps({'profile':repr(controller.applied.connections[0]),'kernel_address':addr,'routes':json.loads(run('ip','-j','route','show','table','49995').stdout)},indent=2)+'\n')
 # Exercise same actual backend as non-admin. Its policy must currently refuse,
 # without --ask/auth agent or writing any connection.
 probe='''import json,sys
from dataclasses import replace
from win95lx.control_panel.network_preferences import *
u,d=sys.argv[1:];b=NetworkManager();old=b.connection(u,True,d);state=NetworkState('win95lx-dev',(old,));pending=state.change_connection(u,ipv4=replace(old.ipv4,address='198.18.255.1'))
try:b.apply(pending,state)
except NetworkError as e:print(json.dumps({'denied':True,'message':str(e)}))
else:print(json.dumps({'denied':False}))
'''
 result=run('runuser','-u','win95','--','env','PYTHONPATH='+str(ROOT/'src'),'/usr/bin/python3','-c',probe,a.owned_uuid,a.owned_device)
 outcome=json.loads(result.stdout);assert outcome['denied'] and 'No password prompt' in outcome['message'];assert backend.connection(a.owned_uuid,True,a.owned_device).ipv4.address=='198.18.255.2'
 (a.output/'nonadmin-denial.json').write_text(json.dumps(outcome,indent=2)+'\n');records.append('Real nonadmin backend rejects missing policy before mutation; no password prompt')
 backend.restore(NetworkState(before['hostname'].strip(),(baseline_connection,)));restored=backend.connection(a.owned_uuid,True,a.owned_device);assert restored.ipv4==baseline_connection.ipv4
 records.append('Actual owned profile/address/DNS rollback restored baseline')
except Exception as error:failure=repr(error)+(' | '+getattr(error,'stderr','') if getattr(error,'stderr','') else '')
finally:
 if created or a.owned_uuid in nm('-g','UUID','connection','show').stdout:
  for args in [('connection','down','uuid',a.owned_uuid),('connection','delete','uuid',a.owned_uuid)]:
   r=nm(*args,check=False);cleanup.append({'command':args,'status':r.returncode,'stderr':r.stderr})
 if run('ip','link','show',a.owned_device,check=False).returncode==0:
  r=run('ip','link','delete',a.owned_device,check=False);cleanup.append({'command':['ip','link','delete',a.owned_device],'status':r.returncode})
 time.sleep(.4);after=primary();(a.output/'primary-after.json').write_text(json.dumps(after,indent=2)+'\n')
 clean=(a.owned_uuid not in nm('-g','UUID','connection','show').stdout and run('ip','link','show',a.owned_device,check=False).returncode!=0)
 report={'checks':records,'failure':failure,'cleanup':cleanup,'owned_profile_and_device_removed':clean,'primary_unchanged':before==after,'owned_uuid':a.owned_uuid,'owned_device':a.owned_device,'scope':'Root actual service transaction and nonadmin denial only; no policy installed, UI not accepted'}
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 if failure or not clean or before!=after:raise SystemExit(1)
