/** While the island is dark: a strip at the top of every page (a pill top-right on a computer) (not on the event page and not on the map, which has its
 *  own sign) — «⚡ Блэкаут 23:41:12 · 37%». A tap opens /blackout. */
import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { bt } from './blackoutI18n';
import { useBlackout, serverNow, fmtLeft, useTick } from './useBlackout';
import './blackout.css';

const HIDE = ['/blackout', '/ton-island', '/', '/auth', '/wiki', '/sys-ops-panel-x9k2m7q', '/support-only', '/chat'];

export default function BlackoutPill({ user }) {
  const loc = useLocation();
  const navigate = useNavigate();
  const { language: lang } = useLanguage();
  const bo = useBlackout(user);
  const ev = bo?.active;
  useTick(!!ev);
  const visible = !!(user && ev) && !(HIDE.includes(loc.pathname) || loc.pathname.startsWith('/wiki/') || loc.pathname.startsWith('/gc-'));
  // on a phone the strip sits at the very top and the page headers move down by its height (--bo-strip),
  // so it never covers a field or a button
  useEffect(() => {
    const el = document.documentElement;
    const phone = window.matchMedia ? !window.matchMedia('(min-width: 1024px)').matches : true;
    el.style.setProperty('--bo-strip', visible && phone ? '30px' : '0px');
    return () => el.style.setProperty('--bo-strip', '0px');
  }, [visible]);
  if (!visible) return null;
  const left = new Date(ev.ends_at).getTime() - serverNow();
  return (
    <button type="button" className="bo-pill" onClick={() => navigate('/blackout')} data-testid="blackout-pill">
      <Zap className="w-4 h-4" />
      <span className="n">{bt(lang, 'title')}</span>
      <span className="t">{fmtLeft(left)}</span>
      <span className="p">· {bt(lang, 'litPct', { pct: Math.floor(ev.pct) })}</span>
      <span className="go">›</span>
    </button>
  );
}
