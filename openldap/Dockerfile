FROM debian:bookworm-slim@sha256:60eac759739651111db372c07be67863818726f754804b8707c90979bda511df

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates \
        ldap-utils \
        openssl \
        slapd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/openldap-entrypoint.sh
RUN chmod +x /usr/local/bin/openldap-entrypoint.sh

EXPOSE 389 636

ENTRYPOINT ["/usr/local/bin/openldap-entrypoint.sh"]
