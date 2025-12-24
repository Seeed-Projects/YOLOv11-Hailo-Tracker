# syntax=docker/dockerfile:1.6

############################
# Stage 1: Build Stage (编译阶段)
############################
# 使用 BUILDPLATFORM 加速，但我们将为 TARGETPLATFORM 生成代码
ARG BUILDPLATFORM
FROM --platform=$BUILDPLATFORM python:3.13-slim AS build

ARG TARGETPLATFORM
ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive

# 安装构建必需的工具
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

# 升级构建核心工具
RUN pip install --upgrade pip setuptools wheel

# 1. 下载并编译 HailoRT C++ 库
WORKDIR /tmp
RUN git clone --branch v${HAILO_VERSION} --depth 1 https://github.com/hailo-ai/hailort.git \
    && cd hailort \
    && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target install --parallel $(nproc)

# 2. 预编译 Python 依赖包 (Wheels)
# 注意：即使在交叉编译时，pip 也需要根据 TARGETPLATFORM 构建
WORKDIR /wheels
COPY requirements.txt .
# 使用 --no-cache-dir 减小体积，确保生成所有依赖的 binary wheel
RUN pip wheel --no-cache-dir --wheel-dir=/wheels -r requirements.txt

# 3. 编译 HailoRT Python 绑定
WORKDIR /tmp/hailort/hailort/libhailort/bindings/python/platform
RUN python setup.py bdist_wheel --dist-dir=/wheels

############################
# Stage 2: Runtime Stage (运行阶段)
############################
ARG TARGETPLATFORM
FROM --platform=$TARGETPLATFORM python:3.13-slim AS runtime

ARG HAILO_VERSION
ENV DEBIAN_FRONTEND=noninteractive \
    HAILORT_LOGGER_PATH=NONE \
    PYTHONUNBUFFERED=1

# 安装运行期最小依赖
# 注意：libglib2.0-0t64 是针对 Debian Trixie/Sid 的新命名，slim-bookworm 请用 libglib2.0-0
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libstdc++6 \
    libgcc-s1 \
    libglib2.0-0 \
    libgl1 \
    curl \
 && rm -rf /var/lib/apt/lists/*

# 从构建阶段拷贝 HailoRT 二进制库和工具
COPY --from=build /usr/local/lib/libhailort.so.${HAILO_VERSION} /usr/local/lib/
COPY --from=build /usr/local/bin/hailortcli /usr/local/bin/
# 拷贝所有预编译好的 Python .whl 文件
COPY --from=build /wheels /tmp/wheels

# 关键修复点：
# 1. 使用 --no-index 强制只从本地 /tmp/wheels 寻找安装包
# 2. 使用 --find-links 指向该目录
# 3. 这可以防止 pip 因为找不到兼容包而尝试调用不存在的 gcc 进行编译
RUN pip install --no-cache-dir --no-index --find-links=/tmp/wheels /tmp/wheels/*.whl \
 && rm -rf /tmp/wheels \
 && ldconfig

# 应用部署
WORKDIR /app
COPY . .

# 环境变量设置（可选，确保动态库查找正确）
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

EXPOSE 8000
CMD ["python3", "run_api.py"]
