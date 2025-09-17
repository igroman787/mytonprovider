FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

ARG MYTONPROVIDER_REPO
ARG MYTONPROVIDER_AUTHOR
ARG MYTONPROVIDER_VERSION
ARG MYTONPROVIDER_MODULES
ARG MYTONPROVIDER_STORAGE_PATH
ARG MYTONPROVIDER_STORAGE_COST
ARG MYTONPROVIDER_SPACE_TO_PROVIDE

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential pkg-config ca-certificates iproute2 iputils-ping fio \
      git curl wget python3 python3-pip virtualenv tar sudo \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 -s /bin/bash admin \
    && echo "admin ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

RUN mkdir -p /scripts \
    && wget -nv "https://raw.githubusercontent.com/gdraheim/docker-systemctl-replacement/master/files/docker/systemctl3.py" -O /usr/bin/systemctl3 \
    && wget -nv "https://raw.githubusercontent.com/${MYTONPROVIDER_AUTHOR}/${MYTONPROVIDER_REPO}/${MYTONPROVIDER_VERSION}/scripts/install.sh" -O /scripts/install.sh \
    && wget -nv "https://raw.githubusercontent.com/${MYTONPROVIDER_AUTHOR}/${MYTONPROVIDER_REPO}/${MYTONPROVIDER_VERSION}/scripts/entrypoint.sh" -O /scripts/entrypoint.sh \
    && wget -nv "https://raw.githubusercontent.com/${MYTONPROVIDER_AUTHOR}/${MYTONPROVIDER_REPO}/${MYTONPROVIDER_VERSION}/scripts/systemctl-wrapper.sh" -O /usr/bin/systemctl

RUN chmod +x /usr/bin/systemctl \
    && chmod +x /usr/bin/systemctl3 \
    && chmod 755 /scripts/install.sh \
    && chmod 755 /scripts/entrypoint.sh \
    && mkdir -p "${MYTONPROVIDER_STORAGE_PATH}" \
    && chown -R admin:admin "${MYTONPROVIDER_STORAGE_PATH}" \
    && bash /scripts/install.sh -u admin \
       -r "${MYTONPROVIDER_REPO}" \
       -a "${MYTONPROVIDER_AUTHOR}" \
       -b "${MYTONPROVIDER_VERSION}" \
       -m "${MYTONPROVIDER_MODULES}" \
       -p "${MYTONPROVIDER_STORAGE_PATH}" \
       -c "${MYTONPROVIDER_STORAGE_COST}" \
       -s "${MYTONPROVIDER_SPACE_TO_PROVIDE}"\
    && mkdir -p /usr/local/share/mytonprovider/storage-seed \
    && cp -a "${MYTONPROVIDER_STORAGE_PATH}/." "/usr/local/share/mytonprovider/storage-seed/"

RUN printf '%s\n' '#!/usr/bin/env bash' 'exec sudo -u admin mytonprovider "$@"'  \
    > /usr/bin/console && chmod 755 /usr/bin/console

ENTRYPOINT ["/scripts/entrypoint.sh"]