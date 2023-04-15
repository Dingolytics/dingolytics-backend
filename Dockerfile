FROM python:3.9.16-slim-bullseye

EXPOSE 5000

RUN useradd --create-home redash

WORKDIR /app/

# Install packages
RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  curl \
  gnupg \
  build-essential \
  pwgen \
  libffi-dev \
  sudo \
  git-core \
  python3-watchdog \
  # Postgres client
  libpq-dev \
  # ODBC support:
  g++ unixodbc-dev \
  # for SAML
  xmlsec1 \
  # Additional packages required for data sources:
  libssl-dev \
  default-libmysqlclient-dev \
  freetds-dev \
  libsasl2-dev \
  unzip \
  libsasl2-modules-gssapi-mit && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# ARG TARGETPLATFORM
# ARG databricks_odbc_driver_url=https://databricks.com/wp-content/uploads/2.6.10.1010-2/SimbaSparkODBC-2.6.10.1010-2-Debian-64bit.zip
# RUN if [ "$TARGETPLATFORM" = "linux/amd64" ]; then \
#   curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
#   && curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list \
#   && apt-get update \
#   && ACCEPT_EULA=Y apt-get install  -y --no-install-recommends msodbcsql17 \
#   && apt-get clean \
#   && rm -rf /var/lib/apt/lists/* \
#   && curl "$databricks_odbc_driver_url" --location --output /tmp/simba_odbc.zip \
#   && chmod 600 /tmp/simba_odbc.zip \
#   && unzip /tmp/simba_odbc.zip -d /tmp/ \
#   && dpkg -i /tmp/SimbaSparkODBC-*/*.deb \
#   && printf "[Simba]\nDriver = /opt/simba/spark/lib/64/libsparkodbc_sb64.so" >> /etc/odbcinst.ini \
#   && rm /tmp/simba_odbc.zip \
#   && rm -rf /tmp/SimbaSparkODBC*; fi

# Install Python dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip~=23.0.1 --timeout 120 \
    && pip install -r requirements-dev.txt -r requirements.txt --timeout 120

# Copy Redash source
COPY LICENSE.original manage.py  ./
COPY etc ./etc
COPY migrations ./migrations
COPY redash ./redash
COPY tests ./tests

# Change ownership of the Redash source
RUN chown -R redash ./
USER redash

ENTRYPOINT ["/app/etc/docker-entrypoint.sh"]

CMD ["server"]
