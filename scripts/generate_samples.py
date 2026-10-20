#!/usr/bin/env python3
"""Generate consistent fictional HR/LDAP/SQL fixtures with pinned Faker and a seed.

Names and relationships are reproducible; LDAP passwords/salts are independently
random and discarded. Running this generator never updates a running database.
"""
import argparse
import base64
import csv
import hashlib
import io
from pathlib import Path
import random
import re
import secrets

from faker import Faker

ROOT = Path(__file__).resolve().parents[1]
DEPARTMENTS = [('Production', '00001'), ('IT Management', '00002'), ('Quality Management', '00003'), ('Marketing', '00004'), ('Selling', '00005'), ('Human Resource Management', '00006')]
FIELDS = ['employeeID', 'name', 'firstname', 'lastname', 'email', 'departmentName', 'departmentCode', 'manager', 'employeeStatus']


def identities(seed=20261020, count=101):
    if count < 67:
        raise ValueError('At least 67 identities are required by the mock fixtures')
    fake = Faker('en_US')
    fake.seed_instance(seed)
    rng = random.Random(seed)
    result = []
    for number in range(count):
        first, last = fake.first_name(), fake.last_name()
        department, code = ('CEO', '00000') if number == 0 else DEPARTMENTS[(number - 1) % len(DEPARTMENTS)]
        manager = '' if number == 0 else f'{0 if number <= 6 else rng.randint(1, 6):08d}'
        result.append(dict(zip(FIELDS, [f'{number:08d}', f'{first} {last}', first, last,
            f'employee{number:08d}@example.com', department, code, manager,
            'true' if number <= 6 or number % 5 else 'false'])))
    return result


def password_hash():
    salt = secrets.token_bytes(16)
    digest = hashlib.sha1(secrets.token_bytes(32) + salt).digest()
    return '{SSHA}' + base64.b64encode(digest + salt).decode()


def ldif_value(key, value):
    if not value.isascii() or value.startswith((' ', ':', '<')) or value.endswith(' '):
        return f'{key}:: {base64.b64encode(value.encode()).decode()}'
    return f'{key}: {value}'


def generate(seed=20261020, count=101, output_root=ROOT):
    rows = identities(seed, count)
    csv_text = io.StringIO(newline='')
    writer = csv.DictWriter(csv_text, fieldnames=FIELDS, delimiter=';', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    ldif = ['dn: ou=Groups,dc=corp1\nchangetype: add\nobjectclass: organizationalUnit\nou: Groups',
            'dn: ou=Users,dc=corp1\nchangetype: add\nobjectclass: organizationalUnit\nou: Users']
    for number in [0, 1, 3, 4]:
        row = rows[number]
        fields = [('dn', f'cn={row["employeeID"]},ou=Users,dc=corp1'), ('changetype', 'add'),
            ('objectclass', 'inetOrgPerson'), ('cn', row['employeeID']), ('givenname', row['firstname']),
            ('sn', row['lastname']), ('displayname', row['name']), ('mail', row['email']),
            ('userpassword', password_hash()), ('objectclass', 'personnel'), ('employeeID', row['employeeID'])]
        ldif.append('\n'.join(ldif_value(k, v) for k, v in fields))
    for group, members in [('Admins', [1, 0]), ('Maintaners', [3, 0])]:
        ldif.append(f'dn: cn={group},ou=Groups,dc=corp1\nchangetype: add\ncn: {group}\nobjectclass: groupOfUniqueNames\n' +
            '\n'.join(f'uniqueMember: cn={rows[i]["employeeID"]},ou=Users,dc=corp1' for i in members))
    statements = []
    for number in [1, 2, 48, 66, 51]:
        row = rows[number]
        name = row['name'].replace("'", "''")
        status = '1' if row['employeeStatus'] == 'true' else '0'
        statements.append("INSERT INTO tbl_user([name],[login],[password_salt],[password_hash],[status]) " +
            f"SELECT N'{name}','{row['employeeID']}',s.salt,HASHBYTES('SHA2_512',s.salt + CRYPT_GEN_RANDOM(32)),'{status}' " +
            'FROM (SELECT CRYPT_GEN_RANDOM(32) AS salt) s;')
    template = (ROOT / 'sqlserver_iiq/scripts/98-create_table_app_mock.sql').read_text()
    block = '-- BEGIN GENERATED SAMPLE USERS\n' + '\n'.join(statements) + '\n-- END GENERATED SAMPLE USERS'
    template, count_replaced = re.subn(r'-- BEGIN GENERATED SAMPLE USERS\n.*?-- END GENERATED SAMPLE USERS', lambda _: block, template, flags=re.S)
    if count_replaced != 1:
        raise ValueError('SQL sample marker block not found exactly once')
    outputs = {
        'data/Application/file/BaseHumanResource.csv': csv_text.getvalue(),
        'data/Application/ldap/bootstrap/ldif/adata.ldif': '\n\n'.join(ldif) + '\n',
        'sqlserver_iiq/scripts/98-create_table_app_mock.sql': template,
    }
    for name, content in outputs.items():
        destination = Path(output_root) / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content)
    print(f'Generated {len(rows)} fictional identities with Faker, seed={seed}; no running data changed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=20261020)
    parser.add_argument('--count', type=int, default=101)
    parser.add_argument('--output-root', type=Path, default=ROOT)
    options = parser.parse_args()
    generate(options.seed, options.count, options.output_root)
