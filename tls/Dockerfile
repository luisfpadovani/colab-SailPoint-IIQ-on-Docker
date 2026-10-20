FROM debian:bookworm-slim@sha256:60eac759739651111db372c07be67863818726f754804b8707c90979bda511df
RUN apt-get update && apt-get install -y --no-install-recommends openssl && rm -rf /var/lib/apt/lists/*
COPY entrypoint.sh /usr/local/bin/prepare-sql-tls
RUN chmod 0555 /usr/local/bin/prepare-sql-tls
ENTRYPOINT ["/usr/local/bin/prepare-sql-tls"]
