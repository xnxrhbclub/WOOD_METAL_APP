FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV BUILDOZER_ALLOW_ROOT=1

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    zip \
    unzip \
    openjdk-17-jdk \
    autoconf \
    libtool \
    pkg-config \
    zlib1g-dev \
    libncurses5-dev \
    libncursesw5-dev \
    cmake \
    libffi-dev \
    libssl-dev \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

RUN pip3 install \
    Cython==0.29.37 \
    buildozer==1.5.0

WORKDIR /app

CMD ["buildozer","android","debug"]
