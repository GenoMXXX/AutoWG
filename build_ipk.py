#!/usr/bin/env python3
from __future__ import annotations

import io
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PKG_NAME = "wg-watchdog"
VERSION = "1.0.0"
ARCH = "all"
OUT = ROOT / f"{PKG_NAME}_{VERSION}_{ARCH}.ipk"


def add_tree(tar: tarfile.TarFile, path: Path, arcname: str) -> None:
    info = tarfile.TarInfo(arcname)
    st = path.stat()
    info.mtime = int(st.st_mtime)
    if path.is_dir():
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        info.size = 0
        tar.addfile(info)
        for child in sorted(path.iterdir(), key=lambda p: p.name):
            child_arc = child.name if arcname in (".", "") else f"{arcname}/{child.name}"
            add_tree(tar, child, child_arc)
        return

    info.size = st.st_size
    if arcname.endswith((".sh", ".cgi", "wg-watchdogd", "postinst", "prerm", "S99wg-watchdog")):
        info.mode = 0o755
    else:
        info.mode = 0o644
    with path.open("rb") as fh:
        tar.addfile(info, fh)


def make_tarball(subdir: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        add_tree(tar, ROOT / subdir, ".")
    return buf.getvalue()


def make_control() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for child in sorted((ROOT / "CONTROL").iterdir(), key=lambda p: p.name):
            add_tree(tar, child, child.name)
    return buf.getvalue()


def make_data() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for child in sorted((ROOT / "opt").rglob("*")):
            rel = child.relative_to(ROOT / "opt")
            arc = "opt/" + str(rel).replace("\\", "/")
            info = tarfile.TarInfo(arc)
            st = child.stat()
            info.mtime = int(st.st_mtime)
            if child.is_dir():
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                info.size = 0
                tar.addfile(info)
            else:
                info.size = st.st_size
                info.mode = 0o755 if arc.endswith((".sh", ".cgi", "wg-watchdogd", "S99wg-watchdog")) else 0o644
                with child.open("rb") as fh:
                    tar.addfile(info, fh)
    return buf.getvalue()


def write_ar(path: Path, members: list[tuple[str, bytes]]) -> None:
    with path.open("wb") as fh:
        fh.write(b"!<arch>\n")
        for name, data in members:
            if len(name) > 15:
                raise ValueError(f"ar member name too long: {name}")
            header = f"{name}/".ljust(16)
            header += f"{0:>12}{0:>6}{0:>6}{0:>8}{len(data):>10}`\n"
            fh.write(header.encode("ascii"))
            fh.write(data)
            if len(data) % 2 == 1:
                fh.write(b"\n")


def main() -> None:
    debian_binary = b"2.0\n"
    control = make_control()
    data = make_data()
    write_ar(
        OUT,
        [
            ("debian-binary", debian_binary),
            ("control.tar.gz", control),
            ("data.tar.gz", data),
        ],
    )
    print(OUT)


if __name__ == "__main__":
    main()
