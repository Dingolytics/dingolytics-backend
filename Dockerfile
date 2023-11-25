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

# Install Python dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
COPY requirements.txt requirements-dev.txt ./
RUN pip install --upgrade pip~=23.0.1 --timeout 120 \
    && pip install -r requirements-dev.txt -r requirements.txt --timeout 120

# Copy source and configurations
COPY LICENSE LICENSE.redash manage.py  ./
COPY etc ./etc
COPY migrations ./migrations
COPY redash ./redash
COPY tests ./tests

# Change ownership of the source
RUN chown -R redash ./
USER redash

ENTRYPOINT ["/app/etc/docker-entrypoint.sh"]

CMD ["server"]
