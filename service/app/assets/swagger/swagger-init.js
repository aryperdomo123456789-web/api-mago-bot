(function () {
  function startSwagger() {
    if (typeof window.SwaggerUIBundle !== "function") {
      window.setTimeout(startSwagger, 50);
      return;
    }
    window.magoSwaggerUi = window.SwaggerUIBundle({
      url: "/openapi.json",
      dom_id: "#swagger-ui",
      deepLinking: true,
      layout: "BaseLayout",
      displayRequestDuration: true,
      filter: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startSwagger, { once: true });
  } else {
    startSwagger();
  }
})();
