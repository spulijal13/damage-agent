import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from damage_agent import champions_learnsets as module


class LearnsetRefreshTests(unittest.TestCase):
    def test_local_read_never_fetches(self):
        with patch.object(module, 'urlopen') as fetch:
            self.assertEqual(module.get_learnsets()['source'], 'local')
            fetch.assert_not_called()

    def test_failed_refresh_preserves_file_and_success_replaces_it(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'learnsets.json'
            target.write_text('{"old": ["protect"]}')
            response = MagicMock()
            response.__enter__.return_value.read.return_value = b'invalid data'
            with patch.object(module, 'FALLBACK_PATH', target), patch.object(module, 'urlopen', return_value=response):
                with self.assertRaises(ValueError):
                    module.refresh_learnsets()
                self.assertEqual(json.loads(target.read_text()), {'old':['protect']})
                entries = {'venusaur':['protect'], **{f'mon{i}':['tackle'] for i in range(200)}}
                with patch.object(module, 'parse_learnsets', return_value=entries):
                    self.assertEqual(module.refresh_learnsets(),201)
                self.assertEqual(module.get_learnsets()['learnsets'], entries)
                self.assertEqual(list(Path(directory).glob('*.tmp')), [])
