# Ultima IV CHT — Windows(mingw64 交叉編譯,GLFW 後端)
# context = xu4/(patched source);產出 /work/u4/xu4.exe + 收集 DLL 到 /work/dll
FROM fedora:41
RUN dnf -y install bzip2 diffutils git make tree unzip findutils curl tar \
      mingw64-gcc-c++ mingw64-zlib mingw64-zlib-static mingw64-libogg \
      mingw64-libvorbis mingw64-libpng mingw64-freetype

# boron 程式(linux 靜態)+ copr build tool
RUN curl -sSL -o /usr/bin/boron http://urlan.sourceforge.net/boron/static/boron-2.1.0-Linux.x86_64 \
 && chmod +x /usr/bin/boron \
 && curl -sSL -o /usr/local/bin/copr "https://sourceforge.net/p/urlan/boron/code/ci/v2.1.0/tree/scripts/copr.b?format=raw" \
 && chmod +x /usr/local/bin/copr

WORKDIR /work
# mingw SDK:glfw / boron / faun
RUN curl -sSL -o glfw.zip  https://github.com/glfw/glfw/releases/download/3.4/glfw-3.4.bin.WIN64.zip \
 && curl -sSL -o boron.zip http://xu4.sourceforge.net/download/boron-x86_64-w64-mingw32-static-2.0.8.zip \
 && curl -sSL -o faun.zip  https://codeberg.org/WickedSmoke/faun/releases/download/v0.2.2/faun-x86_64-w64-mingw32-static-0.2.2.zip \
 && unzip -q glfw.zip && mv glfw-3.4.bin.WIN64 usr && mv usr/lib-mingw-w64 usr/lib \
 && unzip -q boron.zip \
 && unzip -q faun.zip -d usr \
 && echo "=== usr/lib ===" && ls usr/lib | head -20

ARG CACHEBUST=1
COPY . /work/u4
WORKDIR /work/u4
RUN mkdir -p .copr/obj /root/.cache/copr && yes a | boron /usr/local/bin/copr -t mingw "os_api:'glfw" make_util:false > /work/copr.log 2>&1 || true; ls -la xu4.exe 2>/dev/null || echo NO_EXE; echo "=====COPR====="; tail -45 /work/copr.log

# 收集 DLL(mingw sysroot + glfw + faun)
RUN set -e; mkdir -p /work/dll; \
    SYS=/usr/x86_64-w64-mingw32/sys-root/mingw/bin; \
    for d in libgcc_s_seh-1.dll libstdc++-6.dll libwinpthread-1.dll zlib1.dll \
             libpng16-16.dll libogg-0.dll libvorbis-0.dll libvorbisfile-3.dll libssp-0.dll; do \
      cp "$SYS/$d" /work/dll/ 2>/dev/null || echo "miss $d"; \
    done; \
    find /work/usr -iname 'glfw3.dll' -exec cp {} /work/dll/ \; 2>/dev/null || true; \
    find /work/usr -iname 'faun*.dll' -exec cp {} /work/dll/ \; 2>/dev/null || true; \
    echo "=== DLL ===" && ls /work/dll

CMD ["bash","-c","cp /work/u4/xu4.exe /work/dll/*.dll /out/ 2>/dev/null; echo done"]
