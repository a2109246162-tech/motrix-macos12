#!/usr/bin/env python3
"""Iteratively patch missing macOS 13+ symbols in Motrix 2.4.2 for macOS 12."""
import os
import re
import subprocess
import time

WORK = '/Users/pcdata/WorkBuddy/2026-11-16-17-08-09/output/motrix-macos12'
BUNDLE = f'{WORK}/Motrix.app'
EXE = f'{BUNDLE}/Contents/MacOS/Motrix'
FWDIR = f'{BUNDLE}/Contents/Frameworks'
ELECTRON_FW = f'{FWDIR}/Electron Framework.framework/Versions/A/Electron Framework'
MAX_ITER = 45
RUN_SECONDS = 8

state = {}  # framework name -> {'path': real dylib path, 'objc': set(), 'c': set()}


def framework_name_from_path(path):
    m = re.search(r'/([^/]+)\.framework/', path)
    return m.group(1) if m else None


def stub_name(fw):
    return f'libmotrix_{fw}_stub.dylib'


def build_stub(fw):
    info = state[fw]
    src = f'{WORK}/stub_{fw}.m'
    lines = ['#import <Foundation/Foundation.h>', '']
    for cls in sorted(info['objc']):
        lines += [
            f'@interface {cls} : NSObject',
            '@end',
            f'@implementation {cls}',
            '@end',
            '',
        ]
    for sym in sorted(info['c']):
        lines.append(f'void *{sym} = 0;')
    with open(src, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    out = f'{WORK}/{stub_name(fw)}'
    cmd = [
        'xcrun', 'clang', '-shared', '-fobjc-arc', '-o', out, src,
        '-framework', 'Foundation', f'-Wl,-reexport_framework,{fw}',
    ]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        print('COMPILE FAILED:\n' + r.stdout[:3000])
        return False
    dest = f'{FWDIR}/{stub_name(fw)}'
    subprocess.run(['cp', out, dest])
    subprocess.run([
        'install_name_tool', '-id', f'@loader_path/../../../{stub_name(fw)}', dest
    ])
    subprocess.run([
        'install_name_tool', '-change', info['path'],
        f'@loader_path/../../../{stub_name(fw)}', ELECTRON_FW
    ])
    return True


def resign():
    subprocess.run(['xattr', '-cr', BUNDLE])
    subprocess.run([
        'codesign', '--force', '--deep', '--sign', '-', BUNDLE
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    for i in range(MAX_ITER):
        p = subprocess.Popen([EXE], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        time.sleep(RUN_SECONDS)
        rc = p.poll()
        if rc is None:
            p.terminate()
            time.sleep(1)
            if p.poll() is None:
                p.kill()
            print(f'ITER {i}: STABLE — process stayed alive {RUN_SECONDS}s')
            return True
        out = p.stdout.read().decode('utf-8', 'replace')
        m = re.search(r'Symbol not found: \(([^)]+)\)', out)
        e = re.search(r"Expected in: '([^']+)'", out)
        print(f'ITER {i}: exit={rc}')
        print(out[:400].strip())
        if not m or not e:
            print('No dyld symbol pattern; cannot auto-fix further.')
            return False
        sym = m.group(1)
        realpath = e.group(1)
        fw = framework_name_from_path(realpath)
        if not fw:
            print(f'Cannot derive framework from {realpath}')
            return False
        if fw not in state:
            state[fw] = {'path': realpath, 'objc': set(), 'c': set()}
        if sym.startswith('_OBJC_CLASS_$_'):
            state[fw]['objc'].add(sym[len('_OBJC_CLASS_$_'):])
        else:
            state[fw]['c'].add(sym.lstrip('_'))
        print(f'  -> adding {sym} to {fw} stub')
        if not build_stub(fw):
            return False
        resign()
    print('Reached iteration cap')
    return False


if __name__ == '__main__':
    raise SystemExit(0 if main() else 1)
