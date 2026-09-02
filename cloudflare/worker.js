const API_ORIGIN = "https://nashron.onrender.com";

export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
      if (incoming.pathname.startsWith("/api/")) {
        const target = new URL(incoming.pathname + incoming.search, API_ORIGIN);
        return fetch(new Request(target, request));
      }
      // The product HTML keeps the historical /assets/v3 URL prefix while
      // Pages publishes the static directory contents at /v3.
      if (incoming.pathname.startsWith("/assets/")) {
        incoming.pathname = incoming.pathname.slice("/assets".length);
      }
      if (incoming.pathname === "/app" || incoming.pathname === "/app/") {
        incoming.pathname = "/app.html";
      }
    return env.ASSETS.fetch(new Request(incoming, request));
  },
};
