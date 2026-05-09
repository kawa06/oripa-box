/**
 * collection.js - カード管理画面スクリプト
 * 所持カード一覧の表示・コイン変換・発送申請・一括操作を担当する
 * ドラッグ/スワイプでなぞって複数選択に対応
 */

let currentRarity = '';
// 変換・申請対象カードのID（モーダルで使用）
let pendingConvertCardId = null;
let pendingShipCardId = null;
// 一括操作モード: 'convert' または 'ship'
let bulkShipMode = false;
// 選択中のカードIDセット
const selectedCardIds = new Set();
// 現在表示中のカード一覧（全件）
let currentCards = [];

// ===== ドラッグ選択用の状態管理 =====
let isDragging = false;          // ドラッグ中かどうか
let dragStartedOnCard = false;   // カード上でドラッグ開始したか

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

  // ===== ドラッグ/スワイプでなぞり選択のイベント登録 =====
  // グリッドに対して pointerdown/pointermove/pointerup を監視する
  const grid = document.getElementById('collection-grid');
  if (grid) {
    // pointerdown: ドラッグ開始
    grid.addEventListener('pointerdown', (e) => {
      const card = e.target.closest('.collection-card');
      if (card && card.querySelector('.card-checkbox')) {
        // owned カードの上でドラッグ開始
        isDragging = true;
        dragStartedOnCard = true;
        // スクロールを妨げないように setPointerCapture は不使用
        // タッチのデフォルトスクロールを抑制（グリッド上のみ）
        e.preventDefault();
      } else {
        isDragging = false;
        dragStartedOnCard = false;
      }
    });

    // pointermove: なぞり中にカードを選択する
    grid.addEventListener('pointermove', (e) => {
      if (!isDragging || !dragStartedOnCard) return;
      // pointer の位置にある要素を取得
      const el = document.elementFromPoint(e.clientX, e.clientY);
      if (!el) return;
      const card = el.closest('.collection-card');
      if (!card) return;
      const chk = card.querySelector('.card-checkbox');
      if (!chk || chk.checked) return; // 既に選択済みはスキップ
      // カードIDを取得して選択状態に
      const cardId = parseInt(card.id.replace('card-wrap-', ''), 10);
      if (isNaN(cardId)) return;
      chk.checked = true;
      toggleCardSelection(cardId, true);
    });

    // pointerup: ドラッグ終了
    grid.addEventListener('pointerup', () => {
      isDragging = false;
      dragStartedOnCard = false;
    });

    // pointercancel: タッチキャンセル時
    grid.addEventListener('pointercancel', () => {
      isDragging = false;
      dragStartedOnCard = false;
    });
  }
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
  // 選択状態をリセット
  selectedCardIds.clear();
  updateSelectedCount();

  const grid = document.getElementById('collection-grid');
  grid.innerHTML = '<div class="flex-center" style="grid-column: 1 / -1; padding: 60px;"><div class="spinner"></div></div>';

  try {
    const url = rarity ? `/collection?rarity=${encodeURIComponent(rarity)}` : '/collection';
    currentCards = await apiGet(url);

    if (!currentCards.length) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 60px; color: var(--text-secondary);">
          <p style="font-size: 3rem; margin-bottom: 16px;">📭</p>
          <p>カードがありません</p>
          <a href="/frontend/gacha.html" class="btn btn-primary" style="margin-top: 16px; display: inline-flex;">ガチャを引く</a>
        </div>
      `;
      return;
    }

    grid.innerHTML = currentCards.map(card => buildCollectionCard(card)).join('');
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

  // チェックボックス（owned カードのみ選択可能）
  const checkboxHtml = card.status === 'owned'
    ? `<div class="card-checkbox-wrap">
        <input type="checkbox" class="card-checkbox" id="chk-${card.id}"
          onchange="toggleCardSelection(${card.id}, this.checked)">
      </div>`
    : '';

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
    <div class="collection-card rarity-${card.card_rarity}" id="card-wrap-${card.id}">
      ${checkboxHtml}
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

// ===== チェックボックス・選択管理 =====

/** カードの選択状態を切り替える */
function toggleCardSelection(cardId, checked) {
  if (checked) {
    selectedCardIds.add(cardId);
  } else {
    selectedCardIds.delete(cardId);
  }
  // カード外枠のスタイルを更新
  const wrap = document.getElementById(`card-wrap-${cardId}`);
  if (wrap) wrap.classList.toggle('card-selected', checked);
  updateSelectedCount();
}

/** 表示中の owned カードを全選択する */
function selectAllCards() {
  currentCards.forEach(card => {
    if (card.status !== 'owned') return;
    selectedCardIds.add(card.id);
    const chk = document.getElementById(`chk-${card.id}`);
    if (chk) chk.checked = true;
    const wrap = document.getElementById(`card-wrap-${card.id}`);
    if (wrap) wrap.classList.add('card-selected');
  });
  updateSelectedCount();
}

/** 全解除 */
function deselectAllCards() {
  selectedCardIds.clear();
  document.querySelectorAll('.card-checkbox').forEach(chk => { chk.checked = false; });
  document.querySelectorAll('.collection-card').forEach(wrap => wrap.classList.remove('card-selected'));
  updateSelectedCount();
}

/** 選択枚数表示を更新する */
function updateSelectedCount() {
  const el = document.getElementById('selected-count');
  if (el) el.textContent = selectedCardIds.size;
}

// ===== コイン変換モーダル（単体） =====
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

// ===== 一括コイン変換 =====

/** 選択中のカードを一括変換 */
function bulkConvertSelected() {
  if (selectedCardIds.size === 0) {
    alert('変換するカードを選択してください');
    return;
  }
  openBulkConvertModal(Array.from(selectedCardIds));
}

/** 全 owned カードを一括変換 */
function bulkConvertAll() {
  const ids = currentCards.filter(c => c.status === 'owned').map(c => c.id);
  if (ids.length === 0) {
    alert('変換できるカードがありません');
    return;
  }
  openBulkConvertModal(ids);
}

let pendingBulkConvertIds = [];

function openBulkConvertModal(ids) {
  pendingBulkConvertIds = ids;
  document.getElementById('bulk-convert-modal-text').textContent =
    `${ids.length}枚のカードをまとめてコインに変換しますか？この操作は取り消せません。`;
  document.getElementById('bulk-convert-modal').style.display = 'flex';
}

function closeBulkConvertModal() {
  pendingBulkConvertIds = [];
  document.getElementById('bulk-convert-modal').style.display = 'none';
}

async function submitBulkConvert() {
  if (!pendingBulkConvertIds.length) return;
  const ids = pendingBulkConvertIds;
  closeBulkConvertModal();

  try {
    const res = await apiPost('/collection/convert-bulk', { card_ids: ids });
    // コイン残高を更新
    const user = getUser();
    if (user) {
      user.coin_balance = res.new_balance;
      saveUser(user);
      const balanceEl = document.getElementById('coin-balance-display');
      if (balanceEl) balanceEl.textContent = res.new_balance;
    }
    alert(res.message);
    await loadStats();
    await loadCollection(currentRarity);
  } catch (err) {
    alert(`一括変換に失敗しました: ${err.message}`);
  }
}

// ===== 発送申請モーダル（単体・一括共用） =====

/** 単体の発送申請を開く */
async function openShipModal(cardId, cardName, rarity) {
  bulkShipMode = false;
  pendingShipCardId = cardId;
  document.getElementById('ship-modal-card-name').textContent = `対象カード: ${cardName}（${rarity}）`;
  await _prepareShipModal();
}

/** 選択したカードを一括発送申請 */
async function bulkShipSelected() {
  if (selectedCardIds.size === 0) {
    alert('発送申請するカードを選択してください');
    return;
  }
  bulkShipMode = true;
  pendingShipCardId = Array.from(selectedCardIds);
  document.getElementById('ship-modal-card-name').textContent = `${pendingShipCardId.length}枚のカードを発送申請します`;
  await _prepareShipModal();
}

/** 全 owned カードを一括発送申請 */
async function bulkShipAll() {
  const ids = currentCards.filter(c => c.status === 'owned').map(c => c.id);
  if (ids.length === 0) {
    alert('発送申請できるカードがありません');
    return;
  }
  bulkShipMode = true;
  pendingShipCardId = ids;
  document.getElementById('ship-modal-card-name').textContent = `${ids.length}枚のカードを一括発送申請します`;
  await _prepareShipModal();
}

/** 発送モーダルの住所フォームを準備する共通処理 */
async function _prepareShipModal() {
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
  bulkShipMode = false;
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

    if (bulkShipMode) {
      // 一括発送申請
      const ids = Array.isArray(pendingShipCardId) ? pendingShipCardId : [pendingShipCardId];
      const res = await apiPost('/collection/ship-bulk', {
        card_ids: ids,
        address_id: savedAddr.id
      });
      closeShipModal();
      alert(res.message);
    } else {
      // 単体発送申請
      const res = await apiPost('/collection/ship', {
        user_card_id: pendingShipCardId,
        address_id: savedAddr.id
      });
      closeShipModal();
      alert(res.message);
    }

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
