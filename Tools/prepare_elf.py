"""Create a lossless analysis ELF from an explicitly decompressed ExeFS code file."""

import argparse
import hashlib
import json
from pathlib import Path
import struct


PAGE = 0x1000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sections_from_exheader(code, header):
    if len(header) < 0x400:
        raise ValueError("extended header must contain at least 0x400 bytes")
    sections = []
    offset = 0
    for name, field, flags in [(".text", 0x10, 5), (".rodata", 0x20, 4),
                               (".data", 0x30, 6)]:
        address, pages, size = struct.unpack_from("<III", header, field)
        if size > pages * PAGE or address % PAGE:
            raise ValueError(f"invalid {name} layout")
        if offset + pages * PAGE > len(code):
            raise ValueError("code is truncated or still compressed")
        if size:
            sections.append(dict(name=name, address=address, offset=offset,
                                 size=size, flags=flags, pages=pages))
        offset += pages * PAGE
    if offset != len(code):
        raise ValueError(f"expected {offset} decompressed bytes, got {len(code)}")
    bss_size = struct.unpack_from("<I", header, 0x3C)[0]
    data_address, _, data_size = struct.unpack_from("<III", header, 0x30)
    if bss_size:
        sections.append(dict(name=".bss", address=data_address + data_size,
                             offset=None, size=bss_size, flags=6, pages=0))
    for left, right in zip(sections, sections[1:]):
        if left["address"] + left["size"] > right["address"]:
            raise ValueError("overlapping sections")
    return sections


def make_elf(code, sections):
    # Keep the entire original code buffer, including alignment padding, in the ELF.
    image = bytearray(PAGE)
    image.extend(code)
    string_table = b"\0" + b"".join(s["name"].encode() + b"\0" for s in sections)
    string_table += b".shstrtab\0"
    string_offset = len(image)
    image.extend(string_table)
    image.extend(b"\0" * (-len(image) % 4))
    section_offset = len(image)
    image.extend(bytes(40))
    for index, section in enumerate(sections):
        nobits = section["offset"] is None
        file_offset = 0 if nobits else PAGE + section["offset"]
        size = section["size"]
        flags = section["flags"]
        ph = (1, file_offset, section["address"], section["address"],
              0 if nobits else size, size, flags, 1)
        struct.pack_into("<8I", image, 52 + 32 * index, *ph)
        sh_flags = 2 | (1 if flags & 2 else 0) | (4 if flags & 1 else 0)
        image.extend(struct.pack("<10I", string_table.index(section["name"].encode()),
                                 8 if nobits else 1, sh_flags, section["address"],
                                 file_offset, size, 0, 0, 4, 0))
    image.extend(struct.pack("<10I", string_table.index(b".shstrtab"), 3, 0, 0,
                             string_offset, len(string_table), 0, 0, 1, 0))
    ident = b"\x7fELF\x01\x01\x01" + bytes(9)
    struct.pack_into("<16sHHIIIIIHHHHHH", image, 0, ident, 2, 40, 1,
                     sections[0]["address"], 52, section_offset, 0x05000000,
                     52, 32, len(sections), 40, len(sections) + 2, len(sections) + 1)
    return bytes(image)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", type=Path, required=True)
    parser.add_argument("--exheader", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    code, header = args.code.read_bytes(), args.exheader.read_bytes()
    if digest(code) != args.sha256:
        raise ValueError("input code SHA-256 differs from the pinned target")
    sections = sections_from_exheader(code, header)
    elf = make_elf(code, sections)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "code.elf").write_bytes(elf)
    manifest = dict(code_path=str(args.code.resolve()), code_sha256=digest(code),
                    exheader_path=str(args.exheader.resolve()),
                    exheader_sha256=digest(header), elf_sha256=digest(elf),
                    title_id=f"{struct.unpack_from('<Q', header, 0x200)[0]:016X}",
                    status="analysis-import-only", sections=sections)
    (args.out / "input.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
