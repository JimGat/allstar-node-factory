FROM debian:13-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV container=docker

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
       ca-certificates \
       openssh-server \
       python3 \
       python3-venv \
       sudo \
       systemd \
       systemd-sysv \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash ansible \
    && usermod --append --groups sudo ansible \
    && printf 'ansible ALL=(ALL) NOPASSWD:ALL\n' > /etc/sudoers.d/ansible \
    && chmod 0440 /etc/sudoers.d/ansible

RUN python3 -m venv /opt/node-factory-venv \
    && /opt/node-factory-venv/bin/pip install --no-cache-dir ansible-core==2.20.8

WORKDIR /opt/allstar-node-factory
COPY requirements.yml ./requirements.yml
RUN /opt/node-factory-venv/bin/ansible-galaxy collection install \
    --requirements-file requirements.yml

COPY . .

STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
