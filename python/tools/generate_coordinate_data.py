#!/usr/bin/env python3
"""Regenerate GMAT Py's numerical coordinate/atmosphere tables offline.

Inputs are ERFA 2.0.1's built reference library and nut80.c, the official
IERS Conventions (1996) KSV_1996_3 coefficient listing, and GMAT's Apache-2.0
ExponentialAtmosphere.cpp. This script does not download or install anything.
The generators extract scientific coefficient values, not the IERS algorithm.
ERFA-derived values are accompanied by licenses/ERFA.txt in distributions.

ICRF uses the transformation through a common terrestrial frame documented in
GMAT's CoordinateSystem help: IAU 1976/1980 on the FK5 side, IAU 2006/2000A on
the ICRF side. For reproducibility, the common Earth-rotation phase is evaluated
at TAI (the conventional UT1=TAI reference); this is not observed UT1 data.
TT is A1 + (32.184 - 0.0343817) seconds. Epoch columns are GMAT A1 modified
Julian days, JD(A1) - 2430000.0; vector columns are radians. The vectors describe
the passive FK5-to-ICRF rotation expected by ICRFFile/CoordinateConverter.

The 1994 equation-of-equinoxes complementary terms are used only after
1997-01-01, matching GMAT's implemented historical convention. No EOP,
observed celestial-pole offsets, or original ICRF vector values are inputs.
The regenerated table is intentionally identified as ICRF_ERFA_Table.txt;
small model/rounding differences versus NASA's legacy table are documented
in the data manifest and validation report. No ERFA library is needed at
GMAT Py runtime.

Reference source downloads (retrieve separately and verify before use):
  https://github.com/liberfa/erfa/releases/tag/v2.0.1
  https://iers-conventions.obspm.fr/archive/1996/1996IERSConventionsArchive.tar.gz
  NASA GMAT baseline 9363e129be366520c6edb0b4079204ed60666007

Example reference-library build without installation (omit test/version files):
  cc -shared -fPIC -O2 <ERFA src/*.c except t_erfa_c.c,
     t_erfa_c_extra.c, erfaversion.c> -lm -o liberfa-reference.so
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import re

ERFA_NUT80_SHA256 = "08c6fda7949eaa04c64c38e52e62183f32bbbe89c1ab2ece564c545c01532ae7"
IERS_KSV_SHA256 = "914597b5bf658667b02ba8de444a61504117f014186d2d1f8ea31efa59810e36"
A1_TAI_SECONDS = 0.0343817
TT_TAI_SECONDS = 32.184
GMAT_JD_OFFSET = 2430000.0
DAY_SECONDS = 86400.0


def verified_text(path: Path, expected: str) -> str:
    contents = path.read_bytes()
    if hashlib.sha256(contents).hexdigest() != expected:
        raise ValueError(f"Reference source hash does not match: {path}")
    return contents.decode("utf-8")


def coefficient_rows(erfa_source: Path, iers_source: Path) -> tuple[list, list]:
    erfa_text = verified_text(erfa_source, ERFA_NUT80_SHA256)
    array = erfa_text.split("} x[] = {", 1)[1].split("};", 1)[0]
    rows80 = [[float(value) for value in row.split(",")]
              for row in re.findall(r"\{([^{}]+)\}", array)]
    if len(rows80) != 106 or any(len(row) != 9 for row in rows80):
        raise ValueError("ERFA 1980 coefficient inventory is incomplete")

    iers_text = verified_text(iers_source, IERS_KSV_SHA256)
    rows96 = []
    # The first 27 IX blocks are the 263 luni-solar coefficients. Subsequent
    # subroutines use their own IX names and must not be included here.
    blocks = re.findall(r"data (IX\d+)/([^/]+)\s*/", iers_text, re.IGNORECASE)
    for name, block in blocks[:27]:
        values = [int(value) for value in re.findall(
            r"-?\d+", re.sub(r"^\s*\.", "", block, flags=re.MULTILINE))]
        if len(values) % 11:
            raise ValueError(f"Invalid IERS coefficient block: {name}")
        rows96.extend([values[index:index + 11]
                       for index in range(0, len(values), 11)])
    if len(rows96) != 263:
        raise ValueError("IERS 1996 coefficient inventory is incomplete")
    return rows80, rows96


def write_nutation(output: Path, rows80: list, rows96: list) -> None:
    lines = [
        "xx GMAT Py regenerated scientific nutation coefficient table, 2026-10-01.",
        "xx 1980 values: ERFA 2.0.1 nut80.c; Copyright 2013-2023 NumFOCUS Foundation; BSD-3-Clause.",
        "xx 1996 values: IERS Conventions (1996), KSV_1996_3 luni-solar coefficient data.",
        "xx Sources and notices: gmatpy/licenses/DATA_MANIFEST.json and licenses/ERFA.txt.",
    ]
    for model, rows in [(1980, rows80), (1996, rows96)]:
        # The summation order is deterministic. Argument/value identities are
        # retained; only presentation and summation ordering change.
        rows = sorted(rows, key=lambda row: (-abs(row[5]), tuple(row[:5])))
        lines.extend([
            f"xx {model} IAU Theory of Nutation ({len(rows)} term)",
            ("xx a2 a3 a4 a5 A B C D; units 0.0001 arcsecond" if model == 1980
             else "xx a2 a3 a4 a5 A B C D E F; units 0.000001 arcsecond"),
        ])
        lines.extend(" ".join(format(value, ".12g") for value in row)
                     for row in rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def multiply(left: list, right: list) -> list:
    return [[sum(left[i][k] * right[k][j] for k in range(3))
             for j in range(3)] for i in range(3)]


def transpose(matrix: list) -> list:
    return [[matrix[j][i] for j in range(3)] for i in range(3)]


def rotation_z(angle: float) -> list:
    cosine, sine = math.cos(angle), math.sin(angle)
    return [[cosine, sine, 0.0], [-sine, cosine, 0.0], [0.0, 0.0, 1.0]]


class ReferenceErfa:
    Matrix = (ctypes.c_double * 3) * 3
    Vector = ctypes.c_double * 3

    def __init__(self, library: Path):
        self.library = ctypes.CDLL(str(library.resolve()))
        for name in ["eraPnm80", "eraC2i06a"]:
            getattr(self.library, name).argtypes = [ctypes.c_double,
                                                   ctypes.c_double, self.Matrix]
        for name in ["eraGmst82", "eraEqeq94", "eraEra00", "eraObl80"]:
            function = getattr(self.library, name)
            function.argtypes = [ctypes.c_double, ctypes.c_double]
            function.restype = ctypes.c_double
        self.library.eraNut80.argtypes = [ctypes.c_double, ctypes.c_double,
                                          ctypes.POINTER(ctypes.c_double),
                                          ctypes.POINTER(ctypes.c_double)]
        self.library.eraRm2v.argtypes = [self.Matrix, self.Vector]

    def vector_at(self, a1_mjd: float) -> list[float]:
        # Use date-and-fraction splitting to avoid loss of precision from
        # forming a full Julian Date before subtracting the J2000 epoch.
        jd_day = GMAT_JD_OFFSET + math.floor(a1_mjd - 0.5) + 0.5
        a1_fraction = (a1_mjd - 0.5) % 1.0
        tai_fraction = a1_fraction - A1_TAI_SECONDS / DAY_SECONDS
        tt_fraction = tai_fraction + TT_TAI_SECONDS / DAY_SECONDS
        old_matrix, new_matrix = self.Matrix(), self.Matrix()
        self.library.eraPnm80(jd_day, tt_fraction, old_matrix)
        self.library.eraC2i06a(jd_day, tt_fraction, new_matrix)
        if jd_day + tt_fraction > 2450449.5:
            equation_of_equinoxes = self.library.eraEqeq94(jd_day, tt_fraction)
        else:
            longitude, obliquity = ctypes.c_double(), ctypes.c_double()
            self.library.eraNut80(jd_day, tt_fraction,
                                  ctypes.byref(longitude), ctypes.byref(obliquity))
            equation_of_equinoxes = longitude.value * math.cos(
                self.library.eraObl80(jd_day, tt_fraction))
        old_sidereal_angle = self.library.eraGmst82(jd_day, tai_fraction) + equation_of_equinoxes
        new_rotation_angle = self.library.eraEra00(jd_day, tai_fraction)
        old = multiply(rotation_z(old_sidereal_angle), old_matrix)
        new = multiply(rotation_z(new_rotation_angle), new_matrix)
        # A passive rotation FK5->ICRF, matching the sign convention in
        # CoordinateConverter::RotationMatrixFromICRFToFK5's rotM.
        matrix = multiply(transpose(new), old)
        c_matrix = self.Matrix(*(self.Vector(*row) for row in matrix))
        vector = self.Vector()
        self.library.eraRm2v(c_matrix, vector)
        return list(vector)


def write_icrf(output: Path, library: Path, first: int, last: int) -> None:
    erfa = ReferenceErfa(library)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Original coverage is retained; missing days in the legacy table are
    # filled by computation. Columns intentionally contain no comments:
    # GMAT's fscanf reader accepts numeric records only.
    with output.open("w", encoding="ascii") as stream:
        for day in range(first, last + 1):
            epoch = day + A1_TAI_SECONDS / DAY_SECONDS
            vector = erfa.vector_at(epoch)
            stream.write(f"{epoch:.12f}, " + ", ".join(f"{value:.15e}" for value in vector) + "\n")


def write_atmosphere(output: Path, source: Path) -> None:
    text = source.read_text(encoding="utf-8")
    values = {name: {int(index): float(value) for index, value in re.findall(
        name + r"\[(\d+)\]\s*=\s*([\d.eE+\-]+)\s*;", text)}
        for name in ["refHeight", "refDensity", "scaleHeight"]}
    if any(set(column) != set(range(28)) for column in values.values()):
        raise ValueError("Expected the 28 documented GMAT atmosphere constants")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(
        ", ".join(format(values[name][index], ".12g") for name in values) + "\n"
        for index in range(28)), encoding="ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--erfa-library", type=Path, required=True)
    parser.add_argument("--erfa-nut80", type=Path, required=True)
    parser.add_argument("--iers-ksv", type=Path, required=True)
    parser.add_argument("--gmat-exponential", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--first-mjd", type=int, default=6935)
    parser.add_argument("--last-mjd", type=int, default=58070)
    args = parser.parse_args()
    rows80, rows96 = coefficient_rows(args.erfa_nut80, args.iers_ksv)
    paths = [args.output_dir / "planetary_coeff/NUTATION.DAT",
             args.output_dir / "icrf/ICRF_ERFA_Table.txt",
             args.output_dir / "atmosphere/earth/EarthExponentialAtmosphereData.txt"]
    write_nutation(paths[0], rows80, rows96)
    write_icrf(paths[1], args.erfa_library, args.first_mjd, args.last_mjd)
    write_atmosphere(paths[2], args.gmat_exponential)
    print(json.dumps({str(path.relative_to(args.output_dir)): {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
    } for path in paths}, indent=2))


if __name__ == "__main__":
    main()
