FROM mcr.microsoft.com/mssql/server:2022-CU27-ubuntu-22.04
COPY --chown=mssql:root scripts/ /opt/iiq-scripts/
COPY --chown=mssql:root *.sh *.py /opt/iiq/
USER root
RUN chmod 0550 /opt/iiq/*.sh
USER mssql
ENTRYPOINT ["/opt/iiq/entrypoint.sh"]
