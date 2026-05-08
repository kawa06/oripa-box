/**
 * admin.js - 管理画面スクリプト
 * パック・カード・ユーザーの CRUD 操作と在庫管理を担当する
 */

// 現在の編集対象ユーザーID
let grantTargetUserId = null;

// ===== 初期化 =====
document.addEventListener('DOMContentLoaded', async () => {
  // 管理者チェック
  const user = getUser();
  if (!user) {
    window.location.href = '/frontend/login.html';
    return;
  }
  if (!user.is_admin) {
    // 最新情報で再チェック
    try {
      const me = await apiGet('/auth/me');
      if (!me.is_admin) {
        alert('管理者権限が必要です');
        window.location.href = '/frontend/index.html';
        return;
      }
      saveUser(me);
    } catch {
      window.location.href = '/frontend/index.html';
      return;
    }
  }

  // 管理リンク表示
  const adminLink = document.getElementById('nav-admin-link');
  if (adminLink) adminLink.classList.remove('hidden');

  // 初期データ読み込み
  loadUsers();
  loadAdminPacks();
  loadAdminPacksForSelect();
});

// ===== タブ切り替え =====
function switchTab(tabName) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById(`tab-${tabName}`).classList.remove('hidden');
  event.target.classList.add('active');

  if (tabName === 'cards') loadCards();
}

// ===== ユーザー管理 =====
async function loadUsers() {
  const wrap = document.getElementById('users-table-wrap');
  wrap.innerHTML = '<div class="flex-center" style="padding: 40px;"><div class="spinner"></div></div>';
  try {
    const users = await apiGet('/admin/users');
    if (!users.length) {
      wrap.innerHTML = '<p class="text-secondary text-center" style="padding: 24px;">ユーザーがいません</p>';
      return;
    }
    wrap.innerHTML = `
      <table class="admin-table">
        <thead><tr>
          <th>ID</th><th>ユーザー名</th><th>メール</th>
          <th>コイン</th><th>ポイント</th><th>管理者</th><th>登録日</th><th>操作</th>
        </tr></thead>
        <tbody>
          ${users.map(u => `
            <tr>
              <td>${u.id}</td>
              <td>${escapeHtml(u.username)}</td>
              <td>${escapeHtml(u.email)}</td>
              <td><span class="text-gold">${u.coin_balance}</span></td>
              <td>${u.points}</td>
              <td>${u.is_admin ? '<span class="badge-admin">管理者</span>' : '-'}</td>
              <td>${formatDate(u.created_at)}</td>
              <td>
                <button class="btn btn-primary" style="padding: 4px 12px; font-size: 0.8rem;"
                  onclick="openGrantModal(${u.id}, '${escapeHtml(u.username)}')">コイン付与</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    wrap.innerHTML = `<p style="color: var(--error); padding: 24px;">${err.message}</p>`;
  }
}

function openGrantModal(userId, username) {
  grantTargetUserId = userId;
  document.getElementById('grant-target-name').textContent = `対象: ${username}`;
  document.getElementById('grant-amount').value = '';
  document.getElementById('grant-desc').value = '';
  document.getElementById('grant-coin-modal').classList.remove('hidden');
}

function closeGrantModal() {
  grantTargetUserId = null;
  document.getElementById('grant-coin-modal').classList.add('hidden');
}

async function submitGrantCoins() {
  const amount = parseInt(document.getElementById('grant-amount').value);
  const desc = document.getElementById('grant-desc').value;
  if (!amount || amount < 1) {
    showAlert('admin-alert', 'コイン数を正しく入力してください', 'error');
    return;
  }
  try {
    const res = await apiPost('/admin/users/grant-coins', {
      user_id: grantTargetUserId,
      amount,
      description: desc || '管理者によるコイン付与'
    });
    closeGrantModal();
    showAlert('admin-alert', res.message, 'success');
    loadUsers();
  } catch (err) {
    showAlert('admin-alert', err.message, 'error');
  }
}

// ===== パック管理 =====
let packsCache = [];

async function loadAdminPacks() {
  const wrap = document.getElementById('packs-table-wrap');
  wrap.innerHTML = '<div class="flex-center" style="padding: 40px;"><div class="spinner"></div></div>';
  try {
    packsCache = await apiGet('/admin/packs');
    if (!packsCache.length) {
      wrap.innerHTML = '<p class="text-secondary text-center" style="padding: 24px;">パックがありません</p>';
      return;
    }
    wrap.innerHTML = `
      <table class="admin-table">
        <thead><tr>
          <th>ID</th><th>パック名</th><th>コイン</th><th>在庫</th><th>公開</th><th>操作</th>
        </tr></thead>
        <tbody>
          ${packsCache.map(p => `
            <tr>
              <td>${p.id}</td>
              <td>${escapeHtml(p.name)}</td>
              <td><span class="text-gold">${p.price_coins}</span></td>
              <td>${p.stock} / ${p.max_stock}</td>
              <td>${p.is_active ? '<span class="badge-active">公開</span>' : '<span class="badge-inactive">非公開</span>'}</td>
              <td style="display: flex; gap: 4px; flex-wrap: wrap;">
                <button class="btn btn-outline" style="padding: 4px 10px; font-size: 0.8rem;"
                  onclick="openPackModal(${p.id})">編集</button>
                <button class="btn btn-primary" style="padding: 4px 10px; font-size: 0.8rem;"
                  onclick="resetPackStock(${p.id}, '${escapeHtml(p.name)}')">在庫リセット</button>
                <button class="btn btn-danger" style="padding: 4px 10px; font-size: 0.8rem;"
                  onclick="deletePack(${p.id}, '${escapeHtml(p.name)}')">削除</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    wrap.innerHTML = `<p style="color: var(--error); padding: 24px;">${err.message}</p>`;
  }
}

function openPackModal(packId = null) {
  const modal = document.getElementById('pack-modal');
  const title = document.getElementById('pack-modal-title');
  document.getElementById('pack-edit-id').value = '';

  if (packId) {
    const pack = packsCache.find(p => p.id === packId);
    if (!pack) return;
    title.textContent = 'パック編集';
    document.getElementById('pack-edit-id').value = pack.id;
    document.getElementById('pack-name').value = pack.name;
    document.getElementById('pack-desc').value = pack.description || '';
    document.getElementById('pack-price').value = pack.price_coins;
    document.getElementById('pack-stock').value = pack.stock;
    document.getElementById('pack-max-stock').value = pack.max_stock;
    document.getElementById('pack-image-url').value = pack.image_url || '';
    document.getElementById('pack-is-active').checked = pack.is_active;
  } else {
    title.textContent = 'パック追加';
    document.getElementById('pack-name').value = '';
    document.getElementById('pack-desc').value = '';
    document.getElementById('pack-price').value = '';
    document.getElementById('pack-stock').value = '100';
    document.getElementById('pack-max-stock').value = '100';
    document.getElementById('pack-image-url').value = '';
    document.getElementById('pack-is-active').checked = true;
  }
  modal.classList.remove('hidden');
}

function closePackModal() {
  document.getElementById('pack-modal').classList.add('hidden');
}

async function submitPackForm() {
  const packId = document.getElementById('pack-edit-id').value;
  const body = {
    name: document.getElementById('pack-name').value,
    description: document.getElementById('pack-desc').value || null,
    price_coins: parseInt(document.getElementById('pack-price').value),
    stock: parseInt(document.getElementById('pack-stock').value),
    max_stock: parseInt(document.getElementById('pack-max-stock').value),
    image_url: document.getElementById('pack-image-url').value || null,
    is_active: document.getElementById('pack-is-active').checked
  };

  if (!body.name || !body.price_coins) {
    showAlert('admin-alert', 'パック名と必要コインは必須です', 'error');
    return;
  }

  try {
    if (packId) {
      await apiCall(`/admin/packs/${packId}`, { method: 'PUT', body: JSON.stringify(body) });
    } else {
      await apiCall('/admin/packs', { method: 'POST', body: JSON.stringify(body) });
    }
    closePackModal();
    showAlert('admin-alert', 'パックを保存しました', 'success');
    loadAdminPacks();
    loadAdminPacksForSelect();
  } catch (err) {
    showAlert('admin-alert', err.message, 'error');
  }
}

async function resetPackStock(packId, packName) {
  if (!confirm(`「${packName}」の在庫を最大値にリセットしますか？`)) return;
  try {
    const res = await apiCall(`/admin/packs/${packId}/reset-stock`, { method: 'POST', body: '{}' });
    showAlert('admin-alert', res.message, 'success');
    loadAdminPacks();
  } catch (err) {
    showAlert('admin-alert', err.message, 'error');
  }
}

async function deletePack(packId, packName) {
  if (!confirm(`「${packName}」を無効化しますか？（ガチャリストから非表示になります）`)) return;
  try {
    const res = await apiCall(`/admin/packs/${packId}`, { method: 'DELETE', body: '{}' });
    showAlert('admin-alert', res.message, 'success');
    loadAdminPacks();
  } catch (err) {
    showAlert('admin-alert', err.message, 'error');
  }
}

// ===== カード管理 =====
async function loadAdminPacksForSelect() {
  try {
    const packs = await apiGet('/admin/packs');
    const filter = document.getElementById('card-pack-filter');
    const packSelect = document.getElementById('card-pack-id');

    const options = packs.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
    if (filter) filter.innerHTML = '<option value="">全パック</option>' + options;
    if (packSelect) packSelect.innerHTML = options;
  } catch {}
}

async function loadCards() {
  const wrap = document.getElementById('cards-table-wrap');
  const packId = document.getElementById('card-pack-filter')?.value;
  wrap.innerHTML = '<div class="flex-center" style="padding: 40px;"><div class="spinner"></div></div>';
  try {
    const url = packId ? `/admin/cards?pack_id=${packId}` : '/admin/cards';
    const cards = await apiGet(url);
    if (!cards.length) {
      wrap.innerHTML = '<p class="text-secondary text-center" style="padding: 24px;">カードがありません</p>';
      return;
    }
    const rarityColors = { 'A賞': 'var(--rarity-ur)', 'B賞': 'var(--rarity-ssr)', 'C賞': 'var(--rarity-sr)', 'D賞': 'var(--rarity-r)', 'E賞': 'var(--rarity-n)' };
    wrap.innerHTML = `
      <table class="admin-table">
        <thead><tr>
          <th>ID</th><th>パック</th><th>カード名</th><th>レアリティ</th><th>確率</th><th>操作</th>
        </tr></thead>
        <tbody>
          ${cards.map(c => `
            <tr>
              <td>${c.id}</td>
              <td>${escapeHtml(c.pack_name)}</td>
              <td>${escapeHtml(c.name)}</td>
              <td><span style="color: ${rarityColors[c.rarity] || '#fff'}; font-weight: 700;">${c.rarity}</span></td>
              <td>${(c.probability * 100).toFixed(2)}%</td>
              <td style="display: flex; gap: 4px;">
                <button class="btn btn-outline" style="padding: 4px 10px; font-size: 0.8rem;"
                  onclick='openCardModal(${JSON.stringify(c)})'>編集</button>
                <button class="btn btn-danger" style="padding: 4px 10px; font-size: 0.8rem;"
                  onclick="deleteCard(${c.id}, '${escapeHtml(c.name)}')">削除</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  } catch (err) {
    wrap.innerHTML = `<p style="color: var(--error); padding: 24px;">${err.message}</p>`;
  }
}

function openCardModal(card = null) {
  const modal = document.getElementById('card-modal');
  const title = document.getElementById('card-modal-title');
  document.getElementById('card-edit-id').value = '';

  if (card && typeof card === 'object') {
    title.textContent = 'カード編集';
    document.getElementById('card-edit-id').value = card.id;
    document.getElementById('card-pack-id').value = card.pack_id;
    document.getElementById('card-name').value = card.name;
    document.getElementById('card-rarity').value = card.rarity;
    document.getElementById('card-probability').value = card.probability;
    document.getElementById('card-image-url').value = card.image_url || '';
    document.getElementById('card-description').value = card.description || '';
  } else {
    title.textContent = 'カード追加';
    document.getElementById('card-name').value = '';
    document.getElementById('card-rarity').value = 'E賞';
    document.getElementById('card-probability').value = '';
    document.getElementById('card-image-url').value = '';
    document.getElementById('card-description').value = '';
  }
  modal.classList.remove('hidden');
}

function closeCardModal() {
  document.getElementById('card-modal').classList.add('hidden');
}

async function submitCardForm() {
  const cardId = document.getElementById('card-edit-id').value;
  const body = {
    pack_id: parseInt(document.getElementById('card-pack-id').value),
    name: document.getElementById('card-name').value,
    rarity: document.getElementById('card-rarity').value,
    probability: parseFloat(document.getElementById('card-probability').value),
    image_url: document.getElementById('card-image-url').value || null,
    description: document.getElementById('card-description').value || null
  };

  if (!body.name || !body.probability) {
    showAlert('admin-alert', 'カード名と確率は必須です', 'error');
    return;
  }

  try {
    if (cardId) {
      await apiCall(`/admin/cards/${cardId}`, { method: 'PUT', body: JSON.stringify(body) });
    } else {
      await apiCall('/admin/cards', { method: 'POST', body: JSON.stringify(body) });
    }
    closeCardModal();
    showAlert('admin-alert', 'カードを保存しました', 'success');
    loadCards();
  } catch (err) {
    showAlert('admin-alert', err.message, 'error');
  }
}

async function deleteCard(cardId, cardName) {
  if (!confirm(`カード「${cardName}」を削除しますか？`)) return;
  try {
    const res = await apiCall(`/admin/cards/${cardId}`, { method: 'DELETE', body: '{}' });
    showAlert('admin-alert', res.message, 'success');
    loadCards();
  } catch (err) {
    showAlert('admin-alert', err.message, 'error');
  }
}

// ===== ユーティリティ =====
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleDateString('ja-JP');
}
