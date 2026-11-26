import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.system_info import memory_info,cpu_name,inventory

class SystemInfoTests(unittest.TestCase):
    def test_memory_cpu_and_unavailable_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'meminfo').write_text('MemTotal: 4096 kB\nMemAvailable: 1024 kB\nBroken: unknown\n');(root/'cpuinfo').write_text('model name : Test CPU\n')
            self.assertEqual(memory_info(root)['MemTotal'],4194304);self.assertEqual(cpu_name(root),'Test CPU')
            self.assertEqual(memory_info(root/'missing'),{})
    def test_inventory_uses_real_device_nodes_and_excludes_ram_devices(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ('vda','vda1','loop0'):(root/'class/block'/name).mkdir(parents=True)
            (root/'class/block/vda1/partition').write_text('1')
            pci=root/'bus/pci/devices/0000:00:02.0';pci.mkdir(parents=True);(pci/'class').write_text('0x030000');(pci/'vendor').write_text('0x1234');(pci/'device').write_text('0x1111')
            rows=inventory(root);self.assertEqual(len(rows),2);self.assertIn('vda',[device.name for device in rows]);self.assertIn('Display adapters',[device.category for device in rows])
            self.assertEqual(inventory(root/'missing'),())

if __name__=='__main__':unittest.main()
