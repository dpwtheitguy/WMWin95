"""Read actual guest system/device facts without modifying hardware."""
from dataclasses import dataclass
from pathlib import Path
import os,platform,shutil

@dataclass(frozen=True)
class Device:
    name:str
    category:str
    path:str
    driver:str=''
    status:str='Working'

def read_text(path,default=''):
    try:return path.read_text().strip()
    except (OSError,UnicodeError):return default

def memory_info(proc=Path('/proc')):
    result={}
    for line in read_text(proc/'meminfo').splitlines():
        key,_,value=line.partition(':')
        try:result[key]=int(value.strip().split()[0])*1024
        except (ValueError,IndexError):pass
    return result

def cpu_name(proc=Path('/proc')):
    for line in read_text(proc/'cpuinfo').splitlines():
        key,_,value=line.partition(':')
        if key.strip() in ('model name','Hardware'):return value.strip()
    return platform.machine()

def inventory(sys=Path('/sys')):
    devices=[]
    categories={1:'Disk drives',2:'Network adapters',3:'Display adapters',4:'Multimedia',6:'System devices',7:'Ports',12:'USB controllers'}
    root=sys/'bus/pci/devices'
    for path in sorted(root.glob('*')):
        class_id=read_text(path/'class','0')
        try:kind=int(class_id,16)>>16
        except ValueError:kind=0
        vendor=read_text(path/'vendor');identifier=read_text(path/'device')
        driver=path/'driver'
        name=(driver.resolve().name if driver.is_symlink() else 'PCI device')+' ['+path.name+']'
        devices.append(Device(name,categories.get(kind,'Other devices'),str(path),driver.resolve().name if driver.is_symlink() else '',
                              'Working' if driver.is_symlink() else 'No driver bound'))
    for category,folder in (('Disk drives','block'),('Network adapters','net'),('Keyboard and mouse','input')):
        for path in sorted((sys/'class'/folder).glob('*')):
            if folder=='block' and (path.name.startswith(('loop','ram')) or (path/'partition').exists()):continue
            if folder=='input' and not path.name.startswith('input'):continue
            name=read_text(path/'name') or read_text(path/'device/name') or path.name
            devices.append(Device(name,category,str(path)))
    return tuple(sorted(devices,key=lambda d:(d.category,d.name)))

def system_summary(proc=Path('/proc'),root=Path('/')):
    mem=memory_info(proc);usage=shutil.disk_usage(root)
    return {'cpu':cpu_name(proc),'processors':os.cpu_count() or 1,
            'memory':mem.get('MemTotal',0),'available':mem.get('MemAvailable',mem.get('MemFree',0)),
            'swap':mem.get('SwapTotal',0),'swap_free':mem.get('SwapFree',0),
            'disk_total':usage.total,'disk_free':usage.free,'architecture':platform.machine()}
