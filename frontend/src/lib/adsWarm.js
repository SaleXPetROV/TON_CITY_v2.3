/** Early preload of the daily-bonus ad (Monetag's advice): when the Mini App opens and the player still has to watch
 *  ads for the daily bonus, a ymid is taken and the ad preloaded in the background, so it is ready by the press. */
import { warmUpMonetag, warmYmid } from '@/lib/monetag';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
let busy = false;

export async function prepareDailyAd() {
  if (busy || warmYmid('daily_bonus')) return;
  busy = true;
  try {
    const token = localStorage.getItem('token');
    if (!token) return;
    const auth = { Authorization: `Bearer ${token}` };
    const cfg = await (await fetch(`${API}/ads/config`)).json();
    if (!cfg?.enabled || cfg?.monetag === false || !cfg?.zone_id) return;
    const gate = await (await fetch(`${API}/ads/daily/gate`, { headers: auth })).json();
    if (!gate || gate.ok || !gate.required) return;                    // no ads needed today
    const st = await (await fetch(`${API}/ads/daily/start`, { method: 'POST', headers: auth })).json();
    if (st?.ymid) warmUpMonetag(cfg, st.ymid, 'daily_bonus');
  } catch (_) { /* best effort */ } finally { busy = false; }
}
