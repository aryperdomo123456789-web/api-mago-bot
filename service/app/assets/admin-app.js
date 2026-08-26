let currentUser = null;
let currentProfile = null;
let editingUserId = null;

function showTab(name) {
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tabbtn').forEach(el => el.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  document.querySelector(`.tabbtn[data-tab="${name}"]`).classList.add('active');
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: 'include',
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
      ...(window.panelSessionToken ? {'x-panel-session': window.panelSessionToken} : {}),
      ...(window.licenseAdminToken ? {'x-admin-token': window.licenseAdminToken} : {}),
    },
  });
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (e) { data = { raw: text }; }
  if (!res.ok) throw new Error((data && data.detail) || res.status + ' ' + res.statusText);
  return data;
}

function setLoginMessage(msg, error) {
  document.getElementById('loginMsg').innerHTML = error ? '<span style="color:#ffb4b4">' + msg + '</span>' : '<span style="color:#dbfff0">' + msg + '</span>';
}

async function login() {
  const submit = document.getElementById('loginSubmit');
  if (submit) submit.disabled = true;
  try {
    setLoginMessage('Conectando ao servidor...', false);
    const payload = {
      email: document.getElementById('loginEmail').value.trim(),
      password: document.getElementById('loginPassword').value,
    };
    const data = await api('/v1/auth/login', { method: 'POST', body: JSON.stringify(payload) });
    if (data && data.session_token) {
      window.panelSessionToken = data.session_token;
      localStorage.setItem('pd_panel_session', data.session_token);
    }
    setLoginMessage('Login realizado. Abrindo painel...');
    await boot();
  } catch (e) {
    setLoginMessage(e.message, true);
  } finally {
    if (submit) submit.disabled = false;
  }
}

async function logout() {
  try {
    await api('/v1/auth/logout', { method: 'POST', body: '{}' });
  } catch (e) {}
  currentUser = null;
  window.panelSessionToken = '';
  localStorage.removeItem('pd_panel_session');
  document.getElementById('loginView').classList.remove('hidden');
  document.getElementById('appView').classList.add('hidden');
  document.getElementById('dashboardShell').classList.add('hidden');
}

async function loadDashboard() {
  const [projects, licenses, users] = await Promise.all([
    api('/v1/licenses/projects'),
    api('/v1/licenses'),
    api('/v1/users'),
  ]);
  document.getElementById('dashProjects').textContent = (projects.items || []).length;
  document.getElementById('dashLicenses').textContent = (licenses.items || []).length;
  document.getElementById('dashSubscribers').textContent = (users.items || []).filter(u => u.role !== 'owner').length;
  document.getElementById('statSession').textContent = currentUser ? currentUser.email : '-';
  document.getElementById('statOwner').textContent = currentProfile ? currentProfile.display_name : (currentUser ? currentUser.full_name : '-');
  document.getElementById('statUsers').textContent = (users.items || []).length;
}

async function boot() {
  try {
    if (!window.panelSessionToken) {
      document.getElementById('dashboardShell').classList.add('hidden');
      document.getElementById('loginView').classList.remove('hidden');
      document.getElementById('appView').classList.add('hidden');
      setLoginMessage('Entre com o usuário do dono para continuar.', false);
      return;
    }
    const me = await api('/v1/auth/me');
    currentUser = me.user;
    document.getElementById('loginView').classList.add('hidden');
    document.getElementById('dashboardShell').classList.remove('hidden');
    document.getElementById('appView').classList.remove('hidden');
    setLoginMessage('Sessão ativa como ' + currentUser.email);

    const results = await Promise.allSettled([
      loadAccount(),
      loadUsers(),
      loadLicensing(),
      loadDashboard(),
    ]);
    const failed = results.filter(result => result.status === 'rejected');
    if (failed.length) {
      setLoginMessage(
        'Sessão ativa como ' + currentUser.email + '. Alguns blocos não carregaram, mas o painel continua aberto.',
        false
      );
      console.warn('pd-admin boot partial failure', failed.map(item => item.reason));
    }
  } catch (e) {
    document.getElementById('dashboardShell').classList.add('hidden');
    document.getElementById('loginView').classList.remove('hidden');
    document.getElementById('appView').classList.add('hidden');
    currentUser = null;
    currentProfile = null;
    setLoginMessage('Entre com o usuário do dono para continuar.', false);
  }
}

async function loadAccount() {
  const data = await api('/v1/account');
  currentProfile = data.profile;
  document.getElementById('accDisplayName').value = currentProfile.display_name || '';
  document.getElementById('accCompanyName').value = currentProfile.company_name || '';
  document.getElementById('accEmail').value = currentProfile.email || '';
  document.getElementById('accPhone').value = currentProfile.phone || '';
  document.getElementById('accBio').value = currentProfile.bio || '';
  document.getElementById('meBox').innerHTML =
    '<strong>' + data.owner.full_name + '</strong><br>' +
    'Email: ' + data.owner.email + '<br>' +
    'Perfil: ' + data.owner.role + '<br>' +
    'Ativo: ' + (data.owner.is_active ? 'sim' : 'não');
}

async function saveAccount() {
  try {
    const payload = {
      display_name: document.getElementById('accDisplayName').value.trim(),
      company_name: document.getElementById('accCompanyName').value.trim() || null,
      email: document.getElementById('accEmail').value.trim() || null,
      phone: document.getElementById('accPhone').value.trim() || null,
      bio: document.getElementById('accBio').value.trim() || null,
    };
    const data = await api('/v1/account', { method: 'PUT', body: JSON.stringify(payload) });
    currentProfile = data.profile;
    document.getElementById('accountMsg').textContent = 'Conta atualizada com sucesso.';
    await loadDashboard();
  } catch (e) {
    document.getElementById('accountMsg').textContent = e.message;
  }
}

function resetUserForm() {
  editingUserId = null;
  document.getElementById('userFormTitle').textContent = 'Criar usuário comum';
  document.getElementById('userId').value = '';
  document.getElementById('userEmail').value = '';
  document.getElementById('userName').value = '';
  document.getElementById('userPassword').value = '';
  document.getElementById('userRole').value = 'subscriber';
  document.getElementById('userNotes').value = '';
}

function fillUserForm(user) {
  editingUserId = user.id;
  document.getElementById('userFormTitle').textContent = 'Editar usuário';
  document.getElementById('userId').value = user.id;
  document.getElementById('userEmail').value = user.email || '';
  document.getElementById('userName').value = user.full_name || '';
  document.getElementById('userPassword').value = '';
  document.getElementById('userRole').value = user.role || 'subscriber';
  document.getElementById('userNotes').value = user.notes || '';
}

async function saveUser() {
  try {
    const payload = {
      email: document.getElementById('userEmail').value.trim(),
      full_name: document.getElementById('userName').value.trim(),
      role: document.getElementById('userRole').value,
      notes: document.getElementById('userNotes').value.trim() || null,
    };
    const password = document.getElementById('userPassword').value;
    if (password) payload.password = password;
    if (editingUserId) {
      await api('/v1/users/' + editingUserId, { method: 'PUT', body: JSON.stringify(payload) });
      document.getElementById('userMsg').textContent = 'Usuário atualizado.';
    } else {
      if (!payload.password) throw new Error('Senha obrigatória para novo usuário');
      await api('/v1/users', { method: 'POST', body: JSON.stringify(payload) });
      document.getElementById('userMsg').textContent = 'Usuário criado.';
    }
    resetUserForm();
    await loadUsers();
    await loadDashboard();
  } catch (e) {
    document.getElementById('userMsg').textContent = e.message;
  }
}

async function removeUser(id) {
  if (!confirm('Remover este usuário?')) return;
  await api('/v1/users/' + id, { method: 'DELETE', body: '{}' });
  await loadUsers();
  await loadDashboard();
}

async function loadUsers() {
  const data = await api('/v1/users');
  const items = data.items || [];
  const el = document.getElementById('usersList');
  if (!items.length) {
    el.innerHTML = '<div class="muted">Nenhum usuário criado.</div>';
    return;
  }
  el.innerHTML = items.map(u => `
    <div class="item">
      <div>
        <strong>${u.full_name} <span class="pill ${u.role === 'owner' ? '' : 'dangerpill'}">${u.role}</span></strong>
        <div class="meta">
          ${u.email}<br>
          ${u.is_active ? 'Ativo' : 'Inativo'}<br>
          ${u.notes || ''}
        </div>
      </div>
      <div class="actions">
        <button class="secondary" onclick='fillUserForm(${JSON.stringify(u).replace(/'/g, "\\'")})'>Editar</button>
        ${u.role !== 'owner' ? `<button class="danger" onclick="removeUser(${u.id})">Excluir</button>` : ''}
      </div>
    </div>
  `).join('');
}

async function createProject() {
  try {
    const body = {
      name: document.getElementById('projName').value.trim(),
      slug: document.getElementById('projSlug').value.trim(),
      domain: document.getElementById('projDomain').value.trim() || null,
      description: document.getElementById('projDesc').value.trim() || null,
    };
    const r = await api('/v1/licenses/projects', { method: 'POST', body: JSON.stringify(body) });
    document.getElementById('projectMsg').textContent = 'Projeto salvo: ' + r.project.slug;
    await loadLicensing();
    await loadDashboard();
  } catch (e) {
    document.getElementById('projectMsg').textContent = e.message;
  }
}

async function issueLicense() {
  try {
    const scopes = document.getElementById('licScopes').value.split(',').map(s => s.trim()).filter(Boolean);
    const body = {
      label: document.getElementById('licLabel').value.trim(),
      project_slug: document.getElementById('licProjectSlug').value.trim(),
      expires_at: document.getElementById('licExpires').value.trim() || null,
      created_by: document.getElementById('licCreatedBy').value.trim() || null,
      scopes,
      notes: document.getElementById('licNotes').value.trim() || null,
      metadata: {panel: 'admin'},
    };
    const r = await api('/v1/licenses', { method: 'POST', body: JSON.stringify(body) });
    document.getElementById('issueResult').textContent = JSON.stringify(r, null, 2);
    document.getElementById('validateToken').value = r.token || '';
    await loadLicensing();
    await loadDashboard();
  } catch (e) {
    document.getElementById('issueResult').textContent = e.message;
  }
}

async function validateLicense() {
  try {
    const body = {
      token: document.getElementById('validateToken').value.trim(),
      scope: document.getElementById('validateScope').value.trim() || null,
      project_slug: document.getElementById('validateProject').value.trim() || null,
      domain: document.getElementById('validateDomain').value.trim() || null,
    };
    const r = await api('/v1/licenses/validate', { method: 'POST', body: JSON.stringify(body) });
    document.getElementById('validateResult').textContent = JSON.stringify(r, null, 2);
  } catch (e) {
    document.getElementById('validateResult').textContent = e.message;
  }
}

async function revokeLicense(id) {
  await api('/v1/licenses/' + id + '/revoke', { method: 'POST', body: '{}' });
  await loadLicensing();
  await loadDashboard();
}

function renderProjects(items) {
  const el = document.getElementById('projects');
  if (!items.length) {
    el.innerHTML = '<div class="muted">Nenhum projeto cadastrado.</div>';
    return;
  }
  el.innerHTML = items.map(p => `
    <div class="item">
      <div>
        <strong>${p.name}</strong>
        <div class="meta">
          <span class="pill">${p.slug}</span><br>
          ${p.domain ? 'Domínio: ' + p.domain + '<br>' : ''}
          ${p.description ? p.description : ''}
        </div>
      </div>
    </div>
  `).join('');
}

function renderLicenses(items) {
  const el = document.getElementById('licensesList');
  if (!items.length) {
    el.innerHTML = '<div class="muted">Nenhuma licença emitida.</div>';
    return;
  }
  el.innerHTML = items.map(l => `
    <div class="item">
      <div>
        <strong>${l.label} <span class="pill ${l.status !== 'active' ? 'dangerpill' : ''}">${l.status}</span></strong>
        <div class="meta">
          Projeto: ${l.project_slug || '-'}<br>
          UUID: ${l.uuid}<br>
          Scopes: ${(l.scopes || []).join(', ') || '-'}<br>
          Expira: ${l.expires_at || '-'}<br>
          Último uso: ${l.last_used_at || '-'}
        </div>
      </div>
      <div class="actions">
        <button class="secondary" onclick="navigator.clipboard.writeText('${l.uuid}')">Copiar UUID</button>
        <button class="danger" onclick="revokeLicense(${l.id})">Revogar</button>
      </div>
    </div>
  `).join('');
}

async function loadLicensing() {
  const [projects, licenses] = await Promise.all([
    api('/v1/licenses/projects'),
    api('/v1/licenses'),
  ]);
  renderProjects(projects.items || []);
  renderLicenses(licenses.items || []);
}

window.licenseAdminToken = localStorage.getItem('license_admin_token') || '';
window.panelSessionToken = localStorage.getItem('pd_panel_session') || '';

document.getElementById('loginForm').addEventListener('submit', (event) => {
  event.preventDefault();
  login();
});

boot();
resetUserForm();
