'use strict';

const API = 'http://localhost:8000';  // relative URL; nginx proxies /auth /users /events /history to fastapi

let accessToken = localStorage.getItem('ember_access') || '';
let refreshToken = localStorage.getItem('ember_refresh') || '';

async function apiFetch(path, opts = {}) {

  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`;

  let res = await fetch(API + path, { ...opts, headers });

  if (res.status === 401 && refreshToken) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      headers['Authorization'] = `Bearer ${accessToken}`;
      res = await fetch(API + path, { ...opts, headers });
    } else {
      doLogout();
      return null;
    }
  }

  return res;
}

async function tryRefresh() {
  try {
    const res = await fetch(API + '/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    accessToken = data.access_token;
    refreshToken = data.refresh_token || refreshToken;
    localStorage.setItem('ember_access', accessToken);
    localStorage.setItem('ember_refresh', refreshToken);
    return true;
  } catch {
    return false;
  }
}

function saveTokens(access, refresh) {
  accessToken = access;
  refreshToken = refresh;
  localStorage.setItem('ember_access', access);
  localStorage.setItem('ember_refresh', refresh);
}

function clearTokens() {
  accessToken = '';
  refreshToken = '';
  localStorage.removeItem('ember_access');
  localStorage.removeItem('ember_refresh');
}

function doLogout() {
  if (refreshToken) {
    fetch(API + '/auth/logout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {});
  }
  clearTokens();
  window.dispatchEvent(new CustomEvent('ember:logout'));
}
