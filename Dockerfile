# syntax=docker/dockerfile:1.6

ARG TARGETPLATFORM=linux/arm64
ARG HAILO_VERSION="4.23.0"

############################
# Stage 1: Build Stage (在目标架构下构建)
############################
FROM --platform=$TARGETPLATFORM python:3.13-slim AS build

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# 安装构建工具 (此时在 arm64 模拟环境下)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git cmake build-essential \
    autoconf automake unzip zip python3-dev pkg-config \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# 1. 编译 HailoRT
WORKDIR /tmp
RUN git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git \
    && cd hailort \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target install --parallel $(nproc)

# 2. 编译所有依赖 (自动生成 arm64 wheel)
WORKDIR /wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 3. 编译 Python 绑定
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: Runtime Stage
############################
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libstdc++6 libgcc-s1 libglib2.0-0 libgl1 curl \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
COPY --from=build /wheels /tmp/wheels

# 此时 /tmp/wheels 里的全部是 aarch64 格式，安装将顺畅无阻
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels \
 && ldconfig

WORKDIR /app
COPY . .
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

EXPOSE 8000
CMD ["python3", "run_api.py"]
