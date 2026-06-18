# セキュリティとリスクについて（必ずお読みください）

Qji 奏在をインストール・実行する前に、本ソフトウェアが何を行うか、
どのようなリスクがあるかをご理解いただくことを強くお勧めします。

## このインストーラーが行うこと

`install.sh` は以下の操作を **sudo権限を使って** 行います。

1. **システムパッケージの追加**（`apt-get install`）
   ffmpeg, alsa-utils, xterm, python3-tk, gmediarender, shairport-sync,
   avahi-daemon, ufw, libsndfile1, sox など

2. **sudoers設定ファイルの作成**（`/etc/sudoers.d/qji`）
   以下のコマンドをパスワード入力なしで実行できるようにします:
   - `/usr/bin/bluealsa-aplay`
   - `/usr/bin/bluealsad`
   - `/usr/bin/python3 ~/qji/qji.py`
   - `/usr/sbin/modprobe`

3. **カーネルモジュールの自動ロード設定**（`/etc/modules-load.d/`, `/etc/modprobe.d/`）
   ALSAループバック（snd-aloop）を起動時に自動ロードします。

4. **systemdサービスの登録・無効化**
   - shairport-sync / gmediarender の自動起動を無効化（Qjiが必要時に手動起動するため）
   - BubbleUPnP Server のインストール時、自動起動を有効化（任意選択）

5. **ファイアウォール設定の変更**（`ufw allow`）
   AirPlay/DLNA関連のポートをローカルLANサブネットに限定して開放します。

6. **ホームディレクトリへのファイル書き込み**
   `~/qji/`, `~/.config/qji_*.json`, `~/music_mood_db.json`,
   `~/.qji_library_scanned`, デスクトップへの `.desktop` ファイル作成

## 既知のリスクと注意点

### sudoers設定について
`/etc/sudoers.d/qji` の追加は、上記4コマンドに限定したパスワードなし実行権限です。
ただし `modprobe` への無条件のNOPASSWD権限は、理論上は任意のカーネルモジュールを
ロードできてしまうため、セキュリティを重視する環境では **この行を削除し、
必要時にパスワードを入力する運用** に変更することを推奨します。

```bash
sudo visudo -f /etc/sudoers.d/qji
# /usr/sbin/modprobe の行を削除またはコメントアウト
```

### サードパーティAPIキーについて
- Qobuz / SoundCloud / YouTube Music への接続には、各サービスの認証情報
  （トークン、Cookie等）をご自身で取得し、ローカルの設定ファイル
  （`~/.config/` 以下）に保存する形を取っています。これらの認証情報は
  本リポジトリのコードには一切含まれていません。
- Last.fm APIキーも同様に `~/.config/qji_lastfm.json` にローカル保存します。
  未設定でも動作しますが、その場合はムード検出の精度が下がります。

### 外部ネットワークアクセス
- ラジオストリーミング再生時、YouTube Music / SoundCloud / Qobuz の
  API・CDNサーバーへ直接通信します。
- ライブラリー構築時、Last.fm / MusicBrainz の公開APIへ通信します
  （APIキー未設定時はローカルタグ情報のみで動作し、通信は発生しません）。
- BubbleUPnP Serverは公式サイトから直接 `.deb` パッケージをダウンロードします。

### 自己責任での利用
本ソフトウェアは個人の音楽鑑賞用途を目的に開発されたものであり、
商用環境や共有マシンでの利用、セキュリティ要件の厳しい環境での利用は
推奨しません。`install.sh` の内容を実行前に確認することを強く推奨します。

```bash
less install.sh  # 実行前に内容を確認できます
```

## アンインストール

付属の `uninstall.sh` で `~/qji/` とデスクトップアイコンを削除できます。
ただし以下は手動削除が必要です（意図的に自動削除の対象外としています）。

```bash
sudo rm /etc/sudoers.d/qji
sudo rm /etc/systemd/system/bluealsa.service       # 作成した場合
sudo rm /etc/systemd/system/bubbleupnpserver.service  # 作成した場合
sudo rm /etc/modules-load.d/qji-aloop.conf
sudo rm /etc/modprobe.d/qji-aloop.conf
sudo apt-get remove bubbleupnpserver  # BubbleUPnP Serverを削除する場合
```

## 質問・不安な点がある場合

GitHub Issuesにてお気軽にご質問ください。インストール前にコードを読んで
判断したいという方のために、`install.sh` および各 `scripts/*.sh` は
平易なbashスクリプトで記述されており、特殊な難読化は行っていません。
