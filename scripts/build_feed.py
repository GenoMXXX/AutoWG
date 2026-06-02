#!/usr/bin/env python3
from __future__ import annotations

import gzip
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "wg-watchdog_1.0.0_all.ipk"
DOCS = ROOT / "docs"
FEED = DOCS / "opkg"


def parse_control(data: bytes) -> dict[str, str]:
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_value: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_value
        if current_key is not None:
            fields[current_key] = "\n".join(current_value).rstrip("\n")
        current_key = None
        current_value = []

    for raw_line in data.decode("utf-8", errors="replace").splitlines():
        if not raw_line.strip():
            flush()
            continue
        if raw_line.startswith(" ") and current_key is not None:
            current_value.append(raw_line[1:])
            continue
        if ":" not in raw_line:
            continue
        flush()
        key, value = raw_line.split(":", 1)
        current_key = key.strip()
        current_value = [value.lstrip()]

    flush()
    return fields


def extract_control() -> bytes:
    with PKG.open("rb") as fh:
        if fh.read(8) != b"!<arch>\n":
            raise RuntimeError("not an ar archive")
        while True:
            hdr = fh.read(60)
            if not hdr:
                break
            name = hdr[:16].decode("ascii").strip().rstrip("/")
            size = int(hdr[48:58].decode("ascii").strip())
            data = fh.read(size)
            if size % 2 == 1:
                fh.read(1)
            if name == "control.tar.gz":
                import tarfile
                import io

                with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                    member = tar.extractfile("control")
                    if member is None:
                        raise RuntimeError("control file not found")
                    return member.read()
    raise RuntimeError("control.tar.gz not found")


def main() -> None:
    if not PKG.exists():
        raise SystemExit(f"missing package: {PKG}")

    FEED.mkdir(parents=True, exist_ok=True)
    out_pkg = FEED / PKG.name
    out_pkg.write_bytes(PKG.read_bytes())

    control = parse_control(extract_control())
    size = out_pkg.stat().st_size
    sha256 = hashlib.sha256(out_pkg.read_bytes()).hexdigest()

    packages = "\n".join(
        [
            f"Package: {control.get('Package', 'wg-watchdog')}",
            f"Version: {control.get('Version', '1.0.0')}",
            f"Architecture: {control.get('Architecture', 'all')}",
            f"Maintainer: {control.get('Maintainer', 'Codex')}",
            f"License: {control.get('License', 'MIT')}",
            f"Section: {control.get('Section', 'net')}",
            f"Priority: {control.get('Priority', 'optional')}",
            f"Depends: {control.get('Depends', 'busybox, ip-full')}",
            f"Source: {control.get('Source', 'local')}",
            f"Filename: {out_pkg.name}",
            f"Size: {size}",
            f"SHA256sum: {sha256}",
            "Description: Keenetic WireGuard watchdog with local web UI",
            " Monitors a selected Linux WireGuard interface from sysfs and bounces it when",
            " rxbytes stays at zero while txbytes exceeds the configured threshold. Includes",
            " a local web UI served from Entware, automatic service supervision, and a CGI",
            " API for status and configuration.",
            "",
        ]
    )

    (FEED / "Packages").write_text(packages, encoding="utf-8", newline="\n")
    with gzip.open(FEED / "Packages.gz", "wb", compresslevel=9) as fh:
        fh.write(packages.encode("utf-8"))

    (DOCS / "index.html").write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AutoWG feed</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 40px; max-width: 900px; line-height: 1.5; }
    code, pre { background: #f3f4f6; padding: 0.2rem 0.4rem; border-radius: 6px; }
    a { color: #0366d6; }
  </style>
</head>
<body>
  <h1>AutoWG opkg feed</h1>
  <p>Use this feed on Keenetic with Entware:</p>
  <pre>src/gz AutoWG https://GENOMXXX.github.io/AutoWG/opkg
opkg update
opkg install wg-watchdog</pre>
  <p>The package is local-only and runs its own web UI on the router.</p>
</body>
</html>
""",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    main()
