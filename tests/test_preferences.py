import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from inspection import preferences

class PreferencesChecks(unittest.TestCase):
    def test_only_explicit_manual_fields_survive_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'nested'/'preferences.json'
            self.assertEqual(preferences.load(p),{})
            preferences.save(p,{'inspector':'가상 점검자','visit_org':'가상 방문기관','project':'비공개 과제','visit_date':'2026-10-23','api_key':'never'})
            self.assertEqual(preferences.load(p),{'inspector':'가상 점검자','visit_org':'가상 방문기관'})
            preferences.save(p,{'inspector':'가상 수정자'})
            self.assertEqual(preferences.load(p),{'inspector':'가상 수정자'})
            preferences.save(p,{})
            self.assertEqual(preferences.load(p),{})
            self.assertEqual(list(p.parent.iterdir()),[p])

    def test_invalid_file_does_not_crash_or_get_overwritten_on_load(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'preferences.json';p.write_text('{invalid',encoding='utf-8')
            with self.assertRaises(ValueError):preferences.load(p)
            self.assertEqual(p.read_text(encoding='utf-8'),'{invalid')
            p.write_text(json.dumps({'version':1,'pinned':{'inspector':42,'inspector_org':'x'*2001,'visit_org':'가상'}}),encoding='utf-8')
            self.assertEqual(preferences.load(p),{'visit_org':'가상'})

    def test_failed_atomic_save_keeps_previous_values(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'preferences.json';preferences.save(p,{'inspector':'가상 기존'})
            with patch('inspection.preferences.os.replace',side_effect=PermissionError('synthetic')):
                with self.assertRaises(PermissionError):preferences.save(p,{'inspector':'가상 새 값'})
            self.assertEqual(preferences.load(p),{'inspector':'가상 기존'})
            self.assertEqual(list(p.parent.iterdir()),[p])
