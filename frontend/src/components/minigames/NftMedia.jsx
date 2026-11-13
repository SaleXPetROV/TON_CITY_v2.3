/**
 * The NFT itself: a picture, a GIF / animated WebP (an <img> plays it) or a video (mp4 / webm: muted, looped,
 * inline — Telegram's WebView on iOS plays only `playsInline` + `muted`). `poster` = the still picture.
 */
import { useEffect, useRef } from 'react';

const BACK = process.env.REACT_APP_BACKEND_URL || '';
export const mediaSrc = (u) => (!u ? '' : /^(https?:|data:|blob:)/.test(u) ? u : `${BACK}${u}`);

export default function NftMedia({ src, type, poster, className = '', still = false, controls = false, testid }) {
  const ref = useRef(null);
  useEffect(() => {                                     // some WebViews ignore autoPlay until play() is called
    const v = ref.current;
    if (v && !still) { const p = v.play?.(); if (p && p.catch) p.catch(() => {}); }
  }, [src, still]);
  if (type === 'video' && !still) {
    return (
      <video ref={ref} src={mediaSrc(src)} poster={poster ? mediaSrc(poster) : undefined} className={className}
        autoPlay muted loop playsInline controls={controls} preload="metadata" data-testid={testid} />
    );
  }
  const url = still || type === 'video' ? (poster || src) : (src || poster);
  return url ? <img src={mediaSrc(url)} alt="" className={className} draggable={false} data-testid={testid} /> : null;
}

/** A frame of a video file (for the poster that is cut into the 9 pieces) — in the browser, no ffmpeg needed. */
export function videoPoster(file, at = 0.5) {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement('video');
    v.muted = true; v.playsInline = true; v.preload = 'auto'; v.src = url;
    const done = (blob) => { URL.revokeObjectURL(url); resolve(blob || null); };
    const tm = setTimeout(() => done(null), 15000);
    v.onerror = () => { clearTimeout(tm); done(null); };
    v.onloadedmetadata = () => { try { v.currentTime = Math.min(at, Math.max(0, (v.duration || 1) / 2)); } catch (_) { clearTimeout(tm); done(null); } };
    v.onseeked = () => {
      try {
        const c = document.createElement('canvas');
        const k = Math.min(1, 1024 / Math.max(v.videoWidth || 1, v.videoHeight || 1));
        c.width = Math.round((v.videoWidth || 512) * k); c.height = Math.round((v.videoHeight || 512) * k);
        c.getContext('2d').drawImage(v, 0, 0, c.width, c.height);
        c.toBlob((b) => { clearTimeout(tm); done(b); }, 'image/png');
      } catch (_) { clearTimeout(tm); done(null); }
    };
  });
}
