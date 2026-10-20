#!/usr/bin/env python3
"""Update the Microsoft JDBC version and checksum together from Maven Central."""
import argparse
import hashlib
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://repo.maven.apache.org/maven2/com/microsoft/sqlserver/mssql-jdbc/'
VERSION = re.compile(r'\d+\.\d+\.\d+\.jre11')


def download(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise ValueError('Unexpected Maven artifact size')
    return data


def latest_version(metadata):
    versions = [e.text for e in ET.fromstring(metadata).findall('./versioning/versions/version') if e.text and VERSION.fullmatch(e.text)]
    return max(versions, key=lambda v: tuple(map(int, v.split('.')[:3])))


def verified_checksum(version):
    if not VERSION.fullmatch(version):
        raise ValueError('Only stable JRE 11 artifacts are supported')
    artifact = f'{BASE}{version}/mssql-jdbc-{version}.jar'
    expected = download(artifact + '.sha256').decode().strip().lower()
    actual = hashlib.sha256(download(artifact)).hexdigest()
    if not re.fullmatch(r'[a-f0-9]{64}', expected) or actual != expected:
        raise ValueError('Maven artifact checksum mismatch; no files changed')
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', action='store_true', help='Write version/hash changes; otherwise verify the current pin')
    args = parser.parse_args()
    dockerfile = ROOT / 'tomcat/Dockerfile'
    text = dockerfile.read_text()
    current = re.search(r'^ARG MSSQL_JDBC_VERSION=(.+)$', text, re.M).group(1)
    old_hash = re.search(r'^ARG MSSQL_JDBC_SHA256=([a-f0-9]{64})$', text, re.M).group(1)
    version = latest_version(download(BASE + 'maven-metadata.xml')) if args.update else current
    checksum = verified_checksum(version)
    if not args.update:
        if checksum != old_hash:
            raise ValueError('Pinned checksum does not match Maven Central')
        print(f'PASS: pinned JDBC {current} checksum verified against Maven Central')
        return
    if tuple(map(int, version.split('.')[:3])) < tuple(map(int, current.split('.')[:3])):
        raise ValueError('Refusing to downgrade the JDBC driver')
    text = text.replace(f'ARG MSSQL_JDBC_VERSION={current}', f'ARG MSSQL_JDBC_VERSION={version}')
    text = text.replace(f'ARG MSSQL_JDBC_SHA256={old_hash}', f'ARG MSSQL_JDBC_SHA256={checksum}')
    dockerfile.write_text(text)
    readme = ROOT / 'README.md'
    doc = readme.read_text().replace(current, version).replace(old_hash, checksum)
    doc = doc.replace('/tag/v' + current.removesuffix('.jre11'), '/tag/v' + version.removesuffix('.jre11'))
    readme.write_text(doc)
    print(f'JDBC dependency checked: {current} -> {version}; upstream checksum verified')


if __name__ == '__main__':
    main()
