/**
 * history.js - ガチャ履歴画面スクリプト
 * 過去に引いたカードの一覧を表示する
 */

document.addEventListener('DOMContentLoaded', async () => {
  requireAuth();
  // 管理者リンク表示制御
  const user = getUser();
  if (user && user.is_admin) {
    const adminLink = document.getElementById('nav-admin-link');
    if (adminLink) adminLink.classList.remove('hidden');
  }

  await loadHistory();
});

async function loadHistory() {
  const container = document.getElementById('history-list');
  try {
    const history = await apiGet('/gacha/history');

    if (!history.length) {
      container.innerHTML = `
        <div style="text-align: center; padding: 60px; color: var(--text-secondary);">
          <p style="font-size: 3rem; margin-bottom: 16px;">🎲</p>
          <p>まだガチャを引いていません</p>
          <a href="/frontend/gacha.html" class="btn btn-gold" style="margin-top: 16px; display: inline-flex;">ガチャを引く</a>
        </div>
      `;
      return;
    }

    const rarityColors = {
      UR: 'var(--rarity-ur)', SSR: 'var(--rarity-ssr)',
      SR: 'var(--rarity-sr)', R: 'var(--rarity-r)', N: 'var(--rarity-n)'
    };

    container.innerHTML = history.map(item => {
      const color = rarityColors[item.card_rarity] || '#fff';
      const imgTag = item.card_image_url
        ? `<img src="${item.card_image_url}" alt="${item.card_name}" class="history-card-img">`
        : `<span class="history-rarity-dot ${item.card_rarity}"></span>`;

      return `
        <div class="history-item fade-in">
          ${imgTag}
          <div style="flex: 1; min-width: 0;">
            <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
              <span class="rarity-badge" style="background: ${color}22; color: ${color}; border: 1px solid ${color}; padding: 2px 8px; font-size: 0.7rem;">${item.card_rarity}</span>
              <span style="font-weight: 700; color: ${color};">${item.card_name}</span>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px;">
              ${item.pack_name} · ${item.coins_spent}コイン消費
            </p>
          </div>
          <span style="color: var(--text-secondary); font-size: 0.8rem; white-space: nowrap; flex-shrink: 0;">
            ${formatDateTime(item.created_at)}
          </span>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<p style="color: var(--error); text-align: center; padding: 40px;">${err.message}</p>`;
  }
}

function formatDateTime(iso) {
  const d = new Date(iso);
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}/${pad(d.getMonth()+1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
