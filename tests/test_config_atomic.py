import errno
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bosshunter.config import _load_yaml_mapping, _write_yaml_atomic


class ConfigAtomicTests(unittest.TestCase):
    def test_reader_is_closed_before_yaml_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.yaml'
            path.write_text('value: old\n', encoding='utf-8')

            def parse(text):
                # On Windows this replacement fails if the read handle is open.
                replacement = path.with_suffix('.replacement')
                replacement.write_text('value: new\n', encoding='utf-8')
                os.replace(replacement, path)
                self.assertEqual(text, 'value: old\n')
                return {'value': 'old'}

            with patch('bosshunter.config.yaml.safe_load', side_effect=parse):
                self.assertEqual(_load_yaml_mapping(path), {'value': 'old'})
            self.assertEqual(path.read_text(encoding='utf-8'), 'value: new\n')

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_real_windows_reader_released_during_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.yaml'
            path.write_text('value: old\n', encoding='utf-8')
            with path.open(encoding='utf-8') as reader:
                def release_reader(_delay):
                    self.assertEqual(path.read_text(encoding='utf-8'), 'value: old\n')
                    reader.close()

                with patch('bosshunter.config.time.sleep', side_effect=release_reader) as wait:
                    _write_yaml_atomic(path, {'value': 'new'})
                wait.assert_called_once()
            self.assertEqual(_load_yaml_mapping(path), {'value': 'new'})
            self.assertEqual(list(Path(tmp).glob('*.tmp')), [])

    def test_persistent_windows_errors_preserve_original_and_clean_temp(self):
        for code in (5, 32, 33):
            with self.subTest(winerror=code), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'config.yaml'
                original = b'value: old\n'
                path.write_bytes(original)
                error = PermissionError(errno.EACCES, 'locked')
                error.winerror = code
                with (
                    patch('bosshunter.config.os.replace', side_effect=error) as replace,
                    patch('bosshunter.config.time.sleep') as wait,
                    self.assertRaises(PermissionError),
                ):
                    _write_yaml_atomic(path, {'value': 'new'})
                self.assertEqual(replace.call_count, 6)
                self.assertEqual(wait.call_count, 5)
                self.assertLessEqual(sum(call.args[0] for call in wait.call_args_list), 1.2)
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(Path(tmp).glob('*.tmp')), [])

    def test_other_errors_are_not_retried(self):
        for error in (PermissionError(errno.EACCES, 'denied'), OSError(errno.ENOSPC, 'disk full')):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'config.yaml'
                path.write_text('value: old\n', encoding='utf-8')
                with (
                    patch('bosshunter.config.os.replace', side_effect=error) as replace,
                    patch('bosshunter.config.time.sleep') as wait,
                    self.assertRaises(OSError),
                ):
                    _write_yaml_atomic(path, {'value': 'new'})
                replace.assert_called_once()
                wait.assert_not_called()
                self.assertEqual(path.read_text(encoding='utf-8'), 'value: old\n')
                self.assertEqual(list(Path(tmp).glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
