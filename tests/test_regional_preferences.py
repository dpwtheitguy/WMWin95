import sys,unittest,tempfile
from dataclasses import replace
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.regional_preferences import RegionalPreferences,RegionalBackend,regional_preset,current,config_path
from win95lx.control_panel.preferences import PreferenceController

class RegionalTests(unittest.TestCase):
    def test_number_rounding_grouping_and_leading_zero(self):
        p=RegionalPreferences();self.assertEqual(p.number('1234567.125'),'1,234,567.13');self.assertEqual(p.number('-0.5'),'-0.50')
        self.assertEqual(replace(p,leading_zero=False,group_size=0).number('0.5'),'.50')
        self.assertEqual(replace(p,digits=0).number('1234.5'),'1,235')
    def test_all_negative_and_currency_layouts_render_values(self):
        p=RegionalPreferences()
        for fmt in ('(1.1)','-1.1','- 1.1','1.1-','1.1 -'):
            text=replace(p,negative_format=fmt).number('-12.3');self.assertIn('12.30',text)
        for fmt in ('($1.1)','-$1.1','$-1.1','$1.1-','(1.1$)','-1.1$','1.1-$','1.1$-','-1.1 $','-$ 1.1','1.1 $-','$ 1.1-','$ -1.1','1.1- $','($ 1.1)','(1.1 $)'):
            text=replace(p,currency_negative=fmt,currency='€').number('-12.3',True);self.assertIn('€',text);self.assertIn('12.30',text)
    def test_date_time_tokens_literals_and_custom_symbols(self):
        p=RegionalPreferences();value=datetime(2024,2,29,13,4,5)
        self.assertEqual(p.date(value),'2/29/24');self.assertEqual(p.date(value,p.long_date),'Thursday, February 29, 2024')
        self.assertEqual(p.time(value),'1:04:05 PM');self.assertEqual(p.short_time(value),'1:04 PM')
        self.assertEqual(replace(p,time_style='HH:mm:ss',time_separator='.').time(value),'13.04.05')
        self.assertEqual(p.date(value,"yyyy'-'MM'-'dd"),'2024-02-29')
    def test_german_numeric_clipboard_and_localized_names(self):
        p=regional_preset('German (Germany)');value=datetime(2026,3,1)
        self.assertEqual(p.number('1234.56'),'1.234,56');self.assertEqual(p.calculator_input('1.234,56'),'1234.56')
        self.assertEqual(p.calculator_text('1234.56'),'1234,56');self.assertIn('März',p.date(value,p.long_date))
    def test_invalid_symbols_limits_and_formats_are_rejected(self):
        for p in (replace(RegionalPreferences(),decimal=','),replace(RegionalPreferences(),digits=10),replace(RegionalPreferences(),negative_format='invalid'),replace(RegionalPreferences(),am='bad\nvalue')):
            with self.assertRaises(ValueError):p.validate()
    def test_apply_cancel_persistence_cache_invalidation_and_file_failure(self):
        with tempfile.TemporaryDirectory() as d,patch('pathlib.Path.home',return_value=Path(d)):
            path=config_path();controller=PreferenceController(path,RegionalBackend(path),RegionalPreferences)
            self.assertEqual(current().decimal,'.');controller.pending=regional_preset('German (Germany)');controller.apply();self.assertEqual(current().decimal,',')
            controller.pending=RegionalPreferences();controller.cancel();self.assertEqual(controller.pending.decimal,',')
            controller.pending=RegionalPreferences()
            with patch('win95lx.control_panel.preferences.save_preferences',side_effect=OSError('Read only')):
                with self.assertRaises(OSError):controller.apply()
            self.assertEqual(current().decimal,',');self.assertEqual(controller.backend.value.decimal,',')
    def test_list_separator_and_measurement_preset_are_retained(self):
        p=replace(regional_preset('German (Germany)'),list_separator=';')
        self.assertEqual(p.list_text((1,2,3)),'1;2;3');self.assertEqual(p.measurement,'Metric')

if __name__=='__main__':unittest.main()
