import { CityBackdrop } from '@/components/CityBackground';
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
  const shownRef = useRef(initial);
  const resolvingRef = useRef(resolving);
  const doneCalledRef = useRef(false);

  useEffect(() => { resolvingRef.current = resolving; }, [resolving]);
  // The start voice was removed (no intro phrase): the loader follows the app loading only.
  const introPending = () => false;
  const introCap = () => 100;

  useEffect(() => {
    const tick = () => {
      let p = pctRef.current;
      if (resolvingRef.current) {
        // Пока приложение загружается в фоне (bootstrap / auth / данные):
        // до 88% растёт быстро, затем плавно продолжает увеличиваться по 99%
        // (91%, 92%, 93%...), показывая пользователю активный прогресс,
        // вместо того чтобы застывать на одной цифре.
        if (p < 88) {
          p += Math.max(0.35, (88 - p) * 0.045);
        } else if (p < 99) {
          p += Math.max(0.03, (99 - p) * 0.02);
          if (p > 99) p = 99;
        }
      } else {
        // Загрузка завершена: быстро доводим до 100%.
        p += Math.max(2.5, (100 - p) * 0.35);
        if (p >= 100) {
          p = 100;
        }
      }
      pctRef.current = p;
      // the bar shows the slower of the two: the game and the voice (both are «loading»); it never goes back
      // (a phrase started by a touch restarts the voice part from its beginning)
      shownRef.current = Math.max(shownRef.current, Math.min(p, introCap()));
      setPct(shownRef.current);

      if (p >= 100 && !doneCalledRef.current && !introPending()) {
        setPct(100);
        doneCalledRef.current = true;
        clearInterval(iv);
        // Показываем 100% на мгновение и плавно открываем приложение
        setTimeout(() => {
          setHidden(true);
          setTimeout(() => { if (onDone) onDone(); }, 480);
        }, 220);
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
      {/* the same living background as the «Мои бизнесы» page — the loader melts straight into it */}
      <CityBackdrop />
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
