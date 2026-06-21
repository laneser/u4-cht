# Dev Container 建置 + 跨平台打包(含 Windows 交叉編譯)

> 一句話結論:**Windows `.exe` 可以在 WSL / Linux 上產出,完全不需要原生 Windows**——
> 走 `dist/win/Dockerfile` 的 mingw64 交叉編譯(GLFW 後端)。同一份引擎也原生跑 Linux(Allegro 後端)。

本文件說明在 **Dev Container** 內開發,以及三條 Docker 建置管線(Linux / 測試 / Windows)的指令與產物。
所有重活都在 Docker 內完成(可重現);host 端只需 Docker。風格與 `SETUP.md`、`dist/README.md` 一致。

---

## 1. 用 Dev Container 開發

VS Code 開啟本 repo → 命令面板 → **Dev Containers: Reopen in Container**。

- 首次進容器時 `postCreate` 會自動:
  1. `git clone https://github.com/xu4-engine/u4.git xu4`(pinned commit `6a7ee3d0079cfdc1c8fb9ba7a3c710a957155a71`),
     並 `git submodule update --init --recursive`(需 `src/faun` 與 `src/glv`)。
  2. 跑 `tools/apply_cht.sh xu4` 套繁中化:複製 `cht.cpp` / `cht.h`、套 `patches/engine/cht-engine.patch`、
     把 `assets/cjk_font*.bin` 與 `u4_cht.tab` 複製進 `xu4/`、中文化 `vendors.b`。
     字型 `.bin` 已預建入庫(`assets/cjk_font.bin` 等),`apply_cht.sh` 會跳過字型生成。
- 容器內已具 **docker-in-docker**,因此下面三條 `docker build` 管線可直接在容器內執行。
- host 工具:`apply_cht.sh` 在 host 上跑只需 `python3` 標準庫(字型已預建,無 `pillow` / `noto` 也可),
  其餘重活都在 Docker image 內。

> 不用 Dev Container 也可以:依 `SETUP.md` 在 host 手動 `git clone xu4` + `bash tools/apply_cht.sh`,
> 接著直接跑下面的 `docker build`。Dev Container 只是把這段前置自動化。

---

## 2. Linux build + 執行(Allegro 5)

```bash
docker build -f docker/Dockerfile.zh -t u4cht/xu4-allegro xu4
```

- 基底 Ubuntu 24.04 + Allegro 5,源碼建 Boron / Faun,`make download` 自動抓 freeware U4 遊戲資料。
- 產物(image 內 `/build/xu4/`):`src/xu4`(二進位)、`Ultima-IV.mod`、`U4-Upgrade.mod`、
  `render.pak`、`ultima4.zip`、`u4upgrad.zip`。
- 桌面遊玩(Docker + X11)最簡可用 `bash dist/play.sh`(見 `dist/README.md`)。

---

## 3. Headless 截圖測試(pass / fail)

本專案**沒有傳統 unit test framework**;「測試」的形式是 **headless 截圖驗收**——
跑遊戲、截一張 PNG,人眼或比對驗證渲染與中文化是否正確。

```bash
docker build -f docker/Dockerfile.test -t u4cht/xu4-test docker

mkdir -p /tmp/u4shot
docker run --rm -v /tmp/u4shot:/out u4cht/xu4-test 22 3
# → /tmp/u4shot/screen.png
```

- 測試 image 在 `u4cht/xu4-allegro` 之上加 **Xvfb + Mesa 軟體 GL + ImageMagick**。
- `docker/shot.sh` 在 Xvfb 內跑 xu4 並截圖;參數為 `<等待秒數> <scale> [額外 xu4 args]`。
- 自測守護(渲染已知 NPC 對白驗證全鏈路):
  `docker run --rm -e U4CHT_SELFTEST=1 -v /tmp/u4shot:/out u4cht/xu4-test 6 3`。

---

## 4. Windows 執行檔(交叉編譯)— 重點

**在 WSL / Linux 即可產出 Windows `.exe`,免原生 Windows。**
走 `dist/win/Dockerfile`(`fedora:41` + **mingw64** 交叉工具鏈,**GLFW 後端**)。

```bash
# 1) 交叉編譯出 xu4.exe 並收集 DLL
docker build -f dist/win/Dockerfile -t u4cht/win xu4

# 2) 組裝可散布 zip
bash dist/win/make-zip.sh u4-cht-windows-x64.zip
```

產物 `u4-cht-windows-x64.zip` 含:

- `xu4.exe`(GLFW 後端)
- **全部 DLL**:`glfw3` / `libgcc_s_seh` / `libwinpthread` / `zlib1` / `libpng16` /
  `libogg` / `libvorbis(file)` / `libssp`(`libstdc++` 靜態連結)
- `modules`(`Ultima-IV.mod` / `U4-Upgrade.mod` / `render.pak`)
- **三套字型**(Noto 黑體 / Firefly 宋體 / Kai 楷體)
- **遊戲資料**(freeware U4)
- `run.bat`(雙擊即玩;字形可 `set U4CHT_FONT=firefly` 再執行)

> 需強制重建可加 `--build-arg CACHEBUST=1`(見 `dist/README.md` 的 Windows zip 段)。

---

## 5. WSL → Windows 取用

WSL 下的 `/mnt/c/` 就是 Windows 的 `C:\`。把產出的 zip 複製過去即可:

```bash
cp u4-cht-windows-x64.zip /mnt/c/Users/<你>/Downloads/
```

接著在 **Windows 端**:到該資料夾、解壓 zip、雙擊 `run.bat` 即開始遊玩。
(zip 已自包含 DLL + 模組 + 字型 + 遊戲資料,Windows 端不需另外安裝任何 runtime。)

---

## 6. 跨平台總結表

| 平台 | 建置方式 | 後端 | 能否在此 WSL 產出 |
|---|---|---|---|
| Linux(原生) | `docker build -f docker/Dockerfile.zh`;桌面 `dist/play.sh` | Allegro 5 | ✅ 可(本機 Docker) |
| Linux AppImage | `docker build -f dist/appimage/Dockerfile`(自包含含遊戲資料) | Allegro 5 | ✅ 可(本機 Docker) |
| Windows(zip) | `docker build -f dist/win/Dockerfile` + `dist/win/make-zip.sh`(mingw64 交叉編譯) | GLFW | ✅ 可,**免原生 Windows** |
| macOS(.app) | GitHub Actions `build-mac.yml`(macOS runner 原生) | Allegro 5 | ❌ 不行(Linux 無法跨編 Mach-O,須走 CI) |
| Android(APK) | GitHub Actions `build-android.yml` | GLV | ❌ 不行(走 CI) |

- **Linux / Windows** 兩條桌面管線都能在這台 WSL 直接用 Docker 跑完並拿到可散布產物。
- **macOS / Android** 因平台限制走 GitHub Actions;CI 會自行 clone xu4 上游(pinned commit)+ 跑 `apply_cht.sh`。
  細節見 `SETUP.md` §8 與 `docs/macos-port.md`。
