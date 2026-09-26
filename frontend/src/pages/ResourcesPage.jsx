import { useState, useEffect } from 'react';
import { Building2, Package, RefreshCw } from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import Sidebar from '@/components/Sidebar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useTranslation } from '@/lib/translations';
import { useLanguage } from '@/context/LanguageContext';
import { getResource, getAllResources } from '@/lib/resourceConfig';
import { getGameMode } from '@/lib/gameMode';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

// Resources page — hosts the "business count", "warehouse" and "My resources"
// blocks that previously lived on the My Businesses page.
export default function ResourcesPage({ user }) {
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);
  const token = localStorage.getItem('token');

  const [summary, setSummary] = useState({});
  const [resources, setResources] = useState({});
  const [showAll, setShowAll] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

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
      const [bizRes, resRes] = await Promise.all([
        fetch(`${API}/my/businesses`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()).catch(() => ({ summary: {} })),
        fetch(`${API}/my/resources`, { headers: { Authorization: `Bearer ${token}` } }).then((r) => r.json()).catch(() => ({ resources: {} })),
      ]);
      setSummary(bizRes.summary || {});
      setResources(resRes.resources || {});
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

  const allResourceIds = getAllResources().map((r) => r.id);
  const displayResources = showAll
    ? allResourceIds.reduce((acc, id) => { acc[id] = resources[id] || 0; return acc; }, {})
    : Object.fromEntries(Object.entries(resources).filter(([, v]) => v >= 1));

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
            <PageHeader
              icon={<Package className="w-6 h-6 lg:w-8 lg:h-8 text-amber-400" />}
              title={t('myResources') || 'Ресурсы'}
              actionButtons={
                <Button onClick={fetchData} variant="outline" size="icon" className="border-white/10 h-8 w-8 sm:h-10 sm:w-10" disabled={isLoading}>
                  <RefreshCw className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </Button>
              }
            />

            {/* Stats */}
            <div className="grid grid-cols-2 gap-2 sm:gap-4">
              <Card className="glass-panel border-white/10">
                <CardContent className="p-2.5 sm:p-4 flex items-center gap-2 sm:gap-3">
                  <Building2 className="w-6 h-6 sm:w-8 sm:h-8 text-cyber-cyan shrink-0" />
                  <div className="min-w-0">
                    <div className="text-lg sm:text-2xl font-bold text-white leading-tight" data-testid="resources-total-businesses">{summary.total_businesses || 0}</div>
                    <div className="text-[10px] sm:text-xs text-text-muted leading-tight">{t('totalBusinesses')}</div>
                  </div>
                </CardContent>
              </Card>

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

            {/* My Resources */}
            <div className="mt-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
                <h2 className="text-xl font-bold text-white flex items-center gap-2 whitespace-nowrap">
                  <Package className="w-5 h-5 text-amber-400 shrink-0" />
                  {t('myResources')}
                </h2>
                <label className="flex items-center gap-2 cursor-pointer self-start sm:self-auto">
                  <input
                    type="checkbox"
                    checked={showAll}
                    onChange={(e) => setShowAll(e.target.checked)}
                    data-testid="resources-show-all"
                    className="rounded border-gray-600 bg-gray-800 text-amber-500 focus:ring-amber-500"
                  />
                  <span className="text-xs text-text-muted">{t('showAllResources') || 'Показать все'}</span>
                </label>
              </div>

              <Card className="glass-panel border-amber-500/20">
                <CardContent className="p-2 sm:p-4">
                  {Object.keys(displayResources).length === 0 ? (
                    <div className="text-center py-6 text-text-muted">
                      <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>{t('noAccumulatedResources')}</p>
                      <p className="text-xs mt-1">{t('businessesProduceAutomatically')}</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-1.5 sm:gap-3">
                      {Object.entries(displayResources).map(([resource, amount]) => (
                        <div
                          key={resource}
                          data-testid={`resource-card-${resource}`}
                          className={`relative bg-white/5 rounded-lg p-1.5 sm:p-3 text-center border transition-all ${amount > 0 ? 'border-white/10' : 'border-white/5 opacity-50'}`}
                        >
                          <div className="text-lg sm:text-2xl mb-0.5 sm:mb-1 mt-1">{getResource(resource, lang)?.icon || '📦'}</div>
                          <div className="text-sm sm:text-lg font-bold text-white text-center">{Math.floor(amount > 0 ? amount : 0)}</div>
                          <div className="text-[10px] sm:text-xs text-text-muted capitalize text-center truncate">{getResource(resource, lang)?.name || resource}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
