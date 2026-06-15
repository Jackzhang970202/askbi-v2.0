# ============================================================
# AskBI v1.3 - 纯环境镜像 (代码外挂)
# 构建: docker build -t askbi:1.3 .
# 部署: 代码目录 + 此镜像，改 .env 即可运行
# ============================================================
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 直接覆盖为清华 apt 源（自动检测 Debian 版本：bookworm/trixie）
RUN DEBIAN_CODENAME=$(grep -oP '(?<=VERSION_CODENAME=).+' /etc/os-release 2>/dev/null || echo "bookworm") && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ ${DEBIAN_CODENAME} main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ ${DEBIAN_CODENAME}-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security/ ${DEBIAN_CODENAME}-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    rm -f /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# pip 换清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple \
    && pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 只复制依赖清单并安装
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的空目录
RUN mkdir -p /app/data /app/refer /app/refer_list \
    /app/user_upload_files /app/report_files /app/dashboard_files \
    /app/knowledge /app/logs

EXPOSE 8002 8000
