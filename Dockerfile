# syntax=docker/dockerfile:1.6

# --- 全局变量声明区（必须在第一个 FROM 之前） ---
ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG HAILO_VERSION="4.23.0"

############################
# Stage 1: Build Stage (编译阶段)
############################
# 使用 --platform=$BUILDPLATFORM 允许 Docker 使用宿主机原生性能进行编译
FROM --platform=$BUILDPLATFORM python:3.13-slim AS build

# 在阶段内重新声明变量以激活它们
ARG TARGETPLATFORM
ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# 安装构建工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    cmake \
    build-essential \
    autoconf \
    automake \
    unzip \
    zip \
    python3-dev \
    pkg-config \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

# 1. 下载并编译 HailoRT C++ 库
WORKDIR /tmp
RUN git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git \
    && cd hailort \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target install --parallel $(nproc)

# 2. 预编译 Python 依赖包 (Wheels)
WORKDIR /wheels
COPY requirements.txt .
# 即使是交叉编译，pip wheel 也会在 QEMU 环境下生成 TARGETPLATFORM 架构的 wheel
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 3. 编译 HailoRT Python 绑定
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: Runtime Stage (运行阶段)
############################
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE \
    PYTHONUNBUFFERED=1

# 安装运行期最小依赖
# 适配 Debian 12/13 的库名
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libstdc++6 \
    libgcc-s1 \
    libglib2.0-0 \
    libgl1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# 从构建阶段拷贝二进制成果
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
COPY --from=build /wheels /tmp/wheels

# 关键：强制使用本地 Wheels 安装，禁止联网编译
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels \
 && ldconfig

# 应用部署
WORKDIR /app
COPY . .

# 确保运行时能找到动态链接库
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

EXPOSE 8000
CMD ["python3", "run_api.py"]
