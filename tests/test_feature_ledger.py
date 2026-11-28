from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('feature_ledger_tool',ROOT/'tools/feature_ledger.py');ledger=importlib.util.module_from_spec(spec);spec.loader.exec_module(ledger)

class FeatureLedgerTests(unittest.TestCase):
    def setUp(self):self.document=json.loads((ROOT/'config/feature-ledger.json').read_text())
    def test_current_ledger_valid(self):ledger.validate(self.document)
    def test_plus_evidence_does_not_accept_rtm_plus(self):
        self.assertEqual(ledger.variant(self.document,'THEME-CORE','rtm-classic-plus95')['status'],'not_tested')
    def test_ie4_evidence_does_not_accept_classic(self):
        self.assertEqual(ledger.variant(self.document,'EXPL-RECYCLE-MODAL','osr2_5-classic')['status'],'not_tested')
    def test_failed_preview_remains_failed(self):
        self.assertEqual(ledger.variant(self.document,'THEME-PREVIEW','osr2_5-ie4-plus95')['status'],'failed')
    def test_browser_install_does_not_enable_desktop_update(self):
        profile=self.document['profiles']['rtm-classic'];profile['ie_browser_version']='4.01';profile['active_desktop']=True
        with self.assertRaises(ValueError):ledger.validate(self.document)
    def test_plus_and_ie4_are_independent(self):
        self.assertEqual(self.document['profiles']['osr2_5-classic-plus95']['shell_generation'],'classic')
        self.assertEqual(self.document['profiles']['osr2_5-ie4']['plus_pack'],'none')
    def test_plus_label_does_not_invent_component_inventory(self):
        self.assertIsNone(self.document['profiles']['osr2_5-ie4-plus95']['plus_components'])
    def test_plus_components_without_pack_rejected(self):
        self.document['profiles']['rtm-classic']['plus_components']=['desktop_themes']
        with self.assertRaises(ValueError):ledger.validate(self.document)
    def test_unknown_plus_component_rejected(self):
        self.document['profiles']['osr2_5-ie4-plus95']['plus_components']=['invented_component']
        with self.assertRaises(ValueError):ledger.validate(self.document)
    def test_accepted_variant_requires_evidence_and_conditions(self):
        record=self.document['features'][0]['variants']['osr2_5-ie4-plus95'];record['status']='accepted'
        with self.assertRaises(ValueError):ledger.validate(self.document)
        record['conditions']={'state':'named native dialog','resolution':[800,600],'color_depth':8}
        ledger.validate(self.document)
        record['evidence']=[]
        with self.assertRaises(ValueError):ledger.validate(self.document)
    def test_unknown_profile_cannot_fall_back_to_default(self):
        with self.assertRaises(ValueError):ledger.variant(self.document,'THEME-CORE','unknown')
    def test_prepared_reference_does_not_imply_accepted_feature(self):
        self.assertEqual(self.document['profiles']['osr2_5-ie4']['reference_status'],'prepared_reference')
        self.assertEqual(ledger.variant(self.document,'THEME-CORE','osr2_5-ie4')['status'],'not_tested')
    def test_unsafe_default_status_rejected(self):
        self.document['default_variant_status']='accepted'
        with self.assertRaises(ValueError):ledger.validate(self.document)

if __name__=='__main__':unittest.main()
