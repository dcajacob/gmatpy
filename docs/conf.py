"""Sphinx configuration: build from source without loading the native engine."""
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_api import check_api

project = "GMAT Py"
author = "GMAT Py contributors"
copyright = "2026, GMAT Py contributors"
release = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
version = release
extensions = ["sphinx.ext.duration"]
root_doc = "index"
exclude_patterns = ["_build", "examples", "README.rst"]
language = "en"
nitpicky = True
highlight_language = "python"
html_theme = "furo"
html_title = f"GMAT Py {release}"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_theme_options = {
    "source_repository": "https://github.com/dcajacob/gmatpy/",
    "source_branch": "main",
    "source_directory": "docs/",
    "light_css_variables": {"color-brand-primary": "#165d8d", "color-brand-content": "#165d8d"},
    "dark_css_variables": {"color-brand-primary": "#71c4ee", "color-brand-content": "#71c4ee"},
}
html_show_sourcelink = True
html_copy_source = True
python_maximum_signature_line_length = 88
linkcheck_retries = 2
linkcheck_timeout = 20
linkcheck_workers = 5
linkcheck_rate_limit_timeout = 30
# GitHub renders fragment IDs client-side; check the destination pages instead.
linkcheck_anchors = False


def setup(app):
    def validate_api(app):
        check_api(ROOT)

    app.connect("builder-inited", validate_api)
    return {"parallel_read_safe": True, "parallel_write_safe": True}
