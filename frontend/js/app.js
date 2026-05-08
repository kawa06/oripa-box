/**
 * app.js - 共通ユーティリティ
 * API呼び出し、トークン管理、共通UI処理を担当する
 */

// ===== 定数 =====
const API_BASE = '/api';  // FastAPIのベースURL

// ===== トークン管理 =====

/**
 * JWTトークンをlocalStorageに保存する
 */
function saveToken(token) {
  localStorage.setItem('access_token', token);
}

/**
 * localStorageからJWTトークンを取得する
 */
function getToken() {
  return localStorage.getItem('access_token');
}

/**
 * ユーザー情報をlocalStorageに保存する
 */
function saveUser(user) {
  localStorage.setItem('user', JSON.stringify(user));
}

/**
 * localStorageからユーザー情報を取得する
 */
function getUser() {
  const userStr = localStorage.getItem('user');
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

/**
 * ログアウト処理（トークンとユーザー情報を削除）
 */
function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user');
  window.location.href = '/frontend/login.html';
}

/**
 * ログイン済みかチェックする
 * 未ログインの場合はログインページにリダイレクト
 */
function requireAuth() {
  const token = getToken();
  if (!token) {
    window.location.href = '/frontend/login.html';
    return false;
  }
  return true;
}

/**
 * ログイン済みの場合はトップページにリダイレクトする（ログインページ用）
 */
function redirectIfLoggedIn() {
  const token = getToken();
  if (token) {
    window.location.href = '/frontend/index.html';
  }
}

// ===== API呼び出しユーティリティ =====

/**
 * 共通API呼び出し関数
 * JWTトークンを自動付与し、エラーハンドリングを行う
 * 
 * @param {string} path - APIパス（例: '/packs'）
 * @param {Object} options - fetchオプション
 * @returns {Promise<any>} APIレスポンスのJSONデータ
 */
async function apiCall(path, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  // 401の場合はトークン切れと判断してログアウト
  if (response.status === 401) {
    logout();
    throw new Error('認証が切れました。再度ログインしてください。');
  }

  const data = await response.json();

  if (!response.ok) {
    // FastAPIのエラーレスポンス形式に対応
    const message = data.detail || data.message || 'エラーが発生しました';
    throw new Error(message);
  }

  return data;
}

/**
 * GET リクエスト
 */
function apiGet(path) {
  return apiCall(path, { method: 'GET' });
}

/**
 * POST リクエスト
 */
function apiPost(path, body) {
  return apiCall(path, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

/**
 * DELETE リクエスト
 */
function apiDelete(path, body) {
  return apiCall(path, {
    method: 'DELETE',
    body: JSON.stringify(body),
  });
}

// ===== UI ユーティリティ =====

/**
 * アラートメッセージを表示する
 * @param {string} elementId - アラート要素のID
 * @param {string} message - 表示するメッセージ
 * @param {string} type - 'success' または 'error'
 */
function showAlert(elementId, message, type = 'error') {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.className = `alert alert-${type} show`;
  el.textContent = message;
  // 5秒後に自動で消す
  setTimeout(() => {
    el.className = `alert alert-${type}`;
  }, 5000);
}

/**
 * ボタンをローディング状態にする
 * @param {HTMLButtonElement} btn - ボタン要素
 * @param {boolean} loading - ローディング状態にするかどうか
 * @param {string} originalText - 元のテキスト
 */
function setButtonLoading(btn, loading, originalText = '') {
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.innerHTML = '<span class="spinner" style="width:20px;height:20px;border-width:2px;display:inline-block;"></span> 処理中...';
  } else {
    btn.disabled = false;
    btn.textContent = originalText || btn.dataset.originalText || 'OK';
  }
}

// ===== ナビゲーション更新 =====

/**
 * ナビゲーションバーを現在のログイン状態に合わせて更新する
 * コイン残高の表示・非表示も制御する
 */
async function updateNavbar() {
  const token = getToken();
  const user = getUser();
  const coinDisplayEl = document.getElementById('coin-balance-display');
  const navAuthArea = document.getElementById('nav-auth-area');

  if (token && user) {
    // ログイン済み：コイン残高表示
    if (coinDisplayEl) {
      coinDisplayEl.textContent = user.coin_balance;
      coinDisplayEl.closest('.coin-display')?.classList.remove('hidden');
    }
    // ナビゲーション切り替え（ユーザー名クリックでドロップダウン）
    if (navAuthArea) {
      navAuthArea.innerHTML = `
        <div class="user-menu-wrapper" style="position: relative; display: inline-block;">
          <button
            id="user-menu-btn"
            class="btn btn-outline"
            style="padding: 6px 14px; font-size: 0.85rem; cursor: pointer;"
            aria-haspopup="true"
            aria-expanded="false"
          >${user.username} ▾</button>
          <div
            id="user-dropdown"
            style="
              display: none;
              position: absolute;
              right: 0;
              top: calc(100% + 6px);
              min-width: 160px;
              background: var(--card-bg, #1e1b2e);
              border: 1px solid var(--border-color, #3a3a5c);
              border-radius: 8px;
              box-shadow: 0 8px 24px rgba(0,0,0,0.4);
              z-index: 1000;
              overflow: hidden;
            "
          >
            <button
              onclick="logout()"
              style="
                display: block; width: 100%; padding: 12px 16px;
                background: none; border: none; color: var(--text-primary, #e2e8f0);
                font-size: 0.9rem; text-align: left; cursor: pointer;
              "
              onmouseover="this.style.background='rgba(255,255,255,0.07)'"
              onmouseout="this.style.background='none'"
            >ログアウト</button>
            <hr style="margin: 0; border-color: var(--border-color, #3a3a5c);">
            <button
              onclick="openDeleteAccountModal()"
              style="
                display: block; width: 100%; padding: 12px 16px;
                background: none; border: none; color: #f87171;
                font-size: 0.9rem; text-align: left; cursor: pointer;
              "
              onmouseover="this.style.background='rgba(248,113,113,0.1)'"
              onmouseout="this.style.background='none'"
            >アカウント削除</button>
          </div>
        </div>
      `;

      // ドロップダウンのトグル処理
      const menuBtn = document.getElementById('user-menu-btn');
      const dropdown = document.getElementById('user-dropdown');
      if (menuBtn && dropdown) {
        menuBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          const isOpen = dropdown.style.display === 'block';
          dropdown.style.display = isOpen ? 'none' : 'block';
          menuBtn.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
        });
        // メニュー外クリックで閉じる
        document.addEventListener('click', () => {
          dropdown.style.display = 'none';
          menuBtn.setAttribute('aria-expanded', 'false');
        });
      }
    }

    // 管理者の場合はナビに管理リンクを表示
    if (user.is_admin) {
      const adminLink = document.getElementById('nav-admin-link');
      if (adminLink) adminLink.classList.remove('hidden');
    }

    // 最新のコイン残高をAPIから取得して更新
    try {
      const balanceData = await apiGet('/coins/balance');
      if (coinDisplayEl) {
        coinDisplayEl.textContent = balanceData.balance;
      }
      // ローカルストレージのユーザー情報も更新
      const currentUser = getUser();
      if (currentUser) {
        currentUser.coin_balance = balanceData.balance;
        saveUser(currentUser);
      }
    } catch (e) {
      // 残高取得失敗は無視（キャッシュ値を使用）
    }
  } else {
    // 未ログイン
    if (coinDisplayEl) {
      coinDisplayEl.closest('.coin-display')?.classList.add('hidden');
    }
    if (navAuthArea) {
      navAuthArea.innerHTML = `
        <a href="/frontend/login.html" class="btn btn-outline" style="padding: 6px 14px; font-size: 0.85rem;">ログイン</a>
        <a href="/frontend/login.html?tab=register" class="btn btn-primary" style="padding: 6px 14px; font-size: 0.85rem;">新規登録</a>
      `;
    }
  }
}

// ページ読み込み時にナビゲーション更新 + フッター挿入 + ハンバーガーメニュー初期化
document.addEventListener('DOMContentLoaded', () => {
  updateNavbar();
  insertFooter();
  initHamburger();
  insertDeleteAccountModal();
});

/**
 * ハンバーガーメニューのトグル処理を初期化する
 * .hamburger ボタンをクリックすると .navbar-nav に .open クラスを付け外しする
 */
function initHamburger() {
  const hamburger = document.querySelector('.hamburger');
  const navList = document.querySelector('.navbar-nav');
  if (!hamburger || !navList) return;

  hamburger.addEventListener('click', () => {
    const isOpen = navList.classList.toggle('open');
    hamburger.classList.toggle('open', isOpen);
    // アクセシビリティ属性を更新
    hamburger.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  });

  // ナビリンクをタップしたらメニューを閉じる
  navList.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      navList.classList.remove('open');
      hamburger.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
    });
  });

  // メニュー外タップで閉じる
  document.addEventListener('click', (e) => {
    if (!hamburger.contains(e.target) && !navList.contains(e.target)) {
      navList.classList.remove('open');
      hamburger.classList.remove('open');
      hamburger.setAttribute('aria-expanded', 'false');
    }
  });
}

/**
 * 全ページ共通フッターを動的に挿入する
 * body 末尾の <footer class="site-footer"> が未存在の場合のみ追加する
 */
function insertFooter() {
  // index.html は既に静的フッターを持っているので二重挿入しない
  if (document.querySelector('.site-footer')) return;

  const footer = document.createElement('footer');
  footer.className = 'site-footer';
  footer.innerHTML = `
    <div class="footer-links">
      <a href="/frontend/terms.html">利用規約</a>
      <a href="/frontend/legal.html">特定商取引法に基づく表記</a>
      <a href="/frontend/privacy.html">プライバシーポリシー</a>
    </div>
    <p class="footer-copy">&copy; 2025 オリパガチャ All Rights Reserved.</p>
  `;
  document.body.appendChild(footer);
}

// ===== アカウント削除モーダル =====

/**
 * アカウント削除確認モーダルをbodyに挿入する（全ページ共通）
 */
function insertDeleteAccountModal() {
  if (document.getElementById('delete-account-modal')) return;

  const modal = document.createElement('div');
  modal.id = 'delete-account-modal';
  modal.style.cssText = `
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(0,0,0,0.7);
    align-items: center;
    justify-content: center;
    padding: 16px;
  `;
  modal.innerHTML = `
    <div style="
      background: var(--card-bg, #1e1b2e);
      border: 1px solid #f87171;
      border-radius: 12px;
      padding: 32px 28px;
      max-width: 420px;
      width: 100%;
      box-shadow: 0 16px 48px rgba(0,0,0,0.5);
    ">
      <h2 style="color: #f87171; font-size: 1.3rem; margin: 0 0 12px;">アカウント削除</h2>
      <p style="color: var(--text-secondary, #a0aec0); font-size: 0.9rem; line-height: 1.6; margin-bottom: 20px;">
        本当にアカウントを削除しますか？<br>
        この操作は取り消せません。コイン残高・カードコレクション・ガチャ履歴など、全てのデータが完全に削除されます。
      </p>
      <div id="delete-account-alert" class="alert" style="margin-bottom: 16px;"></div>
      <div class="form-group" style="margin-bottom: 20px;">
        <label class="form-label" for="delete-account-password" style="display: block; margin-bottom: 6px; font-size: 0.9rem; color: var(--text-secondary, #a0aec0);">
          確認のためパスワードを入力してください
        </label>
        <input
          type="password"
          id="delete-account-password"
          class="form-input"
          placeholder="パスワードを入力"
          autocomplete="current-password"
          style="font-size: 16px;"
        >
      </div>
      <div style="display: flex; gap: 12px; justify-content: flex-end;">
        <button
          onclick="closeDeleteAccountModal()"
          class="btn btn-outline"
          style="padding: 10px 20px;"
        >キャンセル</button>
        <button
          id="delete-account-confirm-btn"
          onclick="handleDeleteAccount()"
          style="
            padding: 10px 20px;
            background: #f87171;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
          "
        >削除する</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
}

/**
 * アカウント削除モーダルを開く
 */
function openDeleteAccountModal() {
  const modal = document.getElementById('delete-account-modal');
  if (!modal) return;
  // パスワード入力欄とアラートをリセット
  const pwInput = document.getElementById('delete-account-password');
  if (pwInput) pwInput.value = '';
  const alertEl = document.getElementById('delete-account-alert');
  if (alertEl) alertEl.className = 'alert';
  modal.style.display = 'flex';
}

/**
 * アカウント削除モーダルを閉じる
 */
function closeDeleteAccountModal() {
  const modal = document.getElementById('delete-account-modal');
  if (modal) modal.style.display = 'none';
}

/**
 * アカウント削除を実行する
 * パスワードを確認してAPIを呼び出し、成功したらログアウトしてトップへ
 */
async function handleDeleteAccount() {
  const password = document.getElementById('delete-account-password')?.value;
  if (!password) {
    showAlert('delete-account-alert', 'パスワードを入力してください');
    return;
  }

  const btn = document.getElementById('delete-account-confirm-btn');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '削除中...';
  }

  try {
    await apiDelete('/auth/delete-account', { password });

    // 削除成功：ローカルストレージをクリアしてトップへ
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    closeDeleteAccountModal();
    window.location.href = '/frontend/login.html';
  } catch (err) {
    showAlert('delete-account-alert', err.message || 'アカウントの削除に失敗しました');
    if (btn) {
      btn.disabled = false;
      btn.textContent = '削除する';
    }
  }
}
