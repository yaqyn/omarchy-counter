#!/usr/bin/env python3
"""Build a deterministic release archive from a clean, committed checkout."""

import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(["git", "-C", str(root), *args])


if git("status", "--porcelain").strip():
    raise SystemExit("Commit the intended changes before packaging.")
version = json.loads((root / "manifest.json").read_text())["version"]
if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
    raise SystemExit("Use a numeric release version.")
files = sorted(name for name in git("ls-files", "-z").decode().split("\0") if name)
epoch = int(git("show", "-s", "--format=%ct", "HEAD"))
output = root / "dist"
output.mkdir(exist_ok=True)
name = f"omarchy-counter-{version}"
archive = output / f"{name}.tar.gz"
with archive.open("wb") as raw:
    with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=epoch) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as tar:
            for filename in files:
                path = root / filename
                if path.is_symlink() or not path.is_file():
                    raise SystemExit(f"Release files must be regular files: {filename}")
                data = path.read_bytes()
                info = tarfile.TarInfo(f"{name}/{filename}")
                info.size = len(data)
                info.mtime = epoch
                info.mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
                tar.addfile(info, io.BytesIO(data))
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(archive.with_suffix(archive.suffix + ".sha256")).write_text(f"{checksum}  {archive.name}\n")
print(archive)
print(checksum)
