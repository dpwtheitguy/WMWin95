"""Private original namespace-drop prompts with independently measured HWNDs."""
import hashlib,json,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from pixels import read,write

def stage(output):
 output.mkdir(parents=True,exist_ok=True);base=ROOT/'private/screenshots/namespace-transfer-native-20261127';meta=ROOT/'private/reference-tools/namespace-prompt-metadata-v2-20261127'
 definitions=(('classic','classic-c-desktop-left.png','classic-prompt.json','classic'),('ie4','ie4-fresh-prompt-redrawn.png','ie4-fresh-prompt.json','ie4'),('plus','plus-c-desktop-logical-left.png','classic-prompt.json','classic'))
 profiles={};records=[]
 for profile,filename,metadata,geometry_profile in definitions:
  source=base/filename;metadata_path=meta/metadata;data=json.loads(metadata_path.read_text())
  if data.get('prompt') is not True or data['rect'][2:]!=[326,119] or data['yes']!=[84,82,75,23] or data['no']!=[165,82,75,23]:raise ValueError('Native namespace prompt HWND geometry changed; remeasure before staging.')
  x,y,w,h=data['rect'];sw,sh,pixels=read(source)
  if min(x,y)<0 or x+w>sw or y+h>sh:raise ValueError('Native prompt is outside its source capture.')
  dest=output/f'namespace-drop-prompt-{profile}.png';write(dest,w,h,[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
  row={'source':str(source.relative_to(ROOT)),'type':'NATIVE_NAMESPACE_DROP_PROMPT','profile':profile,'output':dest.name,'rectangle':data['rect'],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'metadata':str(metadata_path.relative_to(ROOT)),'metadata_sha256':hashlib.sha256(metadata_path.read_bytes()).hexdigest(),'geometry_measured_profile':geometry_profile,'independent_profile_geometry':profile==geometry_profile,'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
  profiles[profile]=row;records.append(row)
 # The current shell targets IE4 Desktop Update. Alternatives are private
 # reference assets only; this is not an implemented global profile switch.
 shutil.copyfile(output/'namespace-drop-prompt-ie4.png',output/'namespace-drop-prompt.png')
 (output/'namespace-drop-prompt-provenance.json').write_text(json.dumps({'current_profile':'ie4','profiles':profiles,'plus_geometry_note':'Plus screenshot is corroborated visually; crop uses independently measured Classic geometry until a Plus HWND probe is captured.'},indent=2)+'\n')
 menu_meta=ROOT/'private/reference-tools/namespace-transfer-native-20261127/ie4-right-menu.json';menu=json.loads(menu_meta.read_text())
 if menu.get('visible') is not True or menu['rect'][2:]!=[183,49] or [item['rect'] for item in menu['items']]!=[[3,3,177,17],[3,20,177,9],[3,29,177,17]]:raise ValueError('Native namespace drop-menu geometry changed.')
 menu_source=base/'ie4-fresh-right-menu.png';sw,sh,pixels=read(menu_source);x,y,w,h=menu['rect'];write(output/'namespace-drop-menu-ie4.png',w,h,[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
 records.append({'source':str(menu_source.relative_to(ROOT)),'type':'NATIVE_NAMESPACE_DROP_MENU','profile':'ie4','output':'namespace-drop-menu-ie4.png','rectangle':menu['rect'],'source_sha256':hashlib.sha256(menu_source.read_bytes()).hexdigest(),'metadata_sha256':hashlib.sha256(menu_meta.read_bytes()).hexdigest()})
 records.append({'source':'namespace-drop-prompt-ie4.png','type':'CURRENT_PROFILE_ALIAS','output':'namespace-drop-prompt.png','sha256':hashlib.sha256((output/'namespace-drop-prompt.png').read_bytes()).hexdigest()})
 return records
if __name__=='__main__':print(json.dumps({'staged':len(stage(ROOT/'private/shell-assets'))}))
