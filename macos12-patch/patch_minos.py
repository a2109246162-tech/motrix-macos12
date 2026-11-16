#!/usr/bin/env python3
"""Patch LC_BUILD_VERSION minos 13.0 -> 12.0 in every Mach-O inside an .app bundle."""
import os
import struct
import sys

OLD = 0x000D0000  # 13.0
NEW = 0x000C0000  # 12.0
LC_BUILD_VERSION = 0x32
LC_REQ_DYLD = 0x80000000


def patch_thin(data, base):
    """Patch one thin Mach-O slice at absolute offset base. Return count patched."""
    if base + 4 > len(data):
        return 0
    magic_le = struct.unpack_from('<I', data, base)[0]
    if magic_le in (0xFEEDFACF, 0xFEEDFACE):  # little-endian 64 / 32
        endian = '<'
    elif magic_le in (0xCFFAEDFE, 0xCEFAEDFE):  # big-endian
        endian = '>'
    else:
        return 0
    magic = struct.unpack_from(endian + 'I', data, base)[0]
    is64 = magic == 0xFEEDFACF
    header_size = 32 if is64 else 28
    if base + header_size > len(data):
        return 0
    ncmds = struct.unpack_from(endian + 'I', data, base + 16)[0]
    cmd_off = base + header_size
    patched = 0
    for _ in range(ncmds):
        if cmd_off + 8 > len(data):
            break
        cmd, cmdsize = struct.unpack_from(endian + 'II', data, cmd_off)
        if cmdsize < 8:
            break
        if cmd in (LC_BUILD_VERSION, LC_BUILD_VERSION | LC_REQ_DYLD) and cmdsize >= 24:
            minos = struct.unpack_from(endian + 'I', data, cmd_off + 12)[0]
            if minos == OLD:
                struct.pack_into(endian + 'I', data, cmd_off + 12, NEW)
                patched += 1
        cmd_off += cmdsize
    return patched


def patch_file(path):
    with open(path, 'rb') as f:
        data = bytearray(f.read())
    if len(data) < 8:
        return 0
    be = struct.unpack_from('>I', data, 0)[0]
    le = struct.unpack_from('<I', data, 0)[0]
    patched = 0
    if be in (0xCAFEBABE, 0xCAFEBABF):  # fat, big-endian
        is64 = be == 0xCAFEBABF
        nfat = struct.unpack_from('>I', data, 4)[0]
        entry_size = 32 if is64 else 20
        for i in range(nfat):
            off_pos = 8 + i * entry_size + 8
            if off_pos + (8 if is64 else 4) > len(data):
                continue
            if is64:
                off = struct.unpack_from('>Q', data, off_pos)[0]
            else:
                off = struct.unpack_from('>I', data, off_pos)[0]
            patched += patch_thin(data, off)
    elif le in (0xCAFEBABE, 0xCAFEBABF):  # fat, little-endian (rare)
        is64 = le == 0xCAFEBABF
        nfat = struct.unpack_from('<I', data, 4)[0]
        entry_size = 32 if is64 else 20
        for i in range(nfat):
            off_pos = 8 + i * entry_size + 8
            if off_pos + (8 if is64 else 4) > len(data):
                continue
            if is64:
                off = struct.unpack_from('<Q', data, off_pos)[0]
            else:
                off = struct.unpack_from('<I', data, off_pos)[0]
            patched += patch_thin(data, off)
    else:
        patched = patch_thin(data, 0)
    if patched:
        with open(path, 'wb') as f:
            f.write(data)
    return patched


def main():
    root = sys.argv[1]
    total_files = 0
    total_patches = 0
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                n = patch_file(path)
            except Exception as exc:
                print(f'SKIP {path}: {exc}')
                continue
            if n:
                total_files += 1
                total_patches += n
                rel = os.path.relpath(path, root)
                print(f'PATCHED {n} slice(s): {rel}')
    print(f'DONE: {total_files} files, {total_patches} LC_BUILD_VERSION entries')


if __name__ == '__main__':
    main()
