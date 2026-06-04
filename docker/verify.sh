#!/bin/bash
# #1 實機驗證:xdotool 驅動 xu4,截「主選單」與「新遊戲流程」畫面。
# 用真實遊玩路徑驗證 #4(選單)/ H1+#3(對話/訊息)hook,非 self-test。
set -u
export DISPLAY=:99 LIBGL_ALWAYS_SOFTWARE=1 GALLIUM_DRIVER=llvmpipe ALLEGRO_AUDIO_DRIVER=none
SCALE="${1:-3}"
W=$((320 * SCALE)); H=$((200 * SCALE))

Xvfb :99 -screen 0 ${W}x${H}x24 -ac +extension GLX +render -noreset >/out/xvfb.log 2>&1 &
sleep 2
cd /build/xu4
echo "+ ./src/xu4 -q -v -s $SCALE --filter xBRZ" >/out/xu4.log
./src/xu4 -q -v -s "$SCALE" --filter xBRZ >>/out/xu4.log 2>&1 &
XU4=$!

key() { xdotool key --clearmodifiers "$1" 2>/dev/null; sleep "${2:-1}"; }
typ() { xdotool type --clearmodifiers "$1" 2>/dev/null; sleep 1; }
shot() { import -window root "/out/$1" 2>/dev/null && echo "shot $1 OK" || echo "shot $1 FAIL"; }

# 1) 等 intro 動畫跑到主選單(約 25-30s),截主選單
sleep 30
key Return 1
shot menu.png

# 2) 開始新遊戲:主選單熱鍵 i = Initiate New Game
key i 2
shot newgame_q1.png            # gypsy 第一題(美德問答)
# 答幾題(a/b 任選),推進角色創建
for k in b a b a b a b; do key "$k" 1; done
shot after_quiz.png
# 命名 + 確認
typ "Avatar"; key Return 2
shot named.png
# 進入世界後等一下,截畫面(可能有 location/訊息)
sleep 3
key Return 1
shot ingame.png

kill "$XU4" 2>/dev/null
echo "--- xu4.log tail ---"; tail -12 /out/xu4.log
ls -la /out/*.png
