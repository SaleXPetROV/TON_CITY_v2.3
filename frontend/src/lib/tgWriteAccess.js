/** Can the bot write to this player? Telegram tells the Mini App (initData user.allows_write_to_pm); if not, the app
 *  asks «Разрешить боту писать вам?» (WebApp.requestWriteAccess) — at most once in 3 days, so it never nags — and
 *  reports the answer to the server (announcements in Telegram reach only players who allowed it). */
const KEY = 'gc_tg_write_ask_at';
const ASK_EVERY_MS = 3 * 24 * 3600 * 1000;
const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;

function report(body) {
  try {
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${API}/auth/telegram/write-access`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }).catch(() => {});
  } catch (_) { /* ignore */ }
}

/** force — right after a Telegram login (asked regardless of the 3-day pause, as before). */
export function ensureTgWriteAccess(force = false) {
  try {
    const wa = window?.Telegram?.WebApp;
    if (!wa?.initData) return;                                  // not inside Telegram
    const allowed = wa.initDataUnsafe?.user?.allows_write_to_pm;
    if (allowed === true) {
      const last = Number(localStorage.getItem('gc_tg_write_ok_at') || 0);
      if (Date.now() - last > 24 * 3600 * 1000) {               // once a day is enough
        localStorage.setItem('gc_tg_write_ok_at', String(Date.now()));
        report({ allowed: true });
      }
      return;
    }
    if (typeof wa.requestWriteAccess !== 'function') return;
    const last = Number(localStorage.getItem(KEY) || 0);
    if (!force && Date.now() - last < ASK_EVERY_MS) return;
    localStorage.setItem(KEY, String(Date.now()));
    wa.requestWriteAccess((granted) => report({ allowed: false, granted: !!granted }));
  } catch (_) { /* ignore */ }
}
