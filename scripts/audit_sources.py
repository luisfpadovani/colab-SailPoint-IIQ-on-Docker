#!/usr/bin/env python3
"""Reject non-source artifacts in the Git index and optionally new commit history.

Run before publication: python3 scripts/audit_sources.py --base origin/main
Reads staged Git blobs, never local ignored artifacts or credential contents.
This is an artifact guard; Gitleaks handles secret detection separately.
"""
import argparse
from pathlib import PurePosixPath
import re
import subprocess

MAX_SIZE = 1024 * 1024
BLOCKED = ('.zip', '.jar', '.war', '.ear', '.class', '.tar', '.gz', '.tgz', '.7z',
           '.exe', '.dll', '.so', '.key', '.pem', '.crt', '.jks', '.p12', '.keystore', '.pyc')


def path_problem(path):
    name = PurePosixPath(path).name.lower()
    if name.endswith(BLOCKED):
        return 'binary, archive, compiled code or local certificate/key'
    if (name.startswith('.env') and path != '.env.example') or any(
            part in {'.secrets', '.venv', 'venv', '__pycache__'} for part in PurePosixPath(path).parts):
        return 'local secret or generated environment'
    product_name = re.sub(r'^\d+[-_]', '', name)
    if product_name.startswith(('create_identityiq', 'upgrade_identityiq')) or name == 'uiconfig-uiconfig.xml':
        return 'licensed product script or full UI export'
    if path.startswith('tomcat/file_install/ssb/web/'):
        return 'extracted product/build payload'
    return None


def content_problem(data):
    if data.startswith((b'PK\x03\x04', b'PK\x05\x06', b'\x7fELF', b'\xca\xfe\xba\xbe', b'\x1f\x8b')):
        return 'binary payload, regardless of filename'
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return 'non-UTF-8 payload; only text source is allowed'
    if any(ord(char) < 32 and char not in '\n\r\t' for char in text):
        return 'binary control characters'
    if re.search(r'^-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----$', text, re.M):
        return 'private key material'
    return None


def git(*args):
    return subprocess.check_output(['git', *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='Also inspect every new blob in BASE..HEAD')
    args = parser.parse_args()
    candidates = []
    problems = []
    for entry in git('ls-files', '--stage', '-z').decode().split('\0'):
        if not entry:
            continue
        metadata, path = entry.split('\t', 1)
        mode, oid, stage = metadata.split()
        if mode not in {'100644', '100755'} or stage != '0':
            problems.append((path, 'not a regular staged source file'))
        candidates.append((oid, path))
    if args.base:
        base = git('rev-parse', '--verify', args.base + '^{commit}').decode().strip()
        for entry in git('rev-list', '--objects', 'HEAD', '^' + base).decode().splitlines():
            oid, _, path = entry.partition(' ')
            if git('cat-file', '-t', oid).strip() == b'blob':
                candidates.append((oid, path))
    checked = set()
    for oid, path in candidates:
        if (oid, path) in checked:
            continue
        checked.add((oid, path))
        reason = path_problem(path)
        if not reason:
            if int(git('cat-file', '-s', oid)) > MAX_SIZE:
                reason = 'larger than the source artifact limit (1 MiB)'
            else:
                reason = content_problem(git('cat-file', 'blob', oid))
        if reason:
            problems.append((path, reason))
    for path, reason in sorted(set(problems)):
        print('FAIL:', path, '-', reason)
    if problems:
        raise SystemExit(1)
    print(f'PASS: {len(checked)} staged/history source blobs; no forbidden product/local artifacts')


if __name__ == '__main__':
    main()
