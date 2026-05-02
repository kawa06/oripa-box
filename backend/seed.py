"""
初期データ投入スクリプト
サンプルパック・カードと、テスト用ユーザーをDBに追加する

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
                coin_balance=500  # 初期コイン500枚付与
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

            # スタンダードパックのカード一覧
            standard_cards = [
                # UR (1%)
                Card(pack_id=pack1.id, name="神龍カイザー", rarity="UR", probability=0.01,
                     description="伝説の神龍。その力は計り知れない。"),
                # SSR (4%)
                Card(pack_id=pack1.id, name="聖剣士アーサー", rarity="SSR", probability=0.02,
                     description="正義の聖剣を持つ騎士。"),
                Card(pack_id=pack1.id, name="暗黒魔導師ゾルタン", rarity="SSR", probability=0.02,
                     description="闇の魔力を操る謎の魔導師。"),
                # SR (15%)
                Card(pack_id=pack1.id, name="炎の精霊フレア", rarity="SR", probability=0.05,
                     description="炎を自在に操る精霊。"),
                Card(pack_id=pack1.id, name="氷の精霊フロスト", rarity="SR", probability=0.05,
                     description="氷の魔法を使う冷静な精霊。"),
                Card(pack_id=pack1.id, name="雷の勇者サンダー", rarity="SR", probability=0.05,
                     description="稲妻のように素早い勇者。"),
                # R (30%)
                Card(pack_id=pack1.id, name="鉄の戦士アイアン", rarity="R", probability=0.10,
                     description="鉄の鎧を纏う頼もしい戦士。"),
                Card(pack_id=pack1.id, name="風の踊り子シルフ", rarity="R", probability=0.10,
                     description="風のように軽やかな踊り子。"),
                Card(pack_id=pack1.id, name="水の巫女アクア", rarity="R", probability=0.10,
                     description="水の力を持つ神聖な巫女。"),
                # N (50%)
                Card(pack_id=pack1.id, name="村の剣士ケン", rarity="N", probability=0.125,
                     description="武者修行中の若い剣士。"),
                Card(pack_id=pack1.id, name="見習い魔法使いリン", rarity="N", probability=0.125,
                     description="魔法を学んでいる少女。"),
                Card(pack_id=pack1.id, name="町の弓使いアロー", rarity="N", probability=0.125,
                     description="正確な射撃が得意な弓使い。"),
                Card(pack_id=pack1.id, name="森の少女エルフ", rarity="N", probability=0.125,
                     description="森に住む不思議な少女。"),
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
                     description="不死鳥の化身。炎から何度でも蘇る。"),
                # SSR (4%)
                Card(pack_id=pack2.id, name="天空竜セラフィム", rarity="SSR", probability=0.02,
                     description="天上を飛ぶ神聖な竜。"),
                Card(pack_id=pack2.id, name="深淵の魔王バアル", rarity="SSR", probability=0.02,
                     description="深淵から来たる魔王。その力は底知れない。"),
                # SR (15%)
                Card(pack_id=pack2.id, name="聖女ヴァルキリー", rarity="SR", probability=0.05,
                     description="戦場を翔ける聖なる乙女。"),
                Card(pack_id=pack2.id, name="鋼鉄巨人ゴーレム", rarity="SR", probability=0.05,
                     description="鉄で作られた巨大な守護者。"),
                Card(pack_id=pack2.id, name="時空魔道士クロノス", rarity="SR", probability=0.05,
                     description="時間と空間を操る謎の魔道士。"),
                # R (30%)
                Card(pack_id=pack2.id, name="金の騎士オーレス", rarity="R", probability=0.10,
                     description="黄金の鎧を着た誇り高き騎士。"),
                Card(pack_id=pack2.id, name="毒の暗殺者シャドウ", rarity="R", probability=0.10,
                     description="闇に溶け込む素早い暗殺者。"),
                Card(pack_id=pack2.id, name="賢者オラクル", rarity="R", probability=0.10,
                     description="未来を見通す老いた賢者。"),
                # N (50%)
                Card(pack_id=pack2.id, name="鉄壁の盾兵シールド", rarity="N", probability=0.125,
                     description="盾を構える堅固な防御兵。"),
                Card(pack_id=pack2.id, name="小さな妖精ピクシー", rarity="N", probability=0.125,
                     description="いたずら好きな小さな妖精。"),
                Card(pack_id=pack2.id, name="山の石巨人ロック", rarity="N", probability=0.125,
                     description="山に住む石でできた巨人。"),
                Card(pack_id=pack2.id, name="海の人魚マーメイド", rarity="N", probability=0.125,
                     description="海の底に住む美しい人魚。"),
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
                     description="世界を創った神。全ての力を持つ。"),
                # SSR (4%)
                Card(pack_id=pack3.id, name="黄昏の女神ヘル", rarity="SSR", probability=0.02,
                     description="冥界を司る女神。美しくも恐ろしい。"),
                Card(pack_id=pack3.id, name="雷神トール", rarity="SSR", probability=0.02,
                     description="雷鎚ミョルニルを振るう雷神。"),
                # SR (15%)
                Card(pack_id=pack3.id, name="蛇神ヨルムンガンド", rarity="SR", probability=0.05,
                     description="世界を取り巻く巨大な蛇神。"),
                Card(pack_id=pack3.id, name="狼神フェンリル", rarity="SR", probability=0.05,
                     description="世界を滅ぼすと言われる巨大狼。"),
                Card(pack_id=pack3.id, name="知恵神ミーミル", rarity="SR", probability=0.05,
                     description="全知全能の知恵を持つ神。"),
                # R (30%)
                Card(pack_id=pack3.id, name="戦乙女ブリュンヒルデ", rarity="R", probability=0.10,
                     description="最強のワルキューレ。"),
                Card(pack_id=pack3.id, name="火の神ロキ", rarity="R", probability=0.10,
                     description="変幻自在の炎神。"),
                Card(pack_id=pack3.id, name="氷の女王スカジ", rarity="R", probability=0.10,
                     description="雪山を支配する氷の女王。"),
                # N (50%)
                Card(pack_id=pack3.id, name="エインフェリア戦士", rarity="N", probability=0.125,
                     description="ヴァルハラに集う勇敢な戦士。"),
                Card(pack_id=pack3.id, name="ドワーフ職人", rarity="N", probability=0.125,
                     description="優れた武器を作るドワーフ。"),
                Card(pack_id=pack3.id, name="エルフの弓手", rarity="N", probability=0.125,
                     description="長命のエルフ族の弓手。"),
                Card(pack_id=pack3.id, name="ヒューム冒険者", rarity="N", probability=0.125,
                     description="旅する若い人族の冒険者。"),
            ]
            for card in limited_cards:
                db.add(card)
            print(f"限定コレクションパック作成: {len(limited_cards)}枚のカード")

        db.commit()
        print("\n初期データ投入完了!")
        print("テストユーザー: test@example.com / test1234")
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
