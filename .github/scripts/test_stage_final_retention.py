"""Synthetic retention guard tests; these do not qualify any native binary."""
import copy
import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('retention', Path(__file__).with_name('stage-final-retention.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RetentionGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'input'
        self.dest = Path(self.temp.name)/'staged'
        self.root.mkdir()
        self.expected = copy.deepcopy(m.EXPECTED)
        self.write('frozen/artifacts/gmatpy-0.2.0.tar.gz', b'synthetic sdist')
        self.write('frozen/WORKING_TREE.json', b'synthetic working manifest')
        self.expected['source_archive_sha256'] = m.sha(self.root/'frozen/artifacts/gmatpy-0.2.0.tar.gz')
        self.expected['working_tree_manifest_sha256'] = m.sha(self.root/'frozen/WORKING_TREE.json')
        self.write_json('frozen/SOURCE_RECEIPT.json', self.expected)
        self.patch_expected = patch.object(m, 'EXPECTED', self.expected)
        self.patch_expected.start()
        self.addCleanup(self.patch_expected.stop)
        self.env = patch.dict(os.environ, {'GITHUB_REPOSITORY':'dcajacob/gmatpy',
            'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','GITHUB_SHA':'a'*40,'GITHUB_JOB':'native'})
        self.env.start()
        self.addCleanup(self.env.stop)
        for relative in m.EVIDENCE:
            if relative != 'frozen/SOURCE_RECEIPT.json':
                self.write(relative, b'synthetic evidence\n')
        for name in ('auditwheel-before.log','auditwheel-after.log'):
            self.write('qualified/extended/'+name, b'synthetic audit\n')
        self.wheel_name = 'gmatpy-0.2.0-cp314-cp314-manylinux_2_28_aarch64.whl'
        self.wheel = self.root/'qualified/extended/wheelhouse'/self.wheel_name
        self.wheel.parent.mkdir(parents=True)
        self.provenance = {k:self.expected[k] for k in ('source_revision','source_tree_sha256','working_tree_manifest_sha256')}
        self.make_wheel()
        self.profile = {'wheel':self.wheel_name,'sha256':m.sha(self.wheel),'bytes':self.wheel.stat().st_size,
            'tests':'192 passed in 1.00s',
            'state_comparison':{'position_tolerance_km':2e-7,'velocity_tolerance_km_s':2e-10,
                'maximum_position_error_km':0.0,'maximum_velocity_error_km_s':0.0},
            'spline_comparison':{'cases':320,'compared_values':9920,'tolerance':1e-10,'maximum_scaled_error':0,
                'analytic_regressions':{'cases':17,'compared_values':54,
                    'results':[{'passed':True,'finite':True} for _ in range(17)]}},
            'msise_comparison':{'cases':12,'compared_values':51,'passed':True,
                'records':[{'passed':True,'finite':True} for _ in range(12)]}}
        self.result = {'target':'linux-arm64','sdist_sha256':self.expected['source_archive_sha256'],
            'source_tree_sha256':self.expected['source_tree_sha256'],'release_preflight':'passed',
            'profiles':{'extended':self.profile},'python':'synthetic CPython3.14','platform':'synthetic Linux',
            'cspice_library_sha256':'b'*64}
        self.write_json('qualified/CSPICE_BUILD_DEPENDENCY.json',{'target':'linux-arm64','library_sha256':'b'*64})
        self.refresh()

    def write(self, path, data):
        p = self.root/path
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(data)

    def write_json(self, path, value):
        self.write(path, (json.dumps(value,indent=2)+'\n').encode())

    def make_wheel(self):
        with zipfile.ZipFile(self.wheel,'w') as z:
            z.writestr('gmatpy/BUILD_PROVENANCE.json',json.dumps(self.provenance))

    def refresh(self):
        self.write_json('qualified/RESULTS.json',self.result)
        hashes={str(p.relative_to(self.root/'qualified')):m.sha(p)
                for p in (self.root/'qualified').rglob('*') if p.is_file() and p.name!='EVIDENCE_SHA256.json'}
        self.write_json('qualified/EVIDENCE_SHA256.json',hashes)

    def reject(self):
        with self.assertRaises((ValueError,KeyError,FileNotFoundError)):
            m.stage(self.root,'linux-arm64',self.dest)
        self.assertFalse(self.dest.exists())

    def test_exact_allowlist_and_receipt(self):
        m.stage(self.root,'linux-arm64',self.dest)
        receipt=json.loads((self.dest/'RETENTION_RECEIPT.json').read_text())
        for f in receipt['files']:
            self.assertEqual(m.sha(self.dest/f['path']),f['sha256'])
        self.assertEqual(receipt['totals']['payload_bytes'],sum(p.stat().st_size for p in self.dest.rglob('*') if p.is_file()))
        self.assertEqual(receipt['totals']['receipt_bytes'],(self.dest/'RETENTION_RECEIPT.json').stat().st_size)
        self.assertEqual(len(list(self.dest.rglob('*.whl'))),1)
        self.assertFalse((self.dest/'frozen/artifacts').exists())

    def test_changed_source_receipt(self):
        self.write_json('frozen/SOURCE_RECEIPT.json',{**self.expected,'source_revision':'c'*40});self.reject()

    def test_changed_actual_sdist(self):
        self.write('frozen/artifacts/gmatpy-0.2.0.tar.gz',b'changed');self.reject()

    def test_changed_actual_working_manifest(self):
        self.write('frozen/WORKING_TREE.json',b'changed');self.reject()

    def test_changed_evidence(self):
        self.write('qualified/extended/installed-bytes.log',b'changed');self.reject()

    def test_missing_required_evidence(self):
        (self.root/'qualified/extended/build.log').unlink();self.reject()

    def test_symlink_evidence(self):
        p=self.root/'qualified/extended/build.log';p.unlink();p.symlink_to('repair.log');self.reject()

    def test_extra_wheel(self):
        self.write('qualified/extended/wheelhouse/extra.whl',b'no');self.reject()

    def test_wrong_architecture(self):
        self.wheel.rename(self.wheel.with_name(self.wheel_name.replace('aarch64','x86_64')));self.reject()

    def test_wrong_python_abi(self):
        self.wheel.rename(self.wheel.with_name(self.wheel_name.replace('cp314-cp314','cp314-abi3')));self.reject()

    def test_obsolete_build_tag(self):
        self.wheel.rename(self.wheel.with_name(self.wheel_name.replace('0.2.0-','0.2.0-2extended-')));self.reject()

    def macos(self, target, arch):
        self.wheel.unlink()
        self.wheel_name=f'gmatpy-0.2.0-cp314-cp314-macosx_11_0_{arch}.whl'
        self.wheel=self.wheel.with_name(self.wheel_name);self.make_wheel()
        self.result['target']=target
        self.profile.update(wheel=self.wheel_name,sha256=m.sha(self.wheel),bytes=self.wheel.stat().st_size)
        self.write_json('qualified/CSPICE_BUILD_DEPENDENCY.json',{'target':target,'library_sha256':'b'*64})
        self.refresh();m.stage(self.root,target,self.dest)
        self.assertFalse((self.dest/'qualified/extended/auditwheel-after.log').exists())

    def test_macos_arm_allowlist(self):
        self.macos('macos-arm64','arm64')

    def test_macos_intel_allowlist(self):
        self.macos('macos-x86_64','x86_64')

    def test_stale_embedded_provenance(self):
        self.provenance['source_revision']='c'*40;self.make_wheel()
        self.profile.update(sha256=m.sha(self.wheel),bytes=self.wheel.stat().st_size);self.refresh();self.reject()

    def test_unexpected_skips(self):
        self.profile['tests']='191 passed, 1 skipped in 1.00s';self.refresh();self.reject()

    def test_nonfinite_result(self):
        self.profile['state_comparison']['maximum_position_error_km']=float('nan');self.refresh();self.reject()

    def test_widened_tolerance(self):
        self.profile['state_comparison']['position_tolerance_km']=1e-3;self.refresh();self.reject()

    def test_failed_preflight(self):
        self.result['release_preflight']='failed';self.refresh();self.reject()

    def test_evidence_cap(self):
        self.write('qualified/extended/build.log',b'x'*m.EVIDENCE_CAP);self.refresh();self.reject()

    def test_wheel_cap(self):
        with self.wheel.open('r+b') as f:f.truncate(m.WHEEL_CAP+1)
        self.reject()

    def test_unapproved_rerun(self):
        with patch.dict(os.environ,{'GITHUB_RUN_ATTEMPT':'2'}):self.reject()

    def test_unapproved_target(self):
        with self.assertRaises(ValueError):m.stage(self.root,'linux-x86_64',self.dest)
        self.assertFalse(self.dest.exists())


if __name__ == '__main__':
    unittest.main()
