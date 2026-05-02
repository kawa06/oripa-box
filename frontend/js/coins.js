/**
 * coins.js - コイン購入処理
 * Stripe Checkoutを使ったコイン購入とStripe成功後の処理
 */

// 選択中のコインパック
let selectedCoinPack = null;

document.addEventListener('DOMContentLoaded', async () => {
  // 認証チェック
  if (!requireAuth()) return;

  // Stripe成功・キャンセルのURLパラメータを処理
  handleStripeReturn();

  // コインパック一覧を読み込む
  await loadCoinPacks();

  // 取引履歴を読み込む
  await loadTransactionHistory();

  // 購入ボタンのイベント
  const purchaseBtn = document.getElementById('purchase-btn');
  if (purchaseBtn) {
    purchaseBtn.addEventListener('click', handlePurchase);
  }
});

/**
 * Stripeからリダイレクトで戻ってきた場合の処理
 */
function handleStripeReturn() {
  const params = new URLSearchParams(window.location.search);

  if (params.get('success') === 'true') {
    // 決済成功
    showAlert('coin-alert',
      '決済が完了しました！コインが付与されるまで少しお待ちください。',
      'success'
    );
    // URLをクリーンアップ
    window.history.replaceState({}, '', '/frontend/coins.html');
    // コイン残高を更新（Webhookで付与されたはず）
    setTimeout(async () => {
      try {
        const data = await apiGet('/coins/balance');
        const coinEl = document.getElementById('coin-balance-display');
        if (coinEl) coinEl.textContent = data.balance;
        const currentBalance = document.getElementById('current-balance');
        if (currentBalance) currentBalance.textContent = `${data.balance} コイン`;
        const user = getUser();
        if (user) {
          user.coin_balance = data.balance;
          saveUser(user);
        }
        // 取引履歴も更新
        await loadTransactionHistory();
      } catch (e) {
        console.error('残高更新エラー:', e);
      }
    }, 2000);  // Webhookの処理時間を待つ

  } else if (params.get('canceled') === 'true') {
    // 決済キャンセル
    showAlert('coin-alert', '決済がキャンセルされました。', 'error');
    window.history.replaceState({}, '', '/frontend/coins.html');
  }
}

/**
 * コインパック一覧を取得して表示する
 */
async function loadCoinPacks() {
  const container = document.getElementById('coin-pack-grid');
  const balanceEl = document.getElementById('current-balance');

  try {
    // 現在の残高を取得
    const balanceData = await apiGet('/coins/balance');
    if (balanceEl) {
      balanceEl.textContent = `${balanceData.balance} コイン`;
    }

    // コインパック一覧を取得
    const packs = await apiGet('/coins/packs');

    if (!container) return;

    // お得度を計算して表示
    const baseValue = packs[0] ? packs[0].price_jpy / packs[0].coins : 5;  // 基準: 1コイン=5円

    container.innerHTML = packs.map((pack, index) => {
      const valuePerCoin = pack.price_jpy / pack.coins;
      const discountPercent = Math.round((1 - valuePerCoin / baseValue) * 100);
      const isGoodValue = discountPercent > 0;

      return `
        <div class="coin-pack-card" id="coin-pack-${pack.id}"
             onclick="selectCoinPack('${pack.id}', this)">
          ${index > 0 ? `<div class="value-badge">${discountPercent}% お得</div>` : ''}
          <div class="coin-amount">🪙 ${pack.coins.toLocaleString()}</div>
          <div class="coin-price">¥${pack.price_jpy.toLocaleString()}</div>
          <div style="font-size: 0.85rem; color: var(--text-secondary);">
            1コイン ≈ ¥${valuePerCoin.toFixed(1)}
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    if (container) {
      container.innerHTML = `<p style="color: var(--error);">読み込みエラー: ${err.message}</p>`;
    }
  }
}

/**
 * コインパックを選択する
 */
function selectCoinPack(packId, element) {
  // 全ての選択を解除
  document.querySelectorAll('.coin-pack-card').forEach(el => {
    el.classList.remove('selected');
  });

  // 選択を設定
  selectedCoinPack = packId;
  element.classList.add('selected');

  // 購入ボタンを有効化
  const purchaseBtn = document.getElementById('purchase-btn');
  if (purchaseBtn) {
    purchaseBtn.disabled = false;
    // パック名を取得して表示
    const coinAmount = element.querySelector('.coin-amount').textContent;
    const price = element.querySelector('.coin-price').textContent;
    purchaseBtn.textContent = `${coinAmount} を ${price} で購入`;
  }
}

/**
 * コイン購入処理（Stripe Checkoutへリダイレクト）
 */
async function handlePurchase() {
  if (!selectedCoinPack) {
    showAlert('coin-alert', 'コインパックを選択してください');
    return;
  }

  const btn = document.getElementById('purchase-btn');
  setButtonLoading(btn, true);

  try {
    // Stripe Checkout Session URLを取得
    const data = await apiPost('/coins/purchase', { pack_id: selectedCoinPack });

    // Stripe決済ページへリダイレクト
    window.location.href = data.checkout_url;

  } catch (err) {
    // Stripeが設定されていない場合はモックで対応
    if (err.message.includes('Stripe') || err.message.includes('stripe')) {
      showAlert('coin-alert',
        'Stripe決済キーが設定されていません。実際の運用では .env にSTRIPE_SECRET_KEYを設定してください。',
        'error'
      );
    } else {
      showAlert('coin-alert', err.message);
    }
    setButtonLoading(btn, false, 'コインを購入する');
  }
}

/**
 * コイン取引履歴を取得して表示する
 */
async function loadTransactionHistory() {
  const container = document.getElementById('transaction-history');
  if (!container) return;

  try {
    const transactions = await apiGet('/coins/transactions');

    if (transactions.length === 0) {
      container.innerHTML = '<p class="text-secondary text-center mt-16">取引履歴はありません</p>';
      return;
    }

    container.innerHTML = `
      <div class="history-list">
        ${transactions.map(tx => {
          const isPositive = tx.amount > 0;
          const typeLabel = {
            'purchase': 'コイン購入',
            'gacha': 'ガチャ',
            'bonus': 'ボーナス',
          }[tx.transaction_type] || tx.transaction_type;

          return `
            <div class="history-item">
              <div style="
                width: 36px; height: 36px; border-radius: 50%;
                background: ${isPositive ? 'rgba(34, 197, 94, 0.15)' : 'rgba(239, 68, 68, 0.15)'};
                display: flex; align-items: center; justify-content: center;
                font-size: 1rem; flex-shrink: 0;
              ">
                ${isPositive ? '⬆' : '⬇'}
              </div>
              <div style="flex: 1">
                <div style="font-weight: 600;">${typeLabel}</div>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">${tx.description || ''}</div>
              </div>
              <div style="text-align: right;">
                <div style="
                  font-weight: 700;
                  color: ${isPositive ? 'var(--success)' : 'var(--error)'};
                ">
                  ${isPositive ? '+' : ''}${tx.amount} 🪙
                </div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">
                  ${formatDateTime(tx.created_at)}
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  } catch (err) {
    container.innerHTML = '<p class="text-secondary text-center">取引履歴の読み込みに失敗しました</p>';
  }
}

/**
 * 日時を読みやすいフォーマットに変換する
 */
function formatDateTime(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
