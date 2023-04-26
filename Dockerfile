FROM python:3.10.11-slim-bullseye AS compile-image

# Multi-stage build:
# https://docs.docker.com/develop/develop-images/multistage-build/
# https://pythonspeed.com/articles/multi-stage-docker-python/

# Stage 1: Compile Python dependencies
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

RUN pip install --upgrade pip~=23.0.1 --timeout 120 \
  && pip install --user -r requirements.txt --timeout 120

# Stage 2: Create the final image with application code
#------------------------------------------------------

FROM python:3.10.11-slim-bullseye

# Define and create non-root user
ARG USERNAME=redash
RUN useradd --create-home ${USERNAME}

# Copy Python dependencies from compile-image stage
COPY --from=compile-image /root/.local /home/${USERNAME}/.local

# Make sure scripts in .local are usable:
ENV PATH=/home/${USERNAME}/.local/bin:$PATH

# Working directory for application
WORKDIR /home/${USERNAME}/app/

# Copy source and configurations
COPY LICENSE LICENSE.redash manage.py ./etc/docker-entrypoint.sh ./
COPY etc ./etc/
COPY migrations ./migrations/
COPY redash ./redash/
COPY tests ./tests/

# Swith to non-root user
RUN chown -R ${USERNAME} ./ /home/${USERNAME}/.local
USER ${USERNAME}

# Expose port
EXPOSE 5000

# Define entrypoint and default command
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["server"]
