import { useState, useEffect, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Sparkles, Eye, Check, Rocket, Calendar, Users,
  RotateCcw, X, Map as MapIcon,
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// UNIX ISO → HTML datetime-local (MSK). Same helper style as AdminPage.
const utcIsoToMskLocal = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';
  const mskMs = d.getTime() + (3 * 3600 * 1000) - (-d.getTimezoneOffset() * 60000);
  const m = new Date(mskMs);
  const pad = (n) => String(n).padStart(2, '0');
  return `${m.getFullYear()}-${pad(m.getMonth() + 1)}-${pad(m.getDate())}T${pad(m.getHours())}:${pad(m.getMinutes())}`;
};
const mskLocalToUtcIso = (localStr) => {
  if (!localStr) return null;
  // localStr is "YYYY-MM-DDTHH:mm" as MSK — treat as MSK, convert to UTC ISO.
  const [date, time] = localStr.split('T');
  const [Y, M, D] = date.split('-').map(Number);
  const [h, m] = time.split(':').map(Number);
  const utc = Date.UTC(Y, M - 1, D, h - 3, m, 0);
  return new Date(utc).toISOString();
};

const LABEL_OPTIONS = [
  { value: 'coming_epoch_2', label: '🔒 Скоро (Эпоха 2)' },
  { value: 'sold_out', label: '🔥 SOLD OUT' },
  { value: 'unavailable', label: '🔒 Недоступно' },
];

const MAP_OPTIONS = [
  { value: 'ton_island', label: 'GRAM Island' },
];

export default function PresalePanel({ token }) {
  const headers = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const [mapId, setMapId] = useState('ton_island');
  const [inventory, setInventory] = useState([]); // [{type,name_ru,icon,tier,free,total}]
  const [rows, setRows] = useState([]);                 // [{district, type, count}] — «Выставлю» per district
  const [byDistrict, setByDistrict] = useState({});      // {"1": {type: {total, free}}}
  const [districts, setDistricts] = useState([]);        // [{id, name, unlocked, total, free}]
  const [district, setDistrict] = useState(null);        // the district being set up
  const [selectedPlots, setSelectedPlots] = useState([]); // last selection
  const [unavailableLabel, setUnavailableLabel] = useState('coming_epoch_2');
  const [opensAtLocal, setOpensAtLocal] = useState(''); // MSK local
  const [active, setActive] = useState(false);
  const [readyBuyers, setReadyBuyers] = useState(0);
  const [buyButtonText, setBuyButtonText] = useState('');
  const [savingButtonText, setSavingButtonText] = useState(false);

  const [showPreview, setShowPreview] = useState(false);
  const [selecting, setSelecting] = useState(false);
  const [approving, setApproving] = useState(false);
  const [resetting, setResetting] = useState(false);

  const loadInventory = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/admin/presale/inventory?map_id=${mapId}`, { headers });
      setInventory(res.data.businesses || []);
      setByDistrict(res.data.by_district || {});
      const ds = res.data.districts || [];
      setDistricts(ds);
      setDistrict((cur) => (cur != null && ds.some((d) => d.id === cur) ? cur : (ds[0]?.id ?? null)));
    } catch (e) {
      toast.error('Не удалось загрузить список бизнесов');
    }
  }, [mapId, headers]);

  const loadConfig = useCallback(async () => {
    try {
      const [cfgRes, buyersRes] = await Promise.all([
        axios.get(`${API}/admin/presale`, { headers }),
        axios.get(`${API}/admin/presale/ready-buyers`, { headers }),
      ]);
      const cfg = cfgRes.data || {};
      setMapId(cfg.map_id || 'ton_island');
      setUnavailableLabel(cfg.unavailable_label || 'coming_epoch_2');
      setSelectedPlots(cfg.selected_plots || []);
      setSoldFromPresale(Number(cfg.sold_count) || 0);
      setActive(!!cfg.active);
      setOpensAtLocal(utcIsoToMskLocal(cfg.opens_at));
      setBuyButtonText(cfg.buy_button_text || '');
      if (Array.isArray(cfg.businesses) && cfg.businesses.length) {
        setRows(cfg.businesses.filter((b) => b.district != null).map((b) => ({ district: Number(b.district), type: b.type, count: b.count })));
      }
      setReadyBuyers(buyersRes.data?.count || 0);
    } catch (e) {
      /* first-run: no config yet — silent */
    }
  }, [headers]);

  useEffect(() => { loadInventory(); }, [loadInventory]);
  useEffect(() => { loadConfig(); }, [loadConfig]);

  // «Выставлю» follows reality: never more than is free (sold out → 0, the field is greyed), and never less than the
  // unsold plots already in the presale (a plot whose level-0 lease ended is on sale again and counted here)
  useEffect(() => {
    if (!Object.keys(byDistrict).length) return;
    setRows((cur) => {
      const m = {};
      cur.forEach((r) => { m[`${r.district}|${r.type}`] = { ...r }; });
      selectedPlots.forEach((p) => {
        if (p.sold || p.stale || p.district == null) return;
        const k = `${Number(p.district)}|${p.business_type}`;
        m[k] = m[k] || { district: Number(p.district), type: p.business_type, count: 0 };
        m[k].inPresale = (m[k].inPresale || 0) + 1;
      });
      const next = Object.values(m).map((r) => {
        const free = byDistrict[String(r.district)]?.[r.type]?.free ?? 0;
        const n = Math.max(Math.min(Number(r.count) || 0, free), Math.min(r.inPresale || 0, free));
        return { district: r.district, type: r.type, count: n };
      }).filter((r) => r.count > 0);
      const same = next.length === cur.length && next.every((r) => cur.some((c) => c.district === r.district && c.type === r.type && Number(c.count) === r.count));
      return same ? cur : next;
    });
  }, [byDistrict, selectedPlots]);

  const inventoryByType = useMemo(() => {
    const m = {};
    inventory.forEach((it) => { m[it.type] = it; });
    return m;
  }, [inventory]);

  const totalRequested = rows.reduce((s, r) => s + (Number(r.count) || 0), 0);
  const plannedIn = (d) => rows.filter((r) => r.district === d).reduce((s, r) => s + (Number(r.count) || 0), 0);
  const presaleIn = (d) => selectedPlots.filter((p) => Number(p.district) === d && !p.sold && !p.stale).length;
  const onSale = selectedPlots.filter((p) => !p.sold && !p.stale);
  const [soldFromPresale, setSoldFromPresale] = useState(0);   // bought by players (the server sends them apart)
  const planned = (d, type) => Number(rows.find((r) => r.district === d && r.type === type)?.count) || 0;
  // the business types of the chosen district, with how many of each it has
  const districtRows = useMemo(() => {
    const m = byDistrict[String(district)] || {};
    return inventory.filter((it) => m[it.type]).map((it) => ({ ...it, total: m[it.type].total, free: m[it.type].free }));
  }, [inventory, byDistrict, district]);

  // «Выставлю» for one business type of the chosen district (0 / empty removes it; never above its free lots)
  const setPlanned = (it, raw) => {
    let n = raw === '' ? 0 : Math.floor(Number(raw));
    if (!Number.isFinite(n) || n < 0) n = 0;
    if (n > it.free) { n = it.free; toast.warning(`В этом районе свободно только ${it.free}`); }
    // (lowering an old plan whose plots were sold since is always possible: n ≤ free here)
    setRows((r) => {
      const rest = r.filter((x) => !(x.district === district && x.type === it.type));
      return n > 0 ? [...rest, { district, type: it.type, count: n }] : rest;
    });
  };

  const setUnlocked = async (d, on) => {
    try {
      await axios.put(`${API}/admin/city/districts`, { unlocked: { [String(d)]: on } }, { headers });
      toast.success(on ? 'Район открыт' : 'Район закрыт');
      await loadInventory();
    } catch (e) { toast.error('Не удалось сохранить'); }
  };

  // onlyDistrict: re-select only that district — the plots and plans of the other districts are kept as they are
  const handleSelectPlots = async (onlyDistrict = null) => {
    // every plan is sent (so the other districts' plans are saved as they are now); with onlyDistrict the server
    // picks plots only for that district
    const cleaned = rows
      .filter((r) => r.type && Number(r.count) > 0)
      .map((r) => ({ district: r.district, type: r.type, count: Number(r.count) }));
    if (!cleaned.length && onlyDistrict == null) {
      toast.error('Укажите хотя бы один бизнес и количество');
      return;
    }
    setSelecting(true);
    try {
      const res = await axios.post(
        `${API}/admin/presale/select-plots`,
        { map_id: mapId, businesses: cleaned, ...(onlyDistrict != null ? { only_district: onlyDistrict } : {}) },
        { headers },
      );
      setSelectedPlots(res.data.selected_plots || []);
      setSoldFromPresale(Number(res.data.sold_count) || 0);
      if (Array.isArray(res.data.businesses)) {              // the plans as saved (old over-plans cut to what is free)
        setRows(res.data.businesses.filter((b) => b.district != null).map((b) => ({ district: Number(b.district), type: b.type, count: b.count })));
      }
      if ((res.data.warnings || []).length) {
        res.data.warnings.forEach((w) => toast.warning(w));
      } else {
        toast.success(`В пресейле ${res.data.selected_plots?.length || 0} полей`);
      }
      await loadInventory();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось выбрать поля');
    } finally {
      setSelecting(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedPlots.length) {
      toast.error('Сначала нажмите «Выбрать поля»');
      return;
    }
    setApproving(true);
    try {
      const body = {
        opens_at: opensAtLocal ? mskLocalToUtcIso(opensAtLocal) : null,
        unavailable_label: unavailableLabel,
        map_id: mapId,
      };
      await axios.post(`${API}/admin/presale/approve`, body, { headers });
      toast.success('Пресейл активирован — конфигурация применена');
      await loadConfig();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось утвердить пресейл');
    } finally {
      setApproving(false);
    }
  };

  const handleSaveButtonText = async () => {
    setSavingButtonText(true);
    try {
      await axios.post(`${API}/admin/presale/button-text`, { buy_button_text: buyButtonText }, { headers });
      toast.success('Текст кнопки сохранён');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Не удалось сохранить текст кнопки');
    } finally {
      setSavingButtonText(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Сбросить пресейл целиком? Выбранные поля и дата будут удалены.')) return;
    if (!window.confirm('Сбросить пресейл целиком? Выбранные поля и дата будут удалены.')) return;
    setResetting(true);
    try {
      await axios.post(`${API}/admin/presale/reset`, {}, { headers });
      setSelectedPlots([]);
      setActive(false);
      setOpensAtLocal('');
      setRows([]);
      toast.success('Пресейл сброшен');
      await loadConfig();
      await loadInventory();
    } catch (e) {
      toast.error('Не удалось сбросить');
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-5" data-testid="presale-panel">
      {/* which lots are on sale: districts open / lots per district (the map shows prices only for these + presale plots) */}
      {/* Header */}
      <div className="glass-panel rounded-2xl p-5 border border-amber-500/25">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-amber-500/15 flex items-center justify-center">
              <Rocket className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <h3 className="font-unbounded text-base font-bold text-white">Пресейл-раздел</h3>
              <p className="text-xs text-text-muted">
                Точечная продажа бизнесов на карте с датой открытия и золотистой подсветкой выбранных полей.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold border ${
                active
                  ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
                  : 'bg-gray-500/15 border-gray-500/40 text-gray-300'
              }`}
              data-testid="presale-status-badge"
            >
              {active ? '🟢 Активен' : '⚪ Черновик'}
            </span>
          </div>
        </div>

        {/* Ready buyers */}
        <div className="mt-4 flex items-center gap-3 p-3 rounded-lg bg-cyan-500/8 border border-cyan-500/25" data-testid="presale-ready-buyers">
          <Users className="w-4 h-4 text-cyan-300" />
          <span className="text-sm text-white">
            Пополненных балансов: <span className="font-mono font-bold text-cyan-300">{readyBuyers}</span>
          </span>
          <span className="text-xs text-text-muted">(баланс ≥ 5 TON)</span>
        </div>
      </div>

      {/* Map + businesses config */}
      <div className="glass-panel rounded-2xl p-5 border border-white/10 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <MapIcon className="w-4 h-4 text-white/70" />
          <label className="text-sm text-white/80 min-w-[80px]">Карта:</label>
          <Select value={mapId} onValueChange={setMapId}>
            <SelectTrigger className="w-full sm:w-64 bg-panel border-grid-border text-white" data-testid="presale-map-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#0d0e1c] border-white/10 text-white">
              {MAP_OPTIONS.map((m) => (
                <SelectItem key={m.value} value={m.value}>{m.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div>
          <h4 className="text-sm font-bold text-white mb-1">Район и бизнесы к продаже</h4>
          <p className="text-xs text-text-muted mb-2">Выберите район: в таблице — все виды бизнесов этого района, сколько их там, сколько продано, сколько уже в пресейле. Введите, сколько каждого вида выставить. «Выбрать поля: район» выбирает поля только в этом районе — уже выбранные поля других районов не меняются. Нет свободных бизнесов этого вида — «Выставлю» 0. Проданные поля в пресейле не считаются; когда аренда бизнеса 0-го уровня заканчивается, поле снова в продаже и снова считается. На карте цена и покупка — только у полей пресейла; закрытый район затемнён, купить в нём нельзя.</p>
          {districts.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-3" data-testid="presale-districts">
              {districts.map((d) => (
                <button key={d.id} type="button" onClick={() => setDistrict(d.id)} data-testid={`presale-district-${d.id}`}
                  className={`text-left rounded-xl border px-3 py-2 transition ${district === d.id ? 'border-amber-400/70 bg-amber-500/10' : 'border-white/10 bg-white/[0.03] hover:border-white/25'}`}>
                  <div className={`text-sm font-semibold ${d.unlocked ? 'text-white' : 'text-white/50'}`}>{d.name}{!d.unlocked && ' · закрыт'}</div>
                  <div className="text-[11px] text-text-muted">
                    выставлю <b className="text-white">{plannedIn(d.id)}</b> · в пресейле <b className="text-amber-300">{presaleIn(d.id)}</b> · свободно {d.free}/{d.total}
                  </div>
                </button>
              ))}
            </div>
          )}
          {district != null && (
            <label className="inline-flex items-center gap-2 text-xs text-white/80 mb-2">
              <input type="checkbox" checked={!!districts.find((d) => d.id === district)?.unlocked}
                onChange={(e) => setUnlocked(district, e.target.checked)} data-testid="presale-district-open" />
              Район открыт (закрытый затемнён на карте, купить в нём нельзя)
            </label>
          )}
          <div className="overflow-x-auto rounded-lg border border-white/10" data-testid="presale-business-table">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-[11px] text-text-muted">
                <tr>
                  <th className="text-left px-3 py-2 font-medium">Бизнес</th>
                  <th className="px-2 py-2 font-medium">Эшелон</th>
                  <th className="px-2 py-2 font-medium">Участок</th>
                  <th className="px-2 py-2 font-medium">В районе</th>
                  <th className="px-2 py-2 font-medium">Продано</th>
                  <th className="px-2 py-2 font-medium">Сейчас в пресейле</th>
                  <th className="px-2 py-2 font-medium" title="Сколько полей этого вида будет в пресейле всего (уже выставленные непроданные входят в это число)">Выставлю (всего)</th>
                  <th className="px-2 py-2 font-medium">Останется свободных</th>
                </tr>
              </thead>
              <tbody>
                {districtRows.map((it) => {
                  const p = planned(district, it.type);
                  const left = Math.max(0, it.free - p);
                  const inPresale = selectedPlots.filter((x) => x.business_type === it.type && Number(x.district) === district && !x.sold && !x.stale).length;
                  const over = p > it.free;                 // planned before the plots were sold
                  return (
                    <tr key={it.type} className={`border-t border-white/5 ${p > 0 ? 'bg-amber-500/[0.06]' : ''}`} data-testid={`presale-type-${it.type}`}>
                      <td className="px-3 py-1.5 text-white whitespace-nowrap">{it.icon} {it.name_ru}</td>
                      <td className="px-2 py-1.5 text-center text-white/70">T{it.tier}</td>
                      <td className="px-2 py-1.5 text-center text-white/60 font-mono">{(it.size || '').replace('x', '×')}</td>
                      <td className="px-2 py-1.5 text-center font-mono text-white/80">{it.total}</td>
                      <td className="px-2 py-1.5 text-center font-mono text-white/60">{it.total - it.free}</td>
                      <td className="px-2 py-1.5 text-center font-mono text-amber-300">{inPresale || '—'}</td>
                      <td className="px-2 py-1.5 text-center">
                        <Input type="number" min="0" max={it.free} value={p || ''} placeholder="0"
                          onChange={(e) => setPlanned(it, e.target.value)} disabled={it.free <= 0}
                          className={`w-20 mx-auto h-8 text-center bg-panel border-grid-border text-white ${over ? 'border-red-500/60' : ''}`} data-testid={`presale-count-${it.type}`} />
                        {over && <div className="text-[10px] text-red-300 mt-0.5">свободно {it.free}</div>}
                      </td>
                      <td className={`px-2 py-1.5 text-center font-mono font-bold ${left === 0 ? 'text-red-300' : 'text-emerald-300'}`} data-testid={`presale-left-${it.type}`}>{left}</td>
                    </tr>
                  );
                })}
                {!districtRows.length && (
                  <tr><td colSpan={8} className="px-3 py-4 text-center text-text-muted text-xs">Нет данных по району</td></tr>
                )}
              </tbody>
              <tfoot className="border-t border-white/10 bg-white/5 text-xs">
                <tr>
                  <td className="px-3 py-2 text-white font-semibold" colSpan={3}>Итого по району</td>
                  <td className="px-2 py-2 text-center font-mono text-white/80">{districtRows.reduce((n, it) => n + it.total, 0)}</td>
                  <td className="px-2 py-2 text-center font-mono text-white/60">{districtRows.reduce((n, it) => n + it.total - it.free, 0)}</td>
                  <td className="px-2 py-2 text-center font-mono text-amber-300">{presaleIn(district) || '—'}</td>
                  <td className="px-2 py-2 text-center font-mono text-white" data-testid="presale-total-planned">{plannedIn(district)}</td>
                  <td className="px-2 py-2 text-center font-mono text-emerald-300">{districtRows.reduce((n, it) => n + Math.max(0, it.free - planned(district, it.type)), 0)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
          <div className="mt-2 text-xs text-text-muted" data-testid="presale-summary">
            Всего выставлю: <b className="text-white">{totalRequested}</b>
            {districts.filter((d) => plannedIn(d.id) > 0).map((d) => <span key={d.id} className="ml-2">· {d.name}: <b className="text-white">{plannedIn(d.id)}</b></span>)}
          </div>
        </div>

        {/* Custom Buy-button text (global, no i18n) */}
        <div className="flex flex-col gap-2 pt-2 border-t border-white/10">
          <label className="text-sm text-white/80">
            Текст замены кнопки «Купить» для полей вне пресейла (одно глобальное значение):
          </label>
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              value={buyButtonText}
              onChange={(e) => setBuyButtonText(e.target.value)}
              placeholder="Напр.: Скоро в продаже (пусто → «Купить»)"
              className="w-full sm:flex-1 bg-panel border-grid-border text-white"
              data-testid="presale-button-text-input"
              maxLength={60}
            />
            <Button
              onClick={handleSaveButtonText}
              disabled={savingButtonText}
              variant="outline"
              className="border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/10 shrink-0"
              data-testid="presale-button-text-save"
            >
              <Check className="w-4 h-4 mr-1" /> {savingButtonText ? 'Сохраняем…' : 'Сохранить текст'}
            </Button>
          </div>
          <p className="text-xs text-text-muted">
            Кнопка на не-пресейл участках будет задизейблена с этим текстом. Пустое значение → стандартная «Купить».
          </p>
        </div>

        {/* Placeholder label */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <label className="text-sm text-white/80 min-w-[220px]">Замена кнопки «Купить» на прочих полях:</label>
          <Select value={unavailableLabel} onValueChange={setUnavailableLabel}>
            <SelectTrigger className="w-full sm:w-64 bg-panel border-grid-border text-white" data-testid="presale-label-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#0d0e1c] border-white/10 text-white">
              {LABEL_OPTIONS.map((l) => (
                <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Opens at */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <Calendar className="w-4 h-4 text-white/70" />
          <label className="text-sm text-white/80 min-w-[200px]">Дата и время открытия (МСК):</label>
          <Input
            type="datetime-local"
            value={opensAtLocal}
            onChange={(e) => setOpensAtLocal(e.target.value)}
            className="w-full sm:w-64 bg-panel border-grid-border text-white"
            data-testid="presale-opens-at"
          />
          {opensAtLocal && (
            <button
              type="button"
              onClick={() => setOpensAtLocal('')}
              className="text-xs text-red-400 hover:underline"
              data-testid="presale-opens-at-clear"
            >
              Сбросить
            </button>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-3 pt-2 border-t border-white/10">
          <Button
            onClick={() => handleSelectPlots(district)}
            disabled={selecting || district == null}
            className="btn-cyber"
            data-testid="presale-select-btn"
            title="Выбрать поля только в этом районе — поля других районов не меняются"
          >
            <Sparkles className="w-4 h-4 mr-1" /> {selecting ? 'Выбираем…' : `Выбрать поля: ${(districts.find((d) => d.id === district) || {}).name || 'район'}`}
          </Button>
          <Button
            variant="outline"
            onClick={() => handleSelectPlots(null)}
            disabled={selecting}
            className="border-amber-500/40 text-amber-200 hover:bg-amber-500/10"
            data-testid="presale-select-all-btn"
            title="Заново выбрать поля во всех районах по всем планам"
          >
            Во всех районах
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowPreview(true)}
            disabled={!onSale.length && !soldFromPresale}
            className="border-cyan-500/40 text-cyan-300 hover:bg-cyan-500/10 disabled:opacity-40"
            data-testid="presale-preview-btn"
          >
            <Eye className="w-4 h-4 mr-1" /> Просмотр полей ({onSale.length})
          </Button>
          <Button
            onClick={handleApprove}
            disabled={approving || !selectedPlots.length}
            className="bg-gradient-to-r from-amber-500 to-pink-500 hover:from-amber-400 hover:to-pink-400 text-black font-bold"
            data-testid="presale-approve-btn"
          >
            <Check className="w-4 h-4 mr-1" /> {approving ? 'Активируем…' : 'Утвердить'}
          </Button>
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={resetting}
            className="border-red-500/40 text-red-300 hover:bg-red-500/10 ml-auto"
            data-testid="presale-reset-btn"
          >
            <RotateCcw className="w-4 h-4 mr-1" /> Сбросить
          </Button>
        </div>
      </div>

      {/* Preview modal */}
      {showPreview && createPortal(
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 p-4"
          data-testid="presale-preview-modal"
          onClick={() => setShowPreview(false)}
        >
          <div
            className="glass-panel w-full max-w-2xl rounded-2xl border border-amber-500/40 bg-[#12101a] max-h-[85vh] overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Eye className="w-5 h-5 text-amber-300" />
                <h3 className="font-unbounded text-base font-bold text-white">Выбранные поля пресейла</h3>
              </div>
              <button onClick={() => setShowPreview(false)} className="text-white/60 hover:text-white" data-testid="presale-preview-close">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto">
              {soldFromPresale > 0 && (
                <div className="mb-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70" data-testid="presale-preview-sold">
                  Уже куплено игроками из пресейла: <b className="text-white">{soldFromPresale}</b> — здесь не показаны.
                  Если аренда такого бизнеса закончится, поле само снова станет доступно в пресейле.
                </div>
              )}
              {onSale.length === 0 ? (
                <p className="text-text-muted text-center py-8">Сейчас в пресейле нет свободных полей. Укажите количество и нажмите «Выбрать поля».</p>
              ) : (
                <div className="space-y-2">
                  {Object.entries(
                    onSale.reduce((acc, p) => {
                      (acc[p.business_type] = acc[p.business_type] || []).push(p);
                      return acc;
                    }, {})
                  ).map(([biz, plots]) => (
                    <div key={biz} className="rounded-lg border border-white/10 bg-white/5 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-white font-bold">
                          {inventoryByType[biz]?.icon || '🏢'} {inventoryByType[biz]?.name_ru || biz}
                        </span>
                        <span className="text-xs text-text-muted">{plots.length} полей</span>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {plots.map((p, i) => (
                          <span
                            key={i}
                            className="px-2 py-1 rounded bg-amber-500/15 border border-amber-500/40 text-amber-200 text-xs font-mono"
                            data-testid={`presale-preview-plot-${biz}-${i}`}
                          >
                            ({p.x}, {p.y})
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="p-4 border-t border-white/10 flex justify-end">
              <Button onClick={() => setShowPreview(false)} className="btn-cyber" data-testid="presale-preview-close-btn">
                Закрыть
              </Button>
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
