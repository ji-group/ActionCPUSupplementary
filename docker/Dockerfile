# BEAST X (action_likelihood) + two BEAGLE builds + EigenJNI + Python,
# for the supplementary material of "BEAGLE in Action".
#
# Build context is this directory:
#   docker build --platform linux/arm64 -t beast-action docker
#   docker build --platform linux/amd64 -t beast-action docker
#
# Every source is fetched by commit, not by branch name: the action branches
# keep moving and df15374a is not a branch tip.

FROM ubuntu:24.04

ARG TARGETARCH

# Pinned commits (see README, "Software versions").
# BEAST: e6398f67 is what the spring 2026 builds used; the branch tip 88a54cb5
# adds a fix that re-sends the rate matrix to BEAGLE when an action likelihood
# restores (open question Q1).
ARG BEAST_COMMIT=e6398f670d3b6f96f7e80a314c596b3d55a3c087
ARG BEAGLE_FAST_COMMIT=c2b9e060965261712230ccdd2950149410e25f4e
ARG BEAGLE_SLOW_COMMIT=df15374a017f4639645c0ebdbede506e47352be8
ARG EIGENJNI_COMMIT=dfcdbd46114a590d438b49ae059d811647fd1001

# The full JDK, not -headless: CMake's FindJNI requires the AWT library and
# otherwise skips the JNI headers.
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates pkg-config \
        openjdk-17-jdk ant libeigen3-dev python3 \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-${TARGETARCH}

# fetch <url> <commit> <dir>
RUN printf '#!/bin/sh\nset -e\nmkdir -p "$3" && cd "$3" && git init -q && git remote add origin "$1" && git fetch -q --depth 1 origin "$2" && git checkout -q FETCH_HEAD\n' \
        > /usr/local/bin/fetch-commit && chmod 755 /usr/local/bin/fetch-commit

# A portable -march: BEAGLE hard-wires -march=native, which would make an image
# built on one machine crash with SIGILL on another.
RUN if [ "$TARGETARCH" = amd64 ]; then echo "-march=x86-64-v3" > /etc/arch-cxxflags; else : > /etc/arch-cxxflags; fi

# EigenJNI -> /opt/eigenjni/lib/libeigen-jni.so
RUN fetch-commit https://github.com/ji-group/EigenJNI.git ${EIGENJNI_COMMIT} /app/EigenJNI \
    && cd /app/EigenJNI \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="$(cat /etc/arch-cxxflags)" \
             -DCMAKE_INSTALL_PREFIX=/opt/eigenjni \
    && cmake --build build -j \
    && cmake --install build

# BEAGLE "fast" (faster-mat-mult2: action kernel + Eigen dense multiply) -> /opt/beagle-fast
RUN fetch-commit https://github.com/ji-group/beagle-lib.git ${BEAGLE_FAST_COMMIT} /app/beagle-fast \
    && cd /app/beagle-fast \
    && sed -i 's/BEAGLE_OPTIMIZE_FOR_NATIVE_ARCH true/BEAGLE_OPTIMIZE_FOR_NATIVE_ARCH false/' CMakeLists.txt \
    && cmake -S . -B build -DBUILD_CUDA=OFF -DBUILD_OPENCL=OFF \
             -DCMAKE_CXX_FLAGS="$(cat /etc/arch-cxxflags)" \
             -DCMAKE_INSTALL_PREFIX=/opt/beagle-fast -DCMAKE_INSTALL_LIBDIR=lib \
    && cmake --build build -j \
    && cmake --install build

# BEAGLE "slow" (action-dev at the merge base: hand-written dense multiply) -> /opt/beagle-slow
# Its CMake adds plain -O3, so -DNDEBUG is passed here to match the fast build.
RUN fetch-commit https://github.com/ji-group/beagle-lib.git ${BEAGLE_SLOW_COMMIT} /app/beagle-slow \
    && cd /app/beagle-slow \
    && sed -i 's/BEAGLE_OPTIMIZE_FOR_NATIVE_ARCH true/BEAGLE_OPTIMIZE_FOR_NATIVE_ARCH false/' CMakeLists.txt \
    && cmake -S . -B build -DBUILD_CUDA=OFF -DBUILD_OPENCL=OFF \
             -DCMAKE_CXX_FLAGS="-DNDEBUG $(cat /etc/arch-cxxflags)" \
             -DCMAKE_INSTALL_PREFIX=/opt/beagle-slow -DCMAKE_INSTALL_LIBDIR=lib \
    && cmake --build build -j \
    && cmake --install build

# BEAST X, branch action_likelihood -> /app/beast-mcmc/build/dist/beast.jar
RUN fetch-commit https://github.com/beast-dev/beast-mcmc.git ${BEAST_COMMIT} /app/beast-mcmc \
    && cd /app/beast-mcmc \
    && ant dist

ENV BEAST_JAR=/app/beast-mcmc/build/dist/beast.jar \
    BEAGLE_FAST_LIB=/opt/beagle-fast/lib \
    BEAGLE_SLOW_LIB=/opt/beagle-slow/lib \
    EIGENJNI_LIB=/opt/eigenjni/lib

COPY beast beast-slow /usr/local/bin/

WORKDIR /tmp
