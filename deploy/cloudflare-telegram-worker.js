// GRAM City — зеркало Telegram Bot API на Cloudflare Workers.
// Сервер игры ходит сюда вместо api.telegram.org (TELEGRAM_API_BASE в backend/.env).
// Пропускает только запросы бота: /bot<токен>/<метод> и /file/bot<токен>/<путь>.

const TELEGRAM = "https://api.telegram.org";

// Цифры ДО двоеточия в токене вашего бота (например 7712345678).
// Тогда зеркалом сможет пользоваться только ваш бот. Пусто — любой бот.
const ALLOWED_BOT_ID = "";

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (path === "/" || path === "/health") {
      return new Response("ok", { status: 200 });
    }

    const m = path.match(/^\/(?:file\/)?bot(\d+):[A-Za-z0-9_-]+(?:\/|$)/);
    if (!m) {
      return json({ ok: false, error_code: 404, description: "mirror: not a Bot API path" }, 404);
    }
    if (ALLOWED_BOT_ID && m[1] !== ALLOWED_BOT_ID) {
      return json({ ok: false, error_code: 403, description: "mirror: this bot is not allowed" }, 403);
    }

    // заголовки как есть, кроме служебных заголовков Cloudflare / прокси
    const headers = new Headers(request.headers);
    for (const h of ["host", "cf-connecting-ip", "cf-ipcountry", "cf-ray", "cf-visitor",
                     "x-forwarded-for", "x-forwarded-proto", "x-real-ip"]) {
      headers.delete(h);
    }

    const init = { method: request.method, headers, redirect: "follow" };
    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = request.body;            // JSON и multipart (картинки) передаются без изменений
    }

    try {
      const resp = await fetch(TELEGRAM + path + url.search, init);
      return new Response(resp.body, { status: resp.status, statusText: resp.statusText, headers: resp.headers });
    } catch (e) {
      return json({ ok: false, error_code: 502, description: "mirror: " + (e && e.message ? e.message : String(e)) }, 502);
    }
  },
};

function json(obj, status) {
  return new Response(JSON.stringify(obj), { status, headers: { "content-type": "application/json; charset=utf-8" } });
}
