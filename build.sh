#!/bin/bash
# Render.com ビルドスクリプト
# render.yaml の buildCommand から呼び出される

set -e  # エラーが発生したら即座に終了

echo "=== 依存ライブラリをインストール ==="
pip install -r requirements.txt

echo "=== 初期データを投入 ==="
# seed.py は冪等に作られていること（既存データがあれば何もしない）
# PostgreSQL接続失敗時はビルドを止めずに警告だけ出す
python -m backend.seed || echo "[警告] seed.py の実行に失敗しましたが、ビルドを続行します"

echo "=== ビルド完了 ==="
