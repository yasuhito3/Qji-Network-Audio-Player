#!/bin/bash
# ============================================================
# Qji 奏在 インストーラー
# ダブルクリック（または任意のターミナルで実行）で全自動セットアップ
# ============================================================

# --- ターミナル未起動の場合、利用可能なターミナルで自分自身を再起動 ---
if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    INSTALLER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    for term in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        if command -v "$term" &>/dev/null; then
            case "$term" in
                xfce4-terminal) exec "$term" --disable-server -T "Qji インストーラー" -e "bash $0" ;;
                lxterminal)     exec "$term" --title "Qji インストーラー" -e "bash $0" ;;
                mate-terminal)  exec "$term" --title "Qji インストーラー" -e "bash $0" ;;
                gnome-terminal) exec "$term" --title "Qji インストーラー" -- bash "$0" ;;
                konsole)        exec "$term" --title "Qji インストーラー" -e "bash $0" ;;
                qterminal)      exec "$term" -e "bash $0" ;;
                xterm)          exec "$term" -fa "Monospace" -fs 12 -title "Qji インストーラー" -geometry 90x40 -e bash "$0" ;;
            esac
        fi
    done
fi

# エラーが起きてもウィンドウを閉じずにメッセージを表示する
trap 'ec=$?; echo ""; echo "----------------------------------------"; echo "エラーが発生しました（終了コード: $ec）。"; echo "上のログを確認してください。"; echo "----------------------------------------"; read -rp "Enterキーで閉じます..." _; exit 1' ERR

QJI_DIR="$HOME/qji"
LOG_FILE="$HOME/qji_install_debug.log"
mkdir -p "$QJI_DIR"
exec > >(tee "$LOG_FILE") 2>&1
echo "（このインストールの全ログは $LOG_FILE に保存されます）"
echo ""
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null)"
[ -z "$DESKTOP_DIR" ] && DESKTOP_DIR="$HOME/Desktop"
INSTALLER_DIR="$(cd "$(dirname "$0")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    echo "  ╔══════════════════════════════════════════╗"
    echo "  ║        🎵 Qji 奏在 インストーラー         ║"
    echo "  ║   High-Fidelity Music Player for Linux   ║"
    echo "  ╚══════════════════════════════════════════╝"
    echo -e "${RESET}"
}

step() {
    echo -e "\n${CYAN}▶ $1${RESET}"
}

ok() {
    echo -e "  ${GREEN}✓ $1${RESET}"
}

warn() {
    echo -e "  ${YELLOW}⚠  $1${RESET}"
}

err() {
    echo -e "  ${RED}✗ $1${RESET}"
}

banner

echo -e "${BOLD}インストール先: ${QJI_DIR}${RESET}"
echo -e "このスクリプトは以下を行います:"
echo "  1. 必要なシステムパッケージのインストール"
echo "  2. Python パッケージのインストール"
echo "  3. ~/qji/ へファイルをコピー"
echo "  4. デスクトップアイコン（3個）の作成"
echo ""
read -rp "続行しますか？ [Y/n] " answer
case "$answer" in
    [nN]*) echo "インストールを中止しました。"; exit 0 ;;
esac

# ============================================================
# Step 1: システムパッケージ
# ============================================================
step "システムパッケージの確認・インストール"

APT_PACKAGES=(
    python3-pip python3-tk
    ffmpeg alsa-utils
    xterm
    feh
    python3-mutagen
    fonts-noto-cjk
    gmediarender
    gstreamer1.0-plugins-good
    gstreamer1.0-plugins-base
    shairport-sync
    avahi-daemon
    ufw
    libsndfile1
    sox
)

MISSING_APT=()
for pkg in "${APT_PACKAGES[@]}"; do
    if ! dpkg -l "$pkg" &>/dev/null; then
        MISSING_APT+=("$pkg")
    fi
done

if [ ${#MISSING_APT[@]} -gt 0 ]; then
    echo "  インストールするパッケージ: ${MISSING_APT[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y "${MISSING_APT[@]}"
    ok "システムパッケージをインストールしました"
else
    ok "必要なシステムパッケージはすべて導入済みです"
fi

# shairport-sync はパッケージ導入時に自動起動・自動有効化されることが多く、
# 出力デバイスを占有してQjiの再生が失敗する原因になるため無効化する。
# （Qji本体のAirPlayレシーバーアイコンから必要な時だけ起動する）
if systemctl list-unit-files 2>/dev/null | grep -q "^shairport-sync.service"; then
    sudo systemctl stop shairport-sync 2>/dev/null
    sudo systemctl disable shairport-sync 2>/dev/null
    ok "shairport-sync の自動起動を無効化しました（Qjiから必要時のみ起動）"
fi
if systemctl list-unit-files 2>/dev/null | grep -q "^gmediarender.service"; then
    sudo systemctl stop gmediarender 2>/dev/null
    sudo systemctl disable gmediarender 2>/dev/null
    ok "gmediarender の自動起動を無効化しました（Qjiから必要時のみ起動）"
fi

# sudo権限設定（visudo相当）
SUDOERS_FILE="/etc/sudoers.d/qji"
if [ ! -f "$SUDOERS_FILE" ]; then
    {
        echo "# Qji 奏在 — 自動生成 sudo 権限設定"
        echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/bluealsa-aplay"
        echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/bluealsad"
        echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/python3 $HOME/qji/qji.py"
        echo "$USER ALL=(ALL) NOPASSWD: /usr/sbin/modprobe"
    } | sudo tee "$SUDOERS_FILE" >/dev/null
    sudo chmod 440 "$SUDOERS_FILE"
    ok "sudo権限を設定しました ($SUDOERS_FILE)"
else
    ok "sudo権限は設定済みです"
fi

# ============================================================
# Step 2: Python パッケージ
# ============================================================
step "Python パッケージの確認・インストール"

PIP_PACKAGES=(
    mutagen
    requests
    yt-dlp
    ytmusicapi
    numpy
    librosa
    qobuz-dl
)

# オプション（音声認識 — 失敗しても継続）
OPTIONAL_PIP=(
    vosk
    sounddevice
)

pip3 install --quiet --break-system-packages "${PIP_PACKAGES[@]}" 2>/dev/null || \
    pip3 install --quiet "${PIP_PACKAGES[@]}"
ok "必須 Python パッケージをインストールしました"

for pkg in "${OPTIONAL_PIP[@]}"; do
    if pip3 install --quiet --break-system-packages "$pkg" 2>/dev/null || \
       pip3 install --quiet "$pkg" 2>/dev/null; then
        ok "オプション: $pkg"
    else
        warn "オプション $pkg はインストールできませんでした（音声認識は無効になります）"
    fi
done

# ============================================================
# Step 3: ファイルの配置
# ============================================================
step "ファイルを ~/qji/ へコピー"

mkdir -p "$QJI_DIR/sonia_intelligence"
mkdir -p "$QJI_DIR/scripts"

# メインスクリプト群
MAIN_FILES=(
    qji.py
    qji_qobuz.py
    qji_qobuz_browser.py
    qji_soundcloud.py
    qji_soundcloud_browser.py
    qji_ytmusic.py
    qji_ytmusic_browser.py
    audio_equalizer.py
    play_auto.sh
)

for f in "${MAIN_FILES[@]}"; do
    if [ -f "$INSTALLER_DIR/$f" ]; then
        cp "$INSTALLER_DIR/$f" "$QJI_DIR/"
        chmod +x "$QJI_DIR/$f"
        ok "$f"
    else
        warn "$f が見つかりません（スキップ）"
    fi
done

# Sonia Intelligence モジュール
SI_FILES=(
    acoustic_spaces.py
    genre_presets.py
    profile_db.py
    filter_builder.py
    audio_equalizer.py
)

for f in "${SI_FILES[@]}"; do
    if [ -f "$INSTALLER_DIR/sonia_intelligence/$f" ]; then
        cp "$INSTALLER_DIR/sonia_intelligence/$f" "$QJI_DIR/sonia_intelligence/"
        ok "sonia_intelligence/$f"
    elif [ -f "$INSTALLER_DIR/$f" ]; then
        cp "$INSTALLER_DIR/$f" "$QJI_DIR/sonia_intelligence/"
        ok "sonia_intelligence/$f（ルートからコピー）"
    else
        warn "sonia_intelligence/$f が見つかりません（スキップ）"
    fi
done

# アイコン画像をコピー
if [ -d "$INSTALLER_DIR/icons" ]; then
    cp -r "$INSTALLER_DIR/icons" "$QJI_DIR/"
    ok "アイコン画像"
fi

# ライブラリ解析スクリプトをコピー（存在する場合）
if [ -f "$INSTALLER_DIR/scripts/music_library_analyzer.py" ]; then
    cp "$INSTALLER_DIR/scripts/music_library_analyzer.py" "$QJI_DIR/scripts/"
    chmod +x "$QJI_DIR/scripts/music_library_analyzer.py"
    ok "music_library_analyzer.py"
else
    # 同梱されていない場合は最小版を生成
    cat > "$QJI_DIR/scripts/music_library_analyzer.py" << 'PYEOF'
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
music_library_analyzer.py
音楽ライブラリー解析ツール（Qji 奏在 付属）
"""
import os, sys, json
from pathlib import Path

try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3NoHeaderError
    MUTAGEN_OK = True
except ImportError:
    MUTAGEN_OK = False

AUDIO_EXTS = {".flac", ".mp3", ".wav", ".aac", ".m4a", ".ogg", ".opus", ".dsf", ".dff"}

def scan_library(root: str):
    root_path = Path(root).expanduser()
    if not root_path.exists():
        print(f"エラー: ディレクトリが見つかりません: {root_path}")
        return

    stats = {"total": 0, "genres": {}, "formats": {}, "errors": 0}
    print(f"\n🔍 スキャン中: {root_path}\n")

    for dirpath, dirnames, filenames in os.walk(root_path, onerror=lambda e: None):
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() not in AUDIO_EXTS:
                continue
            stats["total"] += 1
            fmt = path.suffix.lower()
            stats["formats"][fmt] = stats["formats"].get(fmt, 0) + 1

            if MUTAGEN_OK:
                try:
                    audio = MutagenFile(path, easy=True)
                    if audio:
                        genre = (audio.get("genre") or ["Unknown"])[0]
                        stats["genres"][genre] = stats["genres"].get(genre, 0) + 1
                except Exception:
                    stats["errors"] += 1

    print(f"📂 総ファイル数: {stats['total']}")
    print(f"\n🎵 フォーマット別:")
    for fmt, cnt in sorted(stats["formats"].items(), key=lambda x: -x[1]):
        print(f"   {fmt:8s} {cnt:5d} ファイル")
    if stats["genres"]:
        print(f"\n🎭 ジャンル別 (上位20):")
        for genre, cnt in sorted(stats["genres"].items(), key=lambda x: -x[1])[:20]:
            bar = "█" * min(40, cnt // max(1, stats["total"] // 100))
            print(f"   {genre[:30]:30s} {cnt:5d}  {bar}")
    print(f"\n⚠  エラー: {stats['errors']} ファイル")

if __name__ == "__main__":
    library_path = sys.argv[1] if len(sys.argv) > 1 else "~/Music"
    scan_library(library_path)
    print("\n解析完了。Enterキーで閉じます...")
    input()
PYEOF
    chmod +x "$QJI_DIR/scripts/music_library_analyzer.py"
    ok "music_library_analyzer.py（最小版を生成）"
fi

if [ -f "$INSTALLER_DIR/scripts/setup_network_ports.sh" ]; then
    cp "$INSTALLER_DIR/scripts/setup_network_ports.sh" "$QJI_DIR/scripts/"
    chmod +x "$QJI_DIR/scripts/setup_network_ports.sh"
    ok "setup_network_ports.sh"
fi

for f in setup_audio_loopback.sh gmediarender_launcher.sh airplay_launcher.sh qji_start.sh build_library_db.sh setup_bubbleupnp.sh equalizer_start.sh; do
    if [ -f "$INSTALLER_DIR/scripts/$f" ]; then
        cp "$INSTALLER_DIR/scripts/$f" "$QJI_DIR/scripts/"
        chmod +x "$QJI_DIR/scripts/$f"
        ok "$f"
    fi
done

# ============================================================
# Step 4: デスクトップアイコンの作成
# ============================================================
step "デスクトップアイコンの作成"

mkdir -p "$DESKTOP_DIR"

# --- 利用可能なターミナルを自動検出 ---
TERM_CMD=""
TERM_EXEC_OPT="-e"
for term in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
    if command -v "$term" &>/dev/null; then
        TERM_BIN="$term"
        case "$term" in
            xfce4-terminal) TERM_CMD="$term --disable-server -T" ; TERM_EXEC_OPT="-x" ;;
            lxterminal)     TERM_CMD="$term --title" ; TERM_EXEC_OPT="-e" ;;
            mate-terminal)  TERM_CMD="$term --title" ; TERM_EXEC_OPT="-e" ;;
            gnome-terminal) TERM_CMD="$term --title" ; TERM_EXEC_OPT="--" ;;
            konsole)        TERM_CMD="$term --title" ; TERM_EXEC_OPT="-e" ;;
            qterminal)      TERM_CMD="$term" ; TERM_EXEC_OPT="-e" ;;
            xterm)          TERM_CMD="$term -fa Monospace -fs 12 -title" ; TERM_EXEC_OPT="-e" ;;
        esac
        break
    fi
done
[ -z "$TERM_CMD" ] && TERM_CMD="xterm -fa Monospace -fs 12 -title" && TERM_EXEC_OPT="-e"
ok "ターミナル: $TERM_BIN"

# --- アイコン画像パスの解決 ---
ICON_QJI="$QJI_DIR/icons/qji.png"
ICON_LIBRARY="$QJI_DIR/icons/music_library.png"
ICON_EQ="$QJI_DIR/icons/equalizer.png"
ICON_NET="$QJI_DIR/icons/installer.png"

# フォールバック: システムアイコン
[ -f "$ICON_QJI" ]     || ICON_QJI="audio-x-generic"
[ -f "$ICON_LIBRARY" ] || ICON_LIBRARY="folder-music"
[ -f "$ICON_EQ" ]      || ICON_EQ="multimedia-volume-control"
[ -f "$ICON_NET" ]     || ICON_NET="network-wired"

# --- 0. 音源ライブラリーDB構築（最初に実行推奨） ---
cat > "$DESKTOP_DIR/①音源ライブラリー構築.desktop" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=①音源ライブラリー構築
Name[ja]=①音源ライブラリー構築
GenericName=Build Music Library DB
Comment=music_mood_db.json を構築（Qji初回起動前に実行推奨）
Exec=$TERM_CMD "🗄 音源ライブラリー構築" $TERM_EXEC_OPT bash "$QJI_DIR/scripts/build_library_db.sh"
Icon=${ICON_LIBRARY}
Terminal=false
StartupNotify=false
Categories=Audio;Music;Utility;
Keywords=library;database;mood;genre;Qji;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/①音源ライブラリー構築.desktop"
ok "①音源ライブラリー構築.desktop"

# --- 1. Qji 奏在 ---
cat > "$DESKTOP_DIR/Qji奏在.desktop" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Qji 奏在
Name[ja]=Qji 奏在
GenericName=High-Fidelity Music Player
Comment=ハイファイ音楽プレーヤー（ターミナル操作）
Comment[ja]=ハイファイ音楽プレーヤー
Exec=$TERM_CMD "🎵 Qji 奏在" $TERM_EXEC_OPT bash "$QJI_DIR/scripts/qji_start.sh"
Icon=${ICON_QJI}
Terminal=false
StartupNotify=false
Categories=Audio;Player;Music;
Keywords=music;player;hifi;jazz;classical;Qji;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/Qji奏在.desktop"
ok "Qji奏在.desktop"

# --- 2. オーディオイコライザー ---
cat > "$DESKTOP_DIR/オーディオイコライザー.desktop" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=オーディオイコライザー
Name[ja]=オーディオイコライザー
GenericName=Audio Equalizer Pro
Comment=Qji 奏在 連携イコライザー（FIFO経由）
Exec=bash "$QJI_DIR/scripts/equalizer_start.sh"
Icon=${ICON_EQ}
Terminal=false
StartupNotify=false
Categories=Audio;Mixer;Utility;
Keywords=equalizer;EQ;audio;Qji;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/オーディオイコライザー.desktop"
ok "オーディオイコライザー.desktop"

# --- 4. ネットワーク設定（AirPlay/DLNA） ---
cat > "$DESKTOP_DIR/ネットワーク設定(AirPlay-DLNA).desktop" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=ネットワーク設定 (AirPlay/DLNA)
Name[ja]=ネットワーク設定 (AirPlay/DLNA)
GenericName=Network Port Setup
Comment=AirPlay・gmediarender用ポートをufwで開放
Exec=bash $QJI_DIR/scripts/setup_network_ports.sh
Icon=${ICON_NET}
Terminal=false
StartupNotify=false
Categories=System;Network;
Keywords=AirPlay;DLNA;UPnP;ufw;firewall;Qji;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/ネットワーク設定(AirPlay-DLNA).desktop"
ok "ネットワーク設定(AirPlay-DLNA).desktop"

# --- 5. オーディオ基盤セットアップ ---
cat > "$DESKTOP_DIR/オーディオ基盤セットアップ.desktop" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=オーディオ基盤セットアップ
Name[ja]=オーディオ基盤セットアップ
GenericName=Audio Loopback Setup
Comment=ALSAループバックと出力DACデバイスを設定（初回必須）
Exec=bash $QJI_DIR/scripts/setup_audio_loopback.sh
Icon=${ICON_NET}
Terminal=false
StartupNotify=false
Categories=System;Audio;
Keywords=ALSA;loopback;DAC;Qji;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/オーディオ基盤セットアップ.desktop"
ok "オーディオ基盤セットアップ.desktop"

# --- 6. gmediarenderレシーバー ---
cat > "$DESKTOP_DIR/gmediarenderレシーバー.desktop" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=gmediarenderレシーバー
Name[ja]=gmediarenderレシーバー
GenericName=UPnP-DLNA Receiver
Comment=スマホ等からのUPnP/DLNAキャストをMusikverein処理して再生
Exec=bash $QJI_DIR/scripts/gmediarender_launcher.sh
Icon=${ICON_LIBRARY}
Terminal=false
StartupNotify=false
Categories=Audio;Network;
Keywords=UPnP;DLNA;gmediarender;Qji;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/gmediarenderレシーバー.desktop"
ok "gmediarenderレシーバー.desktop"

# --- BubbleUPnP Server ---
cat > "$DESKTOP_DIR/BubbleUPnPサーバー.desktop" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=BubbleUPnP Server
Name[ja]=BubbleUPnP Server
GenericName=UPnP Bridge Server
Comment=gmediarender をスマホからコントロールするUPnPブリッジ
Exec=$TERM_CMD "📡 BubbleUPnP Server" $TERM_EXEC_OPT bash "$QJI_DIR/scripts/setup_bubbleupnp.sh"
Icon=${ICON_NET}
Terminal=false
StartupNotify=false
Categories=Audio;Network;
Keywords=BubbleUPnP;UPnP;DLNA;gmediarender;Qji;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/BubbleUPnPサーバー.desktop"
ok "BubbleUPnPサーバー.desktop"

# --- 7. AirPlayレシーバー ---
cat > "$DESKTOP_DIR/AirPlayレシーバー.desktop" << DESKTOP_EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=AirPlayレシーバー
Name[ja]=AirPlayレシーバー
GenericName=AirPlay Receiver
Comment=iPhone/MacからのAirPlay音声をMusikverein処理して再生
Exec=bash $QJI_DIR/scripts/airplay_launcher.sh
Icon=${ICON_QJI}
Terminal=false
StartupNotify=false
Categories=Audio;Network;
Keywords=AirPlay;shairport;Qji;
DESKTOP_EOF
chmod +x "$DESKTOP_DIR/AirPlayレシーバー.desktop"
ok "AirPlayレシーバー.desktop"

# Xubuntu XFCE でアイコンを「信頼済み」かつ実行可能に設定
for desktop_file in "①音源ライブラリー構築" "Qji奏在" "オーディオイコライザー" "ネットワーク設定(AirPlay-DLNA)" "オーディオ基盤セットアップ" "gmediarenderレシーバー" "BubbleUPnPサーバー" "AirPlayレシーバー"; do
    f="$DESKTOP_DIR/${desktop_file}.desktop"
    chmod +x "$f"
    gio set "$f" metadata::trusted true 2>/dev/null || true
    # XFCEバージョンによってはこの属性が必要
    gio set "$f" "metadata::xfce-exe-checksum" "$(sha256sum "$f" | cut -d' ' -f1)" 2>/dev/null || true
done

# デスクトップ表示を再読込
xfdesktop --reload 2>/dev/null || true

# ============================================================
# 完了
# ============================================================
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${GREEN}${BOLD}  ✅ Qji 奏在のインストールが完了しました！${RESET}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""
echo "  インストール先: $QJI_DIR"
echo ""
echo "  デスクトップに作成されたアイコン:"
echo "    🗄 ①音源ライブラリー構築 — 最初に実行推奨(music_mood_db.json)"
echo "    🎵 Qji 奏在          — メインプレーヤー起動"
echo "    🎚️ オーディオイコライザー — EQ GUI 起動"
echo "    🌐 ネットワーク設定 — AirPlay/DLNA用ポート開放(ufw)"
echo "    🔧 オーディオ基盤セットアップ — ALSAループバック設定(初回必須)"
echo "    📡 gmediarenderレシーバー — UPnP/DLNA受信"
echo "    🌐 BubbleUPnP Server    — スマホからのUPnPコントロール"
echo "    📱 AirPlayレシーバー — AirPlay受信"
echo ""
echo -e "  ${YELLOW}★ 初回は必ず「🔧 オーディオ基盤セットアップ」を"
echo -e "    一度実行してから AirPlay/gmediarender をお使いください。${RESET}"
echo ""
echo -e "  ${YELLOW}ヒント: 音楽フォルダのパスは qji.py 内の"
echo -e "  MUSIC_DIR 変数で変更できます。${RESET}"
echo ""
read -rp "Enterキーを押してウィンドウを閉じます..." _
