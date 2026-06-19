# 🎵 Qji 奏在 — インストールパッケージ

**高音質ターミナル音楽プレーヤー for Ubuntu/Debian系 Linux**  
オーディオシステム ならびに　デスクトップオーディオ　向け音響処理システム

`Sonia Intelligence` による音響空間シミュレーション（Musikverein, Concertgebouw,
Carnegie Hall 等）を、ffmpeg + ALSA直接出力で実現する個人開発プロジェクトです。

対応OS: Xubuntu 24.04 / 26.04 · Linux Mint · SparkyLinux（他のUbuntu/Debian系も動作する可能性あり）  
ライセンス: [MIT](./LICENSE)（サードパーティ依存あり、詳細はLICENSE参照）  
インストール前に: [セキュリティとリスクについて](./SECURITY.md) を一読ください

---

## 📦 パッケージ内容

```
Qji_installer/
├── install.sh                    ← メインインストーラー
├── インストール.desktop           ← ダブルクリック起動用
├── LICENSE                       ← ライセンス（MIT + サードパーティ表記）
├── SECURITY.md                   ← セキュリティ・リスクについて
├── qji.py                        ← メインプレーヤー
├── qji_qobuz.py                  ← Qobuz ストリーミング
├── qji_qobuz_browser.py          ← Qobuz ブラウザUI
├── qji_soundcloud.py             ← SoundCloud
├── qji_soundcloud_browser.py     ← SoundCloud ブラウザUI
├── qji_ytmusic.py                ← YouTube Music
├── qji_ytmusic_browser.py        ← YouTube Music ブラウザUI
├── audio_equalizer.py            ← GUIイコライザー
├── play_auto.sh                  ← 自動再生スクリプト
├── run_installer.sh              ← インストーラー検索・起動ブートストラップ
├── uninstall.sh                  ← アンインストーラー
├── sonia_intelligence/
│   ├── acoustic_spaces.py        ← 音響空間モデル
│   ├── genre_presets.py          ← ジャンルプリセット
│   ├── profile_db.py             ← プロファイルDB
│   └── filter_builder.py        ← ffmpegフィルター構築
├── scripts/
│   ├── qji_start.sh              ← Qji起動ラッパー（ロゴ表示・案内）
│   ├── build_library_db.sh       ← ①音源ライブラリー構築
│   ├── music_library_analyzer.py ← ライブラリー解析エンジン
│   ├── equalizer_start.sh        ← イコライザー起動ラッパー
│   ├── setup_audio_loopback.sh   ← ALSAループバック設定
│   ├── gmediarender_launcher.sh  ← UPnP/DLNAレシーバー
│   ├── airplay_launcher.sh       ← AirPlayレシーバー
│   ├── setup_bubbleupnp.sh       ← BubbleUPnP Server導入
│   └── setup_network_ports.sh    ← ufwポート開放
├── config_examples/
│   └── qji_lastfm.json.example   ← Last.fm APIキー設定テンプレート
└── icons/
    ├── qji.png / qji_logo.png
    ├── music_library.png
    ├── equalizer.png
    └── installer.png
```

---

## 🚀 インストール手順

### 方法A: ダブルクリック（推奨）
1. `インストール.desktop` をダブルクリック
2. ターミナルウィンドウが開く
3. 画面の指示に従って `Y` を入力

### 方法B: ターミナルから（方法Aがうまくゆかなかったとき）
```bash
cd ~/ダウンロード/Qji_installer
bash install.sh
```

---

## 🖥️ デスクトップアイコン（インストール後）

| アイコン | 機能 |
|---------|------|
| 🗄 **①音源ライブラリー構築** | 音楽ファイルのタグ解析・ムード判定・`music_mood_db.json`構築（初回推奨） |
| 🎵 **Qji 奏在** | メインプレーヤー（ターミナル操作） |
| 🎚️ **オーディオイコライザー** | GUIイコライザー（Qji と FIFO 連携） |
| 🌐 **ネットワーク設定** | AirPlay/DLNA用ポートをufwで開放（LAN限定） |
| 🔧 **オーディオ基盤セットアップ** | ALSAループバック設定・出力DAC検出（**初回必須**） |
| 📡 **gmediarenderレシーバー** | スマホ等からのUPnP/DLNAキャストを受信・Musikverein処理 |
| 🌐 **BubbleUPnP Server** | gmediarender をスマホからコントロールするUPnPブリッジ |
| 📱 **AirPlayレシーバー** | iPhone/MacからのAirPlayを受信・Musikverein処理 |

---

## 📚 音源ライブラリーの構築について

「①音源ライブラリー構築」は`~/qji/scripts/music_library_analyzer.py`を実行し、
音楽ファイルのタグ・ジャンル・ムードを解析して`~/music_mood_db.json`を作成します。
これがあるとQjiのランダム再生（ジャンル均等インターリーブ）の精度が上がります。

未実行でもQjiは起動できますが、その場合は空のDBから始まります。
スキャン対象フォルダ（`~/Music`、`~/ミュージック`、`/media/`、`/run/media/`配下、
`/mnt`、GVFSマウント等）は実行時に自動検出されます。

---

---

## 📡 BubbleUPnP Server の設定

BubbleUPnP Serverは、gmediarender（UPnP/DLNAレンダラー）をスマートフォンアプリから簡単にコントロールできるようにするブリッジサーバーです。

公式ドキュメント: https://bubblesoftapps.com/bubbleupnpserver2/docs/linux_install.html

### インストール方法

デスクトップの「🌐 BubbleUPnP Server」アイコンをクリックすると自動インストールされます。手動でインストールする場合:

```bash
wget https://bubblesoftapps.com/bubbleupnpserver/bubbleupnpserver_0.9-8_all.deb
sudo apt-get install ./bubbleupnpserver_0.9-8_all.deb
rm bubbleupnpserver_0.9-8_all.deb
```

> ⚠ 旧PPA版がインストール済みの場合は先に削除してください:
> ```bash
> sudo apt-get remove bubbleupnpserver
> sudo rm -rf /root/.bubbleupnpserver
> sudo add-apt-repository --remove ppa:bubbleguuum/bubbleupnpserver
> ```

### セットアップ手順

1. **「📡 gmediarenderレシーバー」を先に起動**（「Qji Player」がUPnPレンダラーとして起動）
2. **「🌐 BubbleUPnP Server」をダブルクリック**（debパッケージを自動ダウンロード・インストール、ポート58050開放）
3. **ブラウザで `http://localhost:58050` を開く**（「Devices」タブで「Qji Player」が見えればOK）
4. **スマホのBubbleUPnPアプリから `http://PCのIPアドレス:58050` に接続**
5. **レンダラーとして「Qji Player」を選択して再生**

### 信号の流れ
```
スマホ（BubbleUPnPアプリ）
    ↓ UPnP コントロール
BubbleUPnP Server（ポート58050）
    ↓ 再生指示
gmediarender（Qji Player）
    ↓ ALSAループバック
ffmpeg（Musikverein音響処理）
    ↓
DAC → アンプ → スピーカー
```

### 注意事項
- gmediarenderを先に起動してからBubbleUPnP Serverを起動してください
- PCとスマホが同じLANに接続されている必要があります
- バージョンは変わる場合があります。最新版は公式サイトをご確認ください

---

## ⚙️ 初回セットアップ順序

1. `インストール.desktop` をダブルクリック → `install.sh` 実行（全パッケージ導入）
2. 🔧 **オーディオ基盤セットアップ** を実行
   - `snd-aloop`（ALSAループバック）を有効化・永続化
   - 接続中のUSB DAC等を検出し `~/qji/.audio_devices` に保存
   - **再起動を推奨**（snd-aloopの自動ロードを反映するため）
3. 🌐 **ネットワーク設定** を実行（AirPlay/DLNAを使う場合）
4. 🎵 Qji本体、または 📡/📱 レシーバーを起動

`~/qji/.audio_devices` の内容は手動編集も可能です:
```
OUTPUT_DEVICE=hw:2,0       # DAC出力
LOOPBACK_IN=hw:1,1,0       # gmediarender/AirPlayの入力先
LOOPBACK_OUT=hw:1,0,0      # ffmpegが読み取る側
```

---

## ⚙️ インストールされるもの

### システムパッケージ（apt）
- `ffmpeg` — 音響処理エンジン
- `aplay` / `alsa-utils` — ALSA 直接出力
- `xterm` — ターミナルエミュレーター
- `feh` — アルバムアート表示
- `python3-tk` — GUIイコライザー用
- `fonts-noto-cjk` — 日本語フォント

### Python パッケージ（pip）
- `mutagen` — 音楽ファイルタグ読み込み
- `requests` — HTTP通信
- `yt-dlp` — YouTube音声ストリーミング
- `ytmusicapi` — YouTube Music検索・ライブラリ連携
- `qobuz-dl` — Qobuz app_secret自動取得用
- `numpy` / `librosa` — ライブラリー構築時のテンポ・音響特徴解析
- `vosk` + `sounddevice` — 音声認識（オプション、失敗しても他機能に影響なし）

### Last.fm（オプション・ムード検出強化）
`~/.config/qji_lastfm.json` を作成:
```json
{"api_key": "あなたのAPIキー"}
```
取得: https://www.last.fm/api/account/create
未設定でもライブラリー構築は動作します（ムード検出の精度が下がるだけです）。

---

## ▶️ YouTube Music の設定（オプション）

「いいね」した曲やライブラリにアクセスしたい場合、初回に以下を実行してブラウザ認証を行ってください:

```bash
python3 -c "from ytmusicapi import YTMusic; YTMusic.setup(filepath='~/.config/qji_ytmusic_auth.json')"
```

認証なしでも yt-dlp 経由の検索・再生は可能です。

---

## 🎛️ 初期設定

### 音楽フォルダの場所
`~/qji/qji.py` 冒頭の `MUSIC_DIRS` リストに、スキャン対象フォルダが
複数列挙されています（`~/Music`、`~/ミュージック`、`/media`、`/run/media/$USER`、
`/mnt`、デスクトップ等）。標準的な場所に音楽ファイルを置いていれば
編集不要ですが、特殊な場所に置く場合はこのリストに追加してください。

```python
MUSIC_DIRS = [
    os.path.expanduser('~/Music'),
    os.path.expanduser('~/ミュージック'),
    '/media',
    f'/run/media/{os.getenv("USER")}',
    '/mnt',
    # 必要に応じて追加
]
```

### 出力デバイス（DAC）
Qji起動時に対話形式でサウンドカードを選択できます（`aplay -l` の結果から
選ぶ形式）。一度選択すると設定が保存され、次回以降は自動的にそのデバイスが
使われます。デバイス番号は環境によって変わるため、ハードコードは不要です。

---

## 🔑 ストリーミングサービスの設定

### Qobuz
初回、Qjiのメニューから Qobuz 機能を選ぶと、対話形式で以下の入力を求められます。

- `X-User-Auth-Token`（Qobuzアカウントのログイントークン）
- `X-App-Id`

`app_secret` は `qobuz-dl` ライブラリ経由で自動取得を試みます
（取得できない場合は手動入力を求められます）。入力した内容は
`~/.config/` 以下にローカル保存され、次回以降は再入力不要です。

取得方法の詳細は、Qji内のQobuzメニュー表示の案内に従ってください
（ブラウザの開発者ツールでヘッダーを確認する方法が一般的です）。

### SoundCloud / YouTube Music
初回起動時に認証を求められます（SoundCloudはclient_id自動取得、
YouTube Musicは`ytmusicapi`のブラウザ認証セットアップが利用できます）。

---

## 📝 操作キー（Qji メインプレーヤー）

| キー | 機能 |
|-----|------|
<<<<<<< HEAD
| `n` / `b` | 次の曲 / 前の曲 |
=======
| `→` / `←` | 次の曲 / 前の曲 |
>>>>>>> 506f0c0f5e0721a748f33bfd746b28c4584c81c4
| `+` / `-` | 音量上げ / 下げ |
| `c` | 音場プリセット切替（Musikverein 等） |
| `g` | ゲインプリセット切替 |
| `q` | 終了 |

---

## 💡 動作確認済み環境

- **OS**: Xubuntu 24.04 / Xubuntu 26.04 / Linux Mint（最新版） / SparkyLinux（最新安定版）
- **デスクトップ環境**: XFCE
- **Python**: 3.10 / 3.11 / 3.12
- **ターミナル**: xfce4-terminal / xterm / lxterminal / mate-terminal / gnome-terminal / konsole / qterminal（自動検出）
- **DAC**: Amanero Combo384 USB DAC
- **Amp**: Mark Levinson
- **Speaker**: Vienna Acoustics

その他のUbuntu/Debian系ディストリビューションでも基本的に動作する見込みですが、
未検証です。動作報告はIssueやPull Requestで歓迎します。

---

## 🔒 セキュリティとリスクについて

インストール時にsudo権限で行われる操作（sudoers設定、システムサービスの
変更、ファイアウォール設定など）について詳しく知りたい方は
[SECURITY.md](./SECURITY.md) をご確認ください。

---

## ⚠️ 注意事項

- ALSA 直接出力のため、PulseAudio の干渉がある場合は  
  `pulseaudio --kill` で停止してください
- `hw:X,0` のデバイス番号は `aplay -l` で確認してください
- Vosk 音声認識モデルは別途ダウンロードが必要です

---

## 🤝 コントリビューション・動作報告

未検証の環境での動作報告、バグ報告、プルリクエストを歓迎します。詳細は
[CONTRIBUTING.md](./CONTRIBUTING.md) をご覧ください。

---

*Qji 奏在 — Sonia Intelligence System 搭載*  
*Musikverein · Concertgebouw · Carnegie Hall 音響シミュレーション*
