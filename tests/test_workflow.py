import hashlib,json,struct,subprocess,sys,tempfile,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from pixels import read,write
from ppm_to_png import convert
from reference_vm import plan
class Workflow(unittest.TestCase):
    def test_ppm_preserves_whitespace_pixel(self):
        with tempfile.TemporaryDirectory() as d:
            ppm=Path(d)/'a.ppm'; png=Path(d)/'a.png'; ppm.write_bytes(b'P6\n1 1\n255\n'+bytes([10,32,13])); convert(ppm,png)
            self.assertEqual(read(png),(1,1,[(10,32,13,255)]))
    def test_reference_hash_enforced_and_diff_exit_code(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); a=d/'a.png'; b=d/'b.png'; cfg=d/'cfg.json'
            write(a,1,1,[(0,0,0,255)]); write(b,1,1,[(1,0,0,255)])
            config={'reference':str(a),'actual':str(b),'reference_sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'masks':[]}; cfg.write_text(json.dumps(config))
            result=subprocess.run([sys.executable,str(ROOT/'tools/compare.py'),str(cfg),'--output',str(d/'results')],capture_output=True)
            self.assertEqual(result.returncode,1,result.stderr); self.assertTrue((d/'results/diff.png').is_file())
            config['reference_sha256']='bad'; cfg.write_text(json.dumps(config))
            result=subprocess.run([sys.executable,str(ROOT/'tools/compare.py'),str(cfg),'--output',str(d/'bad')],capture_output=True)
            self.assertEqual(result.returncode,2); self.assertFalse((d/'bad').exists())
    def test_reference_plan_has_no_network(self):
        cmd=plan(Path('source.iso'),Path('disk.qcow2'),'kvm'); self.assertEqual(cmd[cmd.index('-nic')+1],'none'); self.assertIn('readonly=on',','.join(cmd))
