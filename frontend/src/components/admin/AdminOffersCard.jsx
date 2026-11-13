/** Админка → Задания: «Рекламные задания» (AdsGram Task + просмотры рекламы Monetag / AdsGram) — backend/offers.py */
import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Loader2, Megaphone, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent } from '@/components/ui/card';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const headers = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token') || localStorage.getItem('ton_city_token')}` } });
const fmt = (n) => (n ?? 0).toLocaleString('ru-RU');

function Num({ label, value, onChange, w = 'w-24', testid }) {
  return (
    <label className="flex flex-col">
      <span className="text-[10px] text-text-muted mb-1">{label}</span>
      <Input type="number" value={value} onChange={(e) => onChange(e.target.value)} data-testid={testid}
        className={`${w} bg-black/40 border-white/10 h-9`} />
    </label>
  );
}

export default function AdminOffersCard() {
  const [c, setC] = useState(null);
  const [saving, setSaving] = useState(false);
  const load = () => axios.get(`${API}/admin/offers`, headers()).then((r) => setC(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);
  if (!c) return null;
  const set = (k) => (v) => setC((x) => ({ ...x, [k]: v }));
  const save = async () => {
    setSaving(true);
    try {
      const keys = ['adsgram_task_enabled', 'adsgram_task_block_id', 'adsgram_task_reward', 'adsgram_task_daily_cap', 'adsgram_task_trust_client',
        'ad_offers_enabled', 'ad_offer_reward', 'ad_offer_daily_cap', 'ad_offer_gap_sec'];
      const r = await axios.put(`${API}/admin/offers`, Object.fromEntries(keys.map((k) => [k, c[k]])), headers());
      setC(r.data);
      toast.success('Сохранено');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Не удалось сохранить');
    } finally { setSaving(false); }
  };
  const origin = window.location.origin.replace(/:\d+$/, '');
  const rewardUrl = `${origin}/api/offers/adsgram-task/reward?userid=[userId]&secret=${c.postback_secret}`;
  const copy = () => { navigator.clipboard?.writeText(rewardUrl).then(() => toast.success('Скопировано')).catch(() => {}); };
  const td = c.today || {};

  return (
    <Card className="glass-panel border-yellow-500/30" data-testid="admin-offers-card">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-bold text-white text-sm uppercase tracking-wide flex items-center gap-2"><Megaphone className="w-4 h-4 text-yellow-400" />Рекламные задания (AdsGram / Monetag)</h3>
          <Button size="sm" disabled={saving} onClick={save} className="bg-yellow-500 text-black hover:bg-yellow-400" data-testid="admin-offers-save">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Сохранить'}
          </Button>
        </div>
        <p className="text-xs text-text-muted">
          Блок показывается игрокам на странице «Задания» под вашими заданиями (подписки, соцсети) — даже когда свои задания выполнены.
          Награда идёт на бонусный баланс. Клики по рекламе не вознаграждаются. Лимиты обнуляются в 00:00 МСК.
        </p>

        {/* AdsGram Task */}
        <div className="rounded-xl border border-white/10 p-3 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="text-sm font-bold text-white">Задания партнёров AdsGram (формат «Task»)</div>
              <div className="text-[11px] text-text-muted">Подписка на канал, запуск бота или приложения рекламодателя. Работает только внутри Telegram.</div>
            </div>
            <Switch checked={!!c.adsgram_task_enabled} onCheckedChange={set('adsgram_task_enabled')} data-testid="offers-task-enabled" />
          </div>
          <div className="flex flex-wrap gap-3 items-end">
            <label className="flex flex-col">
              <span className="text-[10px] text-text-muted mb-1">ID блока Task (task-…)</span>
              <Input value={c.adsgram_task_block_id || ''} onChange={(e) => set('adsgram_task_block_id')(e.target.value)} placeholder="task-12345"
                className="w-40 bg-black/40 border-white/10 h-9" data-testid="offers-task-block" />
            </label>
            <Num label="Награда, $CITY" value={c.adsgram_task_reward} onChange={set('adsgram_task_reward')} testid="offers-task-reward" />
            <Num label="Заданий в день на игрока" value={c.adsgram_task_daily_cap} onChange={set('adsgram_task_daily_cap')} testid="offers-task-cap" />
          </div>
          <div className="text-[11px] text-text-muted break-all">
            Reward URL для блока Task в кабинете AdsGram (вставьте целиком):{' '}
            <span className="text-white select-all" data-testid="offers-task-url">{rewardUrl}</span>
            <button type="button" onClick={copy} className="inline-flex items-center ml-1 text-cyber-cyan align-middle"><Copy className="w-3.5 h-3.5" /></button>
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="text-[11px] text-text-muted">
              Начислять по сигналу приложения, не дожидаясь AdsGram. Выключено (рекомендуется) — награда приходит только после
              подтверждения AdsGram через Reward URL. Включайте, только если Reward URL ещё не настроен.
            </div>
            <Switch checked={!!c.adsgram_task_trust_client} onCheckedChange={set('adsgram_task_trust_client')} data-testid="offers-task-trust" />
          </div>
          <div className="text-[11px] text-white/70">Сегодня: выполнено {fmt(td.adsgram_task?.count)} · игроков {fmt(td.adsgram_task?.players)} · выдано {fmt(td.adsgram_task?.city)} $CITY · ждут подтверждения {fmt(td.adsgram_task_pending)}</div>
        </div>

        {/* Rewarded views */}
        <div className="rounded-xl border border-white/10 p-3 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <div className="text-sm font-bold text-white">«Посмотри рекламу — получи $CITY»</div>
              <div className="text-[11px] text-text-muted">
                Вознаграждаемая реклама Monetag / AdsGram — сети и порядок берутся из «Данные → Monetag».
                {c.verify_postback ? ' Засчитываются только просмотры, подтверждённые postback сети.' : ' Засчитывается по отчёту приложения (проверка через postback в «Данные → Monetag» выключена).'}
              </div>
            </div>
            <Switch checked={!!c.ad_offers_enabled} onCheckedChange={set('ad_offers_enabled')} data-testid="offers-ad-enabled" />
          </div>
          {!c.ad_networks_on && <div className="text-[11px] text-red-300">Ни одна рекламная сеть не настроена в «Данные → Monetag» — игроки этот блок не увидят.</div>}
          <div className="flex flex-wrap gap-3 items-end">
            <Num label="Награда за просмотр, $CITY" value={c.ad_offer_reward} onChange={set('ad_offer_reward')} testid="offers-ad-reward" />
            <Num label="Просмотров в день" value={c.ad_offer_daily_cap} onChange={set('ad_offer_daily_cap')} testid="offers-ad-cap" />
            <Num label="Пауза между, сек" value={c.ad_offer_gap_sec} onChange={set('ad_offer_gap_sec')} testid="offers-ad-gap" />
          </div>
          <div className="text-[11px] text-white/70">Сегодня: просмотров {fmt(td.ad?.count)} · игроков {fmt(td.ad?.players)} · выдано {fmt(td.ad?.city)} $CITY</div>
        </div>
      </CardContent>
    </Card>
  );
}
