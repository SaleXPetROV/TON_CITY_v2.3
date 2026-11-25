/** Админка → «События»: список событий игры. Каждое свёрнуто; нажатие раскрывает его настройки. */
import { useCallback, useState } from 'react';
import { ChevronDown, Zap } from 'lucide-react';
import AdminBlackout from '@/components/admin/AdminBlackout';

function blackoutStatus(d) {
  if (!d) return { text: '…', cls: 'bg-white/10 text-white/60' };
  const s = d.settings || {};
  if (!s.enabled) return { text: 'выключено', cls: 'bg-white/10 text-white/60' };
  if (d.active) return { text: `идёт · зажжено ${Math.floor(d.active.pct)}%`, cls: 'bg-red-500/20 text-red-200' };
  if (s.auto) return { text: 'включено · автозапуск', cls: 'bg-amber-500/20 text-amber-200' };
  return { text: 'включено · запуск вручную', cls: 'bg-emerald-500/20 text-emerald-200' };
}

export default function AdminEvents() {
  const [open, setOpen] = useState(null);
  const [bo, setBo] = useState(null);
  const onBo = useCallback((d) => setBo(d), []);
  const items = [
    {
      id: 'blackout', icon: <Zap className="w-5 h-5 text-amber-300" />, title: 'Блэкаут острова',
      sub: 'Остров гаснет, игроки вместе зажигают районы, сдавая ресурсы', status: blackoutStatus(bo),
      body: <AdminBlackout onChange={onBo} />,
    },
  ];
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-3" data-testid="admin-events">
      <h2 className="font-unbounded text-lg font-bold text-white">События</h2>
      {items.map((it) => {
        const isOpen = open === it.id;
        return (
          <div key={it.id} className="rounded-xl border border-white/10 bg-white/[0.02]">
            <button type="button" className="w-full flex items-center gap-3 p-4 text-left" onClick={() => setOpen(isOpen ? null : it.id)}
              aria-expanded={isOpen} data-testid={`admin-event-${it.id}`}>
              {it.icon}
              <div className="flex-1 min-w-0">
                <div className="text-white font-semibold">{it.title}</div>
                <div className="text-xs text-text-muted">{it.sub}</div>
              </div>
              <span className={`text-xs px-2 py-1 rounded ${it.status.cls}`}>{it.status.text}</span>
              <ChevronDown className={`w-4 h-4 text-white/50 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>
            {/* kept mounted (hidden) so the status chip stays live */}
            <div className={isOpen ? 'px-4 pb-4' : 'hidden'}>{it.body}</div>
          </div>
        );
      })}
    </div>
  );
}
