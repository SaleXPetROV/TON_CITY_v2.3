// A TON transaction hash as the 64-char hex explorers use. Deposits seen through toncenter v2 carry it in base64
// («qdx2CPLePh+2oaclPLowHv20VF54rknAU0dpZb1D6XQ=») — tonviewer does not open that form.
export function txHashHex(h) {
  const s = String(h || '').trim();
  if (/^[0-9a-fA-F]{64}$/.test(s)) return s.toLowerCase();
  try {
    const b = s.replace(/-/g, '+').replace(/_/g, '/');
    const bin = atob(b + '='.repeat((4 - (b.length % 4)) % 4));
    if (bin.length === 32) return Array.from(bin, (c) => c.charCodeAt(0).toString(16).padStart(2, '0')).join('');
  } catch (_) { /* not base64 */ }
  return s;
}
export const tonviewerTxUrl = (h) => (h ? `https://tonviewer.com/transaction/${txHashHex(h)}` : null);
