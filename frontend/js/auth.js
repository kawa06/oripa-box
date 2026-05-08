/**
 * auth.js - ログイン・ユーザー登録処理
 */

document.addEventListener('DOMContentLoaded', () => {
  // 既にログイン済みならトップページへ
  redirectIfLoggedIn();

  // URLパラメータでタブを切り替え
  const params = new URLSearchParams(window.location.search);
  if (params.get('tab') === 'register') {
    switchTab('register');
  }

  // ログインフォームのイベント
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', handleLogin);
  }

  // 登録フォームのイベント
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', handleRegister);
  }
});

/**
 * タブ切り替え（ログイン ↔ 新規登録）
 */
function switchTab(tab) {
  const loginPanel = document.getElementById('login-panel');
  const registerPanel = document.getElementById('register-panel');
  const loginTab = document.getElementById('tab-login');
  const registerTab = document.getElementById('tab-register');

  if (tab === 'login') {
    loginPanel.classList.remove('hidden');
    registerPanel.classList.add('hidden');
    loginTab.classList.add('active');
    registerTab.classList.remove('active');
  } else {
    loginPanel.classList.add('hidden');
    registerPanel.classList.remove('hidden');
    loginTab.classList.remove('active');
    registerTab.classList.add('active');
  }
}

/**
 * ログイン処理
 */
async function handleLogin(e) {
  e.preventDefault();
  const btn = document.getElementById('login-btn');
  setButtonLoading(btn, true);

  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;

  try {
    const data = await apiPost('/auth/login', { email, password });

    // トークンとユーザー情報を保存
    saveToken(data.access_token);
    saveUser(data.user);

    // トップページへリダイレクト
    window.location.href = '/frontend/index.html';
  } catch (err) {
    showAlert('login-alert', err.message);
  } finally {
    setButtonLoading(btn, false, 'ログイン');
  }
}

/**
 * ユーザー登録処理
 */
async function handleRegister(e) {
  e.preventDefault();
  const btn = document.getElementById('register-btn');
  setButtonLoading(btn, true);

  const email = document.getElementById('reg-email').value.trim();
  const username = document.getElementById('reg-username').value.trim();
  const password = document.getElementById('reg-password').value;
  const passwordConfirm = document.getElementById('reg-password-confirm').value;

  // クライアント側バリデーション
  if (password !== passwordConfirm) {
    showAlert('register-alert', 'パスワードが一致しません');
    setButtonLoading(btn, false, '新規登録');
    return;
  }

  if (password.length < 6) {
    showAlert('register-alert', 'パスワードは6文字以上で入力してください');
    setButtonLoading(btn, false, '新規登録');
    return;
  }

  try {
    const data = await apiPost('/auth/register', { email, username, password });

    if (data.requires_verification) {
      // メール認証が必要な場合：トークンは保存せず確認メッセージを表示
      showAlert(
        'register-alert',
        '登録が完了しました！確認メールを送信しました。メールを確認して認証を完了してください。',
        'success'
      );
      // フォームを無効化して再送信を防ぐ
      document.getElementById('register-form').style.display = 'none';
    } else {
      // SMTP未設定（開発環境）または管理者の場合：即ログイン
      if (data.access_token && data.user) {
        saveToken(data.access_token);
        saveUser(data.user);
      }
      // 新規登録ボーナスメッセージを一瞬見せてからリダイレクト
      showAlert('register-alert', '登録完了！50コインのボーナスをプレゼント！', 'success');
      setTimeout(() => {
        window.location.href = '/frontend/index.html';
      }, 1500);
    }
  } catch (err) {
    showAlert('register-alert', err.message);
  } finally {
    setButtonLoading(btn, false, '新規登録');
  }
}
