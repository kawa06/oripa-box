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
    // ナビゲーション切り替え
    if (navAuthArea) {
      navAuthArea.innerHTML = `
        <span style="color: var(--text-secondary); font-size: 0.9rem;">${user.username}</span>
        <button onclick="logout()" class="btn btn-outline" style="padding: 6px 14px; font-size: 0.85rem;">ログアウト</button>
      `;
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
