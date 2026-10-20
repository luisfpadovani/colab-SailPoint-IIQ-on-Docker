#!/bin/bash
set -euo pipefail
umask 077
mkdir -p /ca /out/server /out/trust
chmod 700 /ca
chmod 755 /out/server /out/trust
if [ ! -f /ca/ca.key ] && [ ! -f /ca/ca.crt ]; then
  openssl req -x509 -nodes -newkey rsa:3072 -sha256 -days 365 \
    -subj '/CN=IIQ Local Lab SQL CA' \
    -addext 'basicConstraints=critical,CA:TRUE' \
    -addext 'keyUsage=critical,keyCertSign,cRLSign' \
    -keyout /ca/ca.key -out /ca/ca.crt 2>/dev/null
fi
openssl x509 -in /ca/ca.crt -checkend 0 -noout >/dev/null || {
  echo 'SQL lab CA expired; renew the CA and server certificate before starting' >&2; exit 1;
}
if [ ! -f /out/server/server.key ] || \
   ! openssl x509 -in /out/server/server.crt -checkend 86400 -noout >/dev/null 2>&1 || \
   ! openssl verify -CAfile /ca/ca.crt /out/server/server.crt >/dev/null 2>&1; then
  openssl req -new -nodes -newkey rsa:3072 -sha256 -subj /CN=sqlserver \
    -keyout /out/server/server.key -out /tmp/server.csr 2>/dev/null
  cat >/tmp/server.ext <<'EXT'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:sqlserver,DNS:localhost,IP:127.0.0.1
EXT
  openssl x509 -req -in /tmp/server.csr -CA /ca/ca.crt -CAkey /ca/ca.key \
    -CAserial /ca/ca.srl -CAcreateserial -sha256 -days 7 \
    -extfile /tmp/server.ext -out /out/server/server.crt 2>/dev/null
fi
openssl verify -CAfile /ca/ca.crt -verify_hostname sqlserver /out/server/server.crt >/dev/null
chown 10001:10001 /out/server/server.key /out/server/server.crt
chmod 600 /out/server/server.key
chmod 644 /out/server/server.crt
cp /ca/ca.crt /out/trust/ca.crt
chmod 644 /out/trust/ca.crt
printf '%s\n' 'SQL TLS certificate and public client trust prepared'
