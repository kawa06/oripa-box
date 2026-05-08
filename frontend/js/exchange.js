/**
 * exchange.js - ポイント交換所スクリプト
 * カードのポイント変換と、ポイントでのカード入手を担当する
 */

let allShopCards = [];
let currentShopRarity = '';

document.addEventListener('DOMContentLoaded', async () => {
  requireAuth();
  // 管理者リンク表示制御
  const user = getUser();
  if (user && user.is_admin) {
    const adminLink = document.getElementById('nav-admin-link');
    if (adminLink) adminLink.classList.remove('hidden');
  }

  await loadPointBalance();
  await loadConvertCards();
});

// ===== ポイント残高 =====
async function loadPointBalance() {
  try {
    const res = await apiGet('/exchange/point-balance');
    document.getElementById('point-balance-display').textContent = res.points;
  } catch {}
}

// ===== タブ切り替え =====
function switchExchangeTab(tab) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.remove('hidden');
  event.target.classList.add('active');

  if (tab === 'shop') loadShopCards('');
}

// ===== カード→ポイント変換 =====
async function loadConvertCards() {
  const grid = document.getElementById('convert-grid');
  try {
    const cards = await apiGet('/collection');
    if (!cards.length) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px; color: var(--text-secondary);">
          <p>変換できるカードがありません</p>
          <a href="/frontend/gacha.html" class="btn btn-primary" style="margin-top: 16px; display: inline-flex;">ガチャを引く</a>
        </div>
      `;
      return;
    }

    const rarityPoints = { 'E賞': 10, 'D賞': 30, 'C賞': 100, 'B賞': 300, 'A賞': 1000 };
    grid.innerHTML = cards.map(card => {
      const pts = rarityPoints[card.card_rarity] || 10;
      const imgTag = card.card_image_url
        ? `<img src="${card.card_image_url}" alt="${card.card_name}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;">`
        : `<span style="font-size:2.5rem;">🃏</span>`;
      return `
        <div class="collection-card rarity-${card.card_rarity}" style="position: relative;">
          <div class="collection-card-art">${imgTag}
            ${card.count > 1 ? `<span class="card-count-badge">×${card.count}</span>` : ''}
          </div>
          <div class="collection-card-info">
            <span class="rarity-badge" style="font-size: 0.7rem;">${card.card_rarity}</span>
            <p class="collection-card-name">${card.card_name}</p>
            <p class="collection-card-pack">${card.pack_name}</p>
          </div>
          <button class="btn btn-primary" style="width: 100%; padding: 8px; font-size: 0.85rem; border-radius: 0 0 12px 12px; margin-top: 8px;"
            onclick="convertCard(${card.id})">
            +${pts} pt に変換
          </button>
        </div>
      `;
    }).join('');
  } catch (err) {
    grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--error); padding: 40px;">${err.message}</div>`;
  }
}

async function convertCard(userCardId) {
  if (!confirm('このカードをポイントに変換しますか？（1枚分を変換します）')) return;
  try {
    const res = await apiPost('/exchange/convert', { user_card_id: userCardId });
    showAlert('exchange-alert', res.message, 'success');
    document.getElementById('point-balance-display').textContent = res.total_points;
    await loadConvertCards();
  } catch (err) {
    showAlert('exchange-alert', err.message, 'error');
  }
}

// ===== ポイントでカード入手 =====
async function loadShopCards(rarity) {
  currentShopRarity = rarity;
  const grid = document.getElementById('shop-grid');
  grid.innerHTML = '<div class="flex-center" style="grid-column: 1 / -1; padding: 60px;"><div class="spinner"></div></div>';

  try {
    if (!allShopCards.length) {
      allShopCards = await apiGet('/exchange/available-cards');
    }
    // 現在のポイント再取得
    const balanceRes = await apiGet('/exchange/point-balance');
    const currentPoints = balanceRes.points;
    document.getElementById('point-balance-display').textContent = currentPoints;

    const filtered = rarity ? allShopCards.filter(c => c.rarity === rarity) : allShopCards;
    if (!filtered.length) {
      grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-secondary);">カードがありません</div>';
      return;
    }

    grid.innerHTML = filtered.map(card => {
      const canAfford = currentPoints >= card.exchange_cost;
      const imgTag = card.image_url
        ? `<img src="${card.image_url}" alt="${card.name}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;">`
        : `<span style="font-size:2.5rem;">🃏</span>`;
      return `
        <div class="collection-card rarity-${card.rarity}" style="${canAfford ? '' : 'opacity: 0.6;'}">
          <div class="collection-card-art">${imgTag}</div>
          <div class="collection-card-info">
            <span class="rarity-badge" style="font-size: 0.7rem;">${card.rarity}</span>
            <p class="collection-card-name">${card.name}</p>
            <p class="collection-card-pack">${card.pack_name}</p>
          </div>
          <button class="btn ${canAfford ? 'btn-gold' : 'btn-outline'}" style="width: 100%; padding: 8px; font-size: 0.85rem; border-radius: 0 0 12px 12px; margin-top: 8px;"
            onclick="getCard(${card.id})" ${canAfford ? '' : 'disabled'}>
            ${card.exchange_cost} pt で入手
          </button>
        </div>
      `;
    }).join('');
  } catch (err) {
    grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; color: var(--error); padding: 40px;">${err.message}</div>`;
  }
}

async function getCard(cardId) {
  if (!confirm('ポイントを消費してこのカードを入手しますか？')) return;
  try {
    const res = await apiPost('/exchange/get-card', { card_id: cardId });
    showAlert('exchange-alert', res.message, 'success');
    document.getElementById('point-balance-display').textContent = res.remaining_points;
    allShopCards = []; // キャッシュクリア
    await loadShopCards(currentShopRarity);
  } catch (err) {
    showAlert('exchange-alert', err.message, 'error');
  }
}

function filterShop(rarity) {
  document.querySelectorAll('#tab-shop .filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.rarity === rarity);
  });
  loadShopCards(rarity);
}
