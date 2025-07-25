ARG UV_VERSION=0.8.2
ARG PYTHON_VERSION=3.13-bookworm

FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv

FROM python:$PYTHON_VERSION

# Update base image and install aws-cli
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends build-essential unzip cmake git libboost-dev libexpat1-dev zlib1g-dev libbz2-dev && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv --chown=vscode: /uv /uvx /bin/

# Create the vscode user and set up the environment
RUN useradd -ms /bin/bash vscode \
    && mkdir -p /home/vscode/.vscode-server/extensions \
    && chown -R vscode:vscode /home/vscode 

USER vscode
WORKDIR /home/vscode

