#!/bin/bash
set -euo pipefail
cd /usr/local/tomcat
mkdir -p state/BundleManagedAttributeIndex
# Trust only the public LDAP lab certificate, leaving the JDK truststore intact.
cp "$JAVA_HOME/lib/security/cacerts" /tmp/iiq-cacerts
keytool -importcert -noprompt -alias lab-ldap -file /etc/ldap/tls/ldap.crt \
  -keystore /tmp/iiq-cacerts -storepass changeit >/dev/null 2>&1
keytool -importcert -noprompt -alias lab-sql-ca -file /run/sql-trust/ca.crt \
  -keystore /tmp/iiq-cacerts -storepass changeit >/dev/null 2>&1
IIQ=/usr/local/tomcat/webapps/identityiq/WEB-INF/bin/iiq
if [ ! -f state/.initialized ]; then
  config=/usr/local/tomcat/webapps/identityiq/WEB-INF/config
  for file in init.xml; do
    [ ! -f "$config/$file" ] || "$IIQ" console -c "import $config/$file"
  done
  if [ -f "$config/patch/identityiq-8.5p1-objects.xml" ]; then
    "$IIQ" patch 8.5p1
  fi
  for file in sp.init-custom.xml init-lcm.xml; do
    [ ! -f "$config/$file" ] || "$IIQ" console -c "import $config/$file"
  done
  touch state/.initialized
fi
exec bin/catalina.sh run
