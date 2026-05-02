/**
 * gacha.js - ガチャ実行 + カード開封アニメーション
 * 
 * 演出の流れ:
 * 1. ガチャボタンをクリック
 * 2. APIを呼び出してカード抽選
 * 3. 暗転ステージが表示され、カード裏面が現れる
 * 4. カードをクリックするとフリップして表が見える
 * 5. レアリティに応じたエフェクトが発動
 */

// 現在選択中のパックID
let selectedPackId = null;

document.addEventListener('DOMContentLoaded', async () => {
  // 認証チェック
  if (!requireAuth()) return;

  // パック一覧を読み込む
  await loadPacks();

  // ガチャボタンのイベント
  const gachaBtn = document.getElementById('gacha-btn');
  if (gachaBtn) {
    gachaBtn.addEventListener('click', executeGacha);
  }

  // ガチャ履歴を読み込む
  await loadGachaHistory();
});

/**
 * パック一覧を取得してセレクターを表示する
 */
async function loadPacks() {
  const container = document.getElementById('pack-selector-area');
  if (!container) return;

  try {
    const packs = await apiGet('/packs/');

    if (packs.length === 0) {
      container.innerHTML = '<p class="text-secondary text-center">現在利用可能なパックはありません</p>';
      return;
    }

    container.innerHTML = packs.map(pack => `
      <div class="pack-card" onclick="selectPack(${pack.id}, this)"
           data-pack-id="${pack.id}"
           data-price="${pack.price_coins}"
           style="cursor: pointer;">
        <div class="pack-image">
          <span>${getPackEmoji(pack.name)}</span>
          ${pack.stock === 0 ? '<span class="badge-soldout">SOLD OUT</span>' : ''}
        </div>
        <div class="pack-body">
          <h3 class="pack-name">${pack.name}</h3>
          <p class="pack-description">${pack.description || ''}</p>
          <div class="stock-bar">
            <div class="stock-bar-label">
              <span>在庫</span>
              <span>${pack.stock} / ${pack.max_stock}口</span>
            </div>
            <div class="stock-bar-track">
              <div class="stock-bar-fill ${pack.stock / pack.max_stock < 0.2 ? 'low' : ''}"
                   style="width: ${(pack.stock / pack.max_stock) * 100}%"></div>
            </div>
          </div>
        </div>
        <div class="pack-footer">
          <span class="price-tag">🪙 ${pack.price_coins}コイン</span>
          ${pack.stock > 0
            ? `<button class="btn btn-primary" onclick="selectPack(${pack.id}, this.closest('.pack-card')); event.stopPropagation();">選択</button>`
            : `<button class="btn btn-outline" disabled>売り切れ</button>`
          }
        </div>
      </div>
    `).join('');

  } catch (err) {
    container.innerHTML = `<p style="color: var(--error);">パックの読み込みに失敗しました: ${err.message}</p>`;
  }
}

/**
 * パック名からデコレーション用絵文字を返す
 */
function getPackEmoji(name) {
  if (name.includes('プレミアム')) return '💎';
  if (name.includes('限定') || name.includes('コレクション')) return '🌟';
  return '🎴';
}

/**
 * パックを選択する
 */
function selectPack(packId, cardEl) {
  // 前の選択を解除
  document.querySelectorAll('.pack-card.selected').forEach(el => {
    el.classList.remove('selected');
    el.style.borderColor = '';
  });

  // 新しいパックを選択
  selectedPackId = packId;
  const targetCard = cardEl.closest ? cardEl.closest('.pack-card') : cardEl;
  if (targetCard) {
    targetCard.style.borderColor = 'var(--accent-purple)';
    targetCard.classList.add('selected');
  }

  // ガチャボタンを有効化
  const gachaBtn = document.getElementById('gacha-btn');
  const packData = document.querySelector(`.pack-card[data-pack-id="${packId}"]`);
  const price = packData?.dataset.price || '?';
  if (gachaBtn) {
    gachaBtn.disabled = false;
    gachaBtn.innerHTML = `🎲 ガチャを引く（${price}コイン）`;
  }

  // 選択パック名を表示
  const selectedName = document.querySelector(`.pack-card[data-pack-id="${packId}"] .pack-name`)?.textContent;
  const selectedInfo = document.getElementById('selected-pack-info');
  if (selectedInfo && selectedName) {
    selectedInfo.textContent = `選択中: ${selectedName}`;
    selectedInfo.classList.remove('hidden');
  }
}

/**
 * ガチャを実行する
 */
async function executeGacha() {
  if (!selectedPackId) {
    showAlert('gacha-alert', 'パックを選択してください');
    return;
  }

  const gachaBtn = document.getElementById('gacha-btn');
  setButtonLoading(gachaBtn, true);

  try {
    // APIを呼び出してガチャを実行
    const result = await apiPost('/gacha/draw', { pack_id: selectedPackId });

    // 開封演出を表示
    showGachaAnimation(result);

    // コイン残高を更新
    const coinEl = document.getElementById('coin-balance-display');
    if (coinEl) coinEl.textContent = result.remaining_balance;
    const user = getUser();
    if (user) {
      user.coin_balance = result.remaining_balance;
      saveUser(user);
    }

    // パックの在庫を更新
    updatePackStock(selectedPackId, result.pack_remaining_stock);

    // ガチャ履歴を再読み込み
    await loadGachaHistory();

  } catch (err) {
    showAlert('gacha-alert', err.message);
  } finally {
    setButtonLoading(gachaBtn, false, '🎲 ガチャを引く');
    // ガチャボタンを無効化（選択し直しが必要）
    gachaBtn.disabled = selectedPackId === null;
  }
}

/**
 * パックの在庫表示を更新する
 */
function updatePackStock(packId, newStock) {
  const packCard = document.querySelector(`.pack-card[data-pack-id="${packId}"]`);
  if (!packCard) return;

  const maxStock = 100;
  const fillEl = packCard.querySelector('.stock-bar-fill');
  const labelEl = packCard.querySelector('.stock-bar-label span:last-child');

  if (fillEl) {
    const percent = (newStock / maxStock) * 100;
    fillEl.style.width = `${percent}%`;
    fillEl.className = `stock-bar-fill ${percent < 20 ? 'low' : ''}`;
  }
  if (labelEl) {
    labelEl.textContent = `${newStock} / ${maxStock}口`;
  }

  // 在庫ゼロになったら売り切れ表示
  if (newStock <= 0) {
    const imgArea = packCard.querySelector('.pack-image');
    if (imgArea && !imgArea.querySelector('.badge-soldout')) {
      const badge = document.createElement('span');
      badge.className = 'badge-soldout';
      badge.textContent = 'SOLD OUT';
      imgArea.appendChild(badge);
    }
    // ガチャボタン無効化
    const gachaBtn = document.getElementById('gacha-btn');
    if (gachaBtn) {
      gachaBtn.disabled = true;
      gachaBtn.textContent = '売り切れ';
    }
    selectedPackId = null;
  }
}

// ===== カード開封アニメーション =====

/**
 * ガチャ開封演出を表示する
 * @param {Object} result - APIから返ってきたガチャ結果
 */
function showGachaAnimation(result) {
  const card = result.card;
  const rarity = card.rarity;
  const stage = document.getElementById('gacha-stage');

  if (!stage) return;

  // ステージのクラスをリセット
  stage.className = 'gacha-stage';

  // レアリティ別のステージエフェクトを設定
  if (rarity === 'UR') {
    stage.classList.add('ur-glow');
  } else if (rarity === 'SSR') {
    stage.classList.add('ssr-glow');
  }

  // カード表面のHTMLを構築
  const cardFrontHTML = buildCardFrontHTML(card);
  const particlesHTML = buildParticlesHTML(rarity);

  stage.innerHTML = `
    <div class="stage-light"></div>
    ${particlesHTML}
    <div class="card-flip-container rarity-${rarity}" id="flip-container">
      <div class="card-flip-inner">
        <!-- カード裏面 -->
        <div class="card-face card-back"></div>
        <!-- カード表面 -->
        <div class="card-face card-front">
          ${cardFrontHTML}
        </div>
      </div>
      <span class="flip-hint">タップしてカードを開く</span>
    </div>
    <button class="stage-close" id="stage-close-btn" onclick="closeGachaStage()">✕</button>
  `;

  // カードクリックでフリップ
  const flipContainer = stage.querySelector('#flip-container');
  flipContainer.addEventListener('click', () => {
    flipCard(flipContainer, rarity);
  });

  // ステージを表示（フェードイン）
  stage.classList.add('active');
  document.body.style.overflow = 'hidden';  // スクロール防止
}

/**
 * カードをフリップする（裏→表）
 */
function flipCard(container, rarity) {
  if (container.classList.contains('flipped')) return;

  container.classList.add('flipped');

  // フリップヒントを非表示
  const hint = container.querySelector('.flip-hint');
  if (hint) hint.style.display = 'none';

  // 少し待ってから閉じるボタンを表示
  setTimeout(() => {
    const closeBtn = document.getElementById('stage-close-btn');
    if (closeBtn) closeBtn.classList.add('show');
  }, 800);

  // UR/SSRの場合は効果音的な演出（画面が一瞬光る）
  if (rarity === 'UR' || rarity === 'SSR') {
    setTimeout(() => {
      document.body.style.transition = 'background-color 0.1s';
      document.body.style.backgroundColor = rarity === 'UR' ? '#2a2000' : '#200020';
      setTimeout(() => {
        document.body.style.backgroundColor = '';
        document.body.style.transition = '';
      }, 200);
    }, 500);
  }
}

/**
 * ガチャステージを閉じる
 */
function closeGachaStage() {
  const stage = document.getElementById('gacha-stage');
  if (stage) {
    stage.classList.remove('active');
    document.body.style.overflow = '';
  }
}

/**
 * カード表面のHTMLを生成する
 */
function buildCardFrontHTML(card) {
  const rarityColors = {
    'UR': '#ffd700',
    'SSR': '#e879f9',
    'SR': '#a78bfa',
    'R': '#38bdf8',
    'N': '#94a3b8',
  };

  const cardEmojis = {
    'UR': '👑',
    'SSR': '✨',
    'SR': '💫',
    'R': '⭐',
    'N': '🃏',
  };

  const artContent = card.image_url
    ? `<img src="${card.image_url}" alt="${card.name}">`
    : `<span style="font-size: 5rem;">${cardEmojis[card.rarity] || '🃏'}</span>`;

  return `
    <div class="card-art" style="border: 2px solid ${rarityColors[card.rarity] || '#666'}">
      ${artContent}
    </div>
    <div class="card-info">
      <span class="rarity-badge" style="background: linear-gradient(135deg, ${rarityColors[card.rarity]}, ${rarityColors[card.rarity]}88); color: ${card.rarity === 'N' ? '#94a3b8' : '#fff'}; border: 1px solid ${rarityColors[card.rarity]};">
        ${card.rarity}
      </span>
      <p class="card-name" style="color: ${rarityColors[card.rarity]};">${card.name}</p>
      <p style="font-size: 0.8rem; color: var(--text-secondary);">${card.description || ''}</p>
    </div>
  `;
}

/**
 * レアリティ別パーティクルHTMLを生成する（UR/SSR/SRのみ）
 */
function buildParticlesHTML(rarity) {
  if (!['UR', 'SSR', 'SR'].includes(rarity)) return '';

  const colors = {
    'UR': ['#ffd700', '#ff8c00', '#ffec80'],
    'SSR': ['#e879f9', '#c026d3', '#f0abfc'],
    'SR': ['#a78bfa', '#7c3aed', '#c4b5fd'],
  };

  const particleColors = colors[rarity] || ['#ffffff'];
  const count = rarity === 'UR' ? 20 : rarity === 'SSR' ? 15 : 10;

  let html = '<div class="particles-container">';
  for (let i = 0; i < count; i++) {
    const color = particleColors[i % particleColors.length];
    const left = Math.random() * 100;
    const delay = Math.random() * 2;
    const duration = 2 + Math.random() * 2;
    const size = 4 + Math.random() * 6;

    html += `
      <div class="particle" style="
        left: calc(${left}% + 50%);
        top: calc(100% + 50%);
        background: ${color};
        width: ${size}px;
        height: ${size}px;
        animation-delay: ${delay}s;
        animation-duration: ${duration}s;
        box-shadow: 0 0 6px ${color};
      "></div>
    `;
  }
  html += '</div>';
  return html;
}

/**
 * ガチャ履歴を取得して表示する
 */
async function loadGachaHistory() {
  const historyContainer = document.getElementById('gacha-history');
  if (!historyContainer) return;

  try {
    const history = await apiGet('/gacha/history');

    if (history.length === 0) {
      historyContainer.innerHTML = '<p class="text-secondary text-center">まだガチャを引いていません</p>';
      return;
    }

    historyContainer.innerHTML = `
      <div class="history-list">
        ${history.map(item => `
          <div class="history-item">
            <div class="history-rarity-dot ${item.card_rarity}"></div>
            <div style="flex: 1">
              <strong>${item.card_name}</strong>
              <span style="color: var(--text-secondary); font-size: 0.85rem; margin-left: 8px;">${item.pack_name}</span>
            </div>
            <span style="font-size: 0.8rem; color: var(--text-secondary);">${formatDate(item.created_at)}</span>
            <span style="color: var(--accent-gold); font-size: 0.85rem;">-${item.coins_spent}🪙</span>
          </div>
        `).join('')}
      </div>
    `;
  } catch (err) {
    historyContainer.innerHTML = '<p class="text-secondary text-center">履歴の読み込みに失敗しました</p>';
  }
}

/**
 * 日時を読みやすい形式にフォーマットする
 */
function formatDate(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diff = now - date;

  if (diff < 60000) return 'たった今';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}時間前`;

  return date.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric' });
}
