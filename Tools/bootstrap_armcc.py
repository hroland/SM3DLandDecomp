"""Install the pinned, publicly distributed headless ARMCC compiler package locally."""

import hashlib
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / ".local/downloads"
BIN = ROOT / ".local/bin"
TOOLCHAINS = ROOT / ".local/toolchains"
ASSETS = (
    ("https://github.com/decompme/compilers/releases/download/compilers/armcc.zip",
     DOWNLOADS / "armcc.zip", "bda0cea5b13a9c3f08322fa76f9f9dcda59bda290f57f1a06e05cd80044fafdb"),
    ("https://github.com/decompals/wibo/releases/download/1.2.0/wibo-macos",
     BIN / "wibo", "2b3000ef6a7a490c24ccd71967735ae0005e218922e51806cca1b8d77fd3cf7c"),
)


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    for url, destination, expected in ASSETS:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_suffix(destination.suffix + ".download")
            urllib.request.urlretrieve(url, temporary)
            if digest(temporary) != expected:
                raise ValueError(f"Downloaded asset hash differs: {url}")
            temporary.rename(destination)
        if digest(destination) != expected:
            raise ValueError(f"Local asset hash differs: {destination}")
    TOOLCHAINS.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DOWNLOADS / "armcc.zip") as archive:
        for entry in archive.infolist():
            target = (TOOLCHAINS / entry.filename).resolve()
            if not target.is_relative_to(TOOLCHAINS.resolve()):
                raise ValueError("Unsafe compiler archive path")
            if not entry.is_dir():
                data = archive.read(entry)
                if target.exists():
                    if target.read_bytes() != data:
                        raise ValueError(f"Installed toolchain differs from pinned package: {target}")
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
    (BIN / "wibo").chmod(0o755)
    print("Pinned ARMCC compilers and wibo are available under .local/.")


if __name__ == "__main__":
    main()
