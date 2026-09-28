"""Download the public source files used in the network data feasibility study."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


BASE = "https://cms.eirgrid.ie/sites/default/files/publications/"
SOURCES = {
    "TYTFS2024_studyfiles.zip": "TYTFS2024_studyfiles.zip",
    "TYTFS2021_studyfiles.zip": "Study-files.zip",
    "TYTFS2024_report.pdf": "All-Island-Ten-Year-Transmission-Forecast-Statement-2024_1.pdf",
    "ECP-2-1-Line-Ratings-2022-02-09.xlsx": "ECP-2-1-Line-Ratings-2022-02-09.xlsx",
    "2026-Transmission-Outage-Programme-20260907.xlsx": "2026-Transmission-Outage-Programme-20260907.xlsx",
    "Transmission-Outage-Summary-2026-Week-40-41.xlsx": "Transmission-Outage-Summary-2026-Week-40-41.xlsx",
    "Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf": "Wind-Dispatch-Tool-Constraint-Group-Overview_1.pdf",
    "EirGrid-Transmission-System-Map-February-2025.pdf": "EirGrid-Transmission-System-Map-February-2025.pdf",
    "TSO-Contracted-Wind-Report-05-08-2026.pdf": "TSO-Contracted-Wind-Report-05-08-2026.pdf",
    "TSO-Contracted-Non-Wind-Report-05-08-2026.pdf": "TSO-Contracted-Non-Wind-Report-05-08-2026.pdf",
    "ECP-GSS-2-Constraint-Analysis-Excel-Report.xlsx": "ECP-GSS-2-Constraint-Analysis-Excel-Report.xlsx",
    "ECP-GSS-2-Assumptions-Document.pdf": "ECP-GSS-2-Assumptions-Document.pdf",
    "System-Margins-Outlook-IE-25092026.pdf": "System-Margins-Outlook-IE-25092026.pdf",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("data/raw/network_feasibility")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    failures = []
    for filename, remote_name in SOURCES.items():
        url = BASE + remote_name
        destination = args.output_dir / filename
        partial = args.output_dir / (filename + ".part")
        try:
            if not destination.exists():
                request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(request, timeout=45) as response, partial.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                partial.replace(destination)
            digest = hashlib.sha256()
            with destination.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
            manifest.append(
                {
                    "file": filename,
                    "url": url,
                    "size_bytes": destination.stat().st_size,
                    "sha256": digest.hexdigest(),
                    "checked_utc": datetime.now(timezone.utc).isoformat(),
                }
            )
            print(f"OK {filename}: {destination.stat().st_size:,} bytes", flush=True)
        except Exception as error:
            partial.unlink(missing_ok=True)
            failures.append(filename)
            print(f"FAILED {filename}: {error}", flush=True)
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if failures:
        raise SystemExit(f"Download incomplete: {', '.join(failures)}")


if __name__ == "__main__":
    main()
