/** Admin → «Данные» → «Monetag»: the Monetag SDK tag + rewarded ads before the daily login bonus. Russian only. */
import { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { showRewardedAd, warmUpMonetag } from '@/lib/monetag';

const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;
const inp = 'rounded bg-black/40 border border-white/10 px-2 py-1.5 text-white text-sm w-full';


const EV_RU = { impression: 'показ (impression)', click: 'переход по рекламе (click)', valued: 'valued', complete: 'complete', reward: 'reward' };
const REASON_RU = {
  no_ymid: 'нет ymid — сервер не знает, чей это показ', unknown_user: 'ymid не принадлежит ни одному игроку',
  click_same_show: 'переход по той же рекламе — отмечен, но вторым просмотром НЕ считается', already_counted: 'этот показ уже засчитан раньше (повтор postback)',
  event: 'неизвестный тип события — проигнорирован',
};
const explainPb = (r) => {
  if (!r) return 'ещё обрабатывается…';
  if (r.counted) return `✅ засчитан как просмотр${r.purpose === 'admin_test' ? ' (тестовый — в бонус игрока не идёт)' : ''}${r.note ? ` · ${r.note}` : ''}`;
  return `${r.ok ? 'ℹ️' : '⛔'} ${REASON_RU[r.reason] || r.reason || 'не засчитан'}`;
};

/** «Проверка рекламы»: the admin plays a real Monetag ad (or simulates Monetag's postbacks) and sees every step with
 *  the server's answer: what the SDK returned, what happens to the app's report, which postbacks came and how they were counted. */
function AdsTester({ h }) {
  const [ymid, setYmid] = useState('');
  const [log, setLog] = useState([]);
  const [busy, setBusy] = useState(false);
  const seen = useRef(new Set());
  const poll = useRef(null);
  const add = (step, data, tone = 'info') => setLog((l) => [...l, { at: new Date().toLocaleTimeString('ru-RU'), step, data, tone }]);
  useEffect(() => () => clearInterval(poll.current), []);

  const watchPostbacks = (y) => {
    clearInterval(poll.current);
    let n = 0;
    poll.current = setInterval(async () => {
      n += 1;
      if (n > 60) { clearInterval(poll.current); add('Ожидание postback остановлено (3 мин)', null, 'muted'); return; }
      try {
        const r = (await axios.get(`${API}/admin/ads/test/${encodeURIComponent(y)}`, h)).data;
        (r.postbacks || []).forEach((pb) => {
          const key = `${pb.created_at}|${pb.event}`;
          if (pb.test || seen.current.has(key) || !pb.result) return;      // simulated ones are logged by «Имитация»
          seen.current.add(key);
          add(`Postback от Monetag: ${EV_RU[pb.event] || pb.event}${pb.reward ? ` · ${pb.reward}` : ''}`,
            { ответ_сервера: pb.result, что_это_значит: explainPb(pb.result) }, pb.result?.counted ? 'ok' : 'warn');
        });
      } catch (_) { /* keep polling */ }
    }, 3000);
  };

  const newTest = async (keepLog = false) => {
    const r = (await axios.post(`${API}/admin/ads/test/start`, {}, h)).data;
    seen.current = new Set(); if (!keepLog) setLog([]); setYmid(r.ymid);
    add('Новый тест: сервер выдал ymid (его Monetag вернёт в postback)', { ymid: r.ymid, sdk: r.sdk });
    watchPostbacks(r.ymid);
    return r;
  };

  const STEP_RU = {
    sdk_load: 'Загружаю SDK Monetag', sdk_ready: 'SDK загружен', preload_start: 'Предзагрузка рекламы (Monetag ищет рекламу для вас)…',
    preload_ok: 'Реклама найдена и загружена', preload_error: 'Предзагрузка не удалась', show_start: 'Открываю рекламу', show_closed: 'Реклама закрыта',
    show_error: 'Показ не удался', adsgram_load: 'AdsGram: загружаю SDK', adsgram_ready: 'AdsGram: SDK загружен', adsgram_show: 'AdsGram: показываю рекламу',
    adsgram_result: 'AdsGram: ответ SDK', adsgram_error: 'AdsGram: показ не удался', next_network: 'Нет рекламы — пробую следующую сеть',
    warm_wait: 'Жду предзагрузку, начатую заранее…', warm_ready: 'Реклама предзагружена заранее — показываю сразу',
    warm_still_loading: 'Предзагрузка ещё идёт — показываю как есть', warm_failed: 'Заранее рекламы не нашлось — сразу следующая сеть',
  };
  const runAd = async (skipPreload = false, only = undefined, adsgramDebug = false, early = false) => {
    if (busy) return;
    setBusy(true);
    try {
      const r = await newTest();
      if (only !== 'adsgram' && !r.sdk.zone_id && !r.adsgram?.enabled) { add('Не настроена ни одна сеть: укажите зону Monetag или блок AdsGram', null, 'warn'); return; }
      if (only === 'adsgram' && !r.adsgram?.block_id) { add('AdsGram: не указан ID блока', null, 'warn'); return; }
      if (!r.sdk.enabled) add('Реклама для игроков сейчас выключена (галочка «Включено») — тест всё равно покажет рекламу вам.', null, 'warn');
      const tg = window.Telegram?.WebApp;
      add('Где идёт проверка', { внутри_Telegram: !!tg?.initData, платформа: tg?.platform || 'браузер', telegram_id: tg?.initDataUnsafe?.user?.id || null,
        страна_по_IP: r.country || 'не определена (нет заголовка Cloudflare)', браузер: navigator.userAgent.slice(0, 120) }, tg?.initData ? 'info' : 'warn');
      if (['BY', 'RU'].includes(r.country)) add(`Ваша страна по IP — ${r.country}. Для этой страны у Monetag может совсем не быть рекламы: тогда SDK отвечает «Timeout» / «Empty feed». Проверьте с VPN другой страны (например, DE или US).`, null, 'warn');
      if (/\bOPR?\/|\bOP$|Brave|YaBrowser/.test(navigator.userAgent)) add('Похоже, это Opera / Brave / Яндекс Браузер: в них встроен блокировщик рекламы. Он пропускает поиск рекламы, но не даёт ей открыться — SDK ждёт и отвечает «Timeout». Отключите блокировщик для сайта или проверяйте в Telegram.', null, 'warn');
      if (!tg?.initData) add('Вы открыли админку НЕ в Telegram. Rewarded Interstitial Monetag рассчитан на Telegram Mini App: в обычном браузере рекламы часто нет («Timeout» / «Empty feed»). Для честной проверки откройте админку внутри Telegram.', null, 'warn');
      add(skipPreload ? 'Показываю рекламу сразу, без отдельной предзагрузки…' : 'Показываю рекламу Monetag (досмотрите её; можно нажать на неё — проверите «переход»)…', null, 'muted');
      let res = null; let error = '';
      const onCsp = (e) => add('Браузер заблокировал ресурс рекламы (политика безопасности CSP)', { директива: e.effectiveDirective || e.violatedDirective, адрес: e.blockedURI }, 'warn');
      document.addEventListener('securitypolicyviolation', onCsp);
      setTimeout(() => document.removeEventListener('securitypolicyviolation', onCsp), 200000);
      const onStep = (k, d) => add(`SDK: ${STEP_RU[k] || k}`, d && Object.keys(d).length ? d : null, /error/.test(k) ? 'warn' : /ok|ready|closed/.test(k) ? 'ok' : 'muted');
      const cfgAll = { ...r.sdk, monetag: !!r.sdk.zone_id, adsgram: { ...(r.adsgram || {}), enabled: !!(r.adsgram?.block_id) }, order: r.order };
      if (early) {
        // as for the players: the ad is preloaded in advance (app / page opened), shown only if the preload succeeded
        const t0 = Date.now();
        add('Предзагрузка заранее (так игрокам — при открытии приложения)…', null, 'muted');
        const w = warmUpMonetag(cfgAll, r.ymid, 'admin_test');
        const wr = w ? await w.promise : null;
        add(wr?.state === 'ready' ? `Предзагрузка готова за ${Math.round((Date.now() - t0) / 1000)} с — реклама показывается сразу`
          : `Предзагрузка не удалась (${wr?.error?.message || 'нет рекламы'}) — игроку сразу пошла бы следующая сеть, без ожидания`,
        wr?.error ? { code: wr.error.code } : null, wr?.state === 'ready' ? 'ok' : 'warn');
      }
      try { res = await showRewardedAd(cfgAll, r.ymid, 'admin_test', { onStep, skipPreload, only, adsgramDebug }); add(`Реклама закрыта (${res?.network === 'adsgram' ? 'AdsGram' : 'Monetag'})`, { результат_SDK: res ?? '(SDK ничего не вернул — зона без reward-postback)' }, 'ok'); }
      catch (e) {
        error = `${e?.code || ''} ${e?.message || ''}`.trim();
        const isAg = !!e?.adsgram;
        add(isAg ? 'AdsGram: ошибка показа' : 'SDK Monetag: ошибка показа', { code: e?.code, message: e?.message,
          что_это_значит: isAg ? (e.adsgram?.not_telegram || /launch parameters/i.test(e?.message || '')
            ? 'AdsGram показывает рекламу только внутри Telegram (Mini App). В браузере он не работает — откройте админку в Telegram.'
            : /not active/i.test(e?.message || '') ? 'Блок AdsGram ещё не активен (идёт модерация) — дождитесь статуса «Активна» в кабинете AdsGram.'
              : 'См. сообщение AdsGram.')
            : e?.code === 'timeout' ? 'Monetag не отдал рекламу за отведённое время: нет рекламы для этого пользователя/страны прямо сейчас, зона ещё на модерации, медленная сеть, блокировщик рекламы браузера или вы не в Telegram. Если в журнале выше есть «Реклама найдена и загружена», а потом «Timeout» — реклама нашлась, но не смогла открыться (чаще всего блокировщик рекламы или обычный браузер вместо Telegram).'
            : e?.code === 'no_fill' ? 'Empty feed: у Monetag сейчас нет рекламы для этого пользователя (страна, устройство, частота показов).'
              : e?.code === 'sdk' ? 'SDK не загрузился: проверьте домен в теге и блокировщики рекламы.' : 'См. сообщение SDK.' }, 'warn');
      }
      const rep = (await axios.post(`${API}/admin/ads/test/report`, { ymid: r.ymid, sdk_result: res, error }, h)).data;
      add('Отчёт приложения «реклама досмотрена» → ответ сервера', rep, rep.would_count ? 'ok' : 'warn');
      add('Жду postback от Monetag с этим ymid (обычно секунды, иногда минуты)…', null, 'muted');
    } catch (e) { add('Ошибка', { detail: e?.response?.data?.detail || e?.message }, 'warn'); }
    finally { setBusy(false); }
  };

  const simulate = async (event, reward) => {
    try {
      let y = ymid;
      if (!y) y = (await newTest()).ymid;
      const r = (await axios.post(`${API}/admin/ads/test/postback`, { ymid: y, event, reward }, h)).data;
      add(`Имитация postback: ${EV_RU[event] || event}${reward ? ` · ${reward}` : ''} → ответ сервера`, { запрос: r.request, ответ: r.response, что_это_значит: explainPb(r.response) },
        r.response?.counted ? 'ok' : 'warn');
    } catch (e) { add('Ошибка', { detail: e?.response?.data?.detail || e?.message }, 'warn'); }
  };

  const tone = { ok: 'border-emerald-500/40 bg-emerald-500/5', warn: 'border-amber-500/40 bg-amber-500/5', muted: 'border-white/10 bg-black/20 text-text-muted', info: 'border-cyan-500/30 bg-cyan-500/5' };
  return (
    <div className="rounded-xl border border-cyan-400/30 bg-cyan-500/5 p-4 space-y-3" data-testid="ads-tester">
      <div className="font-bold text-white">🧪 Проверка рекламы</div>
      <div className="text-[11px] text-text-muted leading-relaxed">
        «Показать тестовую рекламу» запускает настоящую рекламу Monetag у вас и пишет каждый шаг: что вернул SDK, что сервер сделает с отчётом приложения
        и какие postback пришли от Monetag с этим показом (и засчитан ли он). Досмотрите рекламу без перехода — придёт только «показ»; нажмите на рекламу — придёт ещё
        «переход» (вторым просмотром он не считается). Кнопки имитации отправляют на сервер то же, что прислал бы Monetag, и показывают его ответ.
        Тестовые показы не идут в бонус игроков.
      </div>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" onClick={() => runAd(false)} disabled={busy} data-testid="ads-test-run">{busy ? 'Идёт показ…' : '▶ Показать тестовую рекламу'}</Button>
        <Button size="sm" variant="outline" onClick={() => runAd(false, undefined, false, true)} disabled={busy} data-testid="ads-test-early"
          title="Как у игроков: реклама предзагружается заранее и показывается, только если предзагрузка удалась">▶ Как у игроков: предзагрузка заранее</Button>
        <Button size="sm" variant="outline" onClick={() => runAd(true, 'monetag')} disabled={busy}>▶ Monetag без предзагрузки</Button>
        <Button size="sm" variant="outline" onClick={() => runAd(false, 'adsgram')} disabled={busy} data-testid="ads-test-adsgram">▶ Тест AdsGram</Button>
        <Button size="sm" variant="outline" onClick={() => runAd(false, 'adsgram', true)} disabled={busy} data-testid="ads-test-adsgram-debug"
          title="AdsGram debug: тестовая реклама, работает и пока блок не активирован (Reward URL при этом не вызывается)">▶ AdsGram: тестовая реклама (debug)</Button>
        <Button size="sm" variant="outline" onClick={async () => {
          try {
            // AdsGram confirms only a show opened within the last 10 minutes and not confirmed yet — so every
            // simulation opens a fresh test show (an old / already confirmed one answered «no_open_show»)
            const y = (await newTest(true)).ymid;
            const r = (await axios.post(`${API}/admin/ads/test/adsgram-reward`, { ymid: y }, h)).data;
            add('Имитация: AdsGram прислал «Reward URL» → ответ сервера', { запрос: r.request, ответ: r.response,
              что_это_значит: r.response?.counted ? '✅ показ засчитан (тестовый — в бонус игрока не идёт)' : `⛔ ${r.response?.reason === 'no_open_show' ? 'нет открытого показа: показ старше 10 минут или уже засчитан' : r.response?.reason}` }, r.response?.counted ? 'ok' : 'warn');
          } catch (e) { add('Ошибка', { detail: e?.response?.data?.detail || e?.message }, 'warn'); }
        }} data-testid="ads-sim-adsgram">Имитация: награда AdsGram</Button>
        <Button size="sm" variant="outline" onClick={() => newTest()} data-testid="ads-test-new">Новый тест</Button>
        <Button size="sm" variant="outline" onClick={() => simulate('impression', 'valued')} data-testid="ads-sim-valued">Имитация: показ · valued</Button>
        <Button size="sm" variant="outline" onClick={() => simulate('impression', 'non_valued')}>Имитация: показ · non_valued</Button>
        <Button size="sm" variant="outline" onClick={() => simulate('click', 'valued')} data-testid="ads-sim-click">Имитация: переход (click)</Button>
        <Button size="sm" variant="outline" onClick={() => simulate('impression', 'valued')}>Повтор того же показа</Button>
        {log.length > 0 && <Button size="sm" variant="ghost" onClick={() => setLog([])}>Очистить</Button>}
      </div>
      {ymid && <div className="text-[11px] text-text-muted break-all">ymid теста: <span className="text-white select-all">{ymid}</span></div>}
      <div className="space-y-1.5 max-h-[420px] overflow-y-auto" data-testid="ads-test-log">
        {log.map((x, i) => (
          <div key={i} className={`rounded-lg border p-2 text-xs ${tone[x.tone] || tone.info}`}>
            <div className="text-white"><span className="text-text-muted mr-1.5">{x.at}</span>{x.step}</div>
            {x.data && <pre className="mt-1 whitespace-pre-wrap break-all text-[11px] text-white/80">{JSON.stringify(x.data, null, 2)}</pre>}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function AdsPanel() {
  const h = { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } };
  const [c, setC] = useState(null);
  useEffect(() => { axios.get(`${API}/admin/ads`, h).then((r) => setC(r.data)).catch(() => {}); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!c) return null;
  const set = (k, v) => setC((x) => ({ ...x, [k]: v }));
  const save = async () => {
    try { const r = await axios.put(`${API}/admin/ads`, c, h); setC(r.data); toast.success('Сохранено'); }
    catch (e) { toast.error(e?.response?.data?.detail || 'Ошибка'); }
  };
  const postback = `${window.location.origin.replace(/:\d+$/, '')}/api/ads/monetag/postback?ymid={ymid}&event={event_type}&reward={reward_event_type}&secret=${c.postback_secret}`;
  const errs = Object.entries(c.errors_today || {});
  return (
    <div className="rounded-xl border border-yellow-400/30 bg-yellow-500/5 p-4 space-y-3 mb-4" data-testid="admin-ads">
      <div className="font-bold text-white">📺 Monetag: реклама перед ежедневным бонусом</div>
      <label className="block space-y-1 text-xs text-text-muted">
        <span>Тег SDK из кабинета Monetag (шаг 1 «Чтобы установить SDK скопируйте этот тег») — вставьте целиком</span>
        <textarea rows={3} className={`${inp} font-mono`} value={c.sdk_tag || ''} onChange={(e) => set('sdk_tag', e.target.value)}
          placeholder={"<script src='//libtl.com/sdk.js' data-zone='10012345' data-sdk='show_10012345'></script>"} data-testid="ads-sdk-tag" />
      </label>
      {c.sdk_src ? (
        <div className="text-[11px] text-emerald-300 break-all" data-testid="ads-sdk-parsed">Из тега: SDK {c.sdk_src} · зона {c.monetag_zone_id} · функция {c.sdk_fn}</div>
      ) : (
        <div className="text-[11px] text-text-muted">Тег ещё не сохранён — используется SDK https://libtl.com/sdk.js и зона ниже.</div>
      )}
      {c.sdk_src && !/^https:\/\/([a-z0-9-]+\.)*libtl\.com\//i.test(c.sdk_src) && (
        <div className="text-[11px] text-text-muted">Домен SDK не libtl.com — это нормально (Monetag меняет домены). Скрипты рекламы с любых https-доменов разрешены; если у вас включён строгий режим CSP_STRICT_SCRIPTS=1, добавьте домен в CSP_EXTRA_SCRIPT_SRC и пересоберите фронтенд.</div>
      )}
      <div className="text-[11px] text-text-muted">В кабинете Monetag активируйте формат «Вознаграждённый интерстициальный» (Rewarded Interstitial) — его показывает кнопка «Смотреть рекламу» в «Ежедневном входе».</div>
      <label className="flex items-center gap-2 text-sm text-white"><input type="checkbox" checked={!!c.enabled} onChange={(e) => set('enabled', e.target.checked)} data-testid="ads-enabled" /> Включено</label>
      <div className="grid md:grid-cols-3 gap-3 text-xs text-text-muted">
        <label className="space-y-1"><span>ID зоны (заполняется из тега)</span><input className={inp} value={c.monetag_zone_id} onChange={(e) => set('monetag_zone_id', e.target.value)} data-testid="ads-zone" /></label>
        <label className="space-y-1"><span>Сколько реклам до бонуса</span><input type="number" min={0} max={5} className={inp} value={c.daily_ads_required} onChange={(e) => set('daily_ads_required', e.target.value)} /></label>
        <label className="space-y-1"><span>Мин. пауза между рекламами, сек</span><input type="number" min={0} className={inp} value={c.min_gap_sec} onChange={(e) => set('min_gap_sec', e.target.value)} /></label>
      </div>
      <label className="flex items-center gap-2 text-sm text-white"><input type="checkbox" checked={!!c.verify_postback} onChange={(e) => set('verify_postback', e.target.checked)} /> Засчитывать только просмотры, подтверждённые Monetag (postback)</label>
      <div className="rounded-lg border border-sky-400/30 bg-sky-500/5 p-3 space-y-2" data-testid="ads-adsgram">
        <div className="text-sm font-bold text-white">📢 AdsGram — вторая рекламная сеть (реклама внутри Telegram Mini App)</div>
        <div className="text-[11px] text-text-muted">Официальный Telegram Ads не даёт показывать рекламу внутри Mini App — для этого есть AdsGram (partner.adsgram.ai). Создайте там блок типа «Reward» и вставьте его ID (число). Если первая сеть не показала рекламу (нет рекламы, ошибка, блок неактивен) — сразу показывается вторая; если игрок сам закрыл рекламу — вторую не показываем.</div>
        <label className="flex items-center gap-2 text-sm text-white"><input type="checkbox" checked={!!c.adsgram_enabled} onChange={(e) => set('adsgram_enabled', e.target.checked)} data-testid="ads-adsgram-enabled" /> AdsGram включён</label>
        {c.adsgram_paused_until && (
          <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-2.5 text-[11px] text-amber-200 space-y-1.5" data-testid="ads-adsgram-paused">
            <div>⏸ AdsGram ответил, что блок неактивен («{c.adsgram_paused_reason?.split('\n')[0] || 'Block is not active'}»). До {new Date(c.adsgram_paused_until).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })} игроков
              не отправляем в AdsGram — им сразу показывается Monetag (и окно ошибки AdsGram они не видят). Обычно это модерация блока: дождитесь статуса «Активна» в кабинете AdsGram.</div>
            <button type="button" className="px-2 py-1 rounded border border-amber-400/50 text-amber-100 hover:bg-amber-500/20"
              onClick={async () => {
                try { await axios.post(`${API}/admin/ads/adsgram-resume`, {}, h); set('adsgram_paused_until', ''); toast.success('AdsGram снова включён для игроков'); }
                catch (e) { toast.error(e?.response?.data?.detail || 'Ошибка'); }
              }} data-testid="ads-adsgram-resume">Блок уже активен — включить AdsGram снова</button>
          </div>
        )}
        <div className="grid md:grid-cols-2 gap-3 text-xs text-text-muted">
          <label className="space-y-1"><span>ID блока AdsGram (Reward)</span><input className={inp} value={c.adsgram_block_id || ''} onChange={(e) => set('adsgram_block_id', e.target.value)} placeholder="например 12345" data-testid="ads-adsgram-block" /></label>
          <label className="space-y-1"><span>Порядок сетей</span>
            <select className={inp} value={c.ads_order || 'monetag_first'} onChange={(e) => set('ads_order', e.target.value)} data-testid="ads-order">
              <option value="monetag_first">Сначала Monetag, если нет рекламы — AdsGram</option>
              <option value="adsgram_first">Сначала AdsGram, если нет рекламы — Monetag</option>
              <option value="monetag">Только Monetag</option>
              <option value="adsgram">Только AdsGram</option>
            </select>
          </label>
        </div>
        <div className="text-[11px] text-text-muted break-all">Reward URL для блока AdsGram (вставьте целиком): <span className="text-white select-all">{`${window.location.origin.replace(/:\d+$/, '')}/api/ads/adsgram/reward?userid=[userId]&secret=${c.postback_secret}`}</span></div>
        <div className="text-[11px] text-text-muted">AdsGram присылает подтверждение по Telegram ID игрока — сервер засчитывает его последний показ за 10 минут. С «Засчитывать только подтверждённые» показ AdsGram засчитается после этого запроса.</div>
      </div>
      <label className="flex items-center gap-2 text-sm text-white"><input type="checkbox" checked={!!c.require_valued} onChange={(e) => set('require_valued', e.target.checked)} data-testid="ads-require-valued" /> Засчитывать только оплачиваемые показы (Monetag: <b>valued</b>)</label>
      <div className="text-[11px] text-text-muted break-all">Postback URL для кабинета Monetag (вставьте целиком): <span className="text-white select-all">{postback}</span></div>
      <div className="text-[11px] text-text-muted leading-relaxed">
        <b className="text-white">Откуда берётся ymid.</b> Перед каждым показом приложение получает у сервера новый ymid вида «id игрока.код показа» и передаёт его в SDK Monetag;
        Monetag подставляет его в {'{ymid}'} postback-ссылки. По нему сервер понимает, чей это просмотр, и засчитывает каждый показ один раз (повторы postback и «click» того же показа не считаются).
        {'{reward_event_type}'} — «valued» (оплачиваемый показ) или «non_valued».
      </div>
      <div className="text-[11px] text-text-muted">
        Сегодня: просмотров по отчёту приложения {c.views_today} · подтверждено postback {c.postbacks_today} (всего postback-запросов {c.postbacks_raw_today}) · игроков {c.players_today}.
        {c.last_postback ? <> Последний postback: {new Date(c.last_postback.created_at).toLocaleString('ru-RU')} · event={c.last_postback.event || '—'} · reward={c.last_postback.reward || '—'} · ymid={c.last_postback.ymid ? 'есть' : 'пусто'}.</> : ' Postback от Monetag ещё не приходил — проверьте ссылку в кабинете.'}
        {' '}Пока реклама выключена или нет зоны — бонус выдаётся без рекламы.
      </div>
      {errs.length > 0 && (
        <div className="text-[11px] text-amber-300" data-testid="ads-errors">Ошибки показа сегодня: {errs.map(([m, n]) => `${m} — ${n}`).join(' · ')}
          <span className="text-text-muted"> (Empty feed — у Monetag нет рекламы для этого игрока сейчас; Timeout — реклама не загрузилась за 15 сек.; csp:… — браузер заблокировал ресурс рекламы политикой безопасности: csp:script-src:eval лечится CSP_ADS_EVAL=1 в frontend/.env и пересборкой.)</span>
        </div>
      )}
      <Button size="sm" onClick={save}>Сохранить</Button>
      <AdsTester h={h} />
    </div>
  );
}
