const API_ORIGIN = "https://nashron.onrender.com";

export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
    if (incoming.pathname.startsWith("/api/")) {
      const target = new URL(incoming.pathname + incoming.search, API_ORIGIN);
      return fetch(new Request(target, request));
    }
    if (incoming.pathname === "/app" || incoming.pathname === "/app/") {
      incoming.pathname = "/app.html";
    }
    return env.ASSETS.fetch(new Request(incoming, request));
  },
};
