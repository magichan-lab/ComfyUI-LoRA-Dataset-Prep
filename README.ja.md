# ComfyUI LoRA Dataset Prep

[English](README.md) | 日本語

ComfyUI で画像フォルダーを一括処理し、LoRA 学習用の画像と同名のキャプションを生成するカスタムノードです。画像の短辺・長辺を指定範囲に調整し、必要な場合は ComfyUI のアップスケールモデル（RealESRGAN など）を使用します。キャプションは Qwen3-VL を使って元画像から作成し、学習対象に応じて記述の重点を切り替えられます。

## リポジトリ構成

```text
ComfyUI-LoRA-Dataset-Prep/
├── __init__.py                 # ComfyUI のノード登録
├── nodes.py                    # 一括前処理とキャプション生成
├── caption_prompt.py           # 学習対象別のキャプション指示
├── review.py                   # 画像とキャプションの確認用一覧
├── requirements.txt            # Manager がインストールする依存関係
├── pyproject.toml              # Comfy Registry 用メタデータ
├── workflows/
│   └── lora_dataset_preparation.json
├── README.md                  # 英語版 README
├── README.ja.md               # 日本語版 README
└── LICENSE
```

## インストール

リポジトリ公開後、ComfyUI Manager から **ComfyUI LoRA Dataset Prep** を検索してインストールできます。Registry へ公開する前は、`ComfyUI/custom_nodes/` にこのリポジトリをクローンし、ComfyUI と同じ Python 環境で `pip install -r requirements.txt` を実行してください。インストール後に ComfyUI を再起動します。

アップスケールモデルを使う場合は、対応する `.pth` モデルを `ComfyUI/models/upscale_models/` に配置します。モデル自体はこのリポジトリに含まれません。Qwen3-VL モデルは初回実行時に Hugging Face から取得されます。モデルのライセンスと利用条件は各配布元で確認してください。

## 使い方

1. `workflows/lora_dataset_preparation.json` を ComfyUI の画面へドラッグして読み込みます。
2. `source_folder` に画像フォルダー、`output_folder` に別の出力フォルダーを設定します。相対パスは ComfyUI プロセスの作業ディレクトリ基準です。
3. `training_focus` で学習対象を選びます。`auto`、`person`、`object`、`background`、`outfit`（衣装）、`item`（小物）、`pose`、`art_style`（画風）、`visual_effect`、`expression`、`camera_angle`、`composition`、`logo`、`symbol`、`custom` に対応します。`custom_focus` で追加指示を指定できます。`custom` の場合は入力が必須です。
4. `trigger_word` を学習に使う語句に変更します。既定値 `subject` は例です。空欄ならキャプションに語句を付けません。
5. ワークフローでは `UpscaleModelLoader` が `upscale_model` に接続されています。選択したモデルがインストール済みであることを確認します。モデルを使わない場合は接続を外して `upscale_mode` を `lanczos` に変更します。
6. Queue を実行し、出力フォルダーの `review_index.html` をブラウザーで開いて画像とキャプションを目視で確認します。

入力はフォルダー直下の JPG、PNG、WebP、BMP、TIFF に対応します。出力は `ファイル名.png` と `ファイル名.txt` のペア、処理結果の `prep_report.csv`、確認用の `review_index.html` です。一覧には入力フォルダー内の全画像を表示し、スキップ済みのペアや処理失敗も確認できます。画像をクリックすると出力画像を元のサイズで開けます。元画像は変更しません。`skip_existing` が有効なら、両方の出力ファイルが存在する画像をスキップします。キャプションは常にアップスケール前の元画像から生成します。

キャプションの指示は写真・イラスト・グラフィック・レンダリングに共通で、選択した対象の見た目を優先します。ロゴの文字は明瞭に読める場合のみ記述するよう指示します。`training_focus` や `custom_focus` を変更して既存ペアを作り直す場合は `skip_existing` を無効にしてください。既存のキャプションを手作業で修正している場合は、上書き前に退避してください。

`min_short_side` は短辺の拡大目標、`max_long_side` は長辺の上限です。縦横比を保ち、長辺の上限を優先します。そのため極端な縦長・横長画像では短辺が目標に達しないことがあります。入力画像の同名ベース（拡張子違い、大文字小文字違いを含む）はエラーになります。VRAM 消費量と処理時間は VLM と画像サイズに依存します。

## ComfyUI Manager / Registry への公開

リポジトリは **[magichan-lab/ComfyUI-LoRA-Dataset-Prep](https://github.com/magichan-lab/ComfyUI-LoRA-Dataset-Prep)** です。ノード識別子は `LoRADatasetPrep`、画面上の名前は `LoRA Dataset Prep (Batch Upscale + Caption)`、ワークフロー名は `lora_dataset_preparation.json` に統一しています。

1. [Comfy Registry](https://registry.comfy.org/) で Publisher を作成し、`pyproject.toml` の `PublisherId` を実際の ID に置き換えます。
2. Registry の公開用 API キーを作成し、[公式の公開手順](https://docs.comfy.org/registry/publishing)に従って `comfy node publish` または GitHub Actions でバージョン `0.1.0` を公開します。
3. Registry の公開後、ComfyUI Manager で検索・インストールできることと、同梱ワークフローが読み込めることを確認します。

Registry は ComfyUI Manager の検索・インストール基盤です。従来の `custom-node-list.json` への PR 方式も Manager の文書に記載されていますが、新規公開には Registry の手順を優先します。

## 制限事項

キャプションは自動生成のため誤記や不要な描写があり得ます。学習前に画像とテキストを確認してください。人物画像など、利用する画像の権利と公開範囲は各自で確認してください。
