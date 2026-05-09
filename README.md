# オリパガチャ

トレーディングカードのオリジナルパックガチャサービス。

## 技術スタック

- **フロントエンド**: HTML / CSS / Vanilla JavaScript
- **バックエンド**: FastAPI (Python)
- **データベース**: SQLite (SQLAlchemy)
- **決済**: Stripe Checkout

---

## セットアップ

### 1. Pythonの依存ライブラリをインストール

```bash
cd backend
pip install -r requirements.txt
```

### 2. 環境変数の設定（オプション）

プロジェクトルートに `.env` ファイルを作成して以下を設定します。

```env
SECRET_KEY=your-secret-key-change-in-production
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxx
FRONTEND_URL=http://localhost:8000
DATABASE_URL=sqlite:///./oripa_gacha.db
```

> **Stripeキーの取得**: https://dashboard.stripe.com/apikeys

### 3. 初期データを投入する

```bash
# プロジェクトルートから実行
python -m backend.seed
```

これでサンプルパック3種とテストユーザーが作成されます。

**テストユーザー:**
- Email: `test@example.com`
- Password: `test1234`

### 4. サーバーを起動する

```bash
# プロジェクトルートから実行
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

ブラウザで http://localhost:8000 にアクセスしてください。

---

## 機能一覧

| 機能 | 説明 |
|------|------|
| ユーザー登録 | メールアドレス＋パスワードで登録。登録時に50コインのボーナス付与 |
| ログイン | JWT認証（24時間有効） |
| パック一覧 | 販売中のガチャパックを一覧表示。在庫バー付き |
| ガチャ | コインを消費してパックからカードを1枚抽選 |
| 開封演出 | カードを裏向きで表示→クリックで3Dフリップ。レアリティ別エフェクト |
| コイン購入 | Stripe Checkout経由で安全に課金 |
| 取引履歴 | コイン増減の履歴を確認 |
| ガチャ履歴 | 過去のガチャ結果を確認 |

---

## ガチャ仕様

### レアリティと排出確率

| レアリティ | 確率 | エフェクト |
|-----------|------|-----------|
| UR | 1% | 金色に光る + キラキラパーティクル |
| SSR | 4% | 紫色に光る + パーティクル |
| SR | 15% | 青紫に光る |
| R | 30% | 青い枠 |
| N | 50% | 通常表示 |

### パック仕様

- 各パックは最大100口
- 在庫が0になると「SOLD OUT」表示、ガチャ不可
- 在庫20%以下でバーが赤くなる

### コインパック

| パック | コイン数 | 価格 |
|--------|---------|------|
| pack_100 | 100コイン | 500円 |
| pack_500 | 500コイン | 2,000円 |
| pack_1000 | 1,000コイン | 3,500円 |

---

## Stripe Webhook設定

本番環境でWebhookを使う場合:

```bash
# Stripe CLIをインストールしてローカルテスト
stripe listen --forward-to localhost:8000/api/coins/webhook
```

Webhookエンドポイント: `POST /api/coins/webhook`

イベント: `checkout.session.completed`

---

## ディレクトリ構成

```
oripa-gacha/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPIエントリポイント
│   ├── models.py        # SQLAlchemy models
│   ├── database.py      # DB接続設定
│   ├── auth.py          # JWT認証
│   ├── schemas.py       # Pydantic schemas
│   ├── config.py        # 設定
│   ├── seed.py          # 初期データ投入
│   ├── requirements.txt
│   └── routes/
│       ├── __init__.py
│       ├── auth.py      # 認証API
│       ├── gacha.py     # ガチャAPI
│       ├── coins.py     # コインAPI (Stripe含む)
│       └── packs.py     # パック一覧API
├── frontend/
│   ├── index.html       # パック一覧
│   ├── login.html       # ログイン/登録
│   ├── gacha.html       # ガチャ開封画面
│   ├── coins.html       # コイン購入画面
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── app.js       # 共通ユーティリティ
│       ├── auth.js      # 認証処理
│       ├── gacha.js     # ガチャ+開封アニメーション
│       └── coins.js     # コイン購入処理
└── README.md
```

---

## Render.com へのデプロイ

### デプロイ手順

1. [Render.com](https://render.com) にサインインし、**New → Blueprint** を選択
2. GitHub リポジトリ `kawa06/oripa-box` を連携する
3. `render.yaml` が自動検出され、サービスが作成される
4. **Environment** タブで以下の環境変数を手動設定する

| 環境変数 | 説明 | 例 |
|----------|------|----|
| `SECRET_KEY` | JWT署名用秘密鍵（ランダムな文字列） | `openssl rand -hex 32` の出力 |
| `STRIPE_SECRET_KEY` | Stripe秘密鍵 | `sk_live_...` |
| `STRIPE_PUBLIC_KEY` | Stripe公開鍵 | `pk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | Stripe Webhookシークレット | `whsec_...` |
| `FRONTEND_URL` | デプロイ後のURL（Stripe リダイレクト先） | `https://oripa-gacha.onrender.com` |

> `DATABASE_URL` は `render.yaml` の `fromDatabase` 設定により Render が自動的に注入します。手動設定は不要です。

### PostgreSQL 設定について

`render.yaml` には Render Managed PostgreSQL データベースが含まれています。
Blueprint デプロイ時に自動的に以下が作成・接続されます。

| 項目 | 値 |
|------|-----|
| サービス名 | `oripa-gacha-db` |
| データベース名 | `oripa_gacha` |
| ユーザー名 | `oripa_user` |
| プラン | free |

- Blueprint デプロイ後、`DATABASE_URL` 環境変数に PostgreSQL の接続文字列が自動設定されます
- アプリ側は `database.py` で `postgres://` → `postgresql://` の自動変換に対応済みです
- テーブルはアプリ起動時に `Base.metadata.create_all()` で自動作成されます
- `ALTER TABLE` によるマイグレーションは SQLite 専用です。PostgreSQL では不要（`create_all` が担う）

#### ローカルで PostgreSQL を使う場合

```env
DATABASE_URL=postgresql://ユーザー名:パスワード@localhost:5432/oripa_gacha
```

### SQLite に関する重要な注意事項

> **警告**: Render.com の無料プランは **Ephemeral Filesystem（揮発性ファイルシステム）** を採用しています。  
> サービスが再起動・再デプロイされるたびに `oripa_gacha.db` ファイルは**消去されます**。

- **開発・テスト目的**: SQLite のままで問題ありません（デプロイごとに `build.sh` が seed を再実行します）
- **本番運用**: Render の **PostgreSQL** アドオンへの移行を強く推奨します
  - `DATABASE_URL` 環境変数に PostgreSQL の接続文字列を設定するだけで切り替え可能
  - 例: `postgresql://user:password@host/dbname`

---

## API エンドポイント一覧

| Method | Path | 説明 | 認証 |
|--------|------|------|------|
| POST | /api/auth/register | ユーザー登録 | 不要 |
| POST | /api/auth/login | ログイン | 不要 |
| GET | /api/auth/me | 自分の情報 | 必要 |
| GET | /api/packs/ | パック一覧 | 不要 |
| GET | /api/packs/{id} | パック詳細 | 不要 |
| POST | /api/gacha/draw | ガチャ実行 | 必要 |
| GET | /api/gacha/history | ガチャ履歴 | 必要 |
| GET | /api/coins/balance | コイン残高 | 必要 |
| GET | /api/coins/transactions | 取引履歴 | 必要 |
| POST | /api/coins/purchase | コイン購入 | 必要 |
| POST | /api/coins/webhook | Stripe Webhook | 不要 |
| GET | /api/coins/packs | コインパック一覧 | 不要 |

APIドキュメント: http://localhost:8000/docs
