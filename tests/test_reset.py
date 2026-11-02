import unittest
from types import SimpleNamespace
from unittest.mock import patch,Mock
from inspection.ui import App

class ResetBoundaryTests(unittest.TestCase):
    def test_busy_reset_does_not_touch_settings_or_vault(self):
        controller=SimpleNamespace(busy=True)
        with patch('inspection.ui.preferences.save') as save,patch('inspection.ui.vault.delete') as delete,patch('inspection.ui.vault.save') as key_save:
            self.assertFalse(App.reset_workspace(controller))
            save.assert_not_called();delete.assert_not_called();key_save.assert_not_called()

    def test_preference_failure_keeps_input_and_api_state(self):
        controller=SimpleNamespace(busy=False,preferences_enabled=True,preferences_path='synthetic.json',root=Mock(),safe_error=lambda e:'가상 쓰기 오류',plan='가상 계획서',connected=True)
        with patch('inspection.ui.preferences.save',side_effect=OSError('synthetic denied')),patch('inspection.ui.messagebox.showerror') as error,patch('inspection.ui.vault.read') as read,patch('inspection.ui.vault.delete') as delete:
            self.assertFalse(App.reset_workspace(controller))
            self.assertEqual(controller.plan,'가상 계획서');self.assertTrue(controller.connected)
            error.assert_called_once();read.assert_not_called();delete.assert_not_called()

if __name__=='__main__':unittest.main()
