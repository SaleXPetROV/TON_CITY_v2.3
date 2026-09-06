import React, { useEffect, useRef, useState } from 'react';
import './GramCityLoader.css';

/**
 * Unified GRAM CITY preloader.
 *
 * Shows a neon "GRAM CITY" title with a spinner above it and a white
 * progress line + percentage below it. The percentage climbs smoothly and
 * only reaches 100% once the app is actually ready (`resolving === false`).
 *
 * On a flaky connection the parent keeps `resolving` true (it just keeps
 * retrying in the background) — so the bar simply keeps creeping instead of
 * ever reloading the page or flashing a "loading error".
 *
 * Props:
 *   resolving : boolean  — true while the app is still bootstrapping.
 *   onDone    : ()=>void — called once the bar hits 100% and fades out.
 */
export default function GramCityLoader({ resolving, onDone }) {
  // Continue from where the pre-React boot splash left off (window.__gcBootPct)
  // so there is no visible reset/flicker at the hand-off.
  const initial = (() => {
    try { return Math.min(90, Math.max(0, Number(window.__gcBootPct) || 0)); }
    catch (_) { return 0; }
  })();
  const [pct, setPct] = useState(initial);
  const [hidden, setHidden] = useState(false);
  const pctRef = useRef(initial);
  const resolvingRef = useRef(resolving);
  const doneCalledRef = useRef(false);

  useEffect(() => { resolvingRef.current = resolving; }, [resolving]);

  useEffect(() => {
    const tick = () => {
      let p = pctRef.current;
      if (resolvingRef.current) {
        // Still bootstrapping: ease toward a 90% ceiling so the bar always
        // keeps moving (feels alive) but never "completes" prematurely.
        if (p < 90) {
          p += Math.max(0.35, (90 - p) * 0.045);
          if (p > 90) p = 90;
        }
      } else {
        // Ready: accelerate to 100%.
        p += Math.max(2.2, (100 - p) * 0.28);
        if (p >= 100) {
          p = 100;
        }
      }
      pctRef.current = p;
      setPct(p);

      if (p >= 100 && !doneCalledRef.current) {
        doneCalledRef.current = true;
        clearInterval(iv);
        // Let the user see 100% for a beat, then fade out.
        setTimeout(() => {
          setHidden(true);
          setTimeout(() => { if (onDone) onDone(); }, 480);
        }, 260);
      }
    };
    const iv = setInterval(tick, 70);
    return () => clearInterval(iv);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shown = Math.round(pct);

  return (
    <div
      className={`gc-loader${hidden ? ' gc-loader--hide' : ''}`}
      data-testid="gc-loader"
      role="progressbar"
      aria-valuenow={shown}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="gc-loader__inner">
        <div className="gc-loader__spinner" />
        <div className="gc-loader__title">GRAM CITY</div>
        <div className="gc-loader__progress">
          <div className="gc-loader__track">
            <div className="gc-loader__fill" style={{ width: `${shown}%` }} />
          </div>
          <div className="gc-loader__pct" data-testid="gc-loader-pct">{shown}%</div>
        </div>
      </div>
    </div>
  );
}
