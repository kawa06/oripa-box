/**
 * gacha.js - ガチャ実行 + カード開封アニメーション
 * 
 * 演出の流れ:
 * 1回引き:
 *   1. ガチャボタンをクリック
 *   2. APIを呼び出してカード抽選
 *   3. 暗転ステージが表示され、カード裏面が現れる
 *   4. カードをクリックするとフリップして表が見える
 *   5. 賞に応じたエフェクトが発動（A賞が最も派手な金色）
 *
 * 10回引き:
 *   1. /api/gacha/draw/multi に count=10 でリクエスト
 *   2. 10枚のカードが順番にフリップ表示
 *   3. すべてフリップ後に閉じるボタンが表示
 *
 * 100回引き:
 *   1. /api/gacha/draw/multi に count=100 でリクエスト
 *   2. 結果サマリー（賞ごとの枚数）を表示
 *   3. A賞・B賞のカードのみ個別演出（スクロール可能な一覧も表示）
 */

// 現在選択中のパックID
let selectedPackId = null;
// 選択中のパック価格（コイン）
let selectedPackPrice = 0;
// 全パックデータキャッシュ
let allPacksCache = [];

document.addEventListener('DOMContentLoaded', async () => {
  // 認証チェック
  if (!requireAuth()) return;

  // パック一覧を読み込む
  await loadPacks();

  // 1回引きボタンのイベント
  const gachaBtn = document.getElementById('gacha-btn');
  if (gachaBtn) {
    gachaBtn.addEventListener('click', () => executeGacha(1));
  }
});

/**
 * パック一覧を取得してセレクターを表示する
 */
async function loadPacks() {
  const container = document.getElementById('pack-selector-area');
  if (!container) return;

  try {
    const packs = await apiGet('/packs/');
    allPacksCache = packs;

    if (packs.length === 0) {
      container.innerHTML = '<p class="text-secondary text-center">現在利用可能なパックはありません</p>';
      return;
    }

    container.innerHTML = packs.map(pack => {
      const stockPercent = (pack.stock / pack.max_stock) * 100;
      const isLow = stockPercent < 20;

      // パック画像（image_urlがあれば画像表示、なければ絵文字）
      const packImageHTML = pack.image_url
        ? `<img src="${pack.image_url}" alt="${pack.name}" style="width: 100%; height: 100%; object-fit: cover;">`
        : `<span style="font-size: 4rem;">${getPackEmoji(pack.name)}</span>`;

      // 賞別カードプレビュー
      const prizePreviewHTML = buildPrizePreview(pack.cards || []);

      return `
        <div class="pack-card" onclick="selectPack(${pack.id}, this)"
             data-pack-id="${pack.id}"
             data-price="${pack.price_coins}"
             data-stock="${pack.stock}"
             data-max-stock="${pack.max_stock}"
             style="cursor: pointer;">
          <div class="pack-image">
            ${packImageHTML}
            ${pack.stock === 0 ? '<span class="badge-soldout">SOLD OUT</span>' : ''}
          </div>
          <div class="pack-body">
            <h3 class="pack-name">${pack.name}</h3>
            <p class="pack-description">${pack.description || ''}</p>
            <div class="stock-bar">
              <div class="stock-bar-label">
                <span>在庫</span>
                <span>${pack.stock} / ${pack.max_stock}口 ${isLow ? '⚠️ 残りわずか' : ''}</span>
              </div>
              <div class="stock-bar-track">
                <div class="stock-bar-fill ${isLow ? 'low' : ''}"
                     style="width: ${stockPercent}%"></div>
              </div>
            </div>
          </div>
          ${prizePreviewHTML}
          <div class="pack-footer">
            <span class="price-tag">🪙 ${pack.price_coins}コイン</span>
            ${pack.stock > 0
              ? `<button class="btn btn-primary" onclick="selectPack(${pack.id}, this.closest('.pack-card')); event.stopPropagation();">詳細を見る</button>`
              : `<button class="btn btn-outline" disabled>売り切れ</button>`
            }
          </div>
        </div>
      `;
    }).join('');

  } catch (err) {
    container.innerHTML = `<p style="color: var(--error);">パックの読み込みに失敗しました: ${err.message}</p>`;
  }
}

/**
 * パック一覧に戻る
 */
function showPackList() {
  document.getElementById('pack-list-section').classList.remove('hidden');
  document.getElementById('pack-detail-section').classList.add('hidden');
  selectedPackId = null;
  selectedPackPrice = 0;
}

/**
 * パック詳細ページを表示する
 * @param {Object} pack - パックデータ
 */
function showPackDetail(pack) {
  // パック一覧を隠して詳細を表示
  document.getElementById('pack-list-section').classList.add('hidden');
  document.getElementById('pack-detail-section').classList.remove('hidden');

  // バナー画像
  const bannerWrap = document.getElementById('pack-banner-img-wrap');
  if (pack.image_url) {
    bannerWrap.innerHTML = `<img src="${pack.image_url}" alt="${pack.name}" class="pack-banner-img">`;
    bannerWrap.style.background = '';
  } else {
    bannerWrap.innerHTML = `<span class="pack-banner-emoji">${getPackEmoji(pack.name)}</span>`;
    bannerWrap.style.background = 'linear-gradient(135deg, #1a1a4a, #2a1a5a, #1a2a4a)';
  }

  // パック名
  document.getElementById('pack-detail-name').textContent = pack.name;

  // 賞セクション生成
  const prizesContainer = document.getElementById('pack-detail-prizes');
  prizesContainer.innerHTML = buildDetailPrizeSections(pack.cards || []);

  // 価格・在庫情報
  document.getElementById('pack-detail-price').textContent = `🪙 ${pack.price_coins}コイン`;
  const stockPercent = (pack.stock / pack.max_stock) * 100;
  const isLow = stockPercent < 20;
  document.getElementById('pack-detail-stock').textContent =
    `在庫: ${pack.stock} / ${pack.max_stock}口${isLow ? ' ⚠️ 残りわずか' : ''}`;
  const fillEl = document.getElementById('pack-detail-stock-fill');
  if (fillEl) {
    fillEl.style.width = `${stockPercent}%`;
    fillEl.className = `stock-bar-fill ${isLow ? 'low' : ''}`;
  }

  // ガチャ履歴を読み込む
  loadGachaHistory();

  // ページ先頭にスクロール
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * 賞ごとの詳細セクションHTMLを生成する
 * @param {Array} cards - パックのカードリスト
 */
function buildDetailPrizeSections(cards) {
  if (!cards || cards.length === 0) return '<p class="text-secondary text-center" style="padding:24px;">カード情報がありません</p>';

  const prizeColors = {
    'A賞': '#ffd700',
    'B賞': '#e879f9',
    'C賞': '#a78bfa',
    'D賞': '#38bdf8',
    'E賞': '#94a3b8',
  };
  const prizeOrder = ['A賞', 'B賞', 'C賞', 'D賞', 'E賞'];

  // 各賞のカードをグループ化
  const prizeMap = {};
  prizeOrder.forEach(p => { prizeMap[p] = []; });
  for (const card of cards) {
    if (prizeMap[card.rarity]) prizeMap[card.rarity].push(card);
  }

  // カード枚数の合計（確率計算用）
  const totalCards = cards.length;

  return prizeOrder
    .filter(prize => prizeMap[prize].length > 0)
    .map(prize => {
      const prizeCards = prizeMap[prize];
      const color = prizeColors[prize] || '#666';

      const cardGridHTML = prizeCards.map(card => {
        // probability を % 表示（floatなのでそのまま * 100）
        const probPercent = card.probability != null
          ? (card.probability * 100).toFixed(2)
          : null;

        const imgHTML = card.image_url
          ? `<img src="${card.image_url}" alt="${card.name}" class="detail-card-img">`
          : `<div class="detail-card-placeholder" style="border-color: ${color}88; background: ${color}11;">
               <span style="font-size: 1.5rem;">${prize[0]}</span>
             </div>`;

        // 所持数バッジ（count があれば）
        const countBadge = (card.count != null && card.count > 1)
          ? `<span class="detail-card-count-badge">x${card.count}</span>`
          : '';

        return `
          <div class="detail-card-item">
            <div class="detail-card-img-wrap" style="border-color: ${color};">
              ${imgHTML}
              ${countBadge}
            </div>
            <p class="detail-card-name">${card.name}</p>
            ${probPercent != null ? `<p class="detail-card-prob">${probPercent}%</p>` : ''}
          </div>
        `;
      }).join('');

      return `
        <div class="detail-prize-section">
          <div class="detail-prize-header" style="border-left-color: ${color};">
            <span class="detail-prize-label" style="color: ${color};">${prize}</span>
            <span class="detail-prize-count" style="color: ${color};">${prizeCards.length}種</span>
          </div>
          <div class="detail-card-grid">
            ${cardGridHTML}
          </div>
        </div>
      `;
    }).join('');
}

/**
 * 賞別カードプレビューHTMLを生成する（パック一覧カード用）
 * @param {Array} cards - パックのカードリスト
 */
function buildPrizePreview(cards) {
  if (!cards || cards.length === 0) return '';

  const prizeColors = {
    'A賞': '#ffd700',
    'B賞': '#e879f9',
    'C賞': '#a78bfa',
    'D賞': '#38bdf8',
    'E賞': '#94a3b8',
  };
  const prizeOrder = ['A賞', 'B賞', 'C賞', 'D賞', 'E賞'];

  // 各賞のカードをグループ化
  const prizeMap = {};
  prizeOrder.forEach(p => { prizeMap[p] = []; });
  for (const card of cards) {
    if (prizeMap[card.rarity]) prizeMap[card.rarity].push(card);
  }

  const sections = prizeOrder.map(prize => {
    const prizeCards = prizeMap[prize];
    const color = prizeColors[prize] || '#666';

    const cardImgs = prizeCards.map(card => {
      return card.image_url
        ? `<img src="${card.image_url}" alt="${card.name}" class="prize-preview-img"
                title="${card.name}" style="border-color: ${color};">`
        : `<div class="prize-preview-placeholder"
                title="${card.name}" style="background: ${color}11; border-color: ${color}88;">
             <span style="font-size: 0.75rem;">${prize[0]}</span>
           </div>`;
    }).join('');

    const displayHtml = prizeCards.length > 0
      ? cardImgs
      : `<div class="prize-preview-placeholder"
              style="background: ${color}11; border-color: ${color}44; opacity:0.4;">
           <span style="font-size: 0.75rem;">${prize[0]}</span>
         </div>`;

    return `
      <div class="prize-preview-section">
        <span class="prize-preview-label" style="color: ${color};">${prize}</span>
        <div class="prize-preview-imgs">${displayHtml}</div>
      </div>
    `;
  }).join('');

  return `<div class="pack-prize-preview">${sections}</div>`;
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
  // 新しいパックを選択
  selectedPackId = packId;

  // パックデータ取得（DOM または キャッシュから）
  const packDomEl = document.querySelector(`.pack-card[data-pack-id="${packId}"]`);
  selectedPackPrice = packDomEl ? parseInt(packDomEl.dataset.price, 10) : 0;
  const stock = packDomEl ? parseInt(packDomEl.dataset.stock, 10) : 0;
  const maxStock = packDomEl ? parseInt(packDomEl.dataset.maxStock, 10) : 100;

  // コイン残高取得
  const user = getUser();
  const coinBalance = user ? (user.coin_balance || 0) : 0;

  // ===== 1回引きボタンを更新 =====
  const gachaBtn = document.getElementById('gacha-btn');
  if (gachaBtn) {
    if (stock <= 0) {
      gachaBtn.disabled = true;
      gachaBtn.innerHTML = '売り切れ';
    } else if (coinBalance < selectedPackPrice) {
      gachaBtn.disabled = true;
      gachaBtn.innerHTML = `コイン不足（${selectedPackPrice}コイン必要）`;
    } else {
      gachaBtn.disabled = false;
      gachaBtn.innerHTML = `🎲 1回引く（${selectedPackPrice}コイン）`;
    }
  }

  // 10回引きボタンを更新
  const btn10 = document.getElementById('gacha-btn-10');
  if (btn10) {
    const cost10 = selectedPackPrice * 10;
    const canDraw10 = stock >= 10 && coinBalance >= cost10;
    btn10.disabled = !canDraw10;
    if (stock < 10) {
      btn10.innerHTML = `10回引く（在庫不足）`;
    } else if (coinBalance < cost10) {
      btn10.innerHTML = `10回引く（コイン不足: ${cost10}コイン必要）`;
    } else {
      btn10.innerHTML = `10回引く 🎲×10（${cost10}コイン）`;
    }
  }

  // 100回引きボタンを更新
  const btn100 = document.getElementById('gacha-btn-100');
  if (btn100) {
    const cost100 = selectedPackPrice * 100;
    const canDraw100 = stock >= 100 && coinBalance >= cost100;
    btn100.disabled = !canDraw100;
    if (stock < 100) {
      btn100.innerHTML = `100回引く（在庫不足）`;
    } else if (coinBalance < cost100) {
      btn100.innerHTML = `100回引く（コイン不足: ${cost100}コイン必要）`;
    } else {
      btn100.innerHTML = `100回引く 🎲×100（${cost100}コイン）`;
    }
  }

  // キャッシュからパックデータを取得して詳細表示
  const packData = allPacksCache.find(p => p.id === packId);
  if (packData) {
    showPackDetail(packData);
  }
}

/**
 * ガチャを実行する（count=1 の1回引き用）
 */
async function executeGacha(count) {
  if (!selectedPackId) {
    showAlert('gacha-alert', 'パックを選択してください');
    return;
  }

  const gachaBtn = document.getElementById('gacha-btn');
  setButtonLoading(gachaBtn, true);

  try {
    // count=1 は従来どおり /gacha/draw に送信
    const result = await apiPost('/gacha/draw', { pack_id: selectedPackId, count: 1 });

    // 開封演出を表示
    showGachaAnimation(result);

    // コイン残高を更新
    updateCoinBalance(result.remaining_balance);

    // パックの在庫を更新
    updatePackStock(selectedPackId, result.pack_remaining_stock);

    // ガチャ履歴を再読み込み
    await loadGachaHistory();

  } catch (err) {
    showAlert('gacha-alert', err.message);
  } finally {
    setButtonLoading(gachaBtn, false, `🎲 1回引く（${selectedPackPrice}コイン）`);
    gachaBtn.disabled = selectedPackId === null;
  }
}

/**
 * まとめ引きガチャを実行する（count = 10 or 100）
 */
async function executeGachaMulti(count) {
  if (!selectedPackId) {
    showAlert('gacha-alert', 'パックを選択してください');
    return;
  }

  // ボタンをローディング状態に
  const btnId = count === 10 ? 'gacha-btn-10' : 'gacha-btn-100';
  const targetBtn = document.getElementById(btnId);
  const gachaBtn = document.getElementById('gacha-btn');
  const btn10 = document.getElementById('gacha-btn-10');
  const btn100 = document.getElementById('gacha-btn-100');

  // すべてのボタンを無効化（多重クリック防止）
  [gachaBtn, btn10, btn100].forEach(b => { if (b) b.disabled = true; });
  if (targetBtn) setButtonLoading(targetBtn, true);

  try {
    // まとめ引きAPIを呼び出す
    const result = await apiPost('/gacha/draw/multi', { pack_id: selectedPackId, count });

    // コイン残高を更新
    updateCoinBalance(result.remaining_balance);

    // パックの在庫を更新
    updatePackStock(selectedPackId, result.pack_remaining_stock);

    // 演出を表示
    if (count === 10) {
      showMultiGachaAnimation10(result);
    } else {
      showMultiGachaAnimation100(result);
    }

    // ガチャ履歴を再読み込み
    await loadGachaHistory();

  } catch (err) {
    showAlert('gacha-alert', err.message);
    // エラー時はボタンを再度有効化
    selectPack(selectedPackId, document.querySelector(`.pack-card[data-pack-id="${selectedPackId}"]`));
  } finally {
    if (targetBtn) setButtonLoading(targetBtn, false);
  }
}

/**
 * コイン残高表示を更新する
 */
function updateCoinBalance(newBalance) {
  const coinEl = document.getElementById('coin-balance-display');
  if (coinEl) coinEl.textContent = newBalance;
  const user = getUser();
  if (user) {
    user.coin_balance = newBalance;
    saveUser(user);
  }
}

/**
 * パックの在庫表示を更新する
 */
function updatePackStock(packId, newStock) {
  // パック一覧カードのDOM更新
  const packCard = document.querySelector(`.pack-card[data-pack-id="${packId}"]`);
  if (packCard) {
    const maxStock = parseInt(packCard.dataset.maxStock, 10) || 100;
    packCard.dataset.stock = newStock;

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

    if (newStock <= 0) {
      const imgArea = packCard.querySelector('.pack-image');
      if (imgArea && !imgArea.querySelector('.badge-soldout')) {
        const badge = document.createElement('span');
        badge.className = 'badge-soldout';
        badge.textContent = 'SOLD OUT';
        imgArea.appendChild(badge);
      }
    }
  }

  // 詳細ページの在庫バー更新
  const detailFill = document.getElementById('pack-detail-stock-fill');
  const detailStockLabel = document.getElementById('pack-detail-stock');
  if (detailFill && packCard) {
    const maxStock = parseInt(packCard.dataset.maxStock, 10) || 100;
    const percent = (newStock / maxStock) * 100;
    detailFill.style.width = `${percent}%`;
    detailFill.className = `stock-bar-fill ${percent < 20 ? 'low' : ''}`;
    if (detailStockLabel) {
      detailStockLabel.textContent = `在庫: ${newStock} / ${maxStock}口${percent < 20 ? ' ⚠️ 残りわずか' : ''}`;
    }
  }

  // キャッシュ更新
  const cached = allPacksCache.find(p => p.id === packId);
  if (cached) cached.stock = newStock;

  // 在庫ゼロになったら売り切れ表示
  if (newStock <= 0) {
    const gachaBtn = document.getElementById('gacha-btn');
    if (gachaBtn) {
      gachaBtn.disabled = true;
      gachaBtn.textContent = '売り切れ';
    }
    const btn10 = document.getElementById('gacha-btn-10');
    if (btn10) { btn10.disabled = true; btn10.innerHTML = '10回引く（売り切れ）'; }
    const btn100 = document.getElementById('gacha-btn-100');
    if (btn100) { btn100.disabled = true; btn100.innerHTML = '100回引く（売り切れ）'; }
    selectedPackId = null;
  }
}

// ===== カード開封アニメーション（1回引き） =====

/**
 * ガチャ開封演出を表示する（1回引き）
 * @param {Object} result - APIから返ってきたガチャ結果
 */
function showGachaAnimation(result) {
  const card = result.card;
  const rarity = card.rarity;
  const stage = document.getElementById('gacha-stage');

  if (!stage) return;

  // ステージのクラスをリセット
  stage.className = 'gacha-stage';

  // 賞別のステージエフェクトを設定（A賞が最も派手な金色）
  if (rarity === 'A賞') {
    stage.classList.add('a-glow');
  } else if (rarity === 'B賞') {
    stage.classList.add('b-glow');
  }

  // カード表面のHTMLを構築
  const cardFrontHTML = buildCardFrontHTML(card);
  const particlesHTML = buildParticlesHTML(rarity);

  const rarityClass = `rarity-${rarity}`;

  stage.innerHTML = `
    <div class="stage-light"></div>
    ${particlesHTML}
    <div class="card-flip-container ${rarityClass}" id="flip-container">
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
  document.body.style.overflow = 'hidden';
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

  // A賞・B賞の場合は効果音的な演出（画面が一瞬光る）
  if (rarity === 'A賞' || rarity === 'B賞') {
    setTimeout(() => {
      document.body.style.transition = 'background-color 0.1s';
      document.body.style.backgroundColor = rarity === 'A賞' ? '#2a2000' : '#200020';
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

// ===== まとめ引き演出（10回） =====

/**
 * 10回引き開封演出
 * カードを1枚ずつ順番にフリップ表示する
 * @param {Object} result - MultiGachaResultResponse
 */
function showMultiGachaAnimation10(result) {
  const stage = document.getElementById('gacha-stage');
  if (!stage) return;

  const cards = result.cards.map(r => r.card);
  stage.className = 'gacha-stage gacha-stage-multi';

  stage.innerHTML = `
    <div class="stage-light"></div>
    <div class="multi-stage-header">
      <span style="color: var(--accent-gold); font-weight: 700; font-size: 1.1rem;">10回引き結果</span>
      <span style="color: var(--text-secondary); font-size: 0.85rem;">合計 ${result.total_coins_spent}コイン消費</span>
    </div>
    <div class="multi-cards-grid" id="multi-cards-grid">
      ${cards.map((card, i) => `
        <div class="multi-card-slot" id="slot-${i}" data-rarity="${card.rarity}" data-index="${i}">
          <div class="card-flip-container rarity-${card.rarity}" id="flip-${i}">
            <div class="card-flip-inner">
              <div class="card-face card-back"></div>
              <div class="card-face card-front">
                ${buildCardFrontHTML(card)}
              </div>
            </div>
          </div>
        </div>
      `).join('')}
    </div>
    <div class="multi-stage-footer">
      <span class="flip-hint-multi" id="flip-hint-multi">タップしてカードを開く</span>
      <button class="stage-close show" id="stage-close-btn" onclick="closeGachaStage()" style="display:none; position:static; width:auto; height:auto; padding: 10px 24px; border-radius: 8px; font-size: 0.95rem;">
        閉じる
      </button>
    </div>
  `;

  stage.classList.add('active');
  document.body.style.overflow = 'hidden';

  // 各カードにクリックイベントを設定（順番にフリップ）
  let flippedCount = 0;
  for (let i = 0; i < cards.length; i++) {
    const flipContainer = document.getElementById(`flip-${i}`);
    const rarity = cards[i].rarity;
    flipContainer.addEventListener('click', () => {
      if (!flipContainer.classList.contains('flipped')) {
        flipCard(flipContainer, rarity);
        flippedCount++;
        // すべてフリップしたら閉じるボタンを表示
        if (flippedCount >= cards.length) {
          const hint = document.getElementById('flip-hint-multi');
          if (hint) hint.style.display = 'none';
          const closeBtn = document.getElementById('stage-close-btn');
          if (closeBtn) closeBtn.style.display = 'flex';
        }
      }
    });
  }

  // 「全部開く」ボタンをフッターに追加
  const footer = stage.querySelector('.multi-stage-footer');
  if (footer) {
    const openAllBtn = document.createElement('button');
    openAllBtn.className = 'btn btn-outline';
    openAllBtn.style.cssText = 'padding: 10px 24px; font-size: 0.9rem; margin-right: 8px;';
    openAllBtn.textContent = '全部開く';
    openAllBtn.addEventListener('click', () => {
      for (let i = 0; i < cards.length; i++) {
        const fc = document.getElementById(`flip-${i}`);
        if (fc && !fc.classList.contains('flipped')) {
          fc.classList.add('flipped');
          const hint = fc.querySelector('.flip-hint');
          if (hint) hint.style.display = 'none';
        }
      }
      flippedCount = cards.length;
      openAllBtn.remove();
      const hintEl = document.getElementById('flip-hint-multi');
      if (hintEl) hintEl.style.display = 'none';
      const closeBtn = document.getElementById('stage-close-btn');
      if (closeBtn) closeBtn.style.display = 'flex';
    });
    footer.insertBefore(openAllBtn, footer.firstChild);
  }
}

// ===== まとめ引き演出（100回） =====

/**
 * 100回引き開封演出
 * レアリティサマリー + A賞・B賞のみ個別演出 + 全結果スクロール一覧
 * @param {Object} result - MultiGachaResultResponse
 */
function showMultiGachaAnimation100(result) {
  const stage = document.getElementById('gacha-stage');
  if (!stage) return;

  const rarityOrder = ['A賞', 'B賞', 'C賞', 'D賞', 'E賞'];
  const rarityColors = {
    'A賞': '#ffd700',
    'B賞': '#e879f9',
    'C賞': '#a78bfa',
    'D賞': '#38bdf8',
    'E賞': '#94a3b8',
  };

  // サマリーHTML生成
  const summaryItems = rarityOrder
    .filter(r => result.rarity_summary[r] > 0)
    .map(r => `
      <div style="display:flex; align-items:center; gap:8px; padding: 8px 16px; background: rgba(255,255,255,0.04); border-radius: 8px; border-left: 3px solid ${rarityColors[r]};">
        <span style="font-weight:800; color:${rarityColors[r]}; min-width:40px;">${r}</span>
        <span style="font-size:1.5rem; font-weight:800; color:${rarityColors[r]};">${result.rarity_summary[r]}</span>
        <span style="color: var(--text-secondary); font-size:0.85rem;">枚</span>
      </div>
    `).join('');

  // 高レア（A賞・B賞）カード抽出
  const rareCards = result.cards
    .map(r => r.card)
    .filter(c => c.rarity === 'A賞' || c.rarity === 'B賞');

  // レア演出HTML（A賞・B賞のみ）
  const rareHighlightHTML = rareCards.length > 0
    ? `
      <div class="rare-highlight-section">
        <p style="color: var(--accent-gold); font-weight:700; margin-bottom: 12px;">レア排出!</p>
        <div class="rare-cards-row" id="rare-cards-row">
          ${rareCards.map((card, i) => `
            <div class="multi-card-slot mini" id="rare-slot-${i}" data-rarity="${card.rarity}">
              <div class="card-flip-container rarity-${card.rarity}" id="rare-flip-${i}" style="width:120px; height:170px; cursor:pointer;">
                <div class="card-flip-inner">
                  <div class="card-face card-back"></div>
                  <div class="card-face card-front" style="padding:8px; font-size:0.7rem;">
                    ${buildCardFrontHTML(card)}
                  </div>
                </div>
              </div>
            </div>
          `).join('')}
        </div>
        <p style="color: var(--text-secondary); font-size:0.8rem; margin-top:8px;">タップで開く</p>
      </div>
    `
    : '<p style="color: var(--text-secondary); font-size: 0.9rem;">今回はレアカードなし</p>';

  // 全結果一覧HTML（小サムネ + 画像）
  const allCardsHTML = result.cards.map(r => r.card).map(card => `
    <div style="
      padding: 4px 8px;
      background: rgba(255,255,255,0.03);
      border-radius: 6px;
      border-left: 2px solid ${rarityColors[card.rarity] || '#555'};
      display:flex; align-items:center; gap:8px;
      font-size: 0.8rem;
    ">
      ${card.image_url
        ? `<img src="${card.image_url}" alt="${card.name}" style="width:36px; height:36px; object-fit:cover; border-radius:4px; border:1px solid ${rarityColors[card.rarity] || '#555'}; flex-shrink:0;">`
        : `<span style="width:36px; height:36px; display:flex; align-items:center; justify-content:center; font-size:1.2rem; flex-shrink:0;">🃏</span>`
      }
      <span style="color:${rarityColors[card.rarity] || '#555'}; font-weight:700; min-width:32px;">${card.rarity}</span>
      <span style="color: var(--text-primary);">${card.name}</span>
    </div>
  `).join('');

  stage.className = 'gacha-stage gacha-stage-100';
  stage.innerHTML = `
    <div class="stage-light ${result.rarity_summary['A賞'] > 0 ? 'a-glow' : result.rarity_summary['B賞'] > 0 ? 'b-glow' : ''}"></div>
    <div class="hundred-stage-inner">
      <!-- ヘッダー -->
      <div class="multi-stage-header" style="margin-bottom: 16px;">
        <span style="color: var(--accent-gold); font-weight: 700; font-size: 1.2rem;">100回引き結果</span>
        <span style="color: var(--text-secondary); font-size: 0.85rem;">合計 ${result.total_coins_spent}コイン消費</span>
      </div>

      <!-- 賞別サマリー -->
      <div style="display:flex; flex-direction:column; gap:8px; width:100%; max-width:320px; margin:0 auto 20px;">
        ${summaryItems}
      </div>

      <!-- レア演出エリア -->
      ${rareHighlightHTML}

      <!-- 全結果トグル -->
      <button class="btn btn-outline" id="toggle-all-results-btn" onclick="toggleAllResults()" style="margin: 12px auto 0; padding: 8px 20px; font-size:0.85rem;">
        全結果を表示 (${result.count}枚)
      </button>
      <div id="all-results-list" style="display:none; max-height:240px; overflow-y:auto; width:100%; max-width:360px; margin:10px auto 0; display:none;">
        <div style="display:flex; flex-direction:column; gap:4px;">
          ${allCardsHTML}
        </div>
      </div>

      <!-- 閉じるボタン -->
      <button class="btn btn-gold" onclick="closeGachaStage()" style="margin-top: 16px; padding: 12px 32px; font-size: 1rem;">
        閉じる
      </button>
    </div>
  `;

  stage.classList.add('active');
  document.body.style.overflow = 'hidden';

  // レアカードのフリップイベント
  rareCards.forEach((card, i) => {
    const fc = document.getElementById(`rare-flip-${i}`);
    if (fc) {
      fc.addEventListener('click', () => flipCard(fc, card.rarity));
    }
  });

  // A賞がある場合は背景を金色に
  if (result.rarity_summary['A賞'] > 0) {
    stage.classList.add('a-glow');
  } else if (result.rarity_summary['B賞'] > 0) {
    stage.classList.add('b-glow');
  }
}

/**
 * 100回引き全結果一覧のトグル
 */
function toggleAllResults() {
  const list = document.getElementById('all-results-list');
  const btn = document.getElementById('toggle-all-results-btn');
  if (!list || !btn) return;

  if (list.style.display === 'none' || list.style.display === '') {
    list.style.display = 'block';
    btn.textContent = '全結果を非表示';
  } else {
    list.style.display = 'none';
    const count = list.querySelectorAll('[style]').length;
    btn.textContent = `全結果を表示 (${count}枚)`;
  }
}

/**
 * カード表面のHTMLを生成する
 * image_urlがある場合: 画像をカード面積の約80%に大きく表示し、名前・コインは下部に小さくまとめる
 * image_urlがない場合: 従来どおり絵文字＋カード名＋説明を表示
 */
function buildCardFrontHTML(card) {
  // 賞ごとのカラーマッピング
  const rarityColors = {
    'A賞': '#ffd700',
    'B賞': '#e879f9',
    'C賞': '#a78bfa',
    'D賞': '#38bdf8',
    'E賞': '#94a3b8',
  };

  // 賞ごとの絵文字（画像なしの場合に使用）
  const cardEmojis = {
    'A賞': '👑',
    'B賞': '✨',
    'C賞': '💫',
    'D賞': '⭐',
    'E賞': '🃏',
  };

  const color = rarityColors[card.rarity] || '#666';
  const emoji = cardEmojis[card.rarity] || '🃏';

  // 変換コイン数の表示（coin_valueがある場合のみ）
  // デフォルト値: E賞=10, D賞=30, C賞=100, B賞=300, A賞=1000
  const defaultCoinValues = { 'A賞': 1000, 'B賞': 300, 'C賞': 100, 'D賞': 30, 'E賞': 10 };
  const coinValue = card.coin_value != null ? card.coin_value : (defaultCoinValues[card.rarity] || 10);

  if (card.image_url) {
    // --- 画像優先レイアウト ---
    // カードイラストを80%の高さで大きく表示し、名前・コインは下部に小さくまとめる
    return `
      <div class="card-art card-art-image-priority" style="border: 2px solid ${color}">
        <img src="${card.image_url}" alt="${card.name}">
      </div>
      <div class="card-info card-info-compact">
        <span class="rarity-badge" style="background: linear-gradient(135deg, ${color}, ${color}88); color: ${card.rarity === 'E賞' ? '#94a3b8' : '#fff'}; border: 1px solid ${color}; font-size: 0.65rem; padding: 2px 8px;">
          ${card.rarity}
        </span>
        <p class="card-name card-name-small" style="color: ${color};">${card.name}</p>
        <p class="gacha-card-coin gacha-card-coin-compact">🪙 ${coinValue}コイン</p>
      </div>
    `;
  }

  // --- 画像なし: 従来レイアウト ---
  return `
    <div class="card-art" style="border: 2px solid ${color}">
      <span style="font-size: 5rem;">${emoji}</span>
    </div>
    <div class="card-info">
      <span class="rarity-badge" style="background: linear-gradient(135deg, ${color}, ${color}88); color: ${card.rarity === 'E賞' ? '#94a3b8' : '#fff'}; border: 1px solid ${color};">
        ${card.rarity}
      </span>
      <p class="card-name" style="color: ${color};">${card.name}</p>
      <p style="font-size: 0.8rem; color: var(--text-secondary);">${card.description || ''}</p>
      <p class="gacha-card-coin">🪙 ${coinValue}コイン</p>
    </div>
  `;
}

/**
 * 賞別パーティクルHTMLを生成する（A賞/B賞/C賞のみ）
 */
function buildParticlesHTML(rarity) {
  if (!['A賞', 'B賞', 'C賞'].includes(rarity)) return '';

  // 賞ごとのパーティクルカラー
  const colors = {
    'A賞': ['#ffd700', '#ff8c00', '#ffec80'],
    'B賞': ['#e879f9', '#c026d3', '#f0abfc'],
    'C賞': ['#a78bfa', '#7c3aed', '#c4b5fd'],
  };

  const particleColors = colors[rarity] || ['#ffffff'];
  // A賞は最も多いパーティクルで派手に演出
  const count = rarity === 'A賞' ? 25 : rarity === 'B賞' ? 15 : 10;

  let html = '<div class="particles-container">';
  for (let i = 0; i < count; i++) {
    const color = particleColors[i % particleColors.length];
    const left = Math.random() * 100;
    const delay = Math.random() * 2;
    const duration = 2 + Math.random() * 2;
    const size = rarity === 'A賞' ? 5 + Math.random() * 8 : 4 + Math.random() * 6;

    html += `
      <div class="particle" style="
        left: calc(${left}% + 50%);
        top: calc(100% + 50%);
        background: ${color};
        width: ${size}px;
        height: ${size}px;
        animation-delay: ${delay}s;
        animation-duration: ${duration}s;
        box-shadow: 0 0 ${rarity === 'A賞' ? 10 : 6}px ${color};
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
