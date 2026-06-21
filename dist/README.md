# 散布 / 遊玩

## 桌面遊玩(Docker + X11,最簡)
```bash
U4CHT_FONT=firefly bash dist/play.sh    # 字形:firefly(宋體)/ kai(楷體)/ 省略=Noto
```

## Linux 可執行包
```bash
bash dist/make-release.sh u4-cht-linux.tar.gz
tar xzf u4-cht-linux.tar.gz && cd u4-cht-linux
sudo apt install liballegro5.2 liballegro-acodec5.2 liballegro-audio5.2 libpng16-16 libvorbisfile3
U4CHT_FONT=firefly ./run.sh -s 2 --filter xBRZ
```
`libfaun.so.0` 已隨包(自建,非 apt);`liballegro5.2` 等由系統提供。

## Windows
本專案以 **mingw64 交叉編譯**在 Linux / WSL 上直接產出 Windows 包,**免原生 Windows**(GLFW 後端)。
流程見下方「## Windows zip」段:`docker build -f dist/win/Dockerfile` + `bash dist/win/make-zip.sh`。

## AppImage(Linux,全自包含含遊戲資料)
於 **Ubuntu 22.04** 建置(老 glibc 提升相容性),bundle 所有 .so + modules + 3 字型 + 遊戲資料:
```bash
docker build --build-arg CACHEBUST=1 -f dist/appimage/Dockerfile -t u4cht/appimage xu4
docker run --rm -v "$PWD/out":/out u4cht/appimage   # → out/u4-cht-x86_64.AppImage
chmod +x u4-cht-x86_64.AppImage && ./u4-cht-x86_64.AppImage          # 預設 Noto
U4CHT_FONT=firefly ./u4-cht-x86_64.AppImage                          # 宋體
```

## Windows zip(mingw 交叉編譯,含所有 DLL + 遊戲資料)
GLFW 後端 + 所有 mingw DLL + modules + 3 字型 + 遊戲資料:
```bash
docker build --build-arg CACHEBUST=1 -f dist/win/Dockerfile -t u4cht/win xu4
bash dist/win/make-zip.sh u4-cht-windows-x64.zip
# 解壓後雙擊 run.bat;字形:set U4CHT_FONT=firefly 再執行
```
含 DLL:glfw3 / libgcc_s_seh / libwinpthread / zlib1 / libpng16 / libogg / libvorbis(file) / libssp(libstdc++ 靜態連結)。
