(() => {
  "use strict";

  const MAX_EVENTS = 80;
  const MAX_TEXT = 12000;
  const SECRET_KEYS = /token|secret|password|authorization|cookie|api[_-]?key|private[_-]?key|credential/i;
  const events = [];
  const listeners = new Set();
  let selectedId = null;
  let drawer = null;
  let button = null;
  const debugEnabled = Boolean(
    window.__MAGO_DEBUG__ === true ||
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    new URLSearchParams(window.location.search).get("debug") === "1"
  );

  function now() {
    return new Date().toISOString();
  }

  function requestId() {
    if (window.crypto?.randomUUID) return window.crypto.randomUUID();
    return `mago-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function truncate(value, max = MAX_TEXT) {
    const text = String(value ?? "");
    return text.length > max ? `${text.slice(0, max)}…` : text;
  }

  function sanitize(value, depth = 0, seen = new WeakSet()) {
    if (value === null || value === undefined) return value;
    if (typeof value === "string") return truncate(value, 2000);
    if (typeof value === "number" || typeof value === "boolean") return value;
    if (typeof value === "function") return "[Function]";
    if (depth > 4) return "[Truncated]";
    if (typeof value === "object") {
      if (seen.has(value)) return "[Circular]";
      seen.add(value);
      if (value instanceof Error) {
        return { name: value.name, message: truncate(value.message), stack: truncate(value.stack || "") };
      }
      if (Array.isArray(value)) return value.slice(0, 40).map((item) => sanitize(item, depth + 1, seen));
      const output = {};
      Object.keys(value).slice(0, 80).forEach((key) => {
        output[key] = SECRET_KEYS.test(key) ? "[REDACTED]" : sanitize(value[key], depth + 1, seen);
      });
      return output;
    }
    return String(value);
  }

  function stackLocation(stack) {
    const text = String(stack || "");
    const match = text.match(/(?:at\s+[^()]+\s+\()?((?:https?:\/\/|file:\/\/|\/)[^():\s]+):(\d+):(\d+)\)?/);
    return match ? { file: match[1], line: Number(match[2]), column: Number(match[3]) } : { file: "desconhecido", line: null, column: null };
  }

  function actionPlan(source, message) {
    const common = [
      "Reproduza a falha com o mesmo request ID e preserve o diagnóstico redigido.",
      "Confira o status da dependência e o payload esperado antes de alterar o código.",
      "Aplique a correção em canário, repita o teste de falha e só então promova.",
    ];
    if (source === "network") return ["Verifique conectividade, status HTTP e request ID.", "Confirme se a resposta é JSON e se o endpoint está disponível.", ...common.slice(2)];
    if (/undefined|null|property|Cannot read/i.test(message)) return ["Valide o shape recebido com uma guarda de tipo.", "Use fallback para campos ausentes e preserve o último estado saudável.", ...common.slice(2)];
    return common;
  }

  function notify() {
    listeners.forEach((listener) => listener(events.slice()));
    if (button) button.textContent = `Diagnóstico${events.length ? ` (${events.length})` : ""}`;
    if (drawer) renderDrawer();
  }

  function capture(error, context = {}) {
    const normalized = error instanceof Error ? error : new Error(typeof error === "string" ? error : "Falha desconhecida");
    const source = context.source || "runtime";
    const location = stackLocation(normalized.stack);
    const record = {
      id: requestId(),
      timestamp: now(),
      severity: context.severity || "error",
      source,
      message: truncate(normalized.message || "Falha sem mensagem"),
      stack: truncate(normalized.stack || `${normalized.name}: ${normalized.message}`),
      file: context.file || location.file,
      line: context.line || location.line,
      column: context.column || location.column,
      component: context.component || "desconhecido",
      route: window.location.pathname,
      requestId: context.requestId || null,
      state: sanitize(context.state || {}),
      payload: sanitize(context.payload || {}),
      actionPlan: actionPlan(source, normalized.message || ""),
      recoverable: typeof context.retry === "function",
      retry: context.retry || null,
    };
    events.unshift(record);
    if (events.length > MAX_EVENTS) events.length = MAX_EVENTS;
    selectedId = record.id;
    notify();
    return record;
  }

  function reportHttp(response, url, requestIdValue) {
    if (response.ok) return;
    const error = new Error(`HTTP ${response.status} em ${url}`);
    capture(error, { source: "network", requestId: requestIdValue, payload: { status: response.status, url } });
  }

  function installFetchInterceptor() {
    if (window.__MAGO_FETCH_INTERCEPTED__) return;
    const originalFetch = window.fetch.bind(window);
    window.__MAGO_FETCH_INTERCEPTED__ = true;
    window.fetch = async (input, init = {}) => {
      const controller = new AbortController();
      const timeoutMs = Number(init.timeoutMs || 15000);
      const timer = window.setTimeout(() => controller.abort(), timeoutMs);
      const id = init.requestId || requestId();
      const headers = new Headers(init.headers || {});
      headers.set("X-Request-ID", id);
      const { timeoutMs: _timeoutMs, requestId: _requestId, signal: _signal, ...fetchInit } = init;
      try {
        const response = await originalFetch(input, { ...fetchInit, headers, signal: controller.signal });
        return response;
      } catch (error) {
        const message = error?.name === "AbortError" ? "A requisição excedeu o tempo limite." : (error?.message || "Falha de rede.");
        capture(new Error(message), {
          source: "network",
          requestId: id,
          payload: { url: typeof input === "string" ? input : input.url, method: fetchInit.method || "GET", timeoutMs },
        });
        throw error;
      } finally {
        window.clearTimeout(timer);
      }
    };
  }

  function createElement(tag, props = {}, children = []) {
    const element = document.createElement(tag);
    Object.entries(props).forEach(([key, value]) => {
      if (key === "textContent") element.textContent = value;
      else if (key === "value") element.value = value;
      else if (key === "className") element.className = value;
      else if (key.startsWith("on")) element.addEventListener(key.slice(2).toLowerCase(), value);
      else element.setAttribute(key, value);
    });
    children.forEach((child) => element.append(child));
    return element;
  }

  function reportText(record) {
    return JSON.stringify({ ...record, retry: undefined }, null, 2);
  }

  function copyReport(record) {
    const text = reportText(record);
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(() => notify()).catch(() => fallbackCopy(text));
    } else fallbackCopy(text);
  }

  function fallbackCopy(text) {
    const area = createElement("textarea", { value: text, "aria-hidden": "true" });
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.append(area);
    area.select();
    try { document.execCommand("copy"); } catch (_error) { /* diagnóstico continua disponível no drawer */ }
    area.remove();
  }

  function selected() {
    return events.find((event) => event.id === selectedId) || events[0] || null;
  }

  function renderDrawer() {
    if (!drawer) return;
    const record = selected();
    drawer.replaceChildren();
    const header = createElement("div", { className: "mago-diagnostics-header" }, [
      createElement("div", {}, [createElement("strong", { textContent: "Diagnóstico de falhas" }), createElement("small", { textContent: `${events.length} evento(s) redigido(s)` })]),
      createElement("button", { className: "mago-diagnostics-close", type: "button", textContent: "Fechar", onclick: () => { drawer.hidden = true; } }),
    ]);
    drawer.append(header);
    const list = createElement("div", { className: "mago-diagnostics-list" });
    events.slice(0, 20).forEach((event) => {
      const item = createElement("button", { className: `mago-diagnostics-item${event.id === record?.id ? " selected" : ""}`, type: "button" }, [
        createElement("strong", { textContent: event.message }),
        createElement("small", { textContent: `${event.source} · ${event.component} · ${event.timestamp}` }),
      ]);
      item.addEventListener("click", () => { selectedId = event.id; renderDrawer(); });
      list.append(item);
    });
    drawer.append(list);
    if (!record) {
      drawer.append(createElement("p", { className: "mago-diagnostics-empty", textContent: "Nenhuma falha capturada." }));
      return;
    }
    const detail = createElement("div", { className: "mago-diagnostics-detail" });
    detail.append(
      createElement("h4", { textContent: record.message }),
      createElement("p", { className: "mago-diagnostics-location", textContent: `${record.file}:${record.line || "?"}:${record.column || "?"} · componente: ${record.component} · request: ${record.requestId || "n/a"}` }),
      createElement("pre", { textContent: record.stack }),
      createElement("h5", { textContent: "Estado e payload redigidos" }),
      createElement("pre", { textContent: JSON.stringify({ state: record.state, payload: record.payload }, null, 2) }),
      createElement("h5", { textContent: "Plano de ação" }),
      createElement("ol", {}, record.actionPlan.map((step) => createElement("li", { textContent: step }))),
    );
    const actions = createElement("div", { className: "mago-diagnostics-actions" });
    actions.append(
      createElement("button", { className: "button button-primary small", type: "button", textContent: "Copiar diagnóstico completo", onclick: () => copyReport(record) }),
      createElement("button", { className: "button button-ghost small", type: "button", textContent: "Tentar recarregar componente", onclick: () => { if (record.retry) record.retry(); } }),
      createElement("button", { className: "button button-ghost small", type: "button", textContent: "Limpar logs", onclick: clear }),
    );
    detail.append(actions);
    drawer.append(detail);
  }

  function clear() {
    events.length = 0;
    selectedId = null;
    notify();
  }

  function installDrawer() {
    if (!debugEnabled || button) return;
    button = createElement("button", { className: "mago-diagnostics-trigger", type: "button", textContent: "Diagnóstico", onclick: () => { drawer.hidden = false; renderDrawer(); } });
    drawer = createElement("aside", { className: "mago-diagnostics-drawer", role: "dialog", "aria-label": "Diagnóstico de falhas", hidden: "true" });
    document.body.append(button, drawer);
  }

  function installGlobalHandlers() {
    window.addEventListener("error", (event) => capture(event.error || new Error(event.message), { source: "runtime", file: event.filename, line: event.lineno, column: event.colno }));
    window.addEventListener("unhandledrejection", (event) => capture(event.reason instanceof Error ? event.reason : new Error(String(event.reason || "Promise rejeitada")), { source: "async" }));
  }

  function safeRender(component, renderer, fallback, context = {}) {
    try {
      renderer();
    } catch (error) {
      const retry = () => safeRender(component, renderer, fallback, context);
      capture(error, { source: "render", component, state: context.state, payload: context.payload, retry });
      if (typeof fallback === "function") fallback(retry);
      else if (fallback) fallback.textContent = "Esta área falhou. Abra o diagnóstico e tente novamente.";
    }
  }

  installFetchInterceptor();
  installGlobalHandlers();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", installDrawer, { once: true });
  else installDrawer();

  window.MagoDiagnostics = { capture, clear, subscribe: (listener) => { listeners.add(listener); return () => listeners.delete(listener); }, safeRender, isDebugEnabled: () => debugEnabled, getEvents: () => events.map((event) => ({ ...event, retry: undefined })) };
})();
