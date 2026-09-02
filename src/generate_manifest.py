#!/usr/bin/env python3
"""Generate deterministic hashes for the public verification package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_NAMES = {"SHA256SUMS.txt", "release_manifest.json"}
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", "generated"}


def files() -> list[Path]:
    return sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and path.name not in EXCLUDED_NAMES
            and not any(part in EXCLUDED_PARTS for part in path.relative_to(ROOT).parts)
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def main() -> int:
    records = []
    lines = []
    for path in files():
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        relative = path.relative_to(ROOT).as_posix()
        records.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest})
        lines.append(f"{digest}  {relative}")
    (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {
        "schema": 1,
        "artifact": "anonymous-spn-quantum-resource-verification",
        "release_type": "verification-package",
        "file_count": len(records),
        "files": records,
    }
    (ROOT / "release_manifest.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    print(f"manifested {len(records)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
