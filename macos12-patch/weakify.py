#!/usr/bin/env python3
"""Mark selected undefined Mach-O symbols as weak references (N_WEAK_REF)."""
import struct
import sys

N_WEAK_REF = 0x0040
LC_SYMTAB = 0x2


def weakify_slice(data, base, symbols):
    if base + 4 > len(data):
        return 0
    le = struct.unpack_from('<I', data, base)[0]
    if le in (0xFEEDFACF, 0xFEEDFACE):
        endian = '<'
    elif le in (0xCFFAEDFE, 0xCEFAEDFE):
        endian = '>'
    else:
        return 0
    magic = struct.unpack_from(endian + 'I', data, base)[0]
    is64 = magic == 0xFEEDFACF
    header_size = 32 if is64 else 28
    ncmds = struct.unpack_from(endian + 'I', data, base + 16)[0]
    cmd_off = base + header_size
    symoff = stroff = nsyms = strsize = None
    for _ in range(ncmds):
        if cmd_off + 8 > len(data):
            break
        cmd, cmdsize = struct.unpack_from(endian + 'II', data, cmd_off)
        if cmd == LC_SYMTAB and cmdsize >= 24:
            symoff, nsyms, stroff, strsize = struct.unpack_from(endian + 'IIII', data, cmd_off + 8)
        cmd_off += cmdsize
    if symoff is None or not nsyms:
        return 0
    entry = 16 if is64 else 12
    changed = 0
    strbase = base + stroff
    for i in range(nsyms):
        pos = base + symoff + i * entry
        if pos + entry > len(data):
            break
        strx = struct.unpack_from(endian + 'I', data, pos)[0]
        n_type = data[pos + 4]
        # N_UNDF = 0x00, N_EXT = 0x01; undefined externals have (n_type & 0x0e) == 0
        if (n_type & 0x0e) != 0:
            continue
        if strbase + strx >= len(data):
            continue
        end = data.find(b'\0', strbase + strx)
        if end < 0:
            continue
        name = data[strbase + strx:end].decode('utf-8', 'replace')
        if name not in symbols:
            continue
        desc_pos = pos + 6
        desc = struct.unpack_from(endian + 'H', data, desc_pos)[0]
        if not (desc & N_WEAK_REF):
            struct.pack_into(endian + 'H', data, desc_pos, desc | N_WEAK_REF)
            changed += 1
    return changed


def weakify_file(path, symbols):
    with open(path, 'rb') as f:
        data = bytearray(f.read())
    if len(data) < 8:
        return 0
    be = struct.unpack_from('>I', data, 0)[0]
    le = struct.unpack_from('<I', data, 0)[0]
    changed = 0
    if be in (0xCAFEBABE, 0xCAFEBABF):
        is64fat = be == 0xCAFEBABF
        nfat = struct.unpack_from('>I', data, 4)[0]
        esize = 32 if is64fat else 20
        for i in range(nfat):
            p = 8 + i * esize + 8
            if p + (8 if is64fat else 4) > len(data):
                continue
            off = struct.unpack_from('>Q' if is64fat else '>I', data, p)[0]
            changed += weakify_slice(data, off, symbols)
    elif le in (0xCAFEBABE, 0xCAFEBABF):
        is64fat = le == 0xCAFEBABF
        nfat = struct.unpack_from('<I', data, 4)[0]
        esize = 32 if is64fat else 20
        for i in range(nfat):
            p = 8 + i * esize + 8
            if p + (8 if is64fat else 4) > len(data):
                continue
            off = struct.unpack_from('<Q' if is64fat else '>I', data, p)[0]
            changed += weakify_slice(data, off, symbols)
    else:
        changed = weakify_slice(data, 0, symbols)
    if changed:
        with open(path, 'wb') as f:
            f.write(data)
    return changed


if __name__ == '__main__':
    path = sys.argv[1]
    syms = set(sys.argv[2:])
    n = weakify_file(path, syms)
    print(f'weakified {n} symbol(s) in {path}: {sorted(syms)}')
