/** Админка → Городской рынок: «Порча товаров на складе» (backend/warehouse_spoilage.py) */
import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Loader2, PackageX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent } from '@/components/ui/card';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/admin/warehouse-spoilage`;
const headers = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token') || localStorage.getItem('ton_city_token')}` } });

function Num({ label, hint, unit, value, onChange, testid, step = '1', min = '0', max }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-text-muted">{label}</span>
      <div className="flex items-center gap-2">
        <Input type="number" min={min} max={max} step={step} value={value} onChange={(e) => onChange(e.target.value)} data-testid={testid}
          className="w-24 bg-black/40 border-white/10 h-9" />
        {unit && <span className="text-xs text-text-muted">{unit}</span>}
      </div>
      {hint && <span className="text-[11px] text-text-muted/80">{hint}</span>}
    </label>
  );
}

const pad = (n) => String(n ?? 0).padStart(2, '0');

export default function AdminWarehouseSpoilageCard() {
  const [c, setC] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => { axios.get(API, headers()).then((r) => setC(r.data)).catch(() => {}); }, []);
  if (!c) return null;
  const set = (k) => (v) => setC((x) => ({ ...x, [k]: v }));
  const save = async () => {
    setSaving(true);
    try {
      const r = await axios.put(API, {
        enabled: !!c.enabled, in_pct: Number(c.in_pct), over_pct: Number(c.over_pct), min_units: Number(c.min_units),
        hour_msk: Number(c.hour_msk), minute_msk: Number(c.minute_msk),
      }, headers());
      setC((x) => ({ ...x, ...r.data }));
      toast.success('Сохранено');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Не удалось сохранить');
    } finally { setSaving(false); }
  };
  const last = c.last_run;
  return (
    <Card className="bg-panel/60 border-white/10" data-testid="admin-warehouse-spoilage">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <PackageX className="w-5 h-5 text-rose-300" />
            <div>
              <div className="font-semibold text-white">Порча товаров на складе</div>
              <div className="text-xs text-text-muted">
                Раз в сутки в {pad(c.hour_msk)}:{pad(c.minute_msk)} МСК: товары в пределах склада теряют {c.in_pct}%, излишек сверх
                лимита — {c.over_pct}%. Все ресурсы портятся в одинаковой доле, лоты на рынке не портятся. Игрок получает
                уведомление в Telegram и в проекте на своём языке (перевод LibreTranslate хранится 30 минут).
              </div>
            </div>
          </div>
          <Switch checked={!!c.enabled} onCheckedChange={set('enabled')} data-testid="spoilage-enabled" />
        </div>
        <div className="flex flex-wrap gap-6">
          <Num label="В пределах склада" unit="% в сутки" step="0.5" max="100" value={c.in_pct} onChange={set('in_pct')} testid="sp-in" />
          <Num label="Излишек сверх лимита" unit="% в сутки" step="0.5" max="100" value={c.over_pct} onChange={set('over_pct')} testid="sp-over" />
          <Num label="Минимум" unit="ед. в сутки" step="1" value={c.min_units} onChange={set('min_units')} testid="sp-min" hint="если склад не пуст" />
          <div className="flex gap-2">
            <Num label="Час (МСК)" max="23" value={c.hour_msk} onChange={set('hour_msk')} testid="sp-hour" />
            <Num label="Минуты" max="59" value={c.minute_msk} onChange={set('minute_msk')} testid="sp-minute" />
          </div>
        </div>
        {last && (
          <div className="text-xs text-text-muted" data-testid="spoilage-last-run">
            Последний запуск: {new Date(last.timestamp).toLocaleString('ru-RU')} · игроков: {last.players ?? 0} ·
            испортилось: {Math.round(Number(last.units || 0)).toLocaleString('ru-RU')} ед. · под защитой склада: {last.protected ?? 0}
          </div>
        )}
        <Button onClick={save} disabled={saving} className="bg-cyan-600 hover:bg-cyan-500" data-testid="spoilage-save">
          {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}Сохранить
        </Button>
      </CardContent>
    </Card>
  );
}
