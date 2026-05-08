/**
 * ranking.js - ランキング画面スクリプト
 * A賞カード保有数ランキングを表示する
 */

document.addEventListener('DOMContentLoaded', async () => {
  // 管理者リンク表示制御
  const user = getUser();
  if (user && user.is_admin) {
    const adminLink = document.getElementById('nav-admin-link');
    if (adminLink) adminLink.classList.remove('hidden');
  }

  await loadRanking();
});

async function loadRanking() {
  const container = document.getElementById('ranking-list');
  try {
    const ranking = await apiGet('/ranking/ur');

    if (!ranking.length) {
      container.innerHTML = '<p class="text-secondary text-center" style="padding: 60px;">まだランキングデータがありません</p>';
      return;
    }

    // 自分のユーザー名を取得
    const me = getUser();

    const medalEmojis = ['🥇', '🥈', '🥉'];

    container.innerHTML = `
      <div class="ranking-table">
        ${ranking.map(entry => {
          const medal = entry.rank <= 3 ? medalEmojis[entry.rank - 1] : `#${entry.rank}`;
          const isMe = me && entry.username === me.username;
          return `
            <div class="ranking-row ${isMe ? 'ranking-row-me' : ''}">
              <span class="ranking-rank">${medal}</span>
              <span class="ranking-username">${entry.username}${isMe ? ' (あなた)' : ''}</span>
              <span class="ranking-ur-count">
                <span style="color: var(--rarity-ur); font-weight: 800;">${entry.ur_count}</span>
                <span style="color: var(--text-secondary); font-size: 0.85rem;"> A賞</span>
              </span>
            </div>
          `;
        }).join('')}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<p style="color: var(--error); text-align: center; padding: 40px;">${err.message}</p>`;
  }
}
