"""Verify the production promotion restrictions without uploading or minting credentials."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import urllib.error

import pytest

spec = importlib.util.spec_from_file_location("promotion", Path(__file__).with_name("prepare-pypi-0.2.0.py"))
promotion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(promotion)
RELEASE = Path(__file__).parents[1] / "release"
BASE = (RELEASE / "testpypi-09eafabe.json").read_bytes()
CONFIG = json.loads((RELEASE / "pypi-0.2.0.json").read_text())


def test_exact_trial_configuration():
    manifest = promotion.check_config(CONFIG, BASE)
    assert manifest["candidate_source_revision"] == promotion.guard.SOURCE
    assert manifest["native_build_source_revision"] == promotion.guard.NATIVE_SOURCE


@pytest.mark.parametrize("field,value", [
    ("project", "other"), ("version", "0.2.1"), ("schema_version", 2),
    ("upload_endpoint", "https://test.pypi.org/legacy/"),
    ("base_allowlist_sha256", "0" * 64), ("testpypi_trial_receipt_sha256", "0" * 64),
])
def test_configuration_substitution(field, value):
    config = copy.deepcopy(CONFIG)
    config[field] = value
    with pytest.raises(ValueError):
        promotion.check_config(config, BASE)


def test_changed_base_inventory():
    with pytest.raises(ValueError):
        promotion.check_config(CONFIG, BASE + b"\n")


def test_incomplete_or_extra_bundle():
    for selection in promotion.ORDER:
        config = copy.deepcopy(CONFIG)
        del config["public_testpypi_downloads"][selection]
        with pytest.raises(ValueError):
            promotion.check_config(config, BASE)
    config = copy.deepcopy(CONFIG)
    config["public_testpypi_downloads"]["windows"] = "https://example.com/other.whl"
    with pytest.raises(ValueError):
        promotion.check_config(config, BASE)


@pytest.mark.parametrize("url", [
    "http://test-files.pythonhosted.org/packages/aa/bb/cc/gmatpy-0.2.0.tar.gz",
    "https://localhost/packages/aa/bb/cc/gmatpy-0.2.0.tar.gz",
    "https://user@test-files.pythonhosted.org/packages/aa/bb/cc/gmatpy-0.2.0.tar.gz",
    "https://test-files.pythonhosted.org.evil.example/packages/aa/bb/cc/gmatpy-0.2.0.tar.gz",
    "https://test-files.pythonhosted.org:443/packages/aa/bb/cc/gmatpy-0.2.0.tar.gz",
    "https://test-files.pythonhosted.org/packages/aa/bb/cc/other.tar.gz",
    "https://test-files.pythonhosted.org/packages/aa/bb/../gmatpy-0.2.0.tar.gz",
    "https://test-files.pythonhosted.org/packages/aa/bb/cc/gmatpy-0.2.0.tar.gz?x=1",
    "https://test-files.pythonhosted.org/packages/aa/bb/cc/gmatpy-0.2.0.tar.gz#x",
])
def test_unapproved_download_url(url):
    with pytest.raises(ValueError):
        promotion.check_url(url, "gmatpy-0.2.0.tar.gz")


def test_production_workflow_identity():
    context = {"GITHUB_REPOSITORY": "dcajacob/gmatpy", "GITHUB_REF": "refs/heads/main",
               "GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_RUN_ATTEMPT": "1",
               "GITHUB_WORKFLOW_REF": "dcajacob/gmatpy/.github/workflows/publish-pypi.yml@refs/heads/main"}
    promotion.check_context(context)
    for key in context:
        with pytest.raises(ValueError):
            promotion.check_context(dict(context, **{key: "wrong"}))


class Response(io.BytesIO):
    status = 200
    headers = {}


class Opener:
    def __init__(self, payload):
        self.payload = payload

    def open(self, *args, **kwargs):
        return Response(self.payload)


@pytest.mark.parametrize("payload,passes", [(b"good", True), (b"bad", False),
                                           (b"good extra", False), (b"evil", False)])
def test_download_integrity_and_partial_cleanup(tmp_path, payload, passes):
    record = {"filename": "gmatpy-0.2.0.tar.gz", "bytes": 4, "sha256": hashlib.sha256(b"good").hexdigest()}
    output = tmp_path / record["filename"]
    url = "https://test-files.pythonhosted.org/packages/aa/bb/cc/" + record["filename"]
    if passes:
        promotion.download_one(Opener(payload), url, output, record)
        assert output.read_bytes() == b"good"
    else:
        with pytest.raises(ValueError):
            promotion.download_one(Opener(payload), url, output, record)
        assert not output.exists()


def test_existing_file_is_preserved(tmp_path):
    output = tmp_path / "gmatpy-0.2.0.tar.gz"
    output.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        promotion.download_one(Opener(b"good"), CONFIG["public_testpypi_downloads"]["sdist"], output,
                               {"filename": output.name, "bytes": 4, "sha256": "0" * 64})
    assert output.read_bytes() == b"existing"


def test_redirect_is_rejected():
    with pytest.raises(ValueError):
        promotion.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://evil.example")


@pytest.mark.parametrize("status,allowed", [(404, True), (200, False), (403, False), (503, False)])
def test_project_preflight_fails_closed(status, allowed):
    class ProjectOpener:
        def open(self, *args, **kwargs):
            if status != 200:
                raise urllib.error.HTTPError("https://pypi.org/pypi/gmatpy/json", status, "test", {}, None)
            return Response(b"{}")
    if allowed:
        promotion.require_new_project(ProjectOpener())
    else:
        with pytest.raises((ValueError, urllib.error.HTTPError)):
            promotion.require_new_project(ProjectOpener())
