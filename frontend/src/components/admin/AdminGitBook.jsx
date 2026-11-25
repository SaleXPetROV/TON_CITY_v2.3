/**
 * Админка → «Справочник» → GitBook: Справочник игры берётся из GitBook, ИИ GitBook отвечает в поддержке.
 * Сервер: backend/wiki_gitbook.py (GET/PUT /api/admin/wiki/gitbook, POST /api/admin/wiki/gitbook/sync).
 */
import { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;

const when = (iso) => (iso ? new Date(iso).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—');

export default function AdminGitBook({ h, onSynced }) {
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try { const r = await axios.get(`${API}/admin/wiki/gitbook`, h); setSt(r.data); } catch { /* the card stays empty */ }
  }, [h]);
  useEffect(() => { load(); }, [load]);

  const set = async (k, v) => {
    try { const r = await axios.put(`${API}/admin/wiki/gitbook`, { [k]: v }, h); setSt(r.data); toast.success('Сохранено'); }
    catch { toast.error('Не удалось сохранить'); }
  };
  const sync = async () => {
    setBusy(true);
    try {
      const r = await axios.post(`${API}/admin/wiki/gitbook/sync`, {}, h);
      setSt(r.data);
      const x = r.data.result || {};
      toast.success(x.skipped ? 'Изменений в GitBook нет' : `Готово: из GitBook ${x.from_gitbook || 0}, без изменений ${x.from_code || 0}, скрыто ${x.hidden || 0}`);
      if (onSynced) onSynced();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Синхронизация не удалась'); }
    setBusy(false);
  };

  if (!st) return null;
  const s = st.stats || {};
  const ai = (st.ai && st.ai.total) || {};
  return (
    <Card className="glass-panel border-white/10" data-testid="admin-gitbook">
      <CardHeader className="pb-2">
        <CardTitle className="text-base text-white flex items-center justify-between gap-2 flex-wrap">
          <span>GitBook</span>
          <span className={`text-xs font-normal ${st.configured ? 'text-emerald-300' : 'text-amber-300'}`}>
            {st.configured ? 'подключён' : 'не подключён: на сервере нет GITBOOK_API_TOKEN'}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="grid md:grid-cols-2 gap-4 text-sm">
        <div className="space-y-2">
          <label className="flex items-start gap-3">
            <Switch checked={!!st.settings?.wiki_sync} onCheckedChange={(v) => set('wiki_sync', v)} data-testid="gitbook-wiki-sync" />
            <span><b className="text-white">Справочник из GitBook</b>
              <span className="block text-xs text-text-muted">Каждые 10 минут игра берёт статьи из GitBook. Статья, которую не меняли в GitBook, остаётся с живыми цифрами и готовыми переводами. Изменённая или новая — текст из GitBook, остальные 8 языков переводит LibreTranslate. Убранная из GitBook — скрывается в игре.</span></span>
          </label>
          <div className="text-xs text-text-muted">
            Последняя синхронизация: <span className="text-white">{when(st.last_sync)}</span>
            {st.last_sync && <> · статей {s.articles || 0}: из GitBook {s.from_gitbook || 0}, без изменений {s.from_code || 0}, скрыто {s.hidden || 0}</>}
          </div>
          {st.last_error && <div className="text-xs text-red-300">Ошибка ({when(st.last_try)}): {st.last_error}</div>}
          <Button size="sm" onClick={sync} disabled={busy || !st.configured || !st.settings?.wiki_sync} data-testid="gitbook-sync-now">
            {busy ? 'Синхронизация…' : 'Синхронизировать сейчас'}
          </Button>
        </div>
        <div className="space-y-2">
          <label className="flex items-start gap-3">
            <Switch checked={!!st.settings?.ai_support} onCheckedChange={(v) => set('ai_support', v)} data-testid="gitbook-ai-support" />
            <span><b className="text-white">ИИ GitBook отвечает в поддержке</b>
              <span className="block text-xs text-text-muted">Вопрос игрока в чате Willy GRAM сначала получает ответ ИИ GitBook по документации. Вопрос не про игру или ответа в документации нет — Willy честно говорит, что ответить не может, и предлагает кнопку «Связаться со специалистом». Дважды «Не помогло» — чат уходит агенту. GitBook недоступен — отвечает база Willy, как раньше.</span></span>
          </label>
          <div className="text-xs text-text-muted">
            Ответил ИИ: <span className="text-white">{ai.answered || 0}</span> · нет ответа → агенту: <span className="text-white">{ai.none || 0}</span> · ошибки GitBook: <span className="text-white">{ai.error || 0}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
