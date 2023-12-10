# ibus-jig: Japanese-language Input-method using GPT-4
ibus-jigは、変換ごとにOpenAI APIを呼び出してGPT-4でかな漢字変換を行うことが特徴の、Linux環境で動作する日本語IMEです。

![Writing Japanese text using ibus-jig](https://github.com/y-koj/ibus-jig/assets/119405103/1c78f7a5-5999-4f3d-b030-c11e26a3dc8a)

## 実行・インストール方法
ibus-jigの実行には、OSにインストールしてIMEとして利用する方法と、
`engine/main.py`を実行してOSにインストールせずに試す方法があります。  
まずはインストールせずに試してみることをおすすめします。

### Prerequisites
ibus-jigを実行するには、以下の条件を満たした環境を用意する必要があります。

#### Linuxデスクトップ環境
ibus-jigは、Waylandを無効化したUbuntu 22.04およびGentoo LinuxのGNOME環境でのみ動作を確認しています。  
各環境で`/etc/gdm3/custom.conf`を編集して`WaylandEnable=false`と設定してください。

なお、Ubuntu環境の場合、snapでインストールしたGUIアプリケーションでは日本語入力が行えません。  
これはsnapのセキュリティポリシーによるものなので、日本語入力を行うには、snap以外の方法で同じアプリケーションを再インストールして試してください。

#### IBus
ibus-jigを実行するには[IBus](https://github.com/ibus/ibus)をインストールする必要があります。  
IBusのインストール方法については[公式ドキュメント](https://github.com/ibus/ibus/wiki/Install)を参考にしてください。

#### Python環境
ibus-jigはを実行するにはPython3をインストールする必要があります。Python 3.9およびPython 3.11での動作が確認されています。

以下のコマンドを実行してPyGObjectパッケージとopenaiパッケージをインストールしてください。  
`main.py`で動作を確認する場合は（つまり、OSにインストールしない場合は）venv等のPython仮想環境にインストールしても構いません。
```sh
pip install PyGObject openai
```

### main.pyを利用した実行手順
リポジトリをcloneし、Pythonで`engine/main.py`を実行することでibus-jigによる入力を有効化することができます。  
ibus-jigを無効化したい場合は、Ctrl+Cを押して`main.py`の実行を停止してください。

```sh
git clone https://github.com/y-koj/ibus-jig.git
cd ibus-jig/engine
nano config.py    # config.pyを編集してsecret_keyをOpenAI APIのシークレットキーに書き換える
python3 main.py
```

### OSにインストールする手順
（この項目は書きかけです。）  
`main.py`を実行する手順に加え、インストール用のツールを実行することでシステムにibus-jigをインストールすることができます。

```sh
git clone https://github.com/y-koj/ibus-jig.git
cd ibus-jig
nano engine/config.py     # config.pyを編集してsecret_keyをOpenAI APIのシークレットキーに書き換える
./autogen.sh              # ビルドに必要なファイルを、ビルド環境に合わせて自動生成する
make && sudo make install # ビルドを行い、成功すればインストールする
```

## ライセンス
ibus-jigのもとになった[ibus-tmpl](https://github.com/ibus/ibus-tmpl)はGPLv2で公開されていますが、
ibus-tmplのREADMEに記述された以下の説明の通り、GPTv2以外のライセンスでの再公開を制限していません。  
ibus-tmplの方針にならい、ibus-jigもGPLv2ライセンスで公開しつつ、ibus-jigをもとに作成された入力システムの他ライセンスでの公開を制限しないものとします。
> Ibus-tmpl was released under GPLV2. We wish ibus engine developers would release
> new engines under open source license too, but we do not force it. We allow
> developers start your work from ibus-tmpl and swith to other license.
