/** Админка → Городской рынок: «Тендеры — напоминания и срок предложений» (backend/tender_reminders.py) */
import { useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Loader2, BellRing } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent } from '@/components/ui/card';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api/admin/tender-reminders`;
const headers = () => ({ headers: { Authorization: `Bearer ${localStorage.getItem('token') || localStorage.getItem('ton_city_token')}` } });

function Hours({ label, hint, value, onChange, testid }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-text-muted">{label}</span>
      <div className="flex items-center gap-2">
        <Input type="number" min="0.25" step="0.25" value={value} onChange={(e) => onChange(e.target.value)} data-testid={testid}
          className="w-24 bg-black/40 border-white/10 h-9" />
        <span className="text-xs text-text-muted">ч</span>
      </div>
      {hint && <span className="text-[11px] text-text-muted/80">{hint}</span>}
    </label>
  );
}

export default function AdminTenderRemindersCard() {
  const [c, setC] = useState(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => { axios.get(API, headers()).then((r) => setC(r.data)).catch(() => {}); }, []);
  if (!c) return null;
  const set = (k) => (v) => setC((x) => ({ ...x, [k]: v }));
  const save = async () => {
    setSaving(true);
    try {
      const r = await axios.put(API, {
        enabled: !!c.enabled, first_after_h: Number(c.first_after_h), repeat_h: Number(c.repeat_h), expire_h: Number(c.expire_h),
      }, headers());
      setC(r.data);
      toast.success('Сохранено');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Не удалось сохранить');
    } finally { setSaving(false); }
  };
  return (
    <Card className="bg-panel/60 border-white/10" data-testid="admin-tender-reminders">
      <CardContent className="p-4 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <BellRing className="w-5 h-5 text-amber-300" />
            <div>
              <div className="font-semibold text-white">Тендеры: напоминания и срок предложений</div>
              <div className="text-xs text-text-muted">
                Кто не ответил на предложение по своему тендеру или на изменение условий контракта, получает одно общее
                сообщение в Telegram и в проекте с кнопкой «Открыть предложения». Без ответа предложение закрывается, автор получает уведомление.
              </div>
            </div>
          </div>
          <Switch checked={!!c.enabled} onCheckedChange={set('enabled')} data-testid="tender-reminders-enabled" />
        </div>
        <div className="flex flex-wrap gap-6">
          <Hours label="Первое напоминание через" hint="после отправки предложения" value={c.first_after_h} onChange={set('first_after_h')} testid="tr-first" />
          <Hours label="Повторять не чаще раза в" value={c.repeat_h} onChange={set('repeat_h')} testid="tr-repeat" />
          <Hours label="Закрывать без ответа через" hint="предложение и изменение условий" value={c.expire_h} onChange={set('expire_h')} testid="tr-expire" />
        </div>
        <Button onClick={save} disabled={saving} className="bg-cyan-600 hover:bg-cyan-500" data-testid="tender-reminders-save">
          {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}Сохранить
        </Button>
      </CardContent>
    </Card>
  );
}
