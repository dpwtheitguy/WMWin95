"""Legacy Windows95 data import, independent fixtures and store integration."""
import sys
from pathlib import Path as _BootstrapPath
sys.path.insert(0,str(_BootstrapPath(__file__).resolve().parents[1]/'src'))
from copy import deepcopy
from pathlib import Path
import io,struct,tempfile,unittest,wave
from win95lx.control_panel.theme_import import import_theme,CURSORS
from win95lx.control_panel.theme_appearance import DEFAULT_COLORS,DEFAULT_FONTS,DEFAULT_METRICS
from win95lx.control_panel.sound_preferences import KEYS
from win95lx.control_panel.theme_store import ThemeStore,ThemeChangedError,encode_theme

def baseline():return {'wallpaper':{'file':'','mode':'center','pattern':'(None)','pattern_rows':[0]*8},'pointers':{'scheme':'3D Pointers','overrides':{}},'sounds':{'scheme':'No Sounds','events':{key:''for key in KEYS}},'colors':deepcopy(DEFAULT_COLORS)}
def native(extra='',wall='',pointers=None):
 pointers=pointers or{}
 return ('[Control Panel\\Desktop]\nWallpaper='+wall+'\nTileWallpaper=0\nPattern=(None)\n[Control Panel\\Cursors]\n'+'\n'.join(key+'='+pointers.get(key,'')for key in CURSORS)+'\n[AppEvents\\Schemes\\Apps\\.Default\\SystemStart\\.Current]\nDefaultValue=\n'+extra)
def dib(size):
 stride=((size+31)//32)*4
 return struct.pack('<IiiHHIIiiII',40,size,size*2,1,1,0,stride*size*2,0,0,0,0)+b'\0\0\0\0\xff\xff\xff\0'+bytes(stride*size*2)
def ico():
 first,second=dib(16),dib(32);offset=38
 return struct.pack('<HHH',0,1,2)+struct.pack('<BBBBHHII',16,16,2,0,1,1,len(first),offset)+struct.pack('<BBBBHHII',32,32,2,0,1,1,len(second),offset+len(first))+first+second
def cur():
 image=dib(32);return struct.pack('<HHH',0,2,1)+struct.pack('<BBBBHHII',32,32,2,0,0,0,len(image),22)+image
def bmp():return b'BM'+struct.pack('<IHHI',58,0,0,54)+struct.pack('<IiiHHIIiiII',40,1,1,1,24,0,4,0,0,0,0)+bytes(4)
def metrics():
 n=bytearray(340);i=bytearray(76);struct.pack_into('<I',n,0,340);struct.pack_into('<4i',i,0,76,75,75,1)
 for offset,value in [(4,1),(8,13),(12,13),(16,18),(20,18),(84,15),(88,15),(152,18),(156,18)]:struct.pack_into('<i',n,offset,value)
 for target,offset in [(n,24),(n,92),(n,160),(n,220),(n,280),(i,16)]:
  struct.pack_into('<5i',target,offset,-11,0,0,0,400);target[offset+28:offset+41]=b'MS Sans Serif'
 return '[Metrics]\nNonclientMetrics='+' '.join(map(str,n))+'\nIconMetrics='+' '.join(map(str,i))+'\n'
class ImportTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.file=self.root/'Original.theme';self.cache=self.root/'cache'
 def tearDown(self):self.tmp.cleanup()
 def load(self,text=None,data=None,base=None,assets=None):return import_theme(data if data is not None else(text or native()).encode(),self.file,base or baseline(),self.cache,assets)
 def test_complete_empty_native_theme_resets_pointer_art_only(self):
  name,value=self.load();self.assertEqual(name,'Original');self.assertEqual(value['pointers'],{'scheme':'(None)','overrides':{}});self.assertEqual(set(value),{'wallpaper','pointers','sounds'});self.assertFalse(self.cache.exists())
 def test_case_insensitive_native_sections(self):self.assertEqual(self.load(native().swapcase())[1]['wallpaper']['file'],'')
 def test_utf16_native_file(self):self.assertEqual(self.load(data=native().encode('utf-16'))[0],'Original')
 def test_cp1252_filename(self):
  (self.root/'Café.bmp').write_bytes(bmp());value=self.load(data=native(wall='%ThemeDir%Café.bmp').encode('cp1252'))[1];self.assertEqual(value['wallpaper']['file'],str(self.root/'Café.bmp'))
 def test_case_insensitive_local_filename(self):
  (self.root/'Wallpaper.BMP').write_bytes(bmp());self.assertTrue(self.load(native(wall='%ThemeDir%wallpaper.bmp'))[1]['wallpaper']['file'].endswith('Wallpaper.BMP'))
 def test_cursor_payload_is_data_and_validated(self):
  (self.root/'arrow.cur').write_bytes(cur());value=self.load(native(pointers={'arrow':'%ThemeDir%arrow.cur'}))[1];self.assertEqual(value['pointers']['overrides'],{'arrow':str(self.root/'arrow.cur')})
 def test_unmentioned_sound_event_is_preserved(self):
  base=baseline();base['sounds']['events']['.Default']='sound-ding.wav';self.assertEqual(self.load(base=base)[1]['sounds']['events']['.Default'],'sound-ding.wav')
 def test_local_wave_is_validated(self):
  stream=io.BytesIO()
  with wave.open(stream,'wb')as file:file.setnchannels(1);file.setsampwidth(2);file.setframerate(8000);file.writeframes(bytes(4))
  (self.root/'start.wav').write_bytes(stream.getvalue());text=native().replace('DefaultValue=','DefaultValue=%ThemeDir%start.wav');self.assertTrue(self.load(text)[1]['sounds']['events']['SystemStart'].endswith('start.wav'))
 def test_native_colors_merge_untouched_entries(self):
  value=self.load(native('[Control Panel\\Colors]\nBackground=1 2 3\n'))[1];self.assertEqual(value['colors']['Background'],[1,2,3]);self.assertEqual(value['colors']['ButtonFace'],DEFAULT_COLORS['ButtonFace'])
 def test_metrics_use_original_metrics_section(self):
  value=self.load(native(metrics()))[1];self.assertEqual(value['metrics']['caption_height'],18);self.assertEqual(value['fonts']['caption']['family'],'MS Sans Serif')
 def test_original_ico_sizes_are_preserved(self):
  (self.root/'computer.ico').write_bytes(ico());text=native('[CLSID\\{20D04FE0-3AEA-1069-A2D8-08002B30309D}\\DefaultIcon]\nDefaultValue=%ThemeDir%computer.ico,0\n');value=self.load(text)[1]
  for key,size in [('large',32),('small',16)]:self.assertEqual(struct.unpack_from('>II',Path(value['icons']['computer'][key]).read_bytes(),16),(size,size))
  self.assertEqual(len(list(self.cache.iterdir())),2)
 def test_known_native_system_icons_reset_defaults(self):
  text=native()
  from win95lx.control_panel.theme_import import ICONS
  for role,(clsid,key,index)in ICONS.items():
   if key=='full':continue
   if key=='empty':text+='[CLSID\\{'+clsid+'}\\DefaultIcon]\nempty=%WinDir%SYSTEM\\cool.dll,20\nfull=%WinDir%SYSTEM\\cool.dll,21\n'
   else:text+='[CLSID\\{'+clsid+'}\\DefaultIcon]\n'+key+'=%WinDir%SYSTEM\\cool.dll,'+str(index)+'\n'
  self.assertEqual(self.load(text)[1]['icons'],{})
 def test_only_catalog_saver_identity_is_imported(self):self.assertEqual(self.load(native('[boot]\nSCRNSAVE.EXE=%WinDir%SYSTEM\\Nature.SCR\n'))[1]['screensaver'],{'saver':'plus95-nature'})
 def test_disabled_saver_without_program_is_supported(self):self.assertEqual(self.load(native().replace('TileWallpaper=0','TileWallpaper=0\nScreenSaveActive=0'))[1]['screensaver'],{'saver':''})
 def test_quote_empty_native_strings(self):self.assertEqual(self.load(native(wall='""'))[1]['wallpaper']['file'],'')
 def test_unknown_registry_sections_are_never_executed(self):
  marker=self.root/'executed';self.load(native('[Run]\nCommand=touch '+str(marker)+'\n'));self.assertFalse(marker.exists())
 def test_missing_asset_does_not_write_cache(self):
  with self.assertRaises(ValueError):self.load(native(wall='%ThemeDir%missing.bmp'))
  self.assertFalse(self.cache.exists())
 def test_unsupported_program_icons_are_rejected(self):
  with self.assertRaises(ValueError):self.load(native('[CLSID\\{20D04FE0-3AEA-1069-A2D8-08002B30309D}\\DefaultIcon]\nDefaultValue=evil.dll,0\n'))
 def test_executable_saver_command_is_rejected(self):
  with self.assertRaises(ValueError):self.load(native('[boot]\nSCRNSAVE.EXE=%WinDir%SYSTEM\\Nature.SCR /s\n'))
 def test_parent_traversal_is_rejected(self):
  with self.assertRaises(ValueError):self.load(native(wall='%ThemeDir%../wall.bmp'))
 def test_network_and_url_assets_are_rejected(self):
  for name in ['\\\\server\\wall.bmp','https://example.test/wall.bmp']:
   with self.subTest(name=name),self.assertRaises(ValueError):self.load(native(wall=name))
 def test_unknown_folder_variables_are_rejected(self):
  with self.assertRaises(ValueError):self.load(native(wall='%TEMP%wall.bmp'))
 def test_oversize_definition_is_rejected(self):
  with self.assertRaises(ValueError):self.load(data=b'x'*(256*1024+1))
 def test_nul_text_is_rejected(self):
  with self.assertRaises(ValueError):self.load(data=native().encode()+b'\0')
 def test_configparser_default_inheritance_is_not_native(self):
  with self.assertRaises(ValueError):self.load('[DEFAULT]\nArrow=anything\n'+native())
 def test_duplicate_case_sections_are_rejected(self):
  with self.assertRaises(ValueError):self.load(native('[CONTROL PANEL\\DESKTOP]\nWallpaper=\n'))
 def test_bad_metrics_are_rejected(self):
  with self.assertRaises(ValueError):self.load(native('[Metrics]\nNonclientMetrics=1 2 3\nIconMetrics=1 2 3\n'))
 def test_out_of_range_colors_are_rejected(self):
  with self.assertRaises(ValueError):self.load(native('[Control Panel\\Colors]\nBackground=256 0 0\n'))
 def test_unsupported_stretch_is_not_silently_changed(self):
  with self.assertRaises(ValueError):self.load(native().replace('TileWallpaper=0','TileWallpaper=0\nWallpaperStyle=2'))
 def test_excessive_wallpaper_geometry_is_rejected(self):
  (self.root/'huge.png').write_bytes(b'\x89PNG\r\n\x1a\n'+bytes(8)+struct.pack('>II',999999,999999))
  with self.assertRaises(ValueError):self.load(native(wall='%ThemeDir%huge.png'))
 def test_corrupt_icon_directory_is_rejected(self):
  (self.root/'bad.ico').write_bytes(ico()[:38])
  with self.assertRaises(ValueError):self.load(native('[CLSID\\{20D04FE0-3AEA-1069-A2D8-08002B30309D}\\DefaultIcon]\nDefaultValue=bad.ico,0\n'))
 def test_owned_schema_is_never_downgraded_to_legacy(self):
  with self.assertRaises(ValueError):self.load(native('[Win95LX.Theme]\nSchema=999\n'))
 def store(self):return ThemeStore(self.root,{},legacy_loader=lambda data,path:import_theme(data,path,baseline(),self.cache))
 def test_store_catalog_reads_native_without_changing_definition(self):
  self.file.write_text(native());before=self.file.read_bytes();store=self.store();self.assertIn('Original',store.catalog());self.assertEqual(self.file.read_bytes(),before)
 def test_store_delete_removes_definition_only(self):
  (self.root/'wall.bmp').write_bytes(bmp());self.file.write_text(native(wall='wall.bmp'));store=self.store();token=store.token('Original');store.delete('Original',expected=token);self.assertFalse(self.file.exists());self.assertTrue((self.root/'wall.bmp').exists())
 def test_store_external_edit_token_is_respected(self):
  self.file.write_text(native());store=self.store();token=store.token('Original');self.file.write_text(native()+';changed\n')
  with self.assertRaises(ThemeChangedError):store.save('Original',self.load()[1],overwrite=True,expected=token)
 def test_store_can_explicitly_overwrite_native_with_owned_definition(self):
  self.file.write_text(native());store=self.store();token=store.token('Original');store.save('Original',self.load()[1],overwrite=True,expected=token);self.assertIn(b'[Win95LX.Theme]',self.file.read_bytes());self.assertIn('Original',store.catalog())
 def test_native_valueless_noise_is_ignored(self):self.assertEqual(self.load(native()+'av\n')[0],'Original')
 def test_bad_cursor_is_reported_as_value_error(self):
  (self.root/'bad.cur').write_bytes(b'bad')
  with self.assertRaises(ValueError):self.load(native(pointers={'arrow':'bad.cur'}))
 def test_failed_validation_does_not_commit_icon_cache(self):
  (self.root/'computer.ico').write_bytes(ico());text=native('[CLSID\\{20D04FE0-3AEA-1069-A2D8-08002B30309D}\\DefaultIcon]\nDefaultValue=computer.ico,0\n[Control Panel\\Colors]\nBackground=999 0 0\n')
  with self.assertRaises(ValueError):self.load(text)
  self.assertFalse(self.cache.exists())
 def test_redirected_icon_cache_is_rejected(self):
  target=self.root/'elsewhere';target.mkdir();self.cache.symlink_to(target);(self.root/'computer.ico').write_bytes(ico())
  with self.assertRaises(ValueError):self.load(native('[CLSID\\{20D04FE0-3AEA-1069-A2D8-08002B30309D}\\DefaultIcon]\nDefaultValue=computer.ico,0\n'))
  self.assertFalse(list(target.iterdir()))
 def test_application_specific_events_do_not_overwrite_windows_events(self):
  base=baseline();base['sounds']['events']['Open']='sound-ding.wav'
  text=native('[AppEvents\\Schemes\\Apps\\OtherProgram\\Open\\.Current]\nDefaultValue=missing.wav\n')
  self.assertEqual(self.load(text,base=base)[1]['sounds']['events']['Open'],'sound-ding.wav')
 def test_original_microsoft_sound_installed_alias(self):
  assets=self.root/'assets';assets.mkdir();stream=io.BytesIO()
  with wave.open(stream,'wb')as file:file.setnchannels(1);file.setsampwidth(2);file.setframerate(8000);file.writeframes(bytes(4))
  (assets/'sound-mssound.wav').write_bytes(stream.getvalue());text=native().replace('DefaultValue=','DefaultValue=%WinDir%Media\\The Microsoft Sound.wav')
  self.assertEqual(self.load(text,assets=assets)[1]['sounds']['events']['SystemStart'],str(assets/'sound-mssound.wav'))
if __name__=='__main__':unittest.main()
