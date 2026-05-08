"""
メール送信ユーティリティ
メール認証トークンの生成・送信を担当する
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import timedelta

from backend.auth import create_access_token
from backend.config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM,
    EMAIL_VERIFY_EXPIRE_HOURS, FRONTEND_URL
)

logger = logging.getLogger(__name__)


def create_email_verify_token(user_id: int) -> str:
    """
    メール認証用JWTトークンを生成する
    有効期限: EMAIL_VERIFY_EXPIRE_HOURS 時間
    """
    expires = timedelta(hours=EMAIL_VERIFY_EXPIRE_HOURS)
    token = create_access_token(
        data={"sub": str(user_id), "type": "email_verify"},
        expires_delta=expires
    )
    return token


def send_verification_email(to_email: str, username: str, user_id: int) -> bool:
    """
    メール認証用メールを送信する

    Args:
        to_email: 送信先メールアドレス
        username: ユーザー名（メール本文に使用）
        user_id: ユーザーID（トークン生成に使用）

    Returns:
        送信成功なら True、失敗なら False
    """
    # SMTP設定が未設定の場合はスキップ（ローカル開発環境向け）
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(
            "SMTP設定が未設定のためメール送信をスキップします。"
            "SMTP_USER と SMTP_PASSWORD を設定してください。"
        )
        return False

    # 認証トークンを生成
    token = create_email_verify_token(user_id)

    # 認証URLを生成
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"

    # メール本文（HTML）
    html_body = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Hiragino Sans', 'Meiryo', sans-serif; background: #0f1117; color: #e2e8f0; margin: 0; padding: 0; }}
    .container {{ max-width: 600px; margin: 40px auto; background: #1a1d2e; border-radius: 12px; padding: 40px; }}
    .brand {{ font-size: 1.5rem; font-weight: 700; color: #ffd700; margin-bottom: 24px; }}
    h2 {{ color: #fff; margin-bottom: 16px; }}
    p {{ color: #a0aec0; line-height: 1.7; }}
    .btn {{ display: inline-block; margin: 24px 0; padding: 14px 32px; background: linear-gradient(135deg, #ffd700, #ffaa00); color: #1a1d2e; font-weight: 700; font-size: 1rem; border-radius: 8px; text-decoration: none; }}
    .url {{ font-size: 0.8rem; color: #718096; word-break: break-all; }}
    .footer {{ margin-top: 32px; font-size: 0.8rem; color: #4a5568; border-top: 1px solid #2d3748; padding-top: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="brand">✦ オリパガチャ</div>
    <h2>メールアドレスの認証</h2>
    <p>{username} さん、ご登録ありがとうございます！</p>
    <p>下記のボタンをクリックしてメールアドレスの認証を完了させてください。<br>
       このリンクの有効期限は <strong>24時間</strong> です。</p>
    <a href="{verify_url}" class="btn">メールアドレスを認証する</a>
    <p class="url">URLが開けない場合はこちらをブラウザに貼り付けてください：<br>{verify_url}</p>
    <div class="footer">
      このメールに心当たりがない場合は無視してください。<br>
      オリパガチャ サポートチーム
    </div>
  </div>
</body>
</html>
"""

    # プレーンテキスト版
    text_body = f"""
オリパガチャ - メールアドレスの認証

{username} さん、ご登録ありがとうございます！

以下のURLをクリックしてメールアドレスの認証を完了してください。
このリンクの有効期限は24時間です。

{verify_url}

このメールに心当たりがない場合は無視してください。
オリパガチャ サポートチーム
"""

    try:
        # MIMEメッセージ作成
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "【オリパガチャ】メールアドレスの認証をお願いします"
        msg["From"] = SMTP_FROM or SMTP_USER
        msg["To"] = to_email

        # プレーンテキストとHTMLを添付
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # SMTP接続して送信
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()  # TLS暗号化
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM or SMTP_USER, to_email, msg.as_string())

        logger.info(f"認証メール送信成功: {to_email}")
        return True

    except Exception as e:
        logger.error(f"認証メール送信失敗: {to_email} - {e}")
        return False
