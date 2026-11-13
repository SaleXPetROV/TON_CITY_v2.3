/**
 * PhotoViewer — a photo from the chat on the whole screen.
 *   • zoom: two fingers (pinch), double tap / double click, mouse wheel — 1×…5×, around the fingers / the cursor;
 *   • when zoomed, one finger / the mouse moves the photo (it never leaves the screen);
 *   • at 1×: swipe the photo up or down to close; a tap on the dark area closes too;
 *   • «✕» in the top-left corner (below Telegram's own buttons), Esc on a computer.
 * Rendered in a portal above every modal.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

const MIN = 1;
const MAX = 5;
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));

export default function PhotoViewer({ src, onClose, testIdPrefix = 'chat' }) {
  const boxRef = useRef(null);
  const imgRef = useRef(null);
  const v = useRef({ s: 1, x: 0, y: 0 });             // scale and offset of the photo (px, from the centre)
  const ptrs = useRef(new Map());
  const g = useRef(null);                              // the current gesture
  const lastTap = useRef(0);
  const [, force] = useState(0);
  const [drag, setDrag] = useState(0);                 // swipe-to-close offset at 1×
  const [anim, setAnim] = useState(false);

  const fit = () => {
    const box = boxRef.current, img = imgRef.current;
    if (!box || !img) return { bw: 1, bh: 1, w: 1, h: 1 };
    return { bw: box.clientWidth, bh: box.clientHeight, w: img.clientWidth, h: img.clientHeight };
  };
  // keep the zoomed photo over the screen: no empty band inside the screen on a side where the photo is bigger
  const bound = (s, x, y) => {
    const { bw, bh, w, h } = fit();
    const mx = Math.max(0, (w * s - bw) / 2), my = Math.max(0, (h * s - bh) / 2);
    return { s, x: clamp(x, -mx, mx), y: clamp(y, -my, my) };
  };
  const apply = (n, animate = false) => { v.current = n; setAnim(animate); force((k) => k + 1); };

  // zoom to scale s keeping the screen point (px, py — from the box centre) still
  const zoomAt = useCallback((s, px, py, animate) => {
    const c = v.current;
    const ns = clamp(s, MIN, MAX);
    const k = ns / c.s;
    apply(ns === 1 ? { s: 1, x: 0, y: 0 } : bound(ns, px - (px - c.x) * k, py - (py - c.y) * k), animate);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const local = (e) => {
    const r = boxRef.current.getBoundingClientRect();
    return { px: e.clientX - r.left - r.width / 2, py: e.clientY - r.top - r.height / 2 };
  };

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = prev; };
  }, [onClose]);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return undefined;
    const onWheel = (e) => {
      e.preventDefault();
      const { px, py } = local(e);
      zoomAt(v.current.s * (e.deltaY < 0 ? 1.2 : 1 / 1.2), px, py, false);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [zoomAt]);

  const down = (e) => {
    if (e.target.closest('[data-viewer-close]')) return;
    boxRef.current.setPointerCapture?.(e.pointerId);
    ptrs.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const list = [...ptrs.current.values()];
    if (list.length === 2) {
      const [a, b] = list;
      const mid = local({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 });
      g.current = { type: 'pinch', d: Math.hypot(a.x - b.x, a.y - b.y) || 1, s: v.current.s, x: v.current.x, y: v.current.y, mid };
      setDrag(0);
    } else if (list.length === 1) {
      g.current = { type: 'pan', sx: e.clientX, sy: e.clientY, x: v.current.x, y: v.current.y, moved: false, onImg: e.target === imgRef.current };
    }
  };

  const move = (e) => {
    if (!ptrs.current.has(e.pointerId)) return;
    ptrs.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const gs = g.current;
    if (!gs) return;
    if (gs.type === 'pinch' && ptrs.current.size >= 2) {
      const [a, b] = [...ptrs.current.values()];
      const ns = clamp(gs.s * (Math.hypot(a.x - b.x, a.y - b.y) / gs.d), MIN * 0.8, MAX);
      const mid = local({ clientX: (a.x + b.x) / 2, clientY: (a.y + b.y) / 2 });
      const k = ns / gs.s;
      // the point under the fingers stays under the fingers, and follows them
      const x = mid.px - (gs.mid.px - gs.x) * k;
      const y = mid.py - (gs.mid.py - gs.y) * k;
      apply({ s: ns, x, y });
    } else if (gs.type === 'pan') {
      const dx = e.clientX - gs.sx, dy = e.clientY - gs.sy;
      if (Math.abs(dx) + Math.abs(dy) > 6) gs.moved = true;
      if (v.current.s > 1.01) apply(bound(v.current.s, gs.x + dx, gs.y + dy));
      else if (gs.onImg) setDrag(dy);
    }
  };

  const up = (e) => {
    const gs = g.current;
    ptrs.current.delete(e.pointerId);
    if (gs?.type === 'pinch') {
      if (ptrs.current.size < 2) {
        const c = v.current;
        apply(c.s <= 1.02 ? { s: 1, x: 0, y: 0 } : bound(c.s, c.x, c.y), true);
        g.current = null;
        if (ptrs.current.size === 1) {               // one finger stays down: continue as a pan
          const [p] = [...ptrs.current.values()];
          g.current = { type: 'pan', sx: p.x, sy: p.y, x: v.current.x, y: v.current.y, moved: true, onImg: true };
        }
      }
      return;
    }
    g.current = null;
    if (!gs) return;
    if (v.current.s <= 1.01 && Math.abs(drag) > 110) { onClose(); return; }
    if (drag) { setAnim(true); setDrag(0); }
    if (gs.moved) return;
    // a tap: double tap zooms, a tap outside the photo closes
    const now = Date.now();
    if (now - lastTap.current < 300) {
      lastTap.current = 0;
      const { px, py } = local(e);
      if (v.current.s > 1.01) apply({ s: 1, x: 0, y: 0 }, true);
      else zoomAt(2.5, px, py, true);
      return;
    }
    lastTap.current = now;
    if (!gs.onImg && v.current.s <= 1.01) {
      const t = now;
      setTimeout(() => { if (lastTap.current === t) onClose(); }, 300);
    }
  };

  const { s, x, y } = v.current;
  const fade = s <= 1.01 ? Math.max(0.35, 1 - Math.abs(drag) / 400) : 1;

  return createPortal(
    <div className="fixed inset-0 z-[30000] select-none" data-testid={`${testIdPrefix}-photo-viewer`}
      style={{ background: `rgba(0,0,0,${0.94 * fade})` }}>
      <div ref={boxRef} className="absolute inset-0 overflow-hidden flex items-center justify-center"
        style={{ touchAction: 'none' }}
        onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
        <img ref={imgRef} src={src} alt="" draggable={false} data-testid={`${testIdPrefix}-photo-viewer-img`}
          onLoad={() => force((k) => k + 1)}
          className="max-w-full max-h-full object-contain will-change-transform"
          style={{
            transform: `translate3d(${x}px, ${y + (s <= 1.01 ? drag : 0)}px, 0) scale(${s})`,
            transition: anim ? 'transform 180ms ease-out' : 'none',
            cursor: s > 1.01 ? 'grab' : 'zoom-in',
          }}
          onTransitionEnd={() => setAnim(false)} />
      </div>
      <button type="button" data-viewer-close onClick={onClose} aria-label="Close" data-testid={`${testIdPrefix}-photo-viewer-close`}
        className="absolute left-3 w-11 h-11 rounded-full bg-black/60 border border-white/25 backdrop-blur flex items-center justify-center text-white active:scale-95"
        style={{ top: 'calc(max(var(--tg-safe-top, 0px), env(safe-area-inset-top, 0px)) + 12px)' }}>
        <X className="w-6 h-6" />
      </button>
    </div>,
    document.body,
  );
}
