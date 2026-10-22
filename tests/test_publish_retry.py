import unittest
from unittest.mock import patch
from inspection.exporter import publish_no_replace

def sharing():
    e=PermissionError(13,'synthetic sharing violation');e.winerror=32;return e

class PublishRetryTests(unittest.TestCase):
    def test_transient_sharing_violation_recovers(self):
        with patch('inspection.exporter.os.rename',side_effect=[sharing(),None]) as rename,patch('inspection.exporter.time.sleep') as sleep:
            publish_no_replace('stage','final')
        self.assertEqual(rename.call_count,2);sleep.assert_called_once_with(.05)

    def test_collision_during_retry_never_retried_or_overwritten(self):
        with patch('inspection.exporter.os.rename',side_effect=[sharing(),FileExistsError('existing')]) as rename,patch('inspection.exporter.time.sleep') as sleep:
            with self.assertRaises(FileExistsError):publish_no_replace('stage','final')
        self.assertEqual(rename.call_count,2);self.assertEqual(sleep.call_count,1)

    def test_persistent_sharing_is_bounded(self):
        with patch('inspection.exporter.os.rename',side_effect=sharing()) as rename,patch('inspection.exporter.time.sleep') as sleep:
            with self.assertRaises(PermissionError):publish_no_replace('stage','final')
        self.assertEqual(rename.call_count,7);self.assertLessEqual(sum(c.args[0] for c in sleep.call_args_list),2.6)

    def test_other_io_errors_are_not_retried(self):
        with patch('inspection.exporter.os.rename',side_effect=PermissionError(13,'denied')) as rename,patch('inspection.exporter.time.sleep') as sleep:
            with self.assertRaises(PermissionError):publish_no_replace('stage','final')
        rename.assert_called_once();sleep.assert_not_called()
