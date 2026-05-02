#!/bin/bash
# Render.com ビルドスクリプト
# render.yaml の buildCommand から呼び出される

set -e  # エラーが発生したら即座に終了

echo "=== 依存ライブラリをインストール ==="
pip install -r backend/requirements.txt

echo "=== 初期データを投入 ==="
# seed.py は冪等に作られていること（既存データがあれば何もしない）
python -m backend.seed

echo "=== ビルド完了 ==="
