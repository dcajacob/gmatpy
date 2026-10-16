#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify numerical gravity provenance against separately downloaded sources.

Extract member EGM96 from the NGA egm-96spherical archive and place it beside
the ICGEM JGM2.gfc and JGM3.gfc downloads in --source-dir. Exact URLs/hashes
are recorded in gmatpy/licenses/GRAVITY-DATA.txt. This tool uses no provider
software, does not download or modify files, and makes no legal determination.

Example:
    python python/tools/verify_gravity_provenance.py --source-dir /path/to/sources
"""

from __future__ import annotations

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path


MODELS = {
    "EGM96": {
        "source": "EGM96",
        "source_sha256": "1e5e6c30343989b8e2eda0bb96bde06ef05981eec69934d6e44aace4f0d6a9d5",
        "local_sha256": "4735c9301e20ee8db09b6d0882a24671b327cd35ec5740ea497c8eeb43a39807",
        "rows": 65338,
    },
    "JGM2": {
        "source": "JGM2.gfc",
        "source_sha256": "0779cf74f216d5b38c7a4c4a1a25d596b659605deb7731f00874c17e9ed3f5af",
        "local_sha256": "abac32a233e8662885778018d02e41553a5b6e5e1ee7332d2f69c362423025d3",
        "rows": 2553,
        "c20_delta": "9e-11",
    },
    "JGM3": {
        "source": "JGM3.gfc",
        "source_sha256": "2ec791eec795689291974dd3602b304029da93d3fea30096daa3b368fb231d03",
        "local_sha256": "a622342e7c5421ee0b0f01f1b5cd38e6be87f1118fbd81b8c695e8c969603819",
        "rows": 2553,
        "c20_delta": "4.173569530e-9",
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value: str) -> Decimal:
    return Decimal(value.replace("D", "E").replace("d", "e"))


def read_cof(path: Path) -> dict[tuple[int, int], tuple[Decimal, Decimal]]:
    """Read the same fixed-width RECOEF fields used by GMAT's COF loader."""
    rows = {}
    for line in path.read_text().splitlines():
        if not line.startswith("RECOEF"):
            continue
        key = int(line[8:11]), int(line[11:14])
        c = number(line[17:38].strip())
        s = number(line[38:59].strip()) if line[38:59].strip() else Decimal(0)
        if key in rows:
            raise ValueError(f"Duplicate coefficient {key} in {path}")
        rows[key] = c, s
    return rows


def read_source(path: Path, gfc: bool) -> dict[tuple[int, int], tuple[Decimal, Decimal]]:
    rows = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if gfc:
            if not fields or fields[0] != "gfc":
                continue
            fields = fields[1:]
        n, m = int(fields[0]), int(fields[1])
        # GMAT handles the central field separately and omits degree 0 and 1.
        if n < 2:
            continue
        key = n, m
        if key in rows:
            raise ValueError(f"Duplicate coefficient {key} in {path}")
        rows[key] = number(fields[2]), number(fields[3])
    return rows


def compare(name: str, local: Path, source: Path) -> dict:
    spec = MODELS[name]
    a, b = read_cof(local), read_source(source, name != "EGM96")
    failures = []
    if len(a) != spec["rows"] or set(a) != set(b):
        failures.append("Coefficient inventory differs from the pinned model")
    actual_local_hash, actual_source_hash = sha256(local), sha256(source)
    if actual_local_hash != spec["local_sha256"]:
        failures.append("Local file SHA256 differs from the documented variant")
    if actual_source_hash != spec["source_sha256"]:
        failures.append("Source file SHA256 differs from the pinned provider download")
    max_c = max_s = Decimal(0)
    for key in sorted(set(a) & set(b)):
        c_delta, s_delta = a[key][0] - b[key][0], a[key][1] - b[key][1]
        if key == (2, 0) and name != "EGM96":
            if c_delta != Decimal(spec["c20_delta"]):
                failures.append(f"Unexpected legacy C20 difference: {c_delta}")
            # Sn0 multiplies sin(0*longitude), so its source noise has no effect.
            if a[key][1] != 0:
                failures.append("Legacy local S20 is no longer zero")
            continue
        max_c, max_s = max(max_c, abs(c_delta)), max(max_s, abs(s_delta))
        for component, delta, value in zip(("C", "S"), (c_delta, s_delta), b[key]):
            tolerance = Decimal(0)
            if name == "JGM3":
                tolerance = Decimal(5).scaleb(value.as_tuple().exponent - 1)
            if abs(delta) > tolerance:
                failures.append(f"{component}{key} difference {delta} exceeds {tolerance}")
    result = {
        "model": name,
        "local_sha256": actual_local_hash,
        "source_sha256": actual_source_hash,
        "rows": len(a),
        "non_C20_max_abs_C_delta": str(max_c),
        "non_C20_max_abs_S_delta": str(max_s),
        "comparison_passed": not failures,
        "failures": failures,
    }
    if name != "EGM96":
        result["legacy_C20_delta"] = spec["c20_delta"]
        result["scientific_lineage"] = "Inherited GMAT variant; exact historical C20 transformation unverified"
    if name == "JGM3":
        result["IERS_2003_k20_0_3_correction"] = str(Decimal("4.4228e-8") * Decimal("0.31460") * Decimal("0.3"))
        result["IERS_2003_is_exact_reconstruction"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path,
                        default=Path(__file__).resolve().parents[2] / "application/data")
    args = parser.parse_args()
    try:
        results = [compare(name, args.data_dir / "gravity/earth" / f"{name}.cof",
                           args.source_dir / spec["source"]) for name, spec in MODELS.items()]
    except (OSError, ValueError, ArithmeticError) as exc:
        parser.exit(1, f"Gravity comparison failed: {exc}\n")
    print(json.dumps({"schema_version": 1, "models": results}, indent=2))
    return 0 if all(result["comparison_passed"] for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
