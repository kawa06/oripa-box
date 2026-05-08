"""
初期データ投入スクリプト
サンプルパック・カードと、テスト用ユーザー・管理者をDBに追加する

使い方:
    python -m backend.seed
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import SessionLocal, engine, Base
from backend.models import User, Pack, Card, CoinTransaction
from backend.auth import get_password_hash

# テーブル作成（存在しない場合のみ）
Base.metadata.create_all(bind=engine)

# プレースホルダー画像のベースURL
PLACEHOLDER_BASE = "https://placehold.co/300x420"


def seed():
    db = SessionLocal()

    try:
        # ===== テストユーザー作成 =====
        existing_user = db.query(User).filter(User.email == "test@example.com").first()
        if not existing_user:
            test_user = User(
                email="test@example.com",
                username="テストユーザー",
                hashed_password=get_password_hash("test1234"),
                coin_balance=500,  # 初期コイン500枚付与
                is_admin=False,
                points=0
            )
            db.add(test_user)
            db.flush()  # IDを取得するためにflush

            # 初期コインの取引履歴を記録
            db.add(CoinTransaction(
                user_id=test_user.id,
                amount=500,
                transaction_type="bonus",
                description="テストユーザー初期ボーナス"
            ))
            print(f"テストユーザー作成: {test_user.email} (コイン: {test_user.coin_balance})")
        else:
            print("テストユーザーはすでに存在します")

        # ===== 管理者ユーザー作成 =====
        existing_admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not existing_admin:
            admin_user = User(
                email="admin@example.com",
                username="管理者",
                hashed_password=get_password_hash("admin1234"),
                coin_balance=9999,  # 管理者用初期コイン
                is_admin=True,
                points=0
            )
            db.add(admin_user)
            db.flush()

            # 管理者初期コインの取引履歴
            db.add(CoinTransaction(
                user_id=admin_user.id,
                amount=9999,
                transaction_type="bonus",
                description="管理者初期コイン"
            ))
            print(f"管理者ユーザー作成: {admin_user.email} (コイン: {admin_user.coin_balance})")
        else:
            print("管理者ユーザーはすでに存在します")

        # ===== パック1: スタンダードパック =====
        pack1 = db.query(Pack).filter(Pack.name == "スタンダードパック").first()
        if not pack1:
            pack1 = Pack(
                name="スタンダードパック",
                description="定番カードが揃ったスタンダードなガチャパック。初心者でも遊びやすい！",
                price_coins=50,
                stock=100,
                max_stock=100,
                image_url=None,
                is_active=True
            )
            db.add(pack1)
            db.flush()

            # スタンダードパックのカード一覧（image_url追加）
            standard_cards = [
                # UR (1%)
                Card(pack_id=pack1.id, name="神龍カイザー", rarity="UR", probability=0.01,
                     description="伝説の神龍。その力は計り知れない。",
                     image_url=f"{PLACEHOLDER_BASE}/ffd700/1a1a00?text=%E7%A5%9E%E9%BE%8D%E3%82%AB%E3%82%A4%E3%82%B6%E3%83%BC"),
                # SSR (4%)
                Card(pack_id=pack1.id, name="聖剣士アーサー", rarity="SSR", probability=0.02,
                     description="正義の聖剣を持つ騎士。",
                     image_url=f"{PLACEHOLDER_BASE}/e879f9/1a0020?text=%E8%81%96%E5%89%A3%E5%A3%AB%E3%82%A2%E3%83%BC%E3%82%B5%E3%83%BC"),
                Card(pack_id=pack1.id, name="暗黒魔導師ゾルタン", rarity="SSR", probability=0.02,
                     description="闇の魔力を操る謎の魔導師。",
                     image_url=f"{PLACEHOLDER_BASE}/e879f9/1a0020?text=%E6%9A%97%E9%BB%92%E9%AD%94%E5%B0%8E%E5%B8%AB"),
                # SR (15%)
                Card(pack_id=pack1.id, name="炎の精霊フレア", rarity="SR", probability=0.05,
                     description="炎を自在に操る精霊。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E7%82%8E%E3%83%95%E3%83%AC%E3%82%A2"),
                Card(pack_id=pack1.id, name="氷の精霊フロスト", rarity="SR", probability=0.05,
                     description="氷の魔法を使う冷静な精霊。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E6%B0%B7%E3%83%95%E3%83%AD%E3%82%B9%E3%83%88"),
                Card(pack_id=pack1.id, name="雷の勇者サンダー", rarity="SR", probability=0.05,
                     description="稲妻のように素早い勇者。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E9%9B%B7%E3%82%B5%E3%83%B3%E3%83%80%E3%83%BC"),
                # R (30%)
                Card(pack_id=pack1.id, name="鉄の戦士アイアン", rarity="R", probability=0.10,
                     description="鉄の鎧を纏う頼もしい戦士。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E9%89%84%E3%82%A2%E3%82%A4%E3%82%A2%E3%83%B3"),
                Card(pack_id=pack1.id, name="風の踊り子シルフ", rarity="R", probability=0.10,
                     description="風のように軽やかな踊り子。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E9%A2%A8%E3%82%B7%E3%83%AB%E3%83%95"),
                Card(pack_id=pack1.id, name="水の巫女アクア", rarity="R", probability=0.10,
                     description="水の力を持つ神聖な巫女。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E6%B0%B4%E3%82%A2%E3%82%AF%E3%82%A2"),
                # N (50%)
                Card(pack_id=pack1.id, name="村の剣士ケン", rarity="N", probability=0.125,
                     description="武者修行中の若い剣士。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E5%89%A3%E5%A3%AB%E3%82%B1%E3%83%B3"),
                Card(pack_id=pack1.id, name="見習い魔法使いリン", rarity="N", probability=0.125,
                     description="魔法を学んでいる少女。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E9%AD%94%E6%B3%95%E4%BD%BF%E3%83%AA%E3%83%B3"),
                Card(pack_id=pack1.id, name="町の弓使いアロー", rarity="N", probability=0.125,
                     description="正確な射撃が得意な弓使い。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E5%BC%93%E4%BD%BF%E3%82%A2%E3%83%AD%E3%83%BC"),
                Card(pack_id=pack1.id, name="森の少女エルフ", rarity="N", probability=0.125,
                     description="森に住む不思議な少女。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E5%B0%91%E5%A5%B3%E3%82%A8%E3%83%AB%E3%83%95"),
            ]
            for card in standard_cards:
                db.add(card)
            print(f"スタンダードパック作成: {len(standard_cards)}枚のカード")

        # ===== パック2: プレミアムパック =====
        pack2 = db.query(Pack).filter(Pack.name == "プレミアムパック").first()
        if not pack2:
            pack2 = Pack(
                name="プレミアムパック",
                description="レアカードの排出率がアップした高級ガチャパック！",
                price_coins=100,
                stock=100,
                max_stock=100,
                image_url=None,
                is_active=True
            )
            db.add(pack2)
            db.flush()

            # プレミアムパックのカード一覧（高レアリティに偏重）
            premium_cards = [
                # UR (1%)
                Card(pack_id=pack2.id, name="究極神フェニックス", rarity="UR", probability=0.01,
                     description="不死鳥の化身。炎から何度でも蘇る。",
                     image_url=f"{PLACEHOLDER_BASE}/ffd700/1a1a00?text=%E7%A9%B6%E6%A5%B5%E7%A5%9E%E3%83%95%E3%82%A7%E3%83%8B%E3%83%83%E3%82%AF%E3%82%B9"),
                # SSR (4%)
                Card(pack_id=pack2.id, name="天空竜セラフィム", rarity="SSR", probability=0.02,
                     description="天上を飛ぶ神聖な竜。",
                     image_url=f"{PLACEHOLDER_BASE}/e879f9/1a0020?text=%E5%A4%A9%E7%A9%BA%E7%AB%9C%E3%82%BB%E3%83%A9%E3%83%95%E3%82%A3%E3%83%A0"),
                Card(pack_id=pack2.id, name="深淵の魔王バアル", rarity="SSR", probability=0.02,
                     description="深淵から来たる魔王。その力は底知れない。",
                     image_url=f"{PLACEHOLDER_BASE}/e879f9/1a0020?text=%E6%B7%B1%E6%B7%B5%E9%AD%94%E7%8E%8B%E3%83%90%E3%82%A2%E3%83%AB"),
                # SR (15%)
                Card(pack_id=pack2.id, name="聖女ヴァルキリー", rarity="SR", probability=0.05,
                     description="戦場を翔ける聖なる乙女。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E8%81%96%E5%A5%B3%E3%83%B4%E3%82%A1%E3%83%AB%E3%82%AD%E3%83%AA%E3%83%BC"),
                Card(pack_id=pack2.id, name="鋼鉄巨人ゴーレム", rarity="SR", probability=0.05,
                     description="鉄で作られた巨大な守護者。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E9%8B%BC%E9%89%84%E3%82%B4%E3%83%BC%E3%83%AC%E3%83%A0"),
                Card(pack_id=pack2.id, name="時空魔道士クロノス", rarity="SR", probability=0.05,
                     description="時間と空間を操る謎の魔道士。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E6%99%82%E7%A9%BA%E3%82%AF%E3%83%AD%E3%83%8E%E3%82%B9"),
                # R (30%)
                Card(pack_id=pack2.id, name="金の騎士オーレス", rarity="R", probability=0.10,
                     description="黄金の鎧を着た誇り高き騎士。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E9%87%91%E9%A8%8E%E5%A3%AB%E3%82%AA%E3%83%BC%E3%83%AC%E3%82%B9"),
                Card(pack_id=pack2.id, name="毒の暗殺者シャドウ", rarity="R", probability=0.10,
                     description="闇に溶け込む素早い暗殺者。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E6%9A%97%E6%AE%BA%E8%80%85%E3%82%B7%E3%83%A3%E3%83%89%E3%82%A6"),
                Card(pack_id=pack2.id, name="賢者オラクル", rarity="R", probability=0.10,
                     description="未来を見通す老いた賢者。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E8%B3%A2%E8%80%85%E3%82%AA%E3%83%A9%E3%82%AF%E3%83%AB"),
                # N (50%)
                Card(pack_id=pack2.id, name="鉄壁の盾兵シールド", rarity="N", probability=0.125,
                     description="盾を構える堅固な防御兵。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E7%9B%BE%E5%85%B5%E3%82%B7%E3%83%BC%E3%83%AB%E3%83%89"),
                Card(pack_id=pack2.id, name="小さな妖精ピクシー", rarity="N", probability=0.125,
                     description="いたずら好きな小さな妖精。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E5%A6%96%E7%B2%BE%E3%83%94%E3%82%AF%E3%82%B7%E3%83%BC"),
                Card(pack_id=pack2.id, name="山の石巨人ロック", rarity="N", probability=0.125,
                     description="山に住む石でできた巨人。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E7%9F%B3%E5%B7%A8%E4%BA%BA%E3%83%AD%E3%83%83%E3%82%AF"),
                Card(pack_id=pack2.id, name="海の人魚マーメイド", rarity="N", probability=0.125,
                     description="海の底に住む美しい人魚。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E4%BA%BA%E9%AD%9A%E3%83%9E%E3%83%BC%E3%83%A1%E3%82%A4%E3%83%89"),
            ]
            for card in premium_cards:
                db.add(card)
            print(f"プレミアムパック作成: {len(premium_cards)}枚のカード")

        # ===== パック3: 限定コレクションパック =====
        pack3 = db.query(Pack).filter(Pack.name == "限定コレクションパック").first()
        if not pack3:
            pack3 = Pack(
                name="限定コレクションパック",
                description="期間限定の特別カードが入った希少パック。コレクター必見！",
                price_coins=200,
                stock=100,
                max_stock=100,
                image_url=None,
                is_active=True
            )
            db.add(pack3)
            db.flush()

            # 限定コレクションパックのカード一覧
            limited_cards = [
                # UR (1%)
                Card(pack_id=pack3.id, name="創世神オーディン", rarity="UR", probability=0.01,
                     description="世界を創った神。全ての力を持つ。",
                     image_url=f"{PLACEHOLDER_BASE}/ffd700/1a1a00?text=%E5%89%B5%E4%B8%96%E7%A5%9E%E3%82%AA%E3%83%BC%E3%83%87%E3%82%A3%E3%83%B3"),
                # SSR (4%)
                Card(pack_id=pack3.id, name="黄昏の女神ヘル", rarity="SSR", probability=0.02,
                     description="冥界を司る女神。美しくも恐ろしい。",
                     image_url=f"{PLACEHOLDER_BASE}/e879f9/1a0020?text=%E5%A5%B3%E7%A5%9E%E3%83%98%E3%83%AB"),
                Card(pack_id=pack3.id, name="雷神トール", rarity="SSR", probability=0.02,
                     description="雷鎚ミョルニルを振るう雷神。",
                     image_url=f"{PLACEHOLDER_BASE}/e879f9/1a0020?text=%E9%9B%B7%E7%A5%9E%E3%83%88%E3%83%BC%E3%83%AB"),
                # SR (15%)
                Card(pack_id=pack3.id, name="蛇神ヨルムンガンド", rarity="SR", probability=0.05,
                     description="世界を取り巻く巨大な蛇神。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E8%9B%87%E7%A5%9E%E3%83%A8%E3%83%AB%E3%83%A0%E3%83%B3%E3%82%AC%E3%83%B3%E3%83%89"),
                Card(pack_id=pack3.id, name="狼神フェンリル", rarity="SR", probability=0.05,
                     description="世界を滅ぼすと言われる巨大狼。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E7%8B%BC%E7%A5%9E%E3%83%95%E3%82%A7%E3%83%B3%E3%83%AA%E3%83%AB"),
                Card(pack_id=pack3.id, name="知恵神ミーミル", rarity="SR", probability=0.05,
                     description="全知全能の知恵を持つ神。",
                     image_url=f"{PLACEHOLDER_BASE}/a78bfa/0a0020?text=%E7%9F%A5%E6%81%B5%E7%A5%9E%E3%83%9F%E3%83%BC%E3%83%9F%E3%83%AB"),
                # R (30%)
                Card(pack_id=pack3.id, name="戦乙女ブリュンヒルデ", rarity="R", probability=0.10,
                     description="最強のワルキューレ。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E6%88%A6%E4%B9%99%E5%A5%B3%E3%83%96%E3%83%AA%E3%83%A5%E3%83%B3%E3%83%92%E3%83%AB%E3%83%87"),
                Card(pack_id=pack3.id, name="火の神ロキ", rarity="R", probability=0.10,
                     description="変幻自在の炎神。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E7%81%AB%E7%A5%9E%E3%83%AD%E3%82%AD"),
                Card(pack_id=pack3.id, name="氷の女王スカジ", rarity="R", probability=0.10,
                     description="雪山を支配する氷の女王。",
                     image_url=f"{PLACEHOLDER_BASE}/38bdf8/001a2a?text=%E6%B0%B7%E3%81%AE%E5%A5%B3%E7%8E%8B%E3%82%B9%E3%82%AB%E3%82%B8"),
                # N (50%)
                Card(pack_id=pack3.id, name="エインフェリア戦士", rarity="N", probability=0.125,
                     description="ヴァルハラに集う勇敢な戦士。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E3%82%A8%E3%82%A4%E3%83%B3%E3%83%95%E3%82%A7%E3%83%AA%E3%82%A2"),
                Card(pack_id=pack3.id, name="ドワーフ職人", rarity="N", probability=0.125,
                     description="優れた武器を作るドワーフ。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E3%83%89%E3%83%AF%E3%83%BC%E3%83%95%E8%81%B7%E4%BA%BA"),
                Card(pack_id=pack3.id, name="エルフの弓手", rarity="N", probability=0.125,
                     description="長命のエルフ族の弓手。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E3%82%A8%E3%83%AB%E3%83%95%E5%BC%93%E6%89%8B"),
                Card(pack_id=pack3.id, name="ヒューム冒険者", rarity="N", probability=0.125,
                     description="旅する若い人族の冒険者。",
                     image_url=f"{PLACEHOLDER_BASE}/94a3b8/0a1020?text=%E3%83%92%E3%83%A5%E3%83%BC%E3%83%A0%E5%86%92%E9%99%BA%E8%80%85"),
            ]
            for card in limited_cards:
                db.add(card)
            print(f"限定コレクションパック作成: {len(limited_cards)}枚のカード")

        db.commit()
        print("\n初期データ投入完了!")
        print("テストユーザー: test@example.com / test1234")
        print("管理者ユーザー: admin@example.com / admin1234")
        print("パック一覧:")
        for pack in db.query(Pack).all():
            print(f"  - {pack.name} ({pack.price_coins}コイン / 在庫{pack.stock}口)")

    except Exception as e:
        db.rollback()
        print(f"エラーが発生しました: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
