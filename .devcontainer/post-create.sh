#!/usr/bin/env bash
# 建立容器後置作業:取得 pinned xu4 引擎並套繁中化(idempotent)。
# postCreate 的工作目錄是 workspace 根(/workspaces/u4-cht),以下用相對路徑。
set -e

XU4_COMMIT="6a7ee3d0079cfdc1c8fb9ba7a3c710a957155a71"

if [ ! -d "xu4" ]; then
  echo "[post-create] clone xu4 引擎(pinned ${XU4_COMMIT})"
  git clone https://github.com/xu4-engine/u4.git xu4
  git -C xu4 checkout "${XU4_COMMIT}"
  echo "[post-create] 取得 submodule(src/faun, src/glv)"
  git -C xu4 submodule update --init --recursive src/faun src/glv
  echo "[post-create] 套繁中化 tools/apply_cht.sh"
  bash tools/apply_cht.sh xu4
else
  echo "[post-create] xu4/ 已存在,略過 clone 與 apply_cht(idempotent)。"
  echo "             如需重套:rm -rf xu4 後重新執行 bash .devcontainer/post-create.sh"
fi

cat <<'EOF'

========================================================================
 Ultima IV 繁中版 開發環境就緒。後續可用指令(皆在 workspace 根執行):

 [a] Linux build(Allegro 後端,自源碼建 Boron/Faun + make download 抓資料)
     docker build -f docker/Dockerfile.zh -t u4cht/xu4-allegro xu4

 [b] headless 截圖 pass/fail 測試(需先完成 [a])
     docker build -f docker/Dockerfile.test -t u4cht/xu4-test docker
     mkdir -p /tmp/u4shot
     docker run --rm -v /tmp/u4shot:/out u4cht/xu4-test 22 3
     # → /tmp/u4shot/screen.png

 [c] Windows 交叉編譯打包(mingw64 / GLFW 後端,需先完成 [a])
     docker build -f dist/win/Dockerfile -t u4cht/win xu4
     bash dist/win/make-zip.sh u4-cht-windows-x64.zip

 也可原生在容器內 make 迭代(已裝 Allegro / png / vorbis 等相依):
     cd xu4 && ./configure --allegro && make download && make -C src clean && make
========================================================================

EOF
