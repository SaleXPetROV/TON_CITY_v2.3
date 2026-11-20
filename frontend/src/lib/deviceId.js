/**
 * The device of the player, sent with every API request (backend/device_watch.py — «Мульти-аккаунты → Общее
 * устройство»):
 *   X-Device-Id — a random id made once and kept in this app's storage on this device (localStorage + a cookie for a
 *                 year). Accounts switched in the same Telegram app / browser share it.
 *   X-Device-Fp — the FingerprintJS hash of the device (the same phone/browser gives the same hash even after the
 *                 storage was cleared; weaker: identical phone models may share it).
 */
import { getVisitorId } from '@/lib/fingerprint';

const KEY = 'gc_device_id';
let _id = null;
let _fp = '';

function readCookie() {
  try { const m = document.cookie.match(/(?:^|;\s*)gc_did=([^;]+)/); return m ? decodeURIComponent(m[1]) : ''; } catch (e) { return ''; }
}

export function deviceId() {
  if (_id) return _id;
  let v = '';
  try { v = localStorage.getItem(KEY) || ''; } catch (e) { /* storage blocked */ }
  if (!v) v = readCookie();
  if (!/^[a-z0-9-]{16,64}$/i.test(v)) {
    v = (window.crypto && window.crypto.randomUUID) ? window.crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
  }
  try { localStorage.setItem(KEY, v); } catch (e) { /* ignore */ }
  try { document.cookie = `gc_did=${encodeURIComponent(v)}; path=/; max-age=31536000; SameSite=Lax`; } catch (e) { /* ignore */ }
  _id = v;
  return v;
}

/** start the fingerprint early; requests sent before it is ready go with the id only */
export function warmDeviceFingerprint() {
  getVisitorId().then((v) => { _fp = (v || '').slice(0, 64); }).catch(() => {});
}

export function deviceHeaders() {
  const h = { 'X-Device-Id': deviceId() };
  if (_fp) h['X-Device-Fp'] = _fp;
  return h;
}
