# Ultima IV 繁中版 開發環境
# 基底:VS Code devcontainer Ubuntu 24.04(含 vscode 使用者 / git / 常用工具)
# apt 套件對齊 docker/Dockerfile.zh 的建置相依,讓容器內可原生 make 迭代,
# 也讓 tools/apply_cht.sh 與 tools/*.py 直接可跑。
# 注意:不在此 image 內 clone xu4(那是 post-create.sh 的事),保持 image 精簡。
FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential git make curl ca-certificates pkg-config \
      libpng-dev libvorbis-dev libogg-dev libpulse-dev \
      liballegro5-dev liballegro-acodec5-dev liballegro-audio5-dev \
      python3 python3-pip unzip zip \
 && rm -rf /var/lib/apt/lists/*
