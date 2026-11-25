/** One line of text that always fits its box: the font gets smaller (down to `min` px) instead of wrapping or being
 *  cut — for short buttons whose label is longer in some languages. */
import { useLayoutEffect, useRef, useState } from 'react';

export default function FitText({ children, max = 13, min = 9, className = '' }) {
  const ref = useRef(null);
  const [size, setSize] = useState(max);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const fit = () => {
      const box = el.parentElement;
      if (!box) return;
      let s = max;
      el.style.fontSize = `${s}px`;
      // the room the label really has: the box minus its padding and the other children (the icon)
      const cs = getComputedStyle(box);
      const others = Array.from(box.children).filter((c) => c !== el).reduce((a, c) => a + c.getBoundingClientRect().width, 0);
      const gap = parseFloat(cs.columnGap || cs.gap || '0') || 0;
      const room = box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) - others - gap * (box.children.length - 1);
      while (s > min && el.scrollWidth > room + 0.5) { s -= 0.5; el.style.fontSize = `${s}px`; }
      setSize(s);
    };
    fit();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(fit) : null;
    if (ro && el.parentElement) ro.observe(el.parentElement);
    return () => { if (ro) ro.disconnect(); };
  }, [children, max, min]);
  return <span ref={ref} className={`whitespace-nowrap ${className}`} style={{ fontSize: `${size}px` }}>{children}</span>;
}
