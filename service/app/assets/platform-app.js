(() => {
  "use strict";

  const state = { user: null, tenants: [], projects: [], conversations: [], channels: [], channelProvider: {}, channelActions: {}, inbox: [], apiKeys: [], newlyIssuedKey: null, onboarding: null, ownerWhatsapp: null, selectedTenant: null, section: "overview", signup: false };
  const $ = (selector) => document.querySelector(selector);
  const syncMobileNav = (open) => { const dashboard = $("#dashboard-view"); const toggle = $("#mobile-menu-toggle"); if (!dashboard) return; dashboard.classList.toggle("nav-open", open); document.body.classList.toggle("mobile-nav-open", open); toggle?.setAttribute("aria-expanded", String(open)); toggle?.setAttribute("aria-label", open ? "Fechar menu principal" : "Abrir menu principal"); };
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
    if (!target) return;
    target.textContent = message;
    target.className = success ? "alert success" : "alert";
    target.hidden = false;
  }

  function hideAlert(target) {
    if (!target) return;
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
        ...fetchOptions,
        headers: { "Content-Type": "application/json", ...(fetchOptions.headers || {}) },
        timeoutMs,
        requestId,
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

  async function loadApiKeys() {
    const tenant = state.selectedTenant;
    const project = activeProject();
    state.apiKeys = tenant && project ? (await api(`/v1/platform/projects/${encodeURIComponent(project.id)}/keys?tenant_id=${encodeURIComponent(tenant.id)}`, { component: "api-keys-loader" })).items || [] : [];
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
    syncMobileNav(false);
    $("#auth-view").hidden = false;
    $("#dashboard-view").hidden = true;
  }

  function showDashboard() {
    $("#auth-view").hidden = true;
    $("#dashboard-view").hidden = false;
    syncMobileNav(false);
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
      card("Provider", state.projects[0]?.provider_type || "Meta Cloud — oficial", "adapter server-side"),
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
          listItem("Vincular provider", "Meta Cloud oficial ou Evolution compatibilidade", "server-side"),
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
    const providerInput = node("select", { name: "provider_type" }, [node("option", { value: "meta_cloud", textContent: "Meta Cloud — oficial" }), node("option", { value: "evolution", textContent: "Evolution — compatibilidade" })]);
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

  function activeProject() { return state.projects[0] || null; }

  async function loadOnboarding() {
    const project = activeProject();
    state.onboarding = project ? await api(`/v1/onboarding?project_id=${encodeURIComponent(project.id)}`, { component: "onboarding-loader" }) : null;
  }

  function renderOnboarding() {
    const content = $("#dashboard-content");
    const project = activeProject();
    if (!state.selectedTenant || !project) {
      content.replaceChildren(node("article", { className: "panel-card" }, [node("p", { className: "eyebrow", textContent: "PRIMEIRO VALOR" }), node("h3", { textContent: "Crie seu primeiro projeto" }), node("p", { className: "muted", textContent: "O checklist começa quando existe uma organização e um projeto ativo." }), node("div", { className: "fallback-actions" }, [node("button", { className: "button button-primary small", type: "button", textContent: "Abrir projetos", onclick: () => document.querySelector('[data-section="projects"]')?.click() })])]));
      return;
    }
    const data = state.onboarding || {};
    const progress = data.progress || { completed: 0, total: 5, percent: 0 };
    const steps = node("div", { className: "onboarding-steps" });
    (data.steps || []).forEach((step, index) => {
      const complete = step.status === "complete";
      steps.append(node("article", { className: `onboarding-step${complete ? " is-complete" : ""}` }, [node("span", { className: "step-marker", textContent: complete ? "✓" : String(index + 1) }), node("div", {}, [node("strong", { textContent: step.label }), node("small", { textContent: complete ? "Concluído" : "Próximo passo" })])]));
    });
    const next = data.next_action;
    const actionButton = next?.key === "channel" ? node("button", { className: "button button-primary small", type: "button", textContent: "Conectar canal", onclick: () => document.querySelector('[data-section="channels"]')?.click() }) : next?.key === "simulation" ? node("button", { className: "button button-primary small", type: "button", textContent: "Abrir canais", onclick: () => document.querySelector('[data-section="channels"]')?.click() }) : null;
    content.replaceChildren(node("section", { className: "panel-card onboarding-hero" }, [node("div", { className: "section-intro" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: "PRIMEIRO VALOR" }), node("h3", { textContent: "Leve o projeto do zero ao primeiro evento" }), node("p", { className: "muted", textContent: `${data.organization?.name || state.selectedTenant.legal_name} · ${data.project?.name || project.name}` })]), actionButton || node("span", { className: "badge", textContent: "Em andamento" })]), node("div", { className: "progress-meta" }, [node("strong", { textContent: `${progress.percent || 0}% concluído` }), node("span", { textContent: `${progress.completed || 0} de ${progress.total || 5} etapas` })]), node("div", { className: "progress-track" }, [node("span", { className: "progress-fill", style: `width:${Math.min(100, Math.max(0, Number(progress.percent || 0)))}%` })])]), node("section", { className: "panel-card" }, [node("div", { className: "section-intro" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: "CHECKLIST OPERACIONAL" }), node("h3", { textContent: "Seu ambiente está sendo preparado" })]), node("span", { className: "badge", textContent: data.project?.provider || project.provider_type || "provider pendente" })]), steps]));
  }

  async function loadChannels() {
    const tenant = state.selectedTenant;
    const project = activeProject();
    state.channels = tenant && project ? (await api(`/v1/organizations/${encodeURIComponent(tenant.uuid)}/channels?project_id=${encodeURIComponent(project.uuid)}`, { component: "channels-loader" })).items || [] : [];
  }

  function renderProviderOutput(channel) {
    const provider = state.channelProvider[channel.id];
    if (!provider) return null;
    const qrValue = provider.qrcode || provider.qr || provider.qr_code;
    const qrImage = provider.qrcode_svg || provider.qr_svg;
    const codeValue = provider.code || provider.pairing_code;
    if (!qrValue && !qrImage && !codeValue) return node("p", { className: "muted", textContent: "O provider ainda não retornou QR ou código. Atualize o status em alguns segundos." });
    const output = node("div", { className: "channel-output" }, [node("p", { className: "eyebrow", textContent: codeValue ? "PAIRING" : "QR DO CANAL" })]);
    if (codeValue) output.append(node("div", { className: "pairing-code", textContent: String(codeValue) }));
    if (qrImage) {
      const imageValue = String(qrImage);
      const source = imageValue.startsWith("data:image/") ? imageValue : `data:image/svg+xml;charset=utf-8,${encodeURIComponent(imageValue)}`;
      output.append(node("img", { className: "channel-qr", src: source, alt: "QR Code do canal Evolution para escanear no WhatsApp" }));
    } else if (qrValue) {
      output.append(node("p", { className: "muted", textContent: "QR recebido, mas a imagem ainda não está disponível. Solicite um novo QR." }));
    }
    output.append(node("p", { className: "muted", textContent: "O QR é sensível: escaneie apenas no WhatsApp do número de laboratório e não compartilhe." }));
    return output;
  }

  async function channelAction(channel, action) {
    const actionKey = `${channel.id}:${action}`;
    if (state.channelActions[actionKey]) return;
    state.channelActions[actionKey] = true;
    if (state.section === "channels") renderChannels();
    const method = action === "qr" || action === "status" ? "GET" : "POST";
    const path = action === "qr" ? `/v1/platform/channels/${encodeURIComponent(channel.id)}/qr` : action === "status" ? `/v1/platform/channels/${encodeURIComponent(channel.id)}/status` : `/v1/platform/channels/${encodeURIComponent(channel.id)}/${action}`;
    try {
      const result = await api(path, { method, body: method === "POST" ? "{}" : undefined, component: `channel-${action}`, payloadContext: { channel_id: channel.id } });
      if (result.provider) state.channelProvider[channel.id] = result.provider;
      if (action === "qr") state.channelProvider[channel.id] = result;
      await loadChannels();
      showAlert($("#dashboard-alert"), action === "qr" ? "QR atualizado. Escaneie somente no WhatsApp de laboratório." : "Ação do canal concluída.", true);
    } catch (error) {
      captureError(error, { source: "action", component: `channel-${action}`, payload: { channel_id: channel.id } });
      showAlert($("#dashboard-alert"), error.message);
    } finally {
      delete state.channelActions[actionKey];
      if (state.section === "channels") renderChannels();
    }
  }

  function connectLabelFor(channel) {
    const action = ["created", "disconnected", "degraded"].includes(channel.status) ? "connect" : "reconnect";
    return { action, label: action === "connect" ? "Conectar" : "Reconectar" };
  }

  function renderChannels() {
    const content = $("#dashboard-content");
    const tenant = state.selectedTenant;
    const project = activeProject();
    if (!tenant || !project) { content.replaceChildren(node("article", { className: "panel-card" }, [node("p", { className: "eyebrow", textContent: "CANAIS" }), node("h3", { textContent: "Crie um projeto antes de conectar" }), node("p", { className: "muted", textContent: "Cada canal pertence a uma organização e a um projeto. Isso mantém provider, quotas e auditoria isolados." })])); return; }
    const displayName = node("input", { name: "display_name", placeholder: "ex.: Laboratório WhatsApp", required: "true", minlength: "3", maxlength: "120" });
    const flavor = node("select", { name: "provider_flavor" }, [node("option", { value: "evolution_api", textContent: "Evolution API v2 — compatibilidade" }), node("option", { value: "evolution_go", textContent: "Evolution Go — compatibilidade" })]);
    const form = node("form", { className: "form-stack channel-create-form" }, [node("label", { textContent: "Nome do canal" }, [displayName]), node("label", { textContent: "Flavor do provider" }, [flavor]), node("p", { className: "form-hint", textContent: "Meta Cloud oficial é configurado separadamente. Este wizard é exclusivamente para Evolution compatibilidade." }), node("button", { className: "button button-primary", type: "submit", textContent: "Criar canal de laboratório" }), node("div", { id: "channel-create-msg", className: "alert", hidden: true })]);
    form.addEventListener("submit", async (event) => { event.preventDefault(); const submit = form.querySelector("button[type=submit]"); submit.disabled = true; try { await api(`/v1/organizations/${encodeURIComponent(tenant.uuid)}/channels`, { method: "POST", headers: { "Idempotency-Key": `channel-${crypto.randomUUID ? crypto.randomUUID() : Date.now()}` }, body: JSON.stringify({ project_id: project.uuid, display_name: displayName.value.trim(), provider: "evolution", provider_flavor: flavor.value, events: ["MESSAGES_UPSERT", "CONNECTION_UPDATE"] }), component: "channel-create", payloadContext: { provider: "evolution", provider_flavor: flavor.value } }); await loadChannels(); renderChannels(); showAlert($("#dashboard-alert"), "Canal criado. Agora inicie a conexão para obter o QR.", true); } catch (error) { showAlert($("#channel-create-msg"), error.message); } finally { submit.disabled = false; } });
    const list = node("div", { className: "channel-list" });
    if (!state.channels.length) list.append(node("div", { className: "empty" }, [node("strong", { textContent: "Nenhum canal neste projeto" }), node("p", { className: "muted", textContent: "Crie o canal de laboratório acima. O provider será identificado como Evolution compatibilidade." })]));
    state.channels.forEach((channel) => { const actions = node("div", { className: "button-row" }); const connectAction = connectLabelFor(channel); const connectButton = node("button", { className: "button button-primary small", type: "button", textContent: connectAction.label, onclick: () => void channelAction(channel, connectAction.action) }); const qrButton = node("button", { className: "button button-ghost small", type: "button", textContent: "Obter QR", onclick: () => void channelAction(channel, "qr") }); const statusButton = node("button", { className: "button button-ghost small", type: "button", textContent: "Atualizar status", onclick: () => void channelAction(channel, "status") }); const disconnectButton = node("button", { className: "button button-danger small", type: "button", textContent: "Desconectar", onclick: () => void channelAction(channel, "disconnect") }); [connectButton, qrButton, statusButton, disconnectButton].forEach((button) => { const action = button === connectButton ? connectAction.action : button === qrButton ? "qr" : button === statusButton ? "status" : "disconnect"; if (state.channelActions[`${channel.id}:${action}`]) { button.disabled = true; button.textContent = "Processando…"; } }); actions.append(connectButton, qrButton, statusButton, disconnectButton); const row = node("article", { className: "channel-row" }, [node("div", { className: "channel-row-head" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: channel.provider_flavor || "EVOLUTION" }), node("h4", { textContent: channel.display_name }), node("p", { className: "muted", textContent: `${channel.phone_number || "Número aguardando conexão"} · ${channel.webhook_configured ? "webhook configurado" : "webhook pendente"}` })]), node("span", { className: `badge channel-status-${channel.status}`, textContent: channel.status })]), actions]); const providerOutput = renderProviderOutput(channel); if (providerOutput) row.append(providerOutput); list.append(row); });
    content.replaceChildren(node("section", { className: "panel-card channel-hero" }, [node("div", { className: "section-intro" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: "CANAIS / COMPATIBILIDADE" }), node("h3", { textContent: "Conecte seu primeiro número" }), node("p", { className: "muted", textContent: `${tenant.legal_name} · ${project.name}` })]), node("span", { className: "badge", textContent: "Evolution — compatibilidade" })]), form]), node("section", { className: "panel-card" }, [node("div", { className: "section-intro" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: "CANAIS ATIVOS" }), node("h3", { textContent: "Saúde e conexão" })]), node("span", { className: "badge", textContent: `${state.channels.length} canal(is)` })]), list]));
  }

  async function loadInbox() {
    const tenant = state.selectedTenant;
    const project = activeProject();
    state.inbox = tenant && project ? (await api(`/v1/platform/inbox/conversations?tenant_id=${encodeURIComponent(tenant.id)}&project_id=${encodeURIComponent(project.id)}&limit=50`, { component: "inbox-loader" })).items || [] : [];
  }

  async function inboxAction(conversation, action) {
    const tenant = state.selectedTenant;
    await api(`/v1/platform/inbox/conversations/${encodeURIComponent(conversation.id)}/${action}?tenant_id=${encodeURIComponent(tenant.id)}`, { method: "POST", body: "{}", component: `inbox-${action}`, payloadContext: { conversation_id: conversation.id } });
    await loadInbox(); renderInbox();
  }

  async function openInboxConversation(conversationId) {
    const tenant = state.selectedTenant;
    const data = await api(`/v1/platform/inbox/conversations/${encodeURIComponent(conversationId)}?tenant_id=${encodeURIComponent(tenant.id)}`, { component: "inbox-detail" });
    renderConversationDetail(data);
  }

  function renderInbox() {
    const content = $("#dashboard-content");
    const tenant = state.selectedTenant;
    const project = activeProject();
    if (!tenant || !project) { content.replaceChildren(node("article", { className: "panel-card" }, [node("p", { className: "eyebrow", textContent: "INBOX" }), node("h3", { textContent: "Crie um projeto para abrir o inbox" }), node("p", { className: "muted", textContent: "A distribuição é tenant-scoped e começa com um projeto ativo." })])); return; }
    const list = node("div", { className: "inbox-list" });
    if (!state.inbox.length) list.append(node("div", { className: "empty" }, [node("strong", { textContent: "Inbox aguardando o primeiro evento" }), node("p", { className: "muted", textContent: "Quando um webhook inbound chegar, a conversa aparecerá com estado, fila e assignment." })]));
    state.inbox.forEach((conversation) => { const customer = conversation.customer?.display_name || conversation.customer?.external_ref || "Contato sem nome"; const actions = node("div", { className: "button-row" }); if (conversation.assignment?.assignee_user_id !== state.user?.id) actions.append(node("button", { className: "button button-primary small", type: "button", textContent: "Assumir", onclick: () => inboxAction(conversation, "claim") })); actions.append(node("button", { className: "button button-ghost small", type: "button", textContent: "Resolver", onclick: () => inboxAction(conversation, "resolve") })); const row = node("article", { className: "inbox-row" }, [node("button", { className: "inbox-row-main", type: "button", onclick: () => openInboxConversation(conversation.id) }, [node("div", {}, [node("strong", { textContent: customer }), node("small", { textContent: `${conversation.channel || "canal"} · ${conversation.subject || "Sem assunto"}` })]), node("span", { className: "badge", textContent: conversation.status || "active" })]), actions]); list.append(row); });
    content.replaceChildren(node("section", { className: "panel-card inbox-hero" }, [node("div", { className: "section-intro" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: "INBOX / DISTRIBUIÇÃO" }), node("h3", { textContent: "Atenda sem perder contexto" }), node("p", { className: "muted", textContent: `${tenant.legal_name} · ${state.inbox.length} conversa(s) carregada(s)` })]), node("span", { className: "badge", textContent: "tenant-scoped" })]), list]));
  }

  function renderApiKeys() {
    const content = $("#dashboard-content");
    const tenant = state.selectedTenant;
    const project = activeProject();
    if (!tenant || !project) { content.replaceChildren(node("article", { className: "panel-card" }, [node("p", { className: "eyebrow", textContent: "API KEYS" }), node("h3", { textContent: "Crie um projeto antes da chave" }), node("p", { className: "muted", textContent: "Cada chave pertence a um projeto e nunca é compartilhada entre tenants." })])); return; }
    const scopes = ["channels:read", "channels:write", "webhooks:read", "webhooks:write", "whatsapp:messages:send"];
    const selected = new Set(scopes);
    const scopeList = node("div", { className: "scope-grid" });
    scopes.forEach((scope) => { const checkbox = node("input", { type: "checkbox", value: scope, checked: "true" }); checkbox.checked = selected.has(scope); checkbox.addEventListener("change", () => checkbox.checked ? selected.add(scope) : selected.delete(scope)); scopeList.append(node("label", { className: "check-row scope-option" }, [checkbox, node("span", { textContent: scope })])); });
    const form = node("form", { className: "form-stack" }, [node("p", { className: "form-hint", textContent: `Projeto: ${project.name} · ${tenant.legal_name}` }), node("p", { className: "muted", textContent: "A chave será exibida uma única vez. Copie diretamente desta tela e nunca a envie pelo chat." }), scopeList, node("button", { className: "button button-primary", type: "submit", textContent: "Emitir chave do laboratório" }), node("div", { id: "api-key-create-msg", className: "alert", hidden: true })]);
    form.addEventListener("submit", async (event) => { event.preventDefault(); const submit = form.querySelector("button[type=submit]"); submit.disabled = true; try { const result = await api(`/v1/platform/projects/${encodeURIComponent(project.id)}/keys?tenant_id=${encodeURIComponent(tenant.id)}`, { method: "POST", body: JSON.stringify({ project_id: project.id, scopes: [...selected] }), component: "api-key-create", payloadContext: { scopes: [...selected] } }); state.newlyIssuedKey = result.key || null; await loadApiKeys(); renderApiKeys(); } catch (error) { showAlert($("#api-key-create-msg"), error.message); } finally { submit.disabled = false; } });
    const issued = state.newlyIssuedKey;
    const issuedPanel = issued?.token ? node("article", { className: "one-time-secret" }, [node("p", { className: "eyebrow", textContent: "TOKEN DE USO ÚNICO" }), node("p", { className: "muted", textContent: "Copie agora. O token não será retornado novamente pela API." }), node("code", { className: "secret-token", textContent: issued.token }), node("button", { className: "button button-primary small", type: "button", textContent: "Copiar chave" , onclick: async () => { await navigator.clipboard.writeText(issued.token); showAlert($("#api-key-create-msg"), "Chave copiada para a área de transferência.", true); } })]) : null;
    const rows = node("div", { className: "api-key-list" });
    if (!state.apiKeys.length) rows.append(node("p", { className: "empty", textContent: "Nenhuma chave emitida neste projeto." }));
    state.apiKeys.forEach((key) => rows.append(node("article", { className: "api-key-row" }, [node("div", {}, [node("strong", { textContent: `${key.prefix}••••••••` }), node("small", { textContent: `${(key.scopes || []).join(" · ")} · criada em ${key.created_at || "—"}` })]), node("span", { className: "badge", textContent: key.status })])));
    const panel = node("section", { className: "panel-card" }, [node("div", { className: "section-intro" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: "CREDENCIAL M2M" }), node("h3", { textContent: "Service API Key do projeto" }), node("p", { className: "muted", textContent: "Escopos mínimos para channels, webhooks e envio controlado." })])]), form]);
    if (issuedPanel) panel.append(issuedPanel);
    content.replaceChildren(panel, node("section", { className: "panel-card" }, [node("div", { className: "section-intro" }, [node("div", {}, [node("p", { className: "eyebrow", textContent: "CHAVES ATIVAS" }), node("h3", { textContent: "Listagem mascarada" })]), node("span", { className: "badge", textContent: `${state.apiKeys.length} chave(s)` })]), rows]));
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
    const titles = { overview: "Visão geral", onboarding: "Primeiro valor", projects: "Projetos & providers", channels: "Canais", inbox: "Inbox", conversations: "Conversas", keys: "API keys", webhooks: "Webhooks", usage: "Uso & quotas", "owner-whatsapp": "WhatsApp do dono" };
    $("#dashboard-title").textContent = titles[state.section] || titles.overview;
    const renderers = {
      overview: ["Visão geral", renderOverview],
      onboarding: ["Primeiro valor", renderOnboarding],
      projects: ["Projetos", renderProjects],
      channels: ["Canais", renderChannels],
      inbox: ["Inbox", renderInbox],
      conversations: ["Conversas", renderConversations],
      keys: ["API keys", renderApiKeys],
      webhooks: ["Webhooks", () => renderGeneric("Webhooks", "Eventos Meta entram assinados, passam por idempotência e serão entregues ao endpoint do cliente com replay controlado.")],
      usage: ["Uso & quotas", () => renderGeneric("Uso & quotas", "Consumo por tenant, limite de mensagens e sinais de qualidade do provider ficam observáveis antes de virar incêndio.")],
      "owner-whatsapp": ["WhatsApp do dono", renderOwnerWhatsapp],
    };
    const [label, renderer] = renderers[state.section] || renderers.overview;
    diagnostics.safeRender(state.section, renderer, (retry) => renderFallback(label, retry), { state: { section: state.section, tenant: state.selectedTenant?.id } });
  }

  $("#mobile-menu-toggle")?.addEventListener("click", () => syncMobileNav(!$("#dashboard-view")?.classList.contains("nav-open")));
  $("#sidebar-close")?.addEventListener("click", () => syncMobileNav(false));
  $("#mobile-nav-backdrop")?.addEventListener("click", () => syncMobileNav(false));
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") syncMobileNav(false); });

  const setAuthMode = (mode) => {
    state.signup = mode === "signup";
    $("#login-form").hidden = mode !== "login";
    $("#signup-form").hidden = mode !== "signup";
    $("#password-reset-form").hidden = mode !== "reset";
    $("#reset-confirm-form").hidden = mode !== "confirm-reset";
    $("#toggle-auth").hidden = mode === "reset" || mode === "confirm-reset";
    $("#toggle-reset").hidden = mode === "reset" || mode === "confirm-reset";
    $("#auth-title").textContent = mode === "signup" ? "Crie seu ambiente." : mode === "reset" ? "Redefina sua senha." : mode === "confirm-reset" ? "Escolha uma nova senha." : "Entre no control plane.";
    $("#auth-copy").textContent = mode === "signup" ? "Seu tenant nasce isolado e pronto para receber projetos." : mode === "reset" || mode === "confirm-reset" ? "Acesso seguro, link temporário e nenhuma gambiarra." : "A base é profissional. O acesso também precisa ser.";
    $("#toggle-auth").textContent = mode === "signup" ? "Já tenho acesso" : "Ainda não tenho acesso";
    hideAlert($("#auth-alert"));
  };

  $("#toggle-auth").addEventListener("click", () => setAuthMode(state.signup ? "login" : "signup"));
  $("#toggle-reset").addEventListener("click", () => setAuthMode("reset"));

  $("#password-reset-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    hideAlert($("#auth-alert")); setLoading(form, true);
    try {
      await api("/v1/platform/auth/password-reset/request", { method: "POST", body: JSON.stringify(formObject(form)), component: "password-reset-request" });
      form.reset();
      setAuthMode("login");
      showAlert($("#auth-alert"), "Se a conta existir, o link de redefinição foi enviado.", true);
    } catch (error) { captureError(error, { source: "action", component: "password-reset-request" }); showAlert($("#auth-alert"), error.message); }
    finally { setLoading(form, false); }
  });

  $("#reset-confirm-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    hideAlert($("#auth-alert")); setLoading(form, true);
    try {
      await api("/v1/platform/auth/password-reset/confirm", { method: "POST", body: JSON.stringify(formObject(form)), component: "password-reset-confirm" });
      form.reset();
      setAuthMode("login");
      showAlert($("#auth-alert"), "Senha atualizada. Entre com a nova credencial.", true);
      window.history.replaceState({}, document.title, window.location.pathname);
    } catch (error) { captureError(error, { source: "action", component: "password-reset-confirm" }); showAlert($("#auth-alert"), error.message); }
    finally { setLoading(form, false); }
  });

  const authQuery = new URLSearchParams(window.location.search);
  const verifyToken = authQuery.get("verify");
  const resetToken = authQuery.get("reset");
  if (resetToken) {
    $("#reset-token").value = resetToken;
    setAuthMode("confirm-reset");
  } else if (verifyToken) {
    void api("/v1/platform/auth/verify-email", { method: "POST", body: JSON.stringify({ token: verifyToken }), component: "email-verification" })
      .then(() => { setAuthMode("login"); showAlert($("#auth-alert"), "E-mail confirmado. Agora você já pode entrar.", true); window.history.replaceState({}, document.title, window.location.pathname); })
      .catch((error) => { captureError(error, { source: "action", component: "email-verification" }); showAlert($("#auth-alert"), error.message); setAuthMode("login"); });
  }

  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const mfaRow = $("#login-mfa-row");
    const mfaInput = $("#login-mfa-code");
    hideAlert($("#auth-alert")); setLoading(form, true);
    try {
      const credentials = formObject(form);
      credentials.mfa_code = String(credentials.mfa_code || "").trim() || null;
      const data = await api("/v1/platform/auth/login", { method: "POST", body: JSON.stringify(credentials), component: "auth-form", payloadContext: { mfa_present: Boolean(credentials.mfa_code) } });
      state.user = data.user; await loadTenants(); showDashboard();
    } catch (error) {
      captureError(error, { source: "action", component: "auth-form" });
      const detail = String(error?.message || "");
      if (/mfa code required/i.test(detail)) {
        mfaRow.hidden = false;
        mfaInput.required = true;
        showAlert($("#auth-alert"), "Digite o código de seis dígitos do Google Authenticator para continuar.");
        mfaInput.focus();
      } else {
        showAlert($("#auth-alert"), detail || "Não foi possível autenticar.");
      }
    } finally { setLoading(form, false); }
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

  document.querySelectorAll(".side-link").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll(".side-link").forEach((item) => item.classList.remove("active"));
    button.classList.add("active"); state.section = button.dataset.section; syncMobileNav(false);
    const requestedSection = state.section;
    const loaders = { projects: loadProjects, keys: loadApiKeys, onboarding: loadOnboarding, channels: loadChannels, inbox: loadInbox, conversations: loadConversations, "owner-whatsapp": loadOwnerWhatsapp };
    renderDashboard();
    const loader = loaders[requestedSection];
    if (!state.selectedTenant || !loader) return;
    void loader().then(() => { if (state.section === requestedSection) renderDashboard(); }).catch((error) => { captureError(error, { source: "navigation", component: requestedSection }); showAlert($("#dashboard-alert"), error.message); });
  }));

  void loadSession().catch((error) => { captureError(error, { source: "bootstrap", component: "platform-app" }); showAuth(); });
})();
