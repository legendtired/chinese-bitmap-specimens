import importlib.util
from pathlib import Path
import unittest
import subprocess
import sys
import tempfile

spec = importlib.util.spec_from_file_location('fix_count', Path(__file__).resolve().parents[1] / 'scripts/fix_bdf_char_count.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SAMPLE = b'STARTFONT 2.1\nFONT sample\nCHARS 0\nSTARTCHAR A\nENCODING 65\nDWIDTH 8 0\nBBX 1 1 0 0\nBITMAP\n80\nENDCHAR\nENDFONT\n'

class Counts(unittest.TestCase):
    def test_changes_only_count(self):
        result, old, new = module.fix_count(SAMPLE)
        self.assertEqual(result, SAMPLE.replace(b'CHARS 0', b'CHARS 1'))
        self.assertEqual((old,new),(0,1))
    def test_preserves_crlf(self):
        data = SAMPLE.replace(b'\n', b'\r\n')
        self.assertEqual(module.fix_count(data)[0], data.replace(b'CHARS 0', b'CHARS 1'))
    def test_idempotent(self):
        fixed = module.fix_count(SAMPLE)[0]
        self.assertEqual(module.fix_count(fixed), (fixed,1,1))
    def test_rejects_missing_end(self):
        with self.assertRaises(ValueError): module.fix_count(SAMPLE.replace(b'ENDCHAR\n',b''))
    def test_rejects_repeated_chars(self):
        with self.assertRaises(ValueError): module.fix_count(SAMPLE.replace(b'CHARS 0',b'CHARS 0\nCHARS 0'))
    def test_rejects_missing_chars(self):
        with self.assertRaises(ValueError): module.fix_count(SAMPLE.replace(b'CHARS 0\n', b''))
    def test_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.bdf'
            output = Path(directory) / 'output.bdf'
            source.write_bytes(SAMPLE)
            output.write_bytes(b'keep this')
            run = subprocess.run([sys.executable, module.__file__, str(source), str(output)], capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(output.read_bytes(), b'keep this')
    def test_refuses_input_as_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.bdf'
            source.write_bytes(SAMPLE)
            run = subprocess.run([sys.executable, module.__file__, str(source), str(source)], capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual(source.read_bytes(), SAMPLE)
    def test_rejects_missing_endfont(self):
        with self.assertRaises(ValueError): module.fix_count(SAMPLE.replace(b'ENDFONT\n',b''))

if __name__ == '__main__': unittest.main()
