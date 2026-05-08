/**
 * collection.js - カード管理画面スクリプト
 * 所持カード一覧の表示・コイン変換・発送申請を担当する
 */

let currentRarity = '';
// 変換・申請対象カードのID（モーダルで使用）
let pendingConvertCardId = null;
let pendingShipCardId = null;

document.addEventListener('DOMContentLoaded', async () => {
  requireAuth();
  // 管理者リンク表示制御
  const user = getUser();
  if (user && user.is_admin) {
    const adminLink = document.getElementById('nav-admin-link');
    if (adminLink) adminLink.classList.remove('hidden');
  }

  await loadStats();
  await loadCollection('');
});

// ===== コレクション統計 =====
async function loadStats() {
  const el = document.getElementById('collection-stats');
  try {
    const stats = await apiGet('/collection/stats');
    const rarityColors = {
      'A賞': 'var(--rarity-ur)', 'B賞': 'var(--rarity-ssr)',
      'C賞': 'var(--rarity-sr)', 'D賞': 'var(--rarity-r)', 'E賞': 'var(--rarity-n)'
    };
    el.innerHTML = `
      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-label">合計</span>
          <span class="stat-value">${stats.total}</span>
        </div>
        ${['A賞','B賞','C賞','D賞','E賞'].map(r => `
          <div class="stat-item">
            <span class="stat-label" style="color: ${rarityColors[r]}">${r}</span>
            <span class="stat-value" style="color: ${rarityColors[r]}">${stats[r] || 0}</span>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    el.innerHTML = '<p style="color: var(--text-secondary); padding: 8px;">統計の読み込みに失敗しました</p>';
  }
}

// ===== コレクション読み込み =====
async function loadCollection(rarity) {
  currentRarity = rarity;
  const grid = document.getElementById('collection-grid');
  grid.innerHTML = '<div class="flex-center" style="grid-column: 1 / -1; padding: 60px;"><div class="spinner"></div></div>';

  try {
    const url = rarity ? `/collection?rarity=${encodeURIComponent(rarity)}` : '/collection';
    const cards = await apiGet(url);

    if (!cards.length) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px; color: var(--text-secondary);">
          <p style="font-size: 3rem; margin-bottom: 16px;">📭</p>
          <p>カードがありません</p>
          <a href="/frontend/gacha.html" class="btn btn-primary" style="margin-top: 16px; display: inline-flex;">ガチャを引く</a>
        </div>
      `;
      return;
    }

    grid.innerHTML = cards.map(card => buildCollectionCard(card)).join('');
  } catch (err) {
    grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--error); padding: 40px;">${err.message}</div>`;
  }
}

// ===== カードHTML生成 =====
function buildCollectionCard(card) {
  const rarityColors = {
    'A賞': 'var(--rarity-ur)', 'B賞': 'var(--rarity-ssr)',
    'C賞': 'var(--rarity-sr)', 'D賞': 'var(--rarity-r)', 'E賞': 'var(--rarity-n)'
  };
  const color = rarityColors[card.card_rarity] || '#fff';
  const imgTag = card.card_image_url
    ? `<img src="${card.card_image_url}" alt="${escapeHtml(card.card_name)}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;">`
    : `<span style="font-size:3rem;">🃏</span>`;

  // ステータス表示
  const statusInfo = getStatusInfo(card.status);

  // ステータスによってボタンを変更する
  let actionButtons = '';
  if (card.status === 'owned') {
    actionButtons = `
      <div style="display: flex; gap: 6px; margin-top: 8px;">
        <button
          class="btn btn-primary"
          style="flex: 1; padding: 6px 4px; font-size: 0.75rem;"
          onclick="openConvertModal(${card.id}, '${escapeHtml(card.card_name)}', '${card.card_rarity}', ${card.coin_value})"
        >コイン変換</button>
        <button
          class="btn btn-outline"
          style="flex: 1; padding: 6px 4px; font-size: 0.75rem;"
          onclick="openShipModal(${card.id}, '${escapeHtml(card.card_name)}', '${card.card_rarity}')"
        >発送申請</button>
      </div>
    `;
  } else {
    // 発送申請中・発送済みはステータスのみ表示
    actionButtons = `
      <div style="margin-top: 8px; text-align: center;">
        <span style="
          display: inline-block;
          padding: 4px 10px;
          border-radius: 20px;
          font-size: 0.75rem;
          font-weight: 600;
          background: ${statusInfo.bg};
          color: ${statusInfo.color};
        ">${statusInfo.label}</span>
      </div>
    `;
  }

  return `
    <div class="collection-card rarity-${card.card_rarity}">
      <div class="collection-card-art">
        ${imgTag}
        ${card.count > 1 ? `<span class="card-count-badge">×${card.count}</span>` : ''}
      </div>
      <div class="collection-card-info">
        <span class="rarity-badge" style="font-size: 0.7rem;">${card.card_rarity}</span>
        <p class="collection-card-name">${escapeHtml(card.card_name)}</p>
        <p class="collection-card-pack">${escapeHtml(card.pack_name)}</p>
        <p style="font-size: 0.75rem; color: var(--accent-gold, #f9d923); margin: 2px 0;">${card.coin_value}コイン相当</p>
      </div>
      ${actionButtons}
    </div>
  `;
}

// ===== ステータス表示情報 =====
function getStatusInfo(status) {
  switch (status) {
    case 'shipping_requested':
      return { label: '発送待ち', color: '#fbbf24', bg: 'rgba(251,191,36,0.15)' };
    case 'shipped':
      return { label: '発送済み', color: '#34d399', bg: 'rgba(52,211,153,0.15)' };
    default:
      return { label: '所持中', color: '#a0aec0', bg: 'rgba(160,174,192,0.15)' };
  }
}

// ===== フィルター =====
function filterCollection(rarity) {
  // フィルターボタンの状態更新
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.rarity === rarity);
  });
  loadCollection(rarity);
}

// ===== コイン変換モーダル =====
function openConvertModal(cardId, cardName, rarity, coinValue) {
  pendingConvertCardId = cardId;
  document.getElementById('convert-modal-text').textContent =
    `「${cardName}（${rarity}）」を ${coinValue} コインに変換しますか？この操作は取り消せません。`;
  document.getElementById('convert-modal').style.display = 'flex';
}

function closeConvertModal() {
  pendingConvertCardId = null;
  document.getElementById('convert-modal').style.display = 'none';
}

async function submitConvert() {
  if (!pendingConvertCardId) return;
  const cardId = pendingConvertCardId;
  closeConvertModal();

  try {
    const res = await apiPost('/collection/convert', { user_card_id: cardId });
    // コイン残高を更新してナビバーに反映
    const user = getUser();
    if (user) {
      user.coin_balance = res.new_balance;
      saveUser(user);
      const balanceEl = document.getElementById('coin-balance-display');
      if (balanceEl) balanceEl.textContent = res.new_balance;
    }
    alert(res.message);
    // カード一覧を再読み込み
    await loadStats();
    await loadCollection(currentRarity);
  } catch (err) {
    alert(`変換に失敗しました: ${err.message}`);
  }
}

// ===== 発送申請モーダル =====
async function openShipModal(cardId, cardName, rarity) {
  pendingShipCardId = cardId;
  document.getElementById('ship-modal-card-name').textContent = `対象カード: ${cardName}（${rarity}）`;
  // アラートをリセット
  const alertEl = document.getElementById('ship-modal-alert');
  if (alertEl) alertEl.className = 'alert';

  // 保存済み住所を自動入力
  try {
    const address = await apiGet('/collection/address');
    if (address) {
      document.getElementById('ship-name').value = address.name || '';
      document.getElementById('ship-postal').value = address.postal_code || '';
      document.getElementById('ship-prefecture').value = address.prefecture || '';
      document.getElementById('ship-city').value = address.city || '';
      document.getElementById('ship-address').value = address.address || '';
      document.getElementById('ship-building').value = address.building || '';
      document.getElementById('ship-phone').value = address.phone || '';
    }
  } catch (e) {
    // 住所取得失敗は無視（空のフォームを表示）
  }

  document.getElementById('ship-modal').style.display = 'flex';
}

function closeShipModal() {
  pendingShipCardId = null;
  document.getElementById('ship-modal').style.display = 'none';
}

async function submitShipRequest() {
  if (!pendingShipCardId) return;

  // フォームバリデーション
  const name = document.getElementById('ship-name').value.trim();
  const postal = document.getElementById('ship-postal').value.trim();
  const prefecture = document.getElementById('ship-prefecture').value;
  const city = document.getElementById('ship-city').value.trim();
  const addr = document.getElementById('ship-address').value.trim();
  const building = document.getElementById('ship-building').value.trim();
  const phone = document.getElementById('ship-phone').value.trim();

  if (!name || !postal || !prefecture || !city || !addr || !phone) {
    showAlert('ship-modal-alert', '必須項目をすべて入力してください', 'error');
    return;
  }

  try {
    // 住所を保存
    const savedAddr = await apiPost('/collection/address', {
      name, postal_code: postal, prefecture, city,
      address: addr, building: building || null, phone
    });

    // 発送申請を送信
    const res = await apiPost('/collection/ship', {
      user_card_id: pendingShipCardId,
      address_id: savedAddr.id
    });

    closeShipModal();
    alert(res.message);
    // カード一覧を再読み込み
    await loadStats();
    await loadCollection(currentRarity);
  } catch (err) {
    showAlert('ship-modal-alert', `申請に失敗しました: ${err.message}`, 'error');
  }
}

// ===== HTMLエスケープ =====
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
