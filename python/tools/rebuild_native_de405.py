"""Repackage the official JPL DE405 numeric records for GMAT Py.

Written for GMAT Py on 2026-10-01; Apache-2.0 applies to this utility.
No JPL reader/converter source code or authored explanatory prose is copied.
Scientific input: NASA/JPL Solar System Dynamics, DE405/LE405,
Standish (1998), JPL IOM 312.F-98-048.

Download the authoritative numeric input separately from:
https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de405/lnxp1600p2200.405

The redistribution assessment for the numerical data is described in the
package data manifest; this utility does not create a provider license.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

INPUT_SHA256 = "7ec77287b6fddd3d7adabb87709ee5e926e3d1123fbae5d1485a42913cf175e7"
INPUT_URL = "https://ssd.jpl.nasa.gov/ftp/eph/planets/Linux/de405/lnxp1600p2200.405"
RECORD_SIZE = 1018 * 8
BEGIN_JD = 2430000.5  # 1941-01-06 TDB: original GMAT supported start
END_JD = 2525008.5  # 2201-02-20 TDB: original GMAT supported end


def rebuild(source_path: Path, destination: Path) -> dict:
    data = source_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != INPUT_SHA256:
        raise ValueError("Input is not the verified official JPL DE405 numeric file")
    begin, end, step = struct.unpack_from("<3d", data, 2652)
    n_constants = struct.unpack_from("<i", data, 2676)[0]
    if (begin, end, step, n_constants) != (2305424.5, END_JD, 32.0, 156):
        raise ValueError("Unexpected DE405 numerical layout")
    first_record = int((BEGIN_JD - begin) / step)
    payload = data[(first_record + 2) * RECORD_SIZE:]
    if len(payload) % RECORD_SIZE:
        raise ValueError("Truncated coefficient record")
    if struct.unpack_from("<2d", payload) != (BEGIN_JD, BEGIN_JD + step):
        raise ValueError("Incorrect first record epoch")
    if struct.unpack_from("<2d", payload, len(payload) - RECORD_SIZE) != (END_JD - step, END_JD):
        raise ValueError("Incorrect final record epoch")

    # Create independent factual labels, without copying the provider's labels
    # or the uninitialized padding in the historical GMAT-format header.
    header = bytearray(RECORD_SIZE)
    labels = (
        "GMAT Py numeric DE405 ephemeris; source: NASA/JPL SSD",
        "Begin JD 2430000.5; 1941-01-06 TDB",
        "End JD 2525008.5; 2201-02-20 TDB",
    )
    for i, label in enumerate(labels):
        field = label.encode("ascii")
        if len(field) > 84:
            raise ValueError("Header label exceeds fixed-width field")
        header[i * 84:(i + 1) * 84] = field.ljust(84, b" ")
    # Names are identifiers of the scientific constants. The following fields
    # hold epochs, constant count, AU/EMRAT and coefficient-layout integers.
    header[252:2652] = data[252:2652]
    header[2652:2860] = data[2652:2860]
    struct.pack_into("<d", header, 2652, BEGIN_JD)
    # GMAT's auxiliary RSize field stores the number of doubles per record.
    struct.pack_into("<i", header, 2856, RECORD_SIZE // 8)
    constants = bytearray(RECORD_SIZE)
    constants[:n_constants * 8] = data[RECORD_SIZE:RECORD_SIZE + n_constants * 8]
    output = bytes(header) + bytes(constants) + payload
    destination.write_bytes(output)
    return {
        "source_url": INPUT_URL,
        "source_sha256": INPUT_SHA256,
        "output_filename": destination.name,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "size_bytes": len(output),
        "record_size_bytes": RECORD_SIZE,
        "official_subset_record_offset": first_record,
        "range_jd_tdb": [BEGIN_JD, END_JD],
        "number_of_constants": n_constants,
        "coefficient_bytes": len(payload),
        "method": "Retain every numeric constant, pointer and selected coefficient bit; independently format header labels and zero padding.",
        "last_modifier": "GMAT Py maintainers, independent GMAT Py project; 2026-10-01",
        "scientific_origin": "NASA/JPL Solar System Dynamics DE405/LE405; Standish (1998), JPL IOM 312.F-98-048",
        "copyright_assessment": "Mechanical scientific numeric data; no claim of provider public-domain designation or provider license.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = rebuild(args.source, args.output)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.write_text(serialized)
    print(serialized, end="")


if __name__ == "__main__":
    main()
