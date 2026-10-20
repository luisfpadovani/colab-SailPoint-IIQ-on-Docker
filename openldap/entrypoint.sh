#!/bin/bash
set -euo pipefail

LDAP_SCHEMA_FILE="${LDAP_SCHEMA_FILE:-/bootstrap/schema/attributes.schema}"
LDAP_LDIF_FILE="${LDAP_LDIF_FILE:-/bootstrap/ldif/adata.ldif}"
LDAP_CONFIG_DIR="${LDAP_CONFIG_DIR:-/etc/ldap/slapd.d}"
LDAP_DATA_DIR="${LDAP_DATA_DIR:-/var/lib/ldap}"
: "${LDAP_ADMIN_PASSWORD:?Set LDAP_ADMIN_PASSWORD}"
umask 077
mkdir -p /var/run/slapd
chown openldap:openldap /var/run/slapd
printf '%s' "$LDAP_ADMIN_PASSWORD" >/run/ldap-admin-password
chmod 600 /run/ldap-admin-password
LDAP_BASE_DN="${LDAP_BASE_DN:-dc=corp1}"
LDAP_ORGANISATION="${LDAP_ORGANISATION:-Org Corp1}"
LDAP_ADMIN_DN="cn=admin,${LDAP_BASE_DN}"

first_dc="$(printf '%s\n' "$LDAP_BASE_DN" | sed -n 's/^dc=\([^,]*\).*/\1/p')"
if [ -z "$first_dc" ]; then
  echo "LDAP_BASE_DN must start with dc=, got: ${LDAP_BASE_DN}" >&2
  exit 1
fi

initialize_ldap() {
  local root_password_hash
  root_password_hash="$(slappasswd -T /run/ldap-admin-password)"

  rm -rf "${LDAP_CONFIG_DIR:?}"/* "${LDAP_DATA_DIR:?}"/*
  mkdir -p "$LDAP_CONFIG_DIR" "$LDAP_DATA_DIR" /var/run/slapd
  chown openldap:openldap /var/run/slapd

  cat >/tmp/slapd.conf <<EOF
include /etc/ldap/schema/core.schema
include /etc/ldap/schema/cosine.schema
include /etc/ldap/schema/nis.schema
include /etc/ldap/schema/inetorgperson.schema
EOF

  if [ -f "$LDAP_SCHEMA_FILE" ]; then
    printf 'include %s\n' "$LDAP_SCHEMA_FILE" >>/tmp/slapd.conf
  fi

  cat >>/tmp/slapd.conf <<EOF
pidfile /var/run/slapd/slapd.pid
argsfile /var/run/slapd/slapd.args
modulepath /usr/lib/ldap
moduleload back_mdb
TLSCertificateFile /etc/ldap/tls/ldap.crt
TLSCertificateKeyFile /etc/ldap/tls/ldap.key
TLSCACertificateFile /etc/ldap/tls/ldap.crt
TLSProtocolMin 3.3
# Require TLS for simple binds (bootstrap uses LDAPI).
localSSF 256
security simple_bind=128

database mdb
maxsize 1073741824
suffix "${LDAP_BASE_DN}"
rootdn "${LDAP_ADMIN_DN}"
rootpw ${root_password_hash}
directory ${LDAP_DATA_DIR}
index objectClass eq
access to attrs=userPassword
  by self write
  by anonymous auth
  by * none
access to *
  by users read
  by * none
EOF

  slaptest -u -f /tmp/slapd.conf
  if ! slaptest -f /tmp/slapd.conf -F "$LDAP_CONFIG_DIR" >/tmp/slaptest-generate.log 2>&1; then
    if ! grep -q "bi_db_open failed" /tmp/slaptest-generate.log; then
      cat /tmp/slaptest-generate.log >&2
      exit 1
    fi
  fi
  if [ ! -f "$LDAP_CONFIG_DIR/cn=config.ldif" ]; then
    echo "Failed to generate OpenLDAP cn=config files" >&2
    exit 1
  fi
  chown -R openldap:openldap "$LDAP_CONFIG_DIR" "$LDAP_DATA_DIR"

  cat >/tmp/base.ldif <<EOF
dn: ${LDAP_BASE_DN}
objectClass: top
objectClass: dcObject
objectClass: organization
o: ${LDAP_ORGANISATION}
dc: ${first_dc}
EOF

  slapadd -F "$LDAP_CONFIG_DIR" -b "$LDAP_BASE_DN" -l /tmp/base.ldif
  chown -R openldap:openldap "$LDAP_DATA_DIR"

  slapd -h "ldapi:///" -F "$LDAP_CONFIG_DIR" -u openldap -g openldap -d 0 &
  local bootstrap_pid=$!
  for _ in $(seq 1 30); do
    if ldapsearch -x -H ldapi:/// -D "$LDAP_ADMIN_DN" -y /run/ldap-admin-password -b "$LDAP_BASE_DN" -s base >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  if [ -f "$LDAP_LDIF_FILE" ]; then
    ldapadd -x -H ldapi:/// -D "$LDAP_ADMIN_DN" -y /run/ldap-admin-password -f "$LDAP_LDIF_FILE"
  fi

  kill "$bootstrap_pid"
  wait "$bootstrap_pid" || true
  touch "$LDAP_DATA_DIR/.initialized"
  chown openldap:openldap "$LDAP_DATA_DIR/.initialized"
}

mkdir -p /etc/ldap/tls
chmod 755 /etc/ldap/tls
if [ ! -f /etc/ldap/tls/ldap.crt ] || [ ! -f /etc/ldap/tls/ldap.key ]; then
  openssl req -x509 -nodes -newkey rsa:3072 -sha256 -days 7 \
    -subj /CN=ldap -addext 'subjectAltName=DNS:ldap,DNS:localhost,IP:127.0.0.1' \
    -keyout /etc/ldap/tls/ldap.key -out /etc/ldap/tls/ldap.crt
fi
openssl x509 -checkend 0 -noout -in /etc/ldap/tls/ldap.crt || {
  echo "LDAP certificate expired; replace or renew it before starting" >&2; exit 1;
}
chown openldap:openldap /etc/ldap/tls/ldap.key
chmod 600 /etc/ldap/tls/ldap.key
chmod 644 /etc/ldap/tls/ldap.crt
if [ ! -f "$LDAP_DATA_DIR/.initialized" ]; then
  initialize_ldap
fi

exec slapd -h "ldapi:/// ldaps://0.0.0.0:636/" -F "$LDAP_CONFIG_DIR" -u openldap -g openldap -d 0
