"""Verify the single source artifact shared by all native qualification cells."""
import hashlib,json,sys
from pathlib import Path


def check(root, revision):
    receipt=json.loads((root/'SOURCE_RECEIPT.json').read_text())
    assert receipt['source_revision']==revision
    archives=list((root/'artifacts').glob('*.tar.gz'))
    assert len(archives)==1 and archives[0].name==receipt['source_archive']
    with archives[0].open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==receipt['source_archive_sha256']
    assert hashlib.sha256((root/'WORKING_TREE.json').read_bytes()).hexdigest()==receipt['working_tree_manifest_sha256']
    print('SHARED_SOURCE_IDENTITY_OK',revision,receipt['source_archive_sha256'])
    return receipt


if __name__=='__main__':check(Path(sys.argv[1]),sys.argv[2])
