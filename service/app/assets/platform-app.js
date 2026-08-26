(() => {
  "use strict";

  const state = { user: null, tenants: [], projects: [], conversations: [], ownerWhatsapp: null, selectedTenant: null, section: "overview", signup: false };
  const $ = (selector) => document.querySelector(selector);
  const diagnostics = window.MagoDiagnostics || { capture: () => null, safeRender: (_name, renderer) => renderer() };

  function captureError(error, context = {}) {
    diagnostics.capture(error, { ...context, state: { section: state.section, tenant: state.selectedTenant?.id, projects: state.projects.length, conversations: state.conversations.length } });
  }

  function renderFallback(title, retry) {
    const panel = node("article", { className: "panel-card" }, [
      node("p", { className: "eyebrow", textContent: "FALLBACK ATIVO" }),
      node("h3", { textContent: `${title} indisponível` }),
      node("p", { className: "muted", textContent: "O restante do control plane continua interativo. Abra o diagnóstico para ver a causa e tente novamente." }),
      node("div", { className: "fallback-actions" }, [
        node("button", { className: "button button-primary small", type: "button", textContent: "Tentar novamente", onclick: retry }),
        node("button", { className: "button button-ghost small", type: "button", textContent: "Abrir diagnóstico", onclick: () => { const drawer = document.querySelector(".mago-diagnostics-drawer"); if (drawer) drawer.hidden = false; } }),
      ]),
    ]);
    $("#dashboard-content").replaceChildren(panel);
  }

  function node(tag, props = {}, children = []) {
    const element = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "className") element.className = value;
      else if (key === "textContent") element.textContent = value;
      else if (key.startsWith("on")) element.addEventListener(key.slice(2).toLowerCase(), value);
      else element.setAttribute(key, value);
    });
    children.forEach((child) => element.append(child));
    return element;
  }

  function showAlert(target, message, success = false) {
    target.textContent = message;
    target.className = success ? "alert success" : "alert";
    target.hidden = false;
  }

  function hideAlert(target) {
    target.hidden = true;
    target.textContent = "";
  }

  async function api(path, options = {}) {
    const { component = "api", payloadContext = {}, timeoutMs = 15000, ...fetchOptions } = options;
    const requestId = window.crypto?.randomUUID ? window.crypto.randomUUID() : `mago-${Date.now()}`;
    let response;
    try {
      response = await fetch(path, {
        credentials: "same-origin",
        timeoutMs,
        requestId,
        headers: { "Content-Type": "application/json", ...(fetchOptions.headers || {}) },
        ...fetchOptions,
      });
    } catch (error) {
      captureError(error, { source: "network", component, requestId, payload: payloadContext });
      throw error;
    }
    const responseRequestId = response.headers.get("X-Request-ID") || requestId;
    const raw = await response.text();
    let data = {};
    if (raw) {
      try { data = JSON.parse(raw); }
      catch (error) {
        const parseError = new Error("A resposta do servidor não é um JSON válido.");
        captureError(parseError, { source: "network", component, requestId: responseRequestId, payload: { ...payloadContext, status: response.status, body_preview: raw.slice(0, 500) } });
        throw parseError;
      }
    }
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : (data.detail?.message || data.error?.message || "A operação não foi concluída.");
      const error = new Error(detail);
      error.status = response.status;
      captureError(error, { source: "network", component, requestId: responseRequestId, payload: { ...payloadContext, status: response.status, url: path } });
      throw error;
    }
    return data;
  }

  function formObject(form) {
    return Object.fromEntries(new FormData(form).entries());
  }

  function setLoading(form, loading) {
    const button = form.querySelector("button[type=submit]");
    if (button) { button.disabled = loading; button.dataset.original = button.dataset.original || button.textContent; button.textContent = loading ? "Processando…" : button.dataset.original; }
  }

  async function loadSession() {
    try {
      const data = await api("/v1/platform/auth/me");
      if (!data || !data.user || typeof data.user !== "object") throw new Error("Sessão inválida recebida do servidor.");
      state.user = data.user;
      await loadTenants();
      showDashboard();
    } catch (error) {
      captureError(error, { source: "auth", component: "session-bootstrap" });
      showAuth();
    }
  }

  async function loadTenants() {
    try {
      const data = await api("/v1/platform/tenants/me");
      state.tenants = Array.isArray(data.items) ? data.items : [];
    } catch (error) {
      state.tenants = [];
      captureError(error, { source: "network", component: "tenant-loader" });
    }
    if (!state.tenants.length && ["owner", "platform_superadmin", "platform_operator", "platform_support"].includes(state.user?.role)) {
      const data = await api("/v1/platform/tenants", { component: "tenant-loader" });
      state.tenants = Array.isArray(data.items) ? data.items : [];
    }
    state.selectedTenant = state.tenants[0] || null;
    if (state.selectedTenant) await loadProjects();
  }

  async function loadProjects() {
    if (!state.selectedTenant) { state.projects = []; return; }
    const data = await api(`/v1/platform/projects?tenant_id=${encodeURIComponent(state.selectedTenant.id)}`, { component: "project-loader" });
    state.projects = Array.isArray(data.items) ? data.items : [];
  }

  async function loadConversations() {
    if (!state.selectedTenant) { state.conversations = []; return; }
    const data = await api(`/v1/platform/conversations?tenant_id=${encodeURIComponent(state.selectedTenant.id)}&limit=50`, { component: "conversation-loader" });
    state.conversations = Array.isArray(data.items) ? data.items : [];
  }

  async function loadOwnerWhatsapp() {
    try {
      state.ownerWhatsapp = await api("/v1/platform/owner/whatsapp", { component: "owner-whatsapp-loader" });
    } catch (error) {
      state.ownerWhatsapp = null;
      captureError(error, { source: "network", component: "owner-whatsapp-loader" });
    }
  }

  function showAuth() {
    $("#auth-view").hidden = false;
    $("#dashboard-view").hidden = true;
  }

  function showDashboard() {
    $("#auth-view").hidden = true;
    $("#dashboard-view").hidden = false;
    $("#user-chip").textContent = `${state.user.full_name} · ${state.user.role}`;
    const ownerLink = document.querySelector('[data-section="owner-whatsapp"]');
    if (ownerLink) ownerLink.hidden = !["owner", "platform_superadmin", "platform_operator"].includes(state.user.role);
    renderDashboard();
  }

  function card(title, value, note) {
    return node("article", { className: "kpi" }, [
      node("div", { className: "kpi-label", textContent: title }),
      node("div", { className: "kpi-value", textContent: value }),
      node("div", { className: "kpi-note", textContent: note }),
    ]);
  }

  function listItem(title, subtitle, badge) {
    return node("div", { className: "list-item" }, [
      node("div", {}, [node("strong", { textContent: title }), node("small", { textContent: subtitle })]),
      node("span", { className: "badge", textContent: badge }),
    ]);
  }

  function renderOverview() {
    const content = $("#dashboard-content");
    const tenantName = state.selectedTenant?.legal_name || "Nenhuma organização selecionada";
    const projectLabel = state.projects.length === 1 ? "projeto ativo" : "projetos ativos";
    const grid = node("div", { className: "kpi-grid" }, [
      card("Organização atual", state.selectedTenant ? state.selectedTenant.slug : "—", tenantName),
      card("Projetos", String(state.projects.length), projectLabel),
      card("Plano", state.selectedTenant?.plan_slug || "—", state.selectedTenant?.status || "Aguardando onboarding"),
      card("Provider", state.projects[0]?.provider_type || "Meta Cloud", "adapter server-side"),
    ]);
    const main = node("div", { className: "content-grid" }, [
      node("article", { className: "panel-card code-card" }, [
        node("h3", { textContent: "Comece pelo primeiro request" }),
        node("p", { className: "muted", textContent: "Chave no header. Segredo fora do navegador. Idempotência em cada envio." }),
        node("pre", { className: "code-block", textContent: `curl -X POST https://app.mago-bot.com/v1/projects/PROJECT_ID/messages\\
  -H 'X-API-Key: mb_live_…'\\
  -H 'X-Idempotency-Key: pedido-2026-0001'\\
  -H 'Content-Type: application/json'\\
  -d '{"to":"5511999999999","type":"text","text":{"body":"Olá, mundo."}}'` }),
      ]),
      node("article", { className: "panel-card" }, [
        node("h3", { textContent: "Próximos gates" }),
        node("div", { className: "item-list" }, [
          listItem("Criar projeto", "Separar cada aplicação por contrato", state.projects.length ? "feito" : "agora"),
          listItem("Vincular provider", "Meta Cloud ou compatibilidade Evolution", "server-side"),
          listItem("Gerar API key", "O token aparece uma única vez", "seguro"),
        ]),
      ]),
    ]);
    content.replaceChildren(grid, main);
  }

  function renderProjects() {
    const content = $("#dashboard-content");
    const list = node("div", { className: "panel-card" });
    const createButton = node("button", { className: "button button-primary small", textContent: "Novo projeto" });
    const form = node("form", { className: "form-stack", hidden: true });
    const nameInput = node("input", { name: "name", placeholder: "Nome do projeto", required: "true", minlength: "2" });
    const slugInput = node("input", { name: "slug", placeholder: "meu-projeto", required: "true", pattern: "[a-z0-9-]+" });
    const providerInput = node("select", { name: "provider_type" }, [node("option", { value: "meta_cloud", textContent: "Meta Cloud API" }), node("option", { value: "evolution", textContent: "Evolution (compatibilidade)" })]);
    const submitButton = node("button", { className: "button button-primary", type: "submit", textContent: "Criar projeto" });
    form.append(node("label", { textContent: "Nome" }, [nameInput]), node("label", { textContent: "Slug" }, [slugInput]), node("label", { textContent: "Provider" }, [providerInput]), submitButton);
    createButton.addEventListener("click", () => { form.hidden = !form.hidden; if (!form.hidden) nameInput.focus(); });
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!state.selectedTenant) return;
      submitButton.disabled = true;
      try {
        await api(`/v1/platform/projects?tenant_id=${encodeURIComponent(state.selectedTenant.id)}`, { method: "POST", body: JSON.stringify(formObject(form)) });
        form.reset(); form.hidden = true; await loadProjects(); renderProjects();
      } catch (error) { captureError(error, { source: "action", component: "project-create" }); showAlert($("#dashboard-alert"), error.message); }
      finally { submitButton.disabled = false; }
    });
    list.append(node("div", { className: "section-intro" }, [
      node("div", {}, [node("p", { className: "eyebrow", textContent: "AMBIENTES" }), node("h3", { textContent: "Projetos & providers" })]),
      createButton,
    ]), form);
    if (!state.projects.length) list.append(node("p", { className: "empty", textContent: "Nenhum projeto ainda. Crie o primeiro ambiente para separar chaves, provider e uso." }));
    else state.projects.forEach((project) => list.append(listItem(project.name, `${project.slug} · ${project.provider_type || "provider pendente"}`, project.status)));
    content.replaceChildren(list);
  }

  async function openConversation(conversationId) {
    if (!state.selectedTenant) return;
    try {
      const data = await api(`/v1/platform/conversations/${encodeURIComponent(conversationId)}?tenant_id=${encodeURIComponent(state.selectedTenant.id)}`);
      renderConversationDetail(data);
    } catch (error) {
      captureError(error, { source: "action", component: "conversation-open" });
      showAlert($("#dashboard-alert"), error.message);
    }
  }

  function renderConversations() {
    const content = $("#dashboard-content");
    const cardPanel = node("article", { className: "panel-card" });
    cardPanel.append(node("div", { className: "section-intro" }, [
      node("div", {}, [node("p", { className: "eyebrow", textContent: "CONVERSATION CORE" }), node("h3", { textContent: "Inbox unificada" })]),
      node("span", { className: "badge", textContent: `${state.conversations.length} abertas` }),
    ]));
    if (!state.conversations.length) {
      cardPanel.append(node("p", { className: "empty", textContent: "Nenhuma conversa neste tenant. Quando o primeiro evento chegar, a timeline aparece aqui." }));
    } else {
      const rows = node("div", { className: "conversation-list" });
      state.conversations.forEach((conversation) => {
        const customer = conversation.customer?.display_name || conversation.customer?.external_ref || "Cliente sem nome";
        const row = node("button", { className: "conversation-row", type: "button" }, [
          node("div", {}, [node("strong", { textContent: customer }), node("small", { textContent: `${conversation.channel} · ${conversation.subject || "Sem assunto"}` })]),
          node("span", { className: "badge", textContent: conversation.status }),
        ]);
        row.addEventListener("click", () => openConversation(conversation.id));
        rows.append(row);
      });
      cardPanel.append(rows);
    }
    content.replaceChildren(cardPanel);
  }

  function renderConversationDetail(data) {
    const content = $("#dashboard-content");
    const conversation = data.conversation;
    const panel = node("article", { className: "panel-card" });
    const back = node("button", { className: "button button-ghost small", textContent: "← Voltar para conversas", type: "button" });
    back.addEventListener("click", async () => {
      try { await loadConversations(); renderConversations(); }
      catch (error) { captureError(error, { source: "action", component: "conversation-back" }); renderFallback("Conversas", () => { void loadConversations().then(renderConversations).catch((retryError) => captureError(retryError, { source: "action", component: "conversation-retry" })); }); }
    });
    panel.append(node("div", { className: "section-intro" }, [
      node("div", {}, [node("p", { className: "eyebrow", textContent: "TIMELINE" }), node("h3", { textContent: conversation.customer?.display_name || "Conversa" }), node("p", { className: "muted", textContent: `${conversation.channel} · ${conversation.status} · ${conversation.subject || "Sem assunto"}` })]),
      back,
    ]));
    const timeline = node("div", { className: "timeline" });
    (data.events || []).forEach((event) => {
      timeline.append(node("div", { className: "timeline-item" }, [
        node("div", { className: "timeline-meta", textContent: `${event.actor_type} · ${event.direction} · ${event.channel || conversation.channel}` }),
        node("pre", { className: "timeline-content", textContent: JSON.stringify(event.content, null, 2) }),
      ]));
    });
    if (!data.events?.length) timeline.append(node("p", { className: "empty", textContent: "A conversa ainda não possui eventos." }));
    panel.append(timeline);
    content.replaceChildren(panel);
  }

  function renderGeneric(title, description) {
    const content = $("#dashboard-content");
    content.replaceChildren(node("article", { className: "panel-card" }, [
      node("p", { className: "eyebrow", textContent: "MÓDULO" }),
      node("h3", { textContent: title }),
      node("p", { className: "muted", textContent: description }),
    ]));
  }

  function renderOwnerWhatsapp() {
    const content = $("#dashboard-content");
    const current = state.ownerWhatsapp || { status: "not_configured", provider_type: "meta_cloud", opt_in_required: true };
    const isConnected = current.status === "connected";
    const form = node("form", { className: "form-stack" });
    const phoneId = node("input", { name: "phone_number_id", inputmode: "numeric", autocomplete: "off", placeholder: "ID numérico do Phone Number", required: "true" });
    const wabaId = node("input", { name: "waba_id", inputmode: "numeric", autocomplete: "off", placeholder: "WABA ID (opcional)" });
    const accessToken = node("input", { name: "access_token", type: "password", autocomplete: "new-password", placeholder: "Deixe vazio para manter o token salvo" });
    const appSecret = node("input", { name: "app_secret", type: "password", autocomplete: "new-password", placeholder: "Deixe vazio para manter o App Secret" });
    const verifyToken = node("input", { name: "webhook_verify_token", type: "password", autocomplete: "new-password", placeholder: "Token de verificação do webhook" });
    const templateName = node("input", { name: "welcome_template_name", placeholder: "ex.: welcome_new_signup", pattern: "[A-Za-z0-9_]+" });
    const templateLanguage = node("input", { name: "welcome_template_language", value: "pt_BR", placeholder: "pt_BR" });
    const welcomeEnabled = node("input", { name: "welcome_enabled", type: "checkbox" });
    const saveButton = node("button", { className: "button button-primary", type: "submit", textContent: "Salvar integração" });
    const testButton = node("button", { className: "button button-ghost", type: "button", textContent: "Testar conexão" });
    const disconnectButton = node("button", { className: "button button-danger", type: "button", textContent: "Desconectar" });
    phoneId.value = current.phone_number_id || "";
    wabaId.value = current.waba_id || "";
    templateName.value = current.welcome_template_name || "";
    templateLanguage.value = current.welcome_template_language || "pt_BR";
    welcomeEnabled.checked = current.welcome_enabled === true;
    form.append(
      node("label", { textContent: "Phone Number ID" }, [phoneId]),
      node("label", { textContent: "WABA ID" }, [wabaId]),
      node("label", { textContent: "System User Token" }, [accessToken]),
      node("label", { textContent: "App Secret" }, [appSecret]),
      node("label", { textContent: "Webhook Verify Token" }, [verifyToken]),
      node("label", { textContent: "Template aprovado de boas-vindas" }, [templateName]),
      node("label", { textContent: "Idioma do template" }, [templateLanguage]),
      node("label", { className: "check-row" }, [welcomeEnabled, node("span", { textContent: "Habilitar boas-vindas somente com opt-in" })]),
      node("div", { className: "button-row" }, [saveButton, testButton, disconnectButton]),
    );
    const statusPanel = node("article", { className: "panel-card" }, [
      node("p", { className: "eyebrow", textContent: "STATUS DA CONEXÃO" }),
      node("h3", { textContent: isConnected ? "WhatsApp conectado" : "WhatsApp aguardando configuração" }),
      node("p", { className: "muted", textContent: "O token nunca volta para o navegador. Campos secretos vazios preservam o valor cifrado já salvo." }),
      node("div", { className: "item-list" }, [
        listItem("Provider", current.provider_type || "meta_cloud", current.status || "not_configured"),
        listItem("Número", current.display_phone_number || current.phone_number_id || "—", current.verified_name || "não validado"),
        listItem("Qualidade", current.quality_rating || "—", current.last_checked_at ? "verificado" : "pendente"),
        listItem("Boas-vindas", current.welcome_enabled ? current.welcome_template_name : "desligadas", current.opt_in_required === false ? "bloqueado" : "opt-in obrigatório"),
      ]),
      current.last_error ? node("p", { className: "alert", textContent: current.last_error }) : node("p", { className: "muted", textContent: "Nenhum erro registrado." }),
    ]);
    const formPanel = node("article", { className: "panel-card" }, [
      node("div", { className: "section-intro" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: "OWNER / META CLOUD" }), node("h3", { textContent: "Conectar WhatsApp oficial" })])]),
      node("p", { className: "muted", textContent: "Use o Phone Number ID e as credenciais server-side do WhatsApp Business Platform. Não usamos QR, scraping ou sessão informal." }),
      form,
    ]);
    content.replaceChildren(node("div", { className: "content-grid" }, [formPanel, statusPanel]));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      saveButton.disabled = true;
      try {
        const body = { phone_number_id: phoneId.value.trim(), waba_id: wabaId.value.trim() || null, welcome_enabled: welcomeEnabled.checked, welcome_template_name: templateName.value.trim() || null, welcome_template_language: templateLanguage.value.trim() || "pt_BR", opt_in_required: true };
        if (accessToken.value.trim()) body.access_token = accessToken.value.trim();
        if (appSecret.value.trim()) body.app_secret = appSecret.value.trim();
        if (verifyToken.value.trim()) body.webhook_verify_token = verifyToken.value.trim();
        state.ownerWhatsapp = await api("/v1/platform/owner/whatsapp", { method: "PUT", body: JSON.stringify(body), component: "owner-whatsapp-save", payloadContext: { phone_number_id: body.phone_number_id, welcome_enabled: body.welcome_enabled } });
        showAlert($("#dashboard-alert"), "Integração salva. Agora teste a conexão com a Meta.", true);
        renderOwnerWhatsapp();
      } catch (error) { captureError(error, { source: "action", component: "owner-whatsapp-save", payload: { phone_number_id: phoneId.value.trim() } }); showAlert($("#dashboard-alert"), error.message); }
      finally { saveButton.disabled = false; }
    });
    testButton.addEventListener("click", async () => {
      testButton.disabled = true;
      try { state.ownerWhatsapp = await api("/v1/platform/owner/whatsapp/test", { method: "POST", body: "{}", component: "owner-whatsapp-test" }); showAlert($("#dashboard-alert"), "Conexão Meta validada.", true); renderOwnerWhatsapp(); }
      catch (error) { captureError(error, { source: "action", component: "owner-whatsapp-test" }); showAlert($("#dashboard-alert"), error.message); }
      finally { testButton.disabled = false; }
    });
    disconnectButton.addEventListener("click", async () => {
      if (!window.confirm("Desconectar o WhatsApp do dono e desligar boas-vindas?")) return;
      disconnectButton.disabled = true;
      try { state.ownerWhatsapp = await api("/v1/platform/owner/whatsapp/disconnect", { method: "POST", body: "{}", component: "owner-whatsapp-disconnect" }); showAlert($("#dashboard-alert"), "Integração desconectada.", true); renderOwnerWhatsapp(); }
      catch (error) { captureError(error, { source: "action", component: "owner-whatsapp-disconnect" }); showAlert($("#dashboard-alert"), error.message); }
      finally { disconnectButton.disabled = false; }
    });
  }

  function renderDashboard() {
    const titles = { overview: "Visão geral", projects: "Projetos & providers", conversations: "Conversas", keys: "API keys", webhooks: "Webhooks", usage: "Uso & quotas", "owner-whatsapp": "WhatsApp do dono" };
    $("#dashboard-title").textContent = titles[state.section] || titles.overview;
    const renderers = {
      overview: ["Visão geral", renderOverview],
      projects: ["Projetos", renderProjects],
      conversations: ["Conversas", renderConversations],
      keys: ["API keys", () => renderGeneric("API keys", "Crie credenciais por projeto, atribua scopes mínimos e revogue sem derrubar o tenant inteiro.")],
      webhooks: ["Webhooks", () => renderGeneric("Webhooks", "Eventos Meta entram assinados, passam por idempotência e serão entregues ao endpoint do cliente com replay controlado.")],
      usage: ["Uso & quotas", () => renderGeneric("Uso & quotas", "Consumo por tenant, limite de mensagens e sinais de qualidade do provider ficam observáveis antes de virar incêndio.")],
      "owner-whatsapp": ["WhatsApp do dono", renderOwnerWhatsapp],
    };
    const [label, renderer] = renderers[state.section] || renderers.overview;
    diagnostics.safeRender(state.section, renderer, (retry) => renderFallback(label, retry), { state: { section: state.section, tenant: state.selectedTenant?.id } });
  }

  $("#toggle-auth").addEventListener("click", () => {
    state.signup = !state.signup;
    $("#login-form").hidden = state.signup;
    $("#signup-form").hidden = !state.signup;
    $("#auth-title").textContent = state.signup ? "Crie seu ambiente." : "Entre no control plane.";
    $("#auth-copy").textContent = state.signup ? "Seu tenant nasce isolado e pronto para receber projetos." : "A base é profissional. O acesso também precisa ser.";
    $("#toggle-auth").textContent = state.signup ? "Já tenho acesso" : "Ainda não tenho acesso";
    hideAlert($("#auth-alert"));
  });

  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    hideAlert($("#auth-alert")); setLoading(form, true);
    try {
      const data = await api("/v1/platform/auth/login", { method: "POST", body: JSON.stringify(formObject(form)) });
      state.user = data.user; await loadTenants(); showDashboard();
    } catch (error) { captureError(error, { source: "action", component: "auth-form" }); showAlert($("#auth-alert"), error.message); }
    finally { setLoading(form, false); }
  });

  $("#signup-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    hideAlert($("#auth-alert")); setLoading(form, true);
    try {
      const signupBody = formObject(form);
      signupBody.whatsapp_opt_in = Boolean(form.elements.whatsapp_opt_in?.checked);
      signupBody.whatsapp_opt_in_source = signupBody.whatsapp_opt_in ? "platform_signup_checkbox" : null;
      const data = await api("/v1/platform/auth/signup", { method: "POST", body: JSON.stringify(signupBody), component: "signup-form", payloadContext: { whatsapp_opt_in: signupBody.whatsapp_opt_in } });
      showAlert($("#auth-alert"), data.message || "Conta criada. Confirme o email para entrar.", true);
      form.reset();
    } catch (error) { captureError(error, { source: "action", component: "auth-form" }); showAlert($("#auth-alert"), error.message); }
    finally { setLoading(form, false); }
  });

  $("#logout-button").addEventListener("click", async () => {
    try { await api("/v1/platform/auth/logout", { method: "POST", body: "{}" }); } finally { state.user = null; showAuth(); }
  });

  document.querySelectorAll(".side-link").forEach((button) => button.addEventListener("click", async () => {
    document.querySelectorAll(".side-link").forEach((item) => item.classList.remove("active"));
    button.classList.add("active"); state.section = button.dataset.section;
    if (state.selectedTenant) {
      try {
        if (state.section === "projects") await loadProjects();
        if (state.section === "conversations") await loadConversations();
        if (state.section === "owner-whatsapp") await loadOwnerWhatsapp();
      } catch (error) { captureError(error, { source: "navigation", component: state.section }); }
    }
    renderDashboard();
  }));

  void loadSession().catch((error) => { captureError(error, { source: "bootstrap", component: "platform-app" }); showAuth(); });
})();
