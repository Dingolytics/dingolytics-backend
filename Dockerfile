FROM python:3.10.11-slim-bullseye AS dependencies

# Multi-stage build:
# https://docs.docker.com/develop/develop-images/multistage-build/
# https://pythonspeed.com/articles/multi-stage-docker-python/


# Stage 1: Install Python dependencies
#-------------------------------------

RUN apt update -y && \
  apt install -y --no-install-recommends \
    curl \
    unzip \
    build-essential \
    libffi-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip~=23.0.1 --timeout 300 \
 && pip install --no-cache-dir --user -r requirements.txt --timeout 300


# Stage 2: Create image with application code
#--------------------------------------------

FROM python:3.10.11-slim-bullseye AS application

ARG USERNAME=redash
ARG USERHOME=/home/${USERNAME}

RUN useradd --create-home ${USERNAME}

ENV PATH=${USERHOME}/.local/bin:$PATH
USER ${USERNAME}
WORKDIR ${USERHOME}/app/

COPY --chown=${USERNAME} --from=dependencies /root/.local ${USERHOME}/.local
COPY --chown=${USERNAME} etc ${USERHOME}/etc/
COPY --chown=${USERNAME} . ./

ENTRYPOINT ["./entrypoint.sh"]


# Stage 3a: Create image for development
#---------------------------------------

FROM application AS development

RUN pip install --no-cache-dir --user watchdog --timeout 300


# Stage 3b: Create image for testing
#-----------------------------------

FROM dependencies AS tests

RUN useradd --create-home tests

ENV PATH=/home/tests/.local/bin:$PATH
USER tests
WORKDIR /home/tests/app/

COPY --chown=tests --from=dependencies /root/.local /home/tests/.local
COPY --chown=tests etc /home/tests/etc/

RUN pip install --no-cache-dir --user --timeout 300 \
  -r /home/tests/etc/requirements.tests.txt
