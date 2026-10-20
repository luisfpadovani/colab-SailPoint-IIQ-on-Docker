# syntax=docker/dockerfile:1.7
FROM tomcat:9.0-jdk21-temurin@sha256:c8baa1ecc82859c42fa0a33b5c8499ebe3c6bbba624fefe615fec7ed827e0e90 AS builder
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ant ant-optional python3 && rm -rf /var/lib/apt/lists/*
ENV SPTARGET=docker
COPY file_install/ /usr/local/
RUN unzip -o /usr/local/ssb.zip -d /usr/local/ssb && rm /usr/local/ssb.zip
COPY file_config/ /usr/local/ssb/config/
COPY render-build-config.py /tmp/render-build-config.py
ARG MSSQL_JDBC_VERSION=13.6.0.jre11
ARG MSSQL_JDBC_SHA256=4c566e4022c4dcf1489aeb639fe49a0f6ffae3d796fdc2f56b5b8882d4c3bf5a
RUN mkdir -p /usr/local/ssb/web/WEB-INF/lib && \
    curl --fail --location --proto '=https' --tlsv1.2 "https://repo.maven.apache.org/maven2/com/microsoft/sqlserver/mssql-jdbc/${MSSQL_JDBC_VERSION}/mssql-jdbc-${MSSQL_JDBC_VERSION}.jar" -o /usr/local/ssb/web/WEB-INF/lib/mssql-jdbc.jar && \
    echo "${MSSQL_JDBC_SHA256}  /usr/local/ssb/web/WEB-INF/lib/mssql-jdbc.jar" | sha256sum --check
RUN --mount=type=secret,id=iiq_build_env,required=true \
    python3 /tmp/render-build-config.py /run/secrets/iiq_build_env /usr/local/ssb && \
    cd /usr/local/ssb && sh build.sh clean main && \
    find build/extract/WEB-INF/lib -name 'sqljdbc*.jar' -delete && \
    sed -i 's/`java -version/`env -u JAVA_TOOL_OPTIONS -u JDK_JAVA_OPTIONS java -version/' build/extract/WEB-INF/bin/iiq

FROM tomcat:9.0-jdk21-temurin@sha256:c8baa1ecc82859c42fa0a33b5c8499ebe3c6bbba624fefe615fec7ed827e0e90 AS runtime-base
# Remove download/edit/build utilities inherited from the upstream image, if present.
RUN dpkg-query -W -f='${binary:Package} ${db:Status-Status}\n' | \
    awk '$2 == "installed" && $1 ~ /^(curl|wget|vim|vim-tiny|telnet|ant|ant-optional|zip|unzip)$/ {print $1}' | \
    xargs -r apt-get purge -y && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 10001 iiq && useradd --uid 10001 --gid 10001 --no-create-home iiq && \
    mkdir -p state && chown -R iiq:iiq logs temp work state
USER 10001:10001

FROM runtime-base AS runtime
COPY --from=builder --chown=iiq:iiq /usr/local/ssb/build/extract/ webapps/identityiq/
COPY --chown=iiq:iiq entrypoint.sh /usr/local/bin/iiq-entrypoint.sh
RUN chmod 0550 /usr/local/bin/iiq-entrypoint.sh && chmod 0550 webapps/identityiq/WEB-INF/bin/iiq && \
    mkdir -p state/BundleManagedAttributeIndex && \
    ln -s /usr/local/tomcat/state/BundleManagedAttributeIndex webapps/identityiq/WEB-INF/BundleManagedAttributeIndex
USER 10001:10001
ENTRYPOINT ["/usr/local/bin/iiq-entrypoint.sh"]
