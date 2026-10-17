"""Source-identity rejection checks before native runner allocation/build work."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

path=Path(__file__).resolve().parents[1]/'ci/check_frozen_input.py'
spec=importlib.util.spec_from_file_location('frozen_input',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class FrozenInput(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'artifacts').mkdir()
        (self.root/'artifacts/source.tar.gz').write_bytes(b'immutable archive fixture')
        (self.root/'WORKING_TREE.json').write_text('{"source_revision":"aaaa"}\n')
        self.receipt={'source_revision':'a'*40,'source_archive':'source.tar.gz',
                      'source_archive_sha256':hashlib.sha256(b'immutable archive fixture').hexdigest(),
                      'working_tree_manifest_sha256':hashlib.sha256((self.root/'WORKING_TREE.json').read_bytes()).hexdigest()}
        self.save()

    def save(self):
        (self.root/'SOURCE_RECEIPT.json').write_text(json.dumps(self.receipt))

    def test_exact_receipt_passes(self):
        self.assertEqual(module.check(self.root,'a'*40),self.receipt)

    def test_other_commit_rejected(self):
        with self.assertRaises(AssertionError):module.check(self.root,'b'*40)

    def test_changed_archive_rejected(self):
        (self.root/'artifacts/source.tar.gz').write_bytes(b'changed archive')
        with self.assertRaises(AssertionError):module.check(self.root,'a'*40)

    def test_changed_working_manifest_rejected(self):
        (self.root/'WORKING_TREE.json').write_text('{}')
        with self.assertRaises(AssertionError):module.check(self.root,'a'*40)

    def test_second_source_archive_rejected(self):
        (self.root/'artifacts/extra.tar.gz').write_bytes(b'extra')
        with self.assertRaises(AssertionError):module.check(self.root,'a'*40)

    def test_wrong_filename_rejected(self):
        self.receipt['source_archive']='other.tar.gz';self.save()
        with self.assertRaises(AssertionError):module.check(self.root,'a'*40)


if __name__=='__main__':unittest.main()
