#!/usr/bin/env sh
# 拷贝 CosyVoice 产出的音频（与字幕）到 assets/audio/，作为生成视频前的素材预备步骤。
# generate.py 默认从 config.yaml 的 media.audio 目录读取音频（默认 assets/audio）。
# 源目录取 .env 里的 COSYVOICE_OUTPUT（也可用同名环境变量覆盖）。
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
SRC=${COSYVOICE_OUTPUT:-$(sed -n 's/^COSYVOICE_OUTPUT=//p' "$ROOT/.env" 2>/dev/null | head -1)}
DEST="$ROOT/assets/audio"

# 必需文件：generate.py 依赖的音频
REQUIRED="audio.wav"
# 可选文件：存在则一并同步（供后续字幕/校对使用）
OPTIONAL="audio.srt"

[ -n "$SRC" ] || { echo "未配置 COSYVOICE_OUTPUT（请在 .env 或环境变量中指定源目录）" >&2; exit 1; }
[ -d "$SRC" ] || { echo "源目录不存在：$SRC" >&2; exit 1; }

# 先校验齐全再拷贝，避免出现半套资源
for f in $REQUIRED; do
  [ -f "$SRC/$f" ] || { echo "缺少源文件：$SRC/$f" >&2; exit 1; }
done

synced=""
for f in $REQUIRED; do
  cp "$SRC/$f" "$DEST/$f"
  synced="$synced $f"
done

for f in $OPTIONAL; do
  if [ -f "$SRC/$f" ]; then
    cp "$SRC/$f" "$DEST/$f"
    synced="$synced $f"
  fi
done

echo "已同步：$synced -> $DEST"
