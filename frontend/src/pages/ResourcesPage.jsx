import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Package, Coins, ChevronRight } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTranslation } from '@/lib/translations';
import { useLanguage } from '@/context/LanguageContext';
import { getResource, getAllResources } from '@/lib/resourceConfig';
import { getGameMode } from '@/lib/gameMode';
import BoostersPanel from '@/components/BoostersPanel';
import ResourceInfoModal from '@/components/ResourceInfoModal';
import WikiHelp from '@/wiki/WikiHelp';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

// Estimated warehouse value: units × the price the City pays for each resource (GET /api/my/warehouse-value).
const WH_VALUE = {
  en: { title: 'Estimated warehouse value', hint: 'at the City buyback price, before tax' },
  ru: { title: 'Оценочная стоимость склада', hint: 'по цене выкупа Городом, до налога' },
  es: { title: 'Valor estimado del almacén', hint: 'al precio de recompra de la Ciudad, antes de impuestos' },
  zh: { title: '仓库估值', hint: '按城市回购价计算，税前' },
  fr: { title: 'Valeur estimée de l’entrepôt', hint: 'au prix de rachat de la Ville, avant taxe' },
  de: { title: 'Geschätzter Lagerwert', hint: 'zum Rückkaufpreis der Stadt, vor Steuern' },
  ja: { title: '倉庫の評価額', hint: '街の買取価格で計算・税引前' },
  ko: { title: '창고 예상 가치', hint: '도시 매입가 기준, 세전' },
  id: { title: 'Perkiraan nilai gudang', hint: 'dengan harga beli Kota, sebelum pajak' },
};
const fmtCity = (v) => {
  const n = Number(v || 0);
  return n.toLocaleString('ru-RU', { maximumFractionDigits: n < 10 ? 2 : n < 1000 ? 1 : 0 });
};

// Resources page — hosts the "business count", "warehouse" and "My resources"
// blocks that previously lived on the My Businesses page.
export default function ResourcesPage({ user }) {
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const token = localStorage.getItem('token');
  const navigate = useNavigate();
  const wv = WH_VALUE[lang] || WH_VALUE.en;
  const [whValue, setWhValue] = useState(null);           // {total_city, items: {res: {value_city}}}

  const [summary, setSummary] = useState({});
  const [resources, setResources] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [openRes, setOpenRes] = useState(null);           // the resource window
  // «Ресурсы» (default) / «Усилители»; ?tab=boosters opens the second one
  const [tab, setTab] = useState(() => {
    try { return new URLSearchParams(window.location.search).get('tab') === 'boosters' ? 'boosters' : 'resources'; }
    catch { return 'resources'; }
  });

  const fetchData = async () => {
    setIsLoading(true);
    try {
      if (getGameMode() === 'demo') {
        const [demoBiz, demoState] = await Promise.all([
          fetch(`${API}/demo/my-businesses`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()).catch(() => ({ summary: {} })),
          fetch(`${API}/demo/state`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()).catch(() => ({ profile: {} })),
        ]);
        setSummary(demoBiz.summary || {});
        setResources((demoState.profile && demoState.profile.demo_resources) || {});
        setIsLoading(false);
        return;
      }
      const [bizRes, resRes, valRes] = await Promise.all([
        fetch(`${API}/my/businesses`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()).catch(() => ({ summary: {} })),
        fetch(`${API}/my/resources`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()).catch(() => ({ resources: {} })),
        fetch(`${API}/my/warehouse-value`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => (r.ok ? r.json() : null)).catch(() => null),
      ]);
      setSummary(bizRes.summary || {});
      setResources(resRes.resources || {});
      setWhValue(valRes);
    } catch (e) {
      /* keep last good state */
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const id = setInterval(fetchData, 30000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // «Мои ресурсы» = what the player has (>= 1 unit), as before.
  // «Нет в наличии» = every other resource of the game, shown faded below.
  const allResourceIds = getAllResources().map((r) => r.id);
  // «Ресурсы» = only what can be SOLD. Tutorial rewards (…_tutorial) can't be sold: they live in «Усилители».
  const ownedResources = Object.fromEntries(Object.entries(resources).filter(([k, v]) => v >= 1 && !String(k).endsWith('_tutorial')));
  const missingResourceIds = allResourceIds.filter((id) => !((resources[id] || 0) >= 1));

  const whUsed = Math.floor(summary.total_warehouse_used || 0);
  const whCap = summary.total_warehouse_capacity || 0;
  const whPct = whCap > 0 ? whUsed / whCap : 0;
  const barColor = whPct >= 1 ? 'bg-red-500' : whPct > 0.8 ? 'bg-red-400' : whPct > 0.5 ? 'bg-yellow-400' : 'bg-green-500';

  return (
    <div className="flex h-screen bg-void">
      <Sidebar user={user} />
      <div className="flex-1 overflow-hidden lg:ml-16">
        <ScrollArea className="h-full">
          <div className="p-4 lg:px-6 lg:pt-2 pt-0 pb-28 lg:pb-6 space-y-4 lg:space-y-6">

            {/* no page title / refresh here: the bottom bar names the page («Склад»), the data refreshes every 30 s */}
            <div className="tg-header-pad flex items-stretch gap-2"><div className="flex-1 grid grid-cols-2 gap-2" role="tablist" data-testid="resources-tabs">
              {[['resources', t('resourcesTab') || 'Ресурсы', '📦'], ['boosters', t('boostTab') || 'Усилители', '⚡']].map(([id, label, icon]) => (
                <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)} data-testid={`resources-tab-${id}`}
                  className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-bold uppercase tracking-wide transition-all ${
                    tab === id ? 'border-amber-400/60 bg-amber-400/15 text-amber-300' : 'border-white/10 bg-white/5 text-white/70 hover:border-white/20'}`}>
                  <span>{icon}</span>{label}
                </button>
              ))}
            </div><WikiHelp screen="resources" className="self-center" /></div>

            {tab === 'boosters' && <BoostersPanel t={t} lang={lang} onChanged={fetchData} />}

            {tab === 'resources' && (<>
            {/* Stats */}
            <div className="grid grid-cols-2 gap-2 sm:gap-4">
              {/* «Всего бизнесов» opens the «Бизнесы» page */}
              <button type="button" onClick={() => navigate('/my-businesses')} data-testid="resources-open-businesses"
                className="text-left rounded-xl transition-all active:scale-[0.98] hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-400">
                <Card className="glass-panel border-white/10 h-full">
                  <CardContent className="p-2.5 sm:p-4 flex items-center gap-2 sm:gap-3">
                    <Building2 className="w-6 h-6 sm:w-8 sm:h-8 text-cyber-cyan shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-lg sm:text-2xl font-bold text-white leading-tight" data-testid="resources-total-businesses">{summary.total_businesses || 0}</div>
                      <div className="text-[10px] sm:text-xs text-text-muted leading-tight">{t('totalBusinesses')}</div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/40 shrink-0" />
                  </CardContent>
                </Card>
              </button>

              <Card className="glass-panel border-purple-500/20">
                <CardContent className="p-2.5 sm:p-4 flex items-center gap-2 sm:gap-3">
                  <Package className="w-6 h-6 sm:w-8 sm:h-8 text-purple-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-base sm:text-2xl font-bold text-purple-400 leading-tight truncate" data-testid="resources-warehouse">
                      {whUsed}/{whCap}
                    </div>
                    <div className="text-[10px] sm:text-xs text-text-muted leading-tight">{t('totalWarehouse')}</div>
                    {whCap > 0 && (
                      <div className="w-full bg-gray-700/60 rounded-full h-1.5 mt-1.5 overflow-hidden">
                        <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${Math.min(100, whPct * 100)}%` }} />
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Estimated value of everything on the warehouse */}
            {whValue && (
              <Card className="glass-panel border-emerald-500/20" data-testid="resources-warehouse-value">
                <CardContent className="p-2.5 sm:p-4 flex items-center gap-2 sm:gap-3">
                  <Coins className="w-6 h-6 sm:w-8 sm:h-8 text-emerald-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] sm:text-xs text-text-muted leading-tight">{wv.title}</div>
                    <div className="text-[10px] text-text-muted/70 leading-tight">{wv.hint}</div>
                  </div>
                  <div className="text-lg sm:text-2xl font-bold text-emerald-400 whitespace-nowrap" data-testid="resources-warehouse-value-total">
                    ≈ {fmtCity(whValue.total_city)} <span className="text-xs sm:text-sm">$CITY</span>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* My Resources */}
            <div className="mt-4">
              <h2 className="text-xl font-bold text-white flex items-center gap-2 whitespace-nowrap mb-4" data-testid="resources-my-title">
                <Package className="w-5 h-5 text-amber-400 shrink-0" />
                {t('myResources')}
              </h2>

              <Card className="glass-panel border-amber-500/20">
                <CardContent className="p-2 sm:p-4">
                  {Object.keys(ownedResources).length === 0 ? (
                    <div className="text-center py-6 text-text-muted">
                      <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>{t('noAccumulatedResources')}</p>
                      <p className="text-xs mt-1">{t('businessesProduceAutomatically')}</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-1.5 sm:gap-3">
                      {Object.entries(ownedResources).map(([resource, amount]) => (
                        <button
                          type="button"
                          key={resource}
                          onClick={() => setOpenRes(resource)}
                          data-testid={`resource-card-${resource}`}
                          className={`relative rounded-lg p-1.5 sm:p-3 text-center border transition-all active:scale-95 hover:brightness-110 ${getResource(resource, lang)?.tier === 3 ? 'res-legendary' : 'bg-white/5'} ${amount > 0 ? 'border-white/10' : 'border-white/5 opacity-50'}`}
                        >
                          <div className="text-lg sm:text-2xl mb-0.5 sm:mb-1 mt-1">{getResource(resource, lang)?.icon || '📦'}</div>
                          <div className="text-sm sm:text-lg font-bold text-white text-center">{Math.floor(amount > 0 ? amount : 0)}</div>
                          {whValue?.items?.[resource] && (
                            <div className="text-[10px] sm:text-xs text-emerald-400/90 text-center truncate leading-tight" data-testid={`resource-value-${resource}`}>
                              ≈ {fmtCity(whValue.items[resource].value_city)} $CITY
                            </div>
                          )}
                          <div className="text-[10px] sm:text-xs text-text-muted capitalize text-center truncate">{getResource(resource, lang)?.name || resource}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Out of stock — resources the player does not have yet */}
            {missingResourceIds.length > 0 && (
              <div className="mt-4" data-testid="resources-out-of-stock">
                <h2 className="text-xl font-bold text-white flex items-center gap-2 whitespace-nowrap mb-4">
                  <Package className="w-5 h-5 text-text-muted shrink-0" />
                  {t('resourcesOutOfStock')}
                </h2>
                <Card className="glass-panel border-white/10">
                  <CardContent className="p-2 sm:p-4">
                    <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-1.5 sm:gap-3">
                      {missingResourceIds.map((resource) => {
                        const legend = getResource(resource, lang)?.tier === 3;
                        // tier 3: grey card inside a shimmering legendary frame; every card opens the resource window
                        // (for tier 3 — with its buff), even when the player has none of it
                        return (
                          <button
                            type="button"
                            key={resource}
                            onClick={() => setOpenRes(resource)}
                            data-testid={`resource-missing-${resource}`}
                            className={`relative rounded-lg text-center transition-all active:scale-95 hover:brightness-110 ${legend ? 'res-legendary-frame p-[1.5px]' : 'bg-white/5 border border-white/5 p-1.5 sm:p-3'}`}
                          >
                            <div className={legend ? 'res-legendary-muted rounded-[7px] p-1.5 sm:p-3 h-full' : 'opacity-50'}>
                              <div className={`text-lg sm:text-2xl mb-0.5 sm:mb-1 mt-1 ${legend ? 'opacity-70' : ''}`}>{getResource(resource, lang)?.icon || '📦'}</div>
                              <div className={`text-sm sm:text-lg font-bold text-center ${legend ? 'text-white/60' : 'text-white'}`}>0</div>
                              <div className="text-[10px] sm:text-xs text-text-muted capitalize text-center truncate">{getResource(resource, lang)?.name || resource}</div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}
            </>)}
          </div>
        </ScrollArea>
      </div>
      {openRes && <ResourceInfoModal id={openRes} amount={resources[openRes] || 0} amounts={resources} lang={lang} t={t} onClose={() => setOpenRes(null)} onChanged={fetchData} />}
    </div>
  );
}
