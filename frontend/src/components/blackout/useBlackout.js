/**
 * One shared state of «Блэкаут острова» for the whole app (the banner, the map and the page read the same object).
 * GET /api/blackout every 60 s when calm, every 8 s while the island is dark, every 4 s while the page is open;
 * the server also pushes {type: 'blackout'} over the personal WebSocket — then we refetch at once.
 * Other parts listen to window event 'blackout:event' ({event, data}) for the moment a district lights up.
 */
import { useEffect, useState } from 'react';
import { subscribeUserSocket } from '@/lib/userSocket';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const tok = () => { try { return localStorage.getItem('token') || localStorage.getItem('ton_city_token'); } catch (e) { return null; } };

let state = null;
let timer = null;
let fast = 0;                 // number of open pages that want the fast refresh
let inflight = null;
const subs = new Set();
let unsubSocket = null;
let socketKey = null;
let skew = 0;                 // server clock − local clock (ms): the countdown follows the server

function emit() { subs.forEach((f) => { try { f(state); } catch (e) { /* ignore */ } }); }

export async function refreshBlackout() {
  const t = tok();
  if (!t) return null;
  if (inflight) return inflight;
  inflight = fetch(`${API}/blackout`, { headers: { Authorization: `Bearer ${t}` } })
    .then((r) => (r.ok ? r.json() : null))
    .then((d) => {
      if (d) {
        if (d.server_time) skew = new Date(d.server_time).getTime() - Date.now();
        state = d; emit();
      }
      return d;
    })
    .catch(() => null)
    .finally(() => { inflight = null; schedule(); });
  return inflight;
}

function schedule() {
  clearTimeout(timer);
  if (!subs.size) return;
  const ms = fast > 0 ? 4000 : state?.active ? 8000 : 60000;
  timer = setTimeout(refreshBlackout, ms);
}

export function serverNow() { return Date.now() + skew; }

export function setBlackoutState(d) { if (d) { state = d; emit(); } }

function socketFor(user) {
  const key = user && (user.id || user.email || user.wallet_address || user.username);
  if (!key || key === socketKey) return;
  if (unsubSocket) unsubSocket();
  socketKey = key;
  unsubSocket = subscribeUserSocket(key, (msg) => {
    if (msg?.type !== 'blackout') return;
    window.dispatchEvent(new CustomEvent('blackout:event', { detail: { event: msg.event, data: msg.data || {} } }));
    refreshBlackout();
  });
}

/** const bo = useBlackout(user, {fast: true}) → the last /api/blackout answer (null until loaded). */
export function useBlackout(user, opts = {}) {
  const [s, setS] = useState(state);
  const wantFast = !!opts.fast;
  useEffect(() => {
    subs.add(setS);
    if (wantFast) fast += 1;
    socketFor(user);
    if (!state || wantFast) refreshBlackout(); else schedule();
    return () => {
      subs.delete(setS);
      if (wantFast) fast -= 1;
      if (!subs.size) { clearTimeout(timer); if (unsubSocket) { unsubSocket(); unsubSocket = null; socketKey = null; } }
    };
  }, [user?.id, wantFast]); // eslint-disable-line react-hooks/exhaustive-deps
  return s;
}

export function fmtLeft(ms) {
  if (!Number.isFinite(ms) || ms <= 0) return '00:00:00';
  const t = Math.floor(ms / 1000), h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), x = t % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(x).padStart(2, '0')}`;
}

/** re-render every second (for countdowns) while `on` */
export function useTick(on) {
  const [, set] = useState(0);
  useEffect(() => {
    if (!on) return undefined;
    const id = setInterval(() => set((x) => x + 1), 1000);
    return () => clearInterval(id);
  }, [on]);
}
