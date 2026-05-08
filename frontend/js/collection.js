/**
 * collection.js - コレクション画面スクリプト
 * 所持カード一覧の表示・レアリティフィルタを担当する
 */

let currentRarity = '';

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
      UR: 'var(--rarity-ur)', SSR: 'var(--rarity-ssr)',
      SR: 'var(--rarity-sr)', R: 'var(--rarity-r)', N: 'var(--rarity-n)'
    };
    el.innerHTML = `
      <div class="stats-row">
        <div class="stat-item">
          <span class="stat-label">合計</span>
          <span class="stat-value">${stats.total}</span>
        </div>
        ${['UR','SSR','SR','R','N'].map(r => `
          <div class="stat-item">
            <span class="stat-label" style="color: ${rarityColors[r]}">${r}</span>
            <span class="stat-value" style="color: ${rarityColors[r]}">${stats[r]}</span>
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
    const url = rarity ? `/collection?rarity=${rarity}` : '/collection';
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

function buildCollectionCard(card) {
  const rarityColors = {
    UR: 'var(--rarity-ur)', SSR: 'var(--rarity-ssr)',
    SR: 'var(--rarity-sr)', R: 'var(--rarity-r)', N: 'var(--rarity-n)'
  };
  const color = rarityColors[card.card_rarity] || '#fff';
  const imgTag = card.card_image_url
    ? `<img src="${card.card_image_url}" alt="${card.card_name}" style="width:100%;height:100%;object-fit:cover;border-radius:8px;">`
    : `<span style="font-size:3rem;">🃏</span>`;

  return `
    <div class="collection-card rarity-${card.card_rarity}">
      <div class="collection-card-art">
        ${imgTag}
        ${card.count > 1 ? `<span class="card-count-badge">×${card.count}</span>` : ''}
      </div>
      <div class="collection-card-info">
        <span class="rarity-badge" style="font-size: 0.7rem;">${card.card_rarity}</span>
        <p class="collection-card-name">${card.card_name}</p>
        <p class="collection-card-pack">${card.pack_name}</p>
      </div>
    </div>
  `;
}

// ===== フィルター =====
function filterCollection(rarity) {
  // フィルターボタンの状態更新
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.rarity === rarity);
  });
  loadCollection(rarity);
}
