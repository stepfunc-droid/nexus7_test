FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    make \
    gcc-arm-linux-gnueabihf \
    libc6-dev-armhf-cross \
    bc \
    bison \
    flex \
    libssl-dev \
    libelf-dev \
    device-tree-compiler \
    cpio \
    gzip \
    xz-utils \
    bzip2 \
    wget \
    python3 \
    mkbootimg \
    findutils \
    coreutils \
    tar \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

CMD ["bash", "./build.sh"]
