"""Reject staging identity/asset substitutions without network or publication."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("stage", Path(__file__).with_name("stage-testpypi.py"))
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)
MANIFEST = json.loads((Path(__file__).parents[1] / "release/testpypi-09eafabe.json").read_text())


class StagingTests(unittest.TestCase):
    def setUp(self):
        self.record = MANIFEST["files"]["linux-x86_64"]
        self.release = {
            "id": 123, "draft": True, "tag_name": stage.TAG,
            "target_commitish": stage.guard.SOURCE, "author": {"login": "dcajacob"},
            "assets": [{"id": 456, "name": self.record["filename"],
                        "size": self.record["bytes"], "state": "uploaded",
                        "digest": "sha256:" + self.record["sha256"],
                        "uploader": {"login": "dcajacob"}}],
        }

    def test_exact_draft(self):
        stage.check_release(self.release, "123", "456", self.record)

    def test_wrong_release_identity(self):
        for field, value in (("id", 999), ("draft", False), ("draft", 1),
                             ("tag_name", "v0.2.0"), ("target_commitish", "main"),
                             ("author", {"login": "other"})):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(self.release)
                changed[field] = value
                with self.assertRaises(ValueError):
                    stage.check_release(changed, "123", "456", self.record)

    def test_wrong_asset_identity(self):
        for field, value in (("id", 999), ("name", "other.whl"), ("size", 1),
                             ("state", "starter"), ("digest", "sha256:" + "0" * 64),
                             ("uploader", {"login": "other"})):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.release)
                changed["assets"][0][field] = value
                with self.assertRaises(ValueError):
                    stage.check_release(changed, "123", "456", self.record)

    def test_extra_or_missing_asset(self):
        for assets in ([], self.release["assets"] * 2):
            changed = copy.deepcopy(self.release)
            changed["assets"] = assets
            with self.assertRaises(ValueError):
                stage.check_release(changed, "123", "456", self.record)

    def test_id_injection(self):
        for bad in ("0", "-1", "123/../456", "1?x=1", "1\n", "1;echo x"):
            for release_id, asset_id in ((bad, "456"), ("123", bad)):
                with self.assertRaises(ValueError):
                    stage.check_release(self.release, release_id, asset_id, self.record)

    def test_workflow_identity(self):
        context = {
            "GITHUB_REPOSITORY": stage.guard.REPOSITORY,
            "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_WORKFLOW_REF": stage.guard.REPOSITORY
            + "/.github/workflows/stage-testpypi.yml@refs/heads/main",
        }
        stage.check_context(context)
        for key in context:
            changed = dict(context, **{key: "unapproved"})
            with self.assertRaises(ValueError):
                stage.check_context(changed)


if __name__ == "__main__":
    unittest.main()
