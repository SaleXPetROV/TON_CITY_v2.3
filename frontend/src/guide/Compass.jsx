/**
 * «Дальше» — the compass after the guide: ONE most important thing to do now (GET /api/guide/compass).
 * It sits in the page flow (never over anything). A press opens the right screen and flashes the button;
 * ✕ hides this hint until the next important event (its key changes).
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '@/context/LanguageContext';
import './guide.css';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const DISMISS = 'gc_compass_dismissed';

const TX = {
  ru: { next: 'Дальше', shift: 'Запустите смену: {name} простаивает', repair: 'Почините {name}: прочность {pct}%', sell: 'Продайте до 21:00: склад заполнен на {pct}%', upgrade: 'Улучшите {name} до ур. 1 — аренда кончится через {hours} ч', close: 'Скрыть' },
  en: { next: 'Next', shift: 'Start a shift: {name} is idle', repair: 'Repair {name}: durability {pct}%', sell: 'Sell before 21:00: the warehouse is {pct}% full', upgrade: 'Upgrade {name} to level 1 — the lease ends in {hours} h', close: 'Hide' },
  es: { next: 'Siguiente', shift: 'Lanza un turno: {name} está inactivo', repair: 'Repara {name}: durabilidad {pct}%', sell: 'Vende antes de las 21:00: almacén al {pct}%', upgrade: 'Mejora {name} a nivel 1: el alquiler termina en {hours} h', close: 'Ocultar' },
  zh: { next: '下一步', shift: '开启班次：{name} 闲置中', repair: '维修 {name}：耐久 {pct}%', sell: '21:00 前出售：仓库已满 {pct}%', upgrade: '将 {name} 升到 1 级——租期 {hours} 小时后结束', close: '隐藏' },
  fr: { next: 'Ensuite', shift: 'Lancez un service : {name} est à l’arrêt', repair: 'Réparez {name} : durabilité {pct} %', sell: 'Vendez avant 21:00 : entrepôt plein à {pct} %', upgrade: 'Passez {name} au niveau 1 — le bail finit dans {hours} h', close: 'Masquer' },
  de: { next: 'Weiter', shift: 'Starte eine Schicht: {name} steht still', repair: 'Repariere {name}: Haltbarkeit {pct} %', sell: 'Verkaufe vor 21:00: Lager zu {pct} % voll', upgrade: 'Bringe {name} auf Stufe 1 — die Pacht endet in {hours} Std.', close: 'Ausblenden' },
  ja: { next: '次に', shift: 'シフト開始：{name} が停止中', repair: '{name} を修理：耐久 {pct}%', sell: '21:00前に売却：倉庫 {pct}%', upgrade: '{name} をレベル1に——リース終了まで {hours} 時間', close: '隠す' },
  ko: { next: '다음', shift: '교대 시작: {name} 멈춤', repair: '{name} 수리: 내구도 {pct}%', sell: '21:00 전에 판매: 창고 {pct}%', upgrade: '{name} 1레벨로 — 임대 종료까지 {hours}시간', close: '숨기기' },
  id: { next: 'Berikutnya', shift: 'Mulai shift: {name} diam', repair: 'Perbaiki {name}: daya tahan {pct}%', sell: 'Jual sebelum 21:00: gudang {pct}%', upgrade: 'Naikkan {name} ke level 1 — sewa berakhir {hours} jam lagi', close: 'Sembunyikan' },
};
const ICON = { shift: '▶️', repair: '🔧', sell: '🕘', upgrade: '🏆' };
const fill = (s, v) => String(s || '').replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? String(v[k]) : m));

/** Flash a button once the page has it (after a compass press). */
export function flashTestId(id) {
  let tries = 0;
  const t = setInterval(() => {
    const el = document.querySelector(`[data-testid="${id}"]`);
    if (el || ++tries > 30) {
      clearInterval(t);
      if (!el) return;
      el.scrollIntoView({ block: 'center', behavior: 'smooth' });
      el.classList.add('gc-flash');
      setTimeout(() => el.classList.remove('gc-flash'), 3200);
    }
  }, 200);
}

export default function Compass() {
  const { lang } = useLanguage();
  const navigate = useNavigate();
  const [item, setItem] = useState(null);
  const [hidden, setHidden] = useState(() => { try { return localStorage.getItem(DISMISS) || ''; } catch { return ''; } });

  useEffect(() => {
    let alive = true;
    const load = () => fetch(`${API}/guide/compass`, { headers: { Authorization: `Bearer ${localStorage.getItem('token')}` } })
      .then((r) => (r.ok ? r.json() : null)).then((d) => { if (alive) setItem(d?.item || null); }).catch(() => {});
    load();
    const id = setInterval(load, 60000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (!item || !TX.en[item.kind] || hidden === item.key) return null;
  const tx = TX[lang] || TX.en;
  const open = () => {
    navigate(item.route);
    if (item.focus) flashTestId(item.focus);
  };
  const close = (e) => {
    e.stopPropagation();
    try { localStorage.setItem(DISMISS, item.key); } catch { /* private mode */ }
    setHidden(item.key);
  };
  return (
    <div className="gc-compass" data-testid="compass">
      <button type="button" className="gc-compass-go" onClick={open} data-testid="compass-go">
        <span className="gc-compass-k">{ICON[item.kind]} {tx.next}</span>
        <span className="gc-compass-t">{fill(tx[item.kind], item)}</span>
        <span aria-hidden="true" className="gc-compass-arr">›</span>
      </button>
      <button type="button" className="gc-compass-x" onClick={close} aria-label={tx.close} data-testid="compass-close">✕</button>
    </div>
  );
}
