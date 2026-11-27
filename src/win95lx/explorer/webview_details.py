"""Selection data for IE4 information panels, independent of the renderer."""
from dataclasses import dataclass,field
import shutil

@dataclass(frozen=True)
class Details:
    title: str=''
    type_name: str=''
    description: str=''
    names: tuple=()
    disk: tuple|None=None


def describe(selection,strings,root='/'):
    if selection is None:return Details(description=strings['templates']['mycomp']['strings']['L_Intro_Text'])
    if len(selection)!=1:return Details(title=f'{len(selection)} objects selected.',names=tuple(selection[:16]) if len(selection)<=16 else ())
    name=selection[0]
    if name=='(C:)':
        usage=shutil.disk_usage(root)
        return Details(name,'Local Disk',disk=(usage.total,usage.used,usage.free))
    keys={'Control Panel':'CONTROLPANEL_IT','Printers':'PRINTERS_IT','My Computer':'MYCOMPUTER_IT',
          'Network Neighborhood':'NETWORKNEIGHBORHOOD_IT','Recycle Bin':'RECYCLEBIN_IT',
          'Briefcase':'BRIEFCASE_IT','Scheduled Tasks':'TASKSCHEDULER_IT','Dial-Up Networking':'DIALUPNETWORKING_IT'}
    return Details(name,'System Folder',strings.get('infotips',{}).get(keys.get(name,''),''))


def wrapped(text,font,width):
    # Long filenames/tokens must fit the same measured column as normal words.
    width=max(1,width);lines=[]
    for paragraph in text.split('\n'):
        line=''
        for word in paragraph.split():
            candidate=(line+' '+word).strip()
            if line and font.width(candidate)>width:lines.append(line);line=''
            while font.width(word)>width and len(word)>1:
                cut=1
                while cut<len(word) and font.width(word[:cut+1])<=width:cut+=1
                lines.append(word[:cut]);word=word[cut:]
            line=(line+' '+word).strip()
        lines.append(line)
    return lines


def size_text(value):
    if value>=1024**3:return f'{value/1024**3:.2f} GB'
    if value>=1024**2:return f'{value/1024**2:.0f} MB'
    if value>=1024:return f'{value/1024:.0f} KB'
    return f'{value} bytes'
