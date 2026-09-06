import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Building2, Package, Coins, TrendingUp, RefreshCw, 
  Settings2, Wrench, Zap, ArrowUp, ChevronRight,
  Play, Pause, Check, X, AlertCircle, Shield, Heart,
  Crown, Users, Warehouse, Clock, Loader2, Tag,
  FileText, HandshakeIcon, ChevronDown, Scroll
} from 'lucide-react';
import PageHeader from '@/components/PageHeader';
import SkinPicker from '@/components/SkinPicker';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import Sidebar from '@/components/Sidebar';
import { useTranslation } from '@/lib/translations';
import { useLanguage } from '@/context/LanguageContext';
import { useTutorial } from '@/context/TutorialContext';
import { tBusiness, tResource, tBuff, tResourceBuff, tContract } from '@/lib/translationsExtra';
import { tonToCity, formatCity } from '@/lib/currency';
import { getGameMode } from '@/lib/gameMode';
import { getResource, getAllResources, getResourceName } from '@/lib/resourceConfig';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API = `${BACKEND_URL}/api`;

// Tier colors
const CONTRACT_TYPES = {
  tax_haven: {
    name: 'Налоговая Гавань',
    description: 'Вассал платит 10% с каждой продажи ресурсов на маркетплейсе',
    vassal_note: '10% с каждой продажи в TON',
    patron_note: '10% от выручки вассала при продаже',
    icon: '🏝️',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    penalty: 500,
  },
  raw_material: {
    name: 'Сырьевой Придаток',
    description: 'Вассал отдаёт 15% произведённых товаров Патрону',
    vassal_note: '15% товаров уходит Патрону каждый тик',
    patron_note: 'Получаете 15% ресурсов вассала',
    icon: '⚙️',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    penalty: 750,
  },
  tech_umbrella: {
    name: 'Технологический Зонтик',
    description: 'Вассал экономит 30% на ремонтных комплектах и платит ренту',
    vassal_note: '100 $CITY/день ренты + -30% ремонт',
    patron_note: 'Фиксированная рента 100 $CITY/день',
    icon: '🛡️',
    color: 'text-green-400',
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    penalty: 300,
  },
};

const TIER_COLORS = {
  1: 'bg-green-500/20 text-green-400 border-green-500/30',
  2: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  3: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
};

// Level-0 (застолблённый) → Level-1 upgrade note — localized (all 9 project languages).
const ZERO_UNLOCK_I18N = {
  en: 'Unlock of the MAIN ACCOUNT',
  ru: 'Разблокировка ОСНОВНОГО СЧЁТА',
  es: 'Desbloqueo de la CUENTA PRINCIPAL',
  zh: '解锁主账户',
  fr: 'Déblocage du COMPTE PRINCIPAL',
  de: 'Freischaltung des HAUPTKONTOS',
  ja: 'メインアカウントのロック解除',
  ko: '메인 계정 잠금 해제',
  id: 'Membuka AKUN UTAMA',
};

// Resource icons - V2.0
const resourceIcons = {
  energy: '⚡',
  cu: '🖥️',
  quartz: '💎',
  traffic: '📡',
  cooling: '❄️',
  biomass: '🌿',
  scrap: '🗑️',
  chips: '🔲',
  nft: '🎨',
  neurocode: '🧠',
  logistics: '🚚',
  repair_kits: '🔧',
  vr_experience: '🥽',
  profit_ton: '💰',
  shares: '📈',
  ton: '💎',
  // Backward compat
  food: '🌿',
  algo: '🧠',
  iron: '🔧',
};

export default function MyBusinessesPage({ user, refreshBalance, updateBalance }) {
  const navigate = useNavigate();
  
  // Get language from context
  const { language: lang } = useLanguage();
  const { t } = useTranslation(lang);

  // Tutorial state — used to disable destructive / detail-opening actions
  // while the user is in the onboarding flow. The tutorial intentionally
  // walks them through the page read-only (steps `explain_idle` and
  // `explain_t3_buff`) and any deviation breaks the sandbox flow.
  const tutorial = useTutorial();
  const isTutorialActive = !!tutorial?.active;
  const blockedTutorialToast = () => {
    try {
      toast.info(
        t('tutorial_action_blocked')
          && t('tutorial_action_blocked') !== 'tutorial_action_blocked'
            ? t('tutorial_action_blocked')
            : 'Это действие недоступно во время обучения. Заверши тур, и оно откроется.',
      );
    } catch (e) { /* noop */ }
  };
  
  const [businesses, setBusinesses] = useState([]);
  const [summary, setSummary] = useState({});
  const [resourcesFromBusinesses, setResourcesFromBusinesses] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [selectedBusiness, setSelectedBusiness] = useState(null);
  const [patrons, setPatrons] = useState([]);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [myPlots, setMyPlots] = useState([]);
  
  // Modals
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showAllResources, setShowAllResources] = useState(false);
  const [showRepairModal, setShowRepairModal] = useState(false);
  const [showPatronModal, setShowPatronModal] = useState(false);
  const [showBuffModal, setShowBuffModal] = useState(false);
  const [availableBuffs, setAvailableBuffs] = useState([]);
  const [buffBusiness, setBuffBusiness] = useState(null);

  // ==== T3 Resource Buffs (subscription-style) ====
  // IDs of T3 resources that can be activated as buffs
  const T3_BUFF_RESOURCE_IDS = ['neuro_core', 'gold_bill', 'license_token', 'luck_chip', 'war_protocol', 'bio_module', 'gateway_code'];
  const [resourceBuffsData, setResourceBuffsData] = useState({ buffs: [], active: [] });
  const [activeBuffMults, setActiveBuffMults] = useState({ trade_tax_reduction: 0.0, trade_fee_multiplier: 1.0 });
  const [showResourceBuffModal, setShowResourceBuffModal] = useState(false);
  const [selectedBuffResource, setSelectedBuffResource] = useState(null);
  const [isActivatingBuff, setIsActivatingBuff] = useState(false);
  const [vassals, setVassals] = useState([]);
  const [showVassalsModal, setShowVassalsModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [showSellModal, setShowSellModal] = useState(false);
  const [sellPrice, setSellPrice] = useState('');
  const [sellTaxInfo, setSellTaxInfo] = useState(null);
  const [isCancelingSale, setIsCancelingSale] = useState(false);
  
  // Loading states
  const [isCollecting, setIsCollecting] = useState(false);
  const [isUpgrading, setIsUpgrading] = useState(false);
  const [isRepairing, setIsRepairing] = useState(false);
  const [isSelling, setIsSelling] = useState(false);
  
  // Contract state
  const [contracts, setContracts] = useState({ as_patron: [], as_vassal: [] });
  const [showContractProposalModal, setShowContractProposalModal] = useState(false);
  const [contractTarget, setContractTarget] = useState(null);
  const [proposalType, setProposalType] = useState('tax_haven');
  const [proposalBuff, setProposalBuff] = useState('');
  const [proposalDuration, setProposalDuration] = useState(30);
  const [proposalAutoRenew, setProposalAutoRenew] = useState(false);
  const [isProposing, setIsProposing] = useState(false);
  const [showContractDetailsModal, setShowContractDetailsModal] = useState(false);
  const [selectedContract, setSelectedContract] = useState(null);
  
  // Alliance offers state
  const [allianceOffers, setAllianceOffers] = useState([]);
  const [showAllOffersModal, setShowAllOffersModal] = useState(false);
  const [showPublishOfferModal, setShowPublishOfferModal] = useState(false);
  const [offerBuff, setOfferBuff] = useState('');
  const [offerType, setOfferType] = useState('tax_haven');
  const [offerDuration, setOfferDuration] = useState(30);
  const [isPublishing, setIsPublishing] = useState(false);
  
  // Alliance offers browsing (paginated)
  const [offersPage, setOffersPage] = useState(0);
  const OFFERS_PER_PAGE = 3;
  
  const token = localStorage.getItem('token');

  // ===== Bank owner settings (Block A) =====
  const [showBankSettingsModal, setShowBankSettingsModal] = useState(false);
  const [bankSettings, setBankSettings] = useState({ interest_rate_percent: '', instant_fee_percent: '' });
  const [bankSettingsLoading, setBankSettingsLoading] = useState(false);
  const [bankSettingsSaving, setBankSettingsSaving] = useState(false);
  const isBankBusiness = (biz) =>
    !!biz && (biz.business_type === 'gram_bank' || biz.config?.instant_withdrawal === true);

  const loadBankSettings = async (businessId) => {
    setBankSettingsLoading(true);
    try {
      const res = await fetch(`${API}/bank/settings/${businessId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setBankSettings({
          interest_rate_percent: String(data.interest_rate_percent ?? ''),
          instant_fee_percent: String(data.instant_fee_percent ?? ''),
        });
      }
    } catch (e) {
      /* non-blocking */
    } finally {
      setBankSettingsLoading(false);
    }
  };

  // Sanitize numeric input: digits only, clamp to [0, max], strip leading zeros.
  const sanitizeIntField = (raw, max) => {
    const digits = String(raw).replace(/[^0-9]/g, '');
    if (digits === '') return '';
    let n = parseInt(digits, 10);
    if (Number.isNaN(n)) return '';
    if (n > max) n = max;
    return String(n);
  };

  const saveBankSettings = async () => {
    if (!selectedBusiness) return;
    const interest = parseInt(bankSettings.interest_rate_percent || '0', 10);
    const instant = parseInt(bankSettings.instant_fee_percent || '0', 10);
    setBankSettingsSaving(true);
    try {
      const res = await fetch(`${API}/bank/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          business_id: selectedBusiness.id,
          interest_rate_percent: interest,
          instant_fee_percent: instant,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка сохранения');
      setBankSettings({
        interest_rate_percent: String(data.interest_rate_percent),
        instant_fee_percent: String(data.instant_fee_percent),
      });
      toast.success(t('bankSettingsSaved') || 'Настройки банка сохранены');
      setShowBankSettingsModal(false);
    } catch (e) {
      toast.error(e.message || 'Ошибка сохранения');
    } finally {
      setBankSettingsSaving(false);
    }
  };

  // Fetch alliance offers
  const fetchAllianceOffers = async () => {
    try {
      const res = await fetch(`${API}/alliances/offers`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAllianceOffers(data.offers || []);
      }
    } catch (e) {
      console.error('Failed to fetch alliance offers:', e);
    }
  };

  // Publish offer handler
  const handlePublishOffer = async () => {
    if (!offerBuff || !offerType) {
      toast.error(t('selectBuffAndContractErr') || 'Select a buff and contract type');
      return;
    }
    setIsPublishing(true);
    try {
      const res = await fetch(`${API}/alliances/publish-offer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          buff_id: offerBuff,
          contract_type: offerType,
          duration_days: offerDuration,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка');
      toast.success(t('offerPublishedSuccess') || 'Offer published! Vassals will be able to see it.');
      setShowPublishOfferModal(false);
      setOfferBuff('');
      setOfferType('tax_haven');
      setOfferDuration(30);
      fetchAllianceOffers();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setIsPublishing(false);
    }
  };

  // Accept offer handler
  const handleAcceptOffer = async (offerId, vassalBusinessId) => {
    try {
      const url = vassalBusinessId
        ? `${API}/alliances/accept/${offerId}?vassal_business_id=${vassalBusinessId}`
        : `${API}/alliances/accept/${offerId}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка');
      toast.success(data.message || 'Альянс заключён!');
      fetchAllianceOffers();
      fetchContracts();
      fetchData();
    } catch (e) {
      toast.error(e.message);
    }
  };

  // Cancel own offer
  const handleCancelOffer = async (offerId) => {
    try {
      const res = await fetch(`${API}/alliances/cancel-offer/${offerId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка');
      toast.success(t('offerCancelledSuccess') || 'Offer cancelled');
      fetchAllianceOffers();
    } catch (e) {
      toast.error(e.message);
    }
  };

  // Helper: get color class for consumed resource based on hours remaining
  const getConsumeColor = (resource, dailyAmount) => {
    if (!dailyAmount || dailyAmount <= 0) return 'text-text-muted';
    const available = resourcesFromBusinesses[resource] || 0;
    if (available === 0) return 'text-red-400';
    const hoursRemaining = (available / dailyAmount) * 24;
    if (hoursRemaining <= (5 / 60)) return 'text-red-400';  // ≤ 5 min
    if (hoursRemaining <= 4) return 'text-yellow-400';       // ≤ 4 hours
    return 'text-green-400';                                  // > 4 hours
  };

  // Форматирование адреса кошелька
  const formatWalletAddress = (address) => {
    if (!address) return 'Не привязан';
    if (address.length <= 15) return address;
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  // Расчет налога при продаже
  const calculateSaleTax = async (price) => {
    try {
      const res = await fetch(`${API}/business/calculate-sale-tax`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price: parseFloat(price), business_id: selectedBusiness?.id })
      });
      if (res.ok) {
        const data = await res.json();
        setSellTaxInfo(data);
      }
    } catch (error) {
      console.error('Failed to calculate tax:', error);
    }
  };

  // Продажа бизнеса
  const handleSellBusiness = async () => {
    if (!selectedBusiness || !sellPrice) return;
    
    setIsSelling(true);
    try {
      const res = await fetch(`${API}/business/${selectedBusiness.id}/sell`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          business_id: selectedBusiness.id,
          price: parseFloat(sellPrice) / 1000  // Convert $CITY to TON for backend
        })
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to list business');
      }
      
      const data = await res.json();
      toast.success((t('listedSuccess') || 'Business listed for sale! You will receive {amount} $CITY').replace('{amount}', formatCity(tonToCity(data.listing.seller_receives))));
      setShowSellModal(false);
      setSellPrice('');
      setSellTaxInfo(null);
      fetchData();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsSelling(false);
    }
  };

  // Снять бизнес с продажи
  const handleCancelSale = async () => {
    if (!selectedBusiness) {
      toast.error(t('businessNotSelectedErr') || 'No business selected');
      return;
    }
    
    setIsCancelingSale(true);
    try {
      // Сначала найдём листинг по plot_id или business_id
      const listingsRes = await fetch(`${API}/market/land/listings`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const listingsData = await listingsRes.json();
      
      // Ищем листинг этого бизнеса
      const listing = (listingsData.listings || []).find(l => 
        l.plot_id === selectedBusiness.plot_id || 
        l.business_id === selectedBusiness.id ||
        (l.business && l.business.id === selectedBusiness.id)
      );
      
      if (!listing) {
        toast.error(t('listingNotFoundErr') || 'Listing not found');
        setIsCancelingSale(false);
        return;
      }
      
      // Используем тот же эндпоинт DELETE как на маркетплейсе
      const res = await fetch(`${API}/market/land/listing/${listing.id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      if (!res.ok) {
        const err = await res.json();
        if (err.detail === 'SEIZED_CONTACT_SUPPORT') {
          throw new Error(t('seizedContactSupport') || 'To delist a business, please contact support.');
        }
        throw new Error(err.detail || 'Не удалось снять с продажи');
      }
      
      toast.success(t('unlistedSuccess') || 'Business removed from sale');
      setShowDetailsModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsCancelingSale(false);
    }
  };

  const fetchData = async () => {
    setIsLoading(true);
    try {
      // Demo (Sandbox): show ONLY the demo business + demo resources, fetched
      // from the isolated demo endpoints (never the real ones).
      if (getGameMode() === 'demo') {
        const [demoBiz, demoState] = await Promise.all([
          fetch(`${API}/demo/my-businesses`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()).catch(() => ({ businesses: [], summary: {} })),
          fetch(`${API}/demo/state`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()).catch(() => ({ profile: {} })),
        ]);
        const dbz = demoBiz.businesses || [];
        setBusinesses(dbz);
        setSummary(demoBiz.summary || {});
        setSelectedBusiness((prev) => prev ? (dbz.find((b) => b.id === prev.id) || dbz[0] || null) : prev);
        setResourcesFromBusinesses((demoState.profile && demoState.profile.demo_resources) || {});
        setPatrons([]);
        setMyPlots([]);
        setResourceBuffsData({ buffs: [], active: [] });
        setLastUpdate(new Date());
        setIsLoading(false);
        return;
      }
      const [bizRes, patronsRes, resourcesRes, plotsRes, buffsRes, buffMultsRes] = await Promise.all([
        fetch(`${API}/my/businesses`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
        fetch(`${API}/patrons`).then(r => r.json()),
        fetch(`${API}/my/resources`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()).catch(() => ({ resources: {} })),
        fetch(`${API}/users/me/plots`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()).catch(() => ({ plots: [] })),
        fetch(`${API}/resource-buffs/available`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()).catch(() => ({ buffs: [], active: [] })),
        fetch(`${API}/my/active-buff-multipliers`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()).catch(() => null),
      ]);

      setBusinesses(bizRes.businesses || []);
      setSummary(bizRes.summary || {});
      // Re-sync currently selected business/buff modal targets so any nested
      // detail dialogs (patron buff, upgrade, repair) refresh in-place when
      // server-side data changes (e.g. patron updates its T3 buff via WS).
      const fresh = bizRes.businesses || [];
      setSelectedBusiness((prev) => prev ? (fresh.find((b) => b.id === prev.id) || prev) : prev);
      setBuffBusiness((prev) => prev ? (fresh.find((b) => b.id === prev.id) || prev) : prev);
      setPatrons(patronsRes.patrons || []);
      setResourcesFromBusinesses(resourcesRes.resources || {});
      setMyPlots(plotsRes.plots || []);
      setResourceBuffsData(buffsRes || { buffs: [], active: [] });
      if (buffMultsRes) {
        setActiveBuffMults({ ...(buffMultsRes.multipliers || {}), ...(buffMultsRes.reductions || {}) });
      }
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Failed to fetch businesses:', error);
      toast.error(t('loadDataErr') || 'Failed to load data');
    } finally {
      setIsLoading(false);
    }
  };

  // Silent refresh: re-fetch businesses + resources WITHOUT the loading spinner.
  // Used by the auto-refresh tick so the work-status badge updates on its own
  // (e.g. after the user buys input resources and the next economic tick flips
  // the business back to "working").
  const refreshBusinessesSilently = async () => {
    if (!token) return;
    if (getGameMode() === 'demo') { fetchData(); return; }
    try {
      const [bizRes, resourcesRes] = await Promise.all([
        fetch(`${API}/my/businesses`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
        fetch(`${API}/my/resources`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()).catch(() => null),
      ]);
      if (bizRes?.businesses) {
        const fresh = bizRes.businesses;
        setBusinesses(fresh);
        setSummary(bizRes.summary || {});
        setSelectedBusiness((prev) => prev ? (fresh.find((b) => b.id === prev.id) || prev) : prev);
        setBuffBusiness((prev) => prev ? (fresh.find((b) => b.id === prev.id) || prev) : prev);
      }
      if (resourcesRes?.resources) setResourcesFromBusinesses(resourcesRes.resources);
      setLastUpdate(new Date());
    } catch (_e) { /* keep last good state on transient errors */ }
  };

  // Activate a T3 resource as a buff (consumes 1 unit, lasts N days)
  const handleActivateResourceBuff = async (resourceId) => {
    if (!resourceId) return;
    // v2.1.5: client-side guard — block activation when the user has no real
    // (non-tutorial) business. Mirrors the backend gate so the user gets an
    // instant, localized message instead of a server round-trip.
    const realBizCount = (businesses || []).filter((b) => !b.tutorial).length;
    if (realBizCount === 0) {
      toast.error(t('tutorial_buff_needs_business') || 'Для активации T3-баффа требуется активный бизнес. Приобретите свой первый участок, чтобы применить этот ускоритель.');
      return;
    }
    setIsActivatingBuff(true);
    try {
      const res = await fetch(`${API}/resource-buffs/activate/${resourceId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { detail: text || 'Ошибка активации' }; }
      if (!res.ok) {
        // Translate known error codes (server now returns i18n keys, not RU strings)
        const code = data.detail;
        if (code === 'tutorial_buff_needs_business') {
          throw new Error(t('tutorial_buff_needs_business') || 'Для активации T3-баффа требуется активный бизнес. Приобретите свой первый участок, чтобы применить этот ускоритель.');
        }
        throw new Error(data.detail || 'Ошибка активации');
      }
      toast.success(data.message || 'Баф активирован');
      setShowResourceBuffModal(false);
      setSelectedBuffResource(null);
      fetchData();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsActivatingBuff(false);
    }
  };

  const fetchContracts = async () => {
    try {
      const res = await fetch(`${API}/contracts/my`, { headers: { Authorization: `Bearer ${token}` } });
      if (res.ok) {
        const data = await res.json();
        setContracts(data);
      }
    } catch {}
  };

  useEffect(() => {
    if (!token) {
      navigate('/auth?mode=login');
      return;
    }
    fetchData();
    fetchContracts();
    fetchAllianceOffers();

    // Auto-refresh tick: silently re-sync business status every 60s so the
    // work-status badge ("Простаивает" → "Активен") updates on its own once
    // the conditions are met, without the user reloading the page.
    // Skipped in demo/sandbox mode — the demo economy is static and the
    // periodic re-fetch was perceived as an annoying "page refresh every minute".
    const statusTick = getGameMode() === 'demo'
      ? null
      : setInterval(() => { refreshBusinessesSilently(); }, 60000);
    
    // (Vassal/buff system removed) — Tier 3 purchases no longer auto-open a buff modal.
    
    // ─── WebSocket: realtime patron buff updates ────────────────────────────
    // Server emits {type: 'patron_buff_changed', patron_business_id, buff} to:
    //   • the patron owner (so its T3 details refresh without "обновить")
    //   • each vassal owner (so their business details show the new buff instantly)
    // We connect once, refresh the businesses list on each event, and close on unmount.
    let ws = null;
    try {
      const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const apiHost = (process.env.REACT_APP_BACKEND_URL || '').replace(/^https?:\/\//, '');
      const userKey = user?.id || user?.email || user?.wallet_address || user?.username;
      if (apiHost && userKey) {
        ws = new WebSocket(`${wsScheme}://${apiHost}/api/ws/${encodeURIComponent(userKey)}`);
        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data);
            if (data?.type === 'patron_buff_changed') {
              fetchData();
              if (data?.buff?.name) {
                toast.message('Бафф патрона обновлён', { description: `${data.buff.icon || ''} ${data.buff.name}` });
              }
            }
          } catch (_) {}
        };
        ws.onerror = () => {};
      }
    } catch (_) {}
    return () => { try { ws && ws.close(); } catch (_) {} if (statusTick) clearInterval(statusTick); };
  }, [user]);

  // Collect all income
  const handleCollectAll = async () => {
    setIsCollecting(true);
    try {
      const res = await fetch(`${API}/my/collect-all`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!res.ok) throw new Error('Ошибка сбора');
      
      const data = await res.json();
      
      // Мгновенное отображение начисления
      toast.success(
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <span className="text-2xl animate-bounce">💰</span>
            <span className="text-lg font-bold text-green-400">+{formatCity(tonToCity(data.total_player_income))} $CITY</span>
          </div>
          <div className="text-xs text-gray-400">Собрано с {data.businesses_collected} бизнесов</div>
          <div className="text-xs text-amber-400">Налог: -{formatCity(tonToCity(data.total_tax_paid))} $CITY</div>
        </div>,
        { duration: 5000 }
      );
      
      // Update global balance
      if (refreshBalance) refreshBalance();
      if (updateBalance && data.new_balance !== undefined) {
        updateBalance(data.new_balance);
      }
      
      setLastUpdate(new Date());
      fetchData();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsCollecting(false);
    }
  };

  // Collect single business
  const handleCollect = async (businessId) => {
    try {
      const res = await fetch(`${API}/business/${businessId}/collect`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Ошибка сбора');
      }
      
      const data = await res.json();
      
      // Мгновенное визуальное начисление
      toast.success(
        <div className="flex items-center gap-2">
          <span className="text-xl animate-bounce">💰</span>
          <span className="font-bold text-green-400">+{formatCity(tonToCity(data.player_receives))} $CITY</span>
        </div>,
        { duration: 3000 }
      );
      
      fetchData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  // Upgrade business
  const handleUpgrade = async () => {
    if (!selectedBusiness) return;
    setIsUpgrading(true);

    try {
      // Demo mode: upgrade is applied against demo_balance_city + demo_resources
      // via the isolated demo endpoint (same cost table as real mode).
      if (getGameMode() === 'demo') {
        const res = await fetch(`${API}/demo/business/upgrade`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json().catch(() => ({}));
        if (data.status === 'upgraded') {
          toast.success((t('upgradeSuccess') || 'Upgraded to level {level}!').replace('{level}', data.new_level));
          setShowUpgradeModal(false);
          fetchData();
        } else if (data.status === 'insufficient_city') {
          toast.error(`${t('upgradeError') || 'Ошибка улучшения'}: $CITY ${Math.ceil(data.need_city)} / ${Math.floor(data.have_city)}`);
        } else if (data.status === 'insufficient_resource') {
          const resName = getResourceName(data.resource, lang) || data.resource;
          const msg = (t('insufficientResourceUpgrade') || 'Insufficient {res}: need {need}, have {have}')
            .replace('{res}', resName)
            .replace('{need}', data.need)
            .replace('{have}', data.have);
          toast.error(msg);
        } else if (data.status === 'max_level') {
          toast.info(t('upgradeMaxLevel') || 'Достигнут максимальный уровень');
        } else {
          toast.error(t('upgradeError') || 'Ошибка улучшения');
        }
        setIsUpgrading(false);
        return;
      }

      const res = await fetch(`${API}/business/${selectedBusiness.id}/upgrade`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!res.ok) {
        const err = await res.json();
        const d = err.detail;
        // Structured "insufficient resource" error → localize into user's language.
        if (d && typeof d === 'object' && d.code === 'insufficient_resource') {
          const resName = getResourceName(d.resource, lang) || d.resource;
          const msg = (t('insufficientResourceUpgrade') || 'Insufficient {res}: need {need}, have {have}')
            .replace('{res}', resName)
            .replace('{need}', d.need)
            .replace('{have}', d.have);
          throw new Error(msg);
        }
        throw new Error((typeof d === 'string' && d) || d?.message || t('upgradeError') || 'Ошибка улучшения');
      }
      
      const data = await res.json();
      toast.success((t('upgradeSuccess') || 'Upgraded to level {level}!').replace('{level}', data.new_level));
      setShowUpgradeModal(false);
      if (refreshBalance) refreshBalance();
      fetchData();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsUpgrading(false);
    }
  };

  // Repair business
  const handleRepair = async () => {
    if (!selectedBusiness) return;
    setIsRepairing(true);

    try {
      // Demo mode: repair is paid in demo $CITY via the isolated demo endpoint.
      if (getGameMode() === 'demo') {
        const res = await fetch(`${API}/demo/business/repair`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json().catch(() => ({}));
        if (data.status === 'repaired') {
          toast.success((t('repairSuccess') || 'Repaired! Paid: {amount} $CITY').replace('{amount}', formatCity(data.paid_city ?? data.cost_city)));
        } else if (data.status === 'insufficient') {
          toast.error((t('repairInsufficientCity') || 'Not enough $CITY: need {need}').replace('{need}', formatCity(data.need)));
        } else if (data.status === 'already_full') {
          toast.info(t('repairAlreadyFull') || 'Durability is already full');
        }
        setShowRepairModal(false);
        fetchData();
        setIsRepairing(false);
        return;
      }

      const res = await fetch(`${API}/business/${selectedBusiness.id}/repair`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });

      // Safe JSON parsing: backend may return HTML/plain on 500
      const text = await res.text();
      let data;
      try { data = JSON.parse(text); } catch {
        data = { detail: res.status === 500 ? 'Ошибка сервера при ремонте. Попробуйте позже.' : (text || 'Ошибка ремонта') };
      }

      if (!res.ok) {
        throw new Error(data.detail || 'Ошибка ремонта');
      }

      const cost = data.cost_city ?? (data.cost_paid ? tonToCity(data.cost_paid) : 0);
      toast.success((t('repairSuccess') || 'Repaired! Paid: {amount} $CITY').replace('{amount}', formatCity(cost)));

      // Instantly update global balance so UI reflects payment without page reload
      if (updateBalance && data.new_balance !== undefined) {
        updateBalance(data.new_balance);
      }
      if (refreshBalance) refreshBalance();

      setShowRepairModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setIsRepairing(false);
    }
  };

  // Set patron
  const handleSetPatron = async (patronId) => {
    if (!selectedBusiness) return;
    
    try {
      const url = patronId 
        ? `${API}/business/${selectedBusiness.id}/set-patron?patron_id=${patronId}`
        : `${API}/business/${selectedBusiness.id}/set-patron`;
        
      const res = await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Ошибка назначения патрона');
      }
      
      toast.success(patronId ? (t('patronAssigned') || 'Patron assigned!') : (t('patronRemoved') || 'Patron removed'));
      setShowPatronModal(false);
      fetchData();
    } catch (error) {
      toast.error(error.message);
    }
  };

  // Open buff selection for Tier 3 business
  const openBuffModal = async (biz) => {
    setBuffBusiness(biz);
    try {
      const res = await fetch(`${API}/tier3/buffs`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setAvailableBuffs(data.buffs || []);
    } catch {
      setAvailableBuffs([]);
    }
    setShowBuffModal(true);
  };

  const handleSetBuff = async (buffId) => {
    if (!buffBusiness) return;
    try {
      const res = await fetch(`${API}/business/${buffBusiness.id}/set-buff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ buff_id: buffId })
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || 'Ошибка'); }
      toast.success(t('buffSelectedToast'));
      setShowBuffModal(false);
      fetchData();
    } catch (e) { toast.error(e.message); }
  };

  const openVassalsModal = async (biz) => {
    setSelectedBusiness(biz);
    try {
      const res = await fetch(`${API}/business/${biz.id}/vassals`, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setVassals(data.vassals || []);
    } catch { setVassals([]); }
    setShowVassalsModal(true);
  };

  // Open business details
  const openDetails = async (biz) => {
    // Reset bank settings fields; load fresh if this is a bank.
    setBankSettings({ interest_rate_percent: '', instant_fee_percent: '' });
    // Demo mode: never hit the real /business/{id} endpoint — use the demo
    // business object we already have from /api/demo/my-businesses.
    if (getGameMode() === 'demo') {
      setSelectedBusiness(biz);
      setShowDetailsModal(true);
      return;
    }
    try {
      const res = await fetch(`${API}/business/${biz.id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      const merged = { ...biz, ...data };
      setSelectedBusiness(merged);
      setShowDetailsModal(true);
      if (isBankBusiness(merged)) loadBankSettings(merged.id);
    } catch (error) {
      setSelectedBusiness(biz);
      setShowDetailsModal(true);
      if (isBankBusiness(biz)) loadBankSettings(biz.id);
    }
  };

  // Get durability color
  const getDurabilityColor = (durability) => {
    if (durability >= 70) return 'bg-green-500';
    if (durability >= 40) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  // Contract handlers
  const openContractProposal = async (vassalInfo) => {
    setContractTarget(vassalInfo);
    setProposalType('tax_haven');
    setProposalBuff('');
    // Load buffs if not already loaded
    if (availableBuffs.length === 0) {
      try {
        const res = await fetch(`${API}/tier3/buffs`, { headers: { Authorization: `Bearer ${token}` } });
        const data = await res.json();
        setAvailableBuffs(data.buffs || []);
      } catch {}
    }
    setShowContractProposalModal(true);
  };

  const handleProposeContract = async () => {
    if (!contractTarget || !proposalType || !proposalBuff) {
      toast.error(t('selectBuffAndContractErr') || 'Select a buff and contract type');
      return;
    }
    setIsProposing(true);
    try {
      const res = await fetch(`${API}/contracts/propose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          type: proposalType,
          vassal_business_id: contractTarget.business_id,
          patron_buff: proposalBuff,
          duration_days: proposalDuration,
          auto_renew: proposalAutoRenew,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка');
      toast.success(t('contractOfferSentSuccess') || 'Contract offer sent!');
      setShowContractProposalModal(false);
      fetchContracts();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setIsProposing(false);
    }
  };

  const handleContractAction = async (contractId, action) => {
    try {
      const res = await fetch(`${API}/contracts/${contractId}/${action}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Ошибка');
      toast.success(data.message || 'Готово');
      fetchContracts();
      fetchData();
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex h-screen bg-void">
        <Sidebar user={user} />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-12 h-12 text-cyber-cyan animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-void">
      <Sidebar user={user} />
      
      <div className="flex-1 overflow-hidden lg:ml-16">
        <ScrollArea className="h-full">
          <div className="p-4 lg:px-6 lg:pt-2 lg:pb-6 pt-0 space-y-4 lg:space-y-6">
            {/* Header - Mobile Optimized */}
            <PageHeader 
              icon={<Building2 className="w-6 h-6 lg:w-8 lg:h-8 text-cyber-cyan" />}
              title={t('myBusinessesTitle')}
              actionButtons={
                <Button onClick={fetchData} variant="outline" size="icon" className="border-white/10 h-8 w-8 sm:h-10 sm:w-10" disabled={isLoading}>
                  <RefreshCw className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </Button>
              }
            />
              
            {/* Stats — on mobile fit both cards in a single full-width row */}
            <div className="grid grid-cols-2 gap-2 sm:gap-4">
              <Card className="glass-panel border-white/10">
                <CardContent className="p-2.5 sm:p-4 flex items-center gap-2 sm:gap-3">
                  <Building2 className="w-6 h-6 sm:w-8 sm:h-8 text-cyber-cyan shrink-0" />
                  <div className="min-w-0">
                    <div className="text-lg sm:text-2xl font-bold text-white leading-tight">{summary.total_businesses || 0}</div>
                    <div className="text-[10px] sm:text-xs text-text-muted leading-tight">{t('totalBusinesses')}</div>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-panel border-purple-500/20">
                <CardContent className="p-2.5 sm:p-4 flex items-center gap-2 sm:gap-3">
                  <Package className="w-6 h-6 sm:w-8 sm:h-8 text-purple-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-base sm:text-2xl font-bold text-purple-400 leading-tight truncate">
                      {Math.floor(summary.total_warehouse_used || 0)}/{summary.total_warehouse_capacity || 0}
                    </div>
                    <div className="text-[10px] sm:text-xs text-text-muted leading-tight">{t('totalWarehouse')}</div>
                    {/* Total warehouse color bar */}
                    {(summary.total_warehouse_capacity || 0) > 0 && (() => {
                      const pct = (summary.total_warehouse_used || 0) / (summary.total_warehouse_capacity || 1);
                      const barColor = pct >= 1 ? 'bg-red-500' : pct > 0.8 ? 'bg-red-400' : pct > 0.5 ? 'bg-yellow-400' : 'bg-green-500';
                      return (
                        <div className="w-full bg-gray-700/60 rounded-full h-1.5 mt-1.5 overflow-hidden">
                          <div className={`h-1.5 rounded-full ${barColor}`} style={{ width: `${Math.min(100, pct * 100)}%` }} />
                        </div>
                      );
                    })()}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* === T3 Active Buffs Banner === */}
            {(resourceBuffsData.active || []).length > 0 && (
              <div className="mb-6" data-testid="active-buffs-banner">
                <Card className="glass-panel border-purple-500/30 bg-purple-500/5">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Shield className="w-5 h-5 text-purple-400" />
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">{t('activeBuffsTitle') || 'Активные бафы'}</h3>
                      <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/30 ml-auto">
                        {resourceBuffsData.active.length} / 2
                      </Badge>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {resourceBuffsData.active.map((b) => (
                        <div
                          key={b.resource_id}
                          className="flex items-center gap-3 p-3 rounded-lg bg-white/5 border border-purple-500/20"
                          data-testid={`active-buff-${b.resource_id}`}
                        >
                          <div className="text-2xl">{b.buff_icon}</div>
                          <div className="flex-1 min-w-0">
                            <div className="font-bold text-white text-sm">{tResourceBuff(b.resource_id, 'name', lang) || b.buff_name}</div>
                            <div className="text-xs text-text-muted line-clamp-1">{tResourceBuff(b.resource_id, 'description', lang) || b.buff_description}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-purple-300 font-mono font-bold" data-testid={`buff-time-${b.resource_id}`}>
                              {b.remaining_label || (b.days_remaining != null ? `${b.days_remaining}д` : '—')}
                            </div>
                            <div className="text-[10px] text-text-muted">{t('remainingShort') || 'осталось'}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Businesses List. The Trial Center card now lives INSIDE this
                same grid so it appears ALONGSIDE the real business cards
                (not on its own row above them). It is hidden while the
                tutorial is running and only appears once onboarding is done. */}
            {businesses.length === 0 && (getGameMode() === 'demo' || isTutorialActive) ? (
              <Card className="glass-panel border-white/10">
                <CardContent className="p-12 text-center">
                  <Building2 className="w-16 h-16 text-text-muted mx-auto mb-4" />
                  <h3 className="text-xl font-bold text-white mb-2">{t('noBusinessesYet')}</h3>
                  <p className="text-text-muted mb-4">
                    {t('buyPlotAndBuild')}
                  </p>
                  <Button onClick={() => navigate('/maps')} className="bg-cyber-cyan text-black" data-testid="go-to-maps-btn">
                    {t('goToIsland')}
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {businesses.map((biz) => (
                  <motion.div
                    key={biz.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="group"
                  >
                    <Card className="glass-panel border-white/10 hover:border-cyber-cyan/30 transition-all h-full flex flex-col" data-testid={biz.tutorial ? 'tutorial-business-card' : `business-card-${biz.id}`}>
                      <CardContent className="p-4 flex flex-col flex-1">
                        {/* Header */}
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <div className="text-3xl">{biz.config?.icon || '🏢'}</div>
                            <div>
                              <h3 className="font-bold text-white">
                                {biz.config?.name?.[lang] || biz.config?.name?.en || biz.config?.name?.ru || tBusiness(biz.business_type, lang)}
                              </h3>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge className={TIER_COLORS[biz.config?.tier || 1]}>
                                  {t('tierLabel')} {biz.config?.tier || 1}
                                </Badge>
                                <Badge variant="outline" className="border-white/20">
                                  {biz.level === 0 ? (t('levelLabel') || 'Lv.') + ' 0' : `${t('levelLabel') || 'Lv.'} ${biz.level ?? 1}`}
                                </Badge>
                              </div>
                            </div>
                          </div>
                          
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => {
                              if (isTutorialActive) { blockedTutorialToast(); return; }
                              openDetails(biz);
                            }}
                            disabled={isTutorialActive}
                            className="text-text-muted hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                            data-testid={`business-settings-${biz.id}`}
                          >
                            <Settings2 className="w-4 h-4" />
                          </Button>
                        </div>
                        
                        {/* Durability Bar */}
                        <div className="mb-3">
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-text-muted flex items-center gap-1">
                              <Heart className="w-3 h-3" /> {t('durabilityLabel')}
                            </span>
                            <span className={biz.durability < 30 ? 'text-red-400' : 'text-white'}>
                              {(biz.durability ?? 100).toFixed(1)}%
                            </span>
                          </div>
                          <Progress 
                            value={biz.durability ?? 100} 
                            className="h-2" 
                          />
                          {biz.durability < 30 && (
                            <div className="flex items-center gap-1 text-red-400 text-xs mt-1">
                              <AlertCircle className="w-3 h-3" />
                              {t('needsRepair')}
                            </div>
                          )}
                        </div>
                        
                        {/* Production & Storage Status */}
                        <div className="p-3 bg-white/5 rounded-lg mb-3">
                          {/* Work status badge with reason */}
                          <div className="flex justify-between text-sm mb-2">
                            <span className="text-text-muted">{t('businessStatus')}:</span>
                            {(() => {
                              // Determine work status and reason
                              let status = 'working';
                              let reason = '';
                              
                              // Seized businesses take priority — force-listed by GRAM CITY.
                              if (biz.is_seized) {
                                status = 'seized';
                                reason = '';
                              } else if (biz.on_sale) {
                                status = 'on_sale';
                                reason = '';
                              } else if (biz.durability <= 0) {
                                status = 'stopped';
                                reason = `0% ${t('durability')}`;
                              } else if (biz.work_status === 'idle') {
                                status = 'idle';
                                // Show the ACTUAL idle reason from the backend
                                // (storage_full vs no_resources) instead of always
                                // labelling it "No resources".
                                reason = biz.work_status_reason === 'storage_full'
                                  ? (t('warehouseFull') || 'Склад переполнен')
                                  : (t('noResourcesAvailable') || 'Нет ресурсов');
                              } else if (biz.work_status === 'stopped' || biz.work_status === 'halted') {
                                status = 'stopped';
                                reason = biz.work_status_reason === 'durability_zero'
                                  ? `0% ${t('durability')}`
                                  : (biz.stop_reason || t('stopped'));
                              }
                              
                              return (
                                <div className="flex flex-col items-end">
                                  <Badge data-testid={`work-status-${biz.id}`} className={
                                    status === 'working' 
                                      ? 'bg-green-500/20 text-green-400' 
                                      : status === 'on_sale'
                                      ? 'bg-amber-500/20 text-amber-400'
                                      : status === 'seized'
                                      ? 'bg-red-600/30 text-red-300 border border-red-500/40'
                                      : status === 'idle'
                                      ? 'bg-yellow-500/20 text-yellow-400'
                                      : 'bg-red-500/20 text-red-400'
                                  }>
                                    {status === 'working' ? t('active') : 
                                     status === 'on_sale' ? t('onSale') :
                                     status === 'seized' ? (t('seizedStatus') || 'For sale (Seized)') :
                                     status === 'idle' ? t('idle') || 'Idle' : t('stopped')}
                                  </Badge>
                                  {reason && (
                                    <span className={`text-xs mt-0.5 ${status === 'on_sale' ? 'text-amber-400' : 'text-red-400'}`}>{reason}</span>
                                  )}
                                </div>
                              );
                            })()}
                          </div>
                          
                          {/* Production info - what it produces */}
                          {biz.config?.produces && (
                            <div className="flex justify-between text-sm mb-1">
                              <span className="text-text-muted">{t('produces')}:</span>
                              <span className="text-cyan-300 font-medium flex items-center gap-1">
                                {getResource(biz.config.produces, lang)?.icon || resourceIcons[biz.config.produces] || '📦'} {getResource(biz.config.produces, lang)?.name || biz.config.produces}
                              </span>
                            </div>
                          )}
                          
                          {/* Production amount based on durability + active buffs (TIER3_BUFFS Стахановец / resource Разгон системы) */}
                          {(() => {
                            const base = biz.production?.base_production || biz.config?.base_production || 100;
                            const dur = biz.durability ?? 100;
                            const durMult = dur <= 0 ? 0 : dur < 50 ? 0.8 : 1.0;
                            // user_buff_multiplier = TIER3_BUFFS production-buff (Стахановец) × resource buff (Разгон системы).
                            const buffMult = biz.production?.user_buff_multiplier || 1.0;
                            const dailyBaseRaw = base * durMult;
                            const dailyRaw = dailyBaseRaw * buffMult;
                            const fmt = (v) => (v < 100 ? Number(v.toFixed(2)) : Math.round(v));
                            const hourly = dailyRaw / 24;
                            const hasBuff = Math.abs(buffMult - 1.0) > 0.001;
                            return (
                              <>
                                <div className="flex justify-between text-sm mb-1">
                                  <span className="text-text-muted">{t('outputPerDay') || 'Output/day'}:</span>
                                  <span className="flex items-baseline gap-1.5">
                                    {hasBuff && (
                                      <span className="text-xs line-through text-text-muted/60">{fmt(dailyBaseRaw)}</span>
                                    )}
                                    <span className={`font-mono ${hasBuff ? 'text-emerald-400 font-semibold' : 'text-green-400'}`}>
                                      {fmt(dailyRaw)} {t('unitsShort')}
                                    </span>
                                  </span>
                                </div>
                                <div className="flex justify-between text-sm mb-1">
                                  <span className="text-text-muted">{t('outputPerHour') || 'Output/hour'}:</span>
                                  <span className={`font-mono text-xs ${hasBuff ? 'text-emerald-400/80' : 'text-green-400/70'}`}>
                                    {hourly.toFixed(2)} {t('unitsShort')}
                                  </span>
                                </div>
                              </>
                            );
                          })()}
                          
                          {/* Consumption info - what it consumes */}
                          {(() => {
                            const consumes = biz.production?.consumption_breakdown || biz.config?.consumes;
                            if (!consumes) return null;
                            const entries = Array.isArray(consumes)
                              ? consumes.map(c => [c.resource || c.type, c.amount || c.rate || 0])
                              : Object.entries(consumes);
                            return entries.length > 0 && (
                              <div className="mt-1 space-y-0.5">
                                {entries.map(([res, amt], i) => {
                                  const resInfo = getResource(res, lang);
                                  const colorClass = getConsumeColor(res, amt);
                                  return (
                                    <div key={i} className="flex justify-between text-sm">
                                      <span className={colorClass}>{t('consumes') || 'Consumes'}:</span>
                                      <span className={`font-medium flex items-center gap-1 ${colorClass}`}>
                                        {resInfo?.icon || '📦'} {resInfo?.name || res} {amt} {t('unitsPerDayShort')}
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                            );
                          })()}
                          
                          {/* Storage bar */}
                          {biz.storage_info && biz.storage_info.capacity > 0 && (() => {
                            const pct = biz.storage_info.capacity > 0
                              ? biz.storage_info.used / biz.storage_info.capacity
                              : 0;
                            const barColor = biz.storage_info.is_full ? 'bg-red-500'
                              : pct > 0.8 ? 'bg-red-400'
                              : pct > 0.5 ? 'bg-yellow-400'
                              : 'bg-green-500';
                            const textColor = biz.storage_info.is_full || pct > 0.8 ? 'text-red-400 font-bold'
                              : pct > 0.5 ? 'text-yellow-400'
                              : 'text-green-400';
                            return (
                              <div className="mt-2">
                                <div className="flex justify-between text-xs mb-1">
                                  <span className="text-text-muted flex items-center gap-1">
                                    <Package className="w-3 h-3" /> {t('warehouseLabel')}
                                  </span>
                                  <span className={textColor}>
                                    {biz.storage_info.used}/{biz.storage_info.capacity}
                                  </span>
                                </div>
                                <div className="w-full bg-gray-700/60 rounded-full h-2.5 overflow-hidden">
                                  <div
                                    className={`h-2.5 rounded-full transition-all duration-500 ${barColor}`}
                                    style={{ width: `${Math.min(100, pct * 100)}%` }}
                                  />
                                </div>
                                {biz.storage_info.is_full && (
                                  <div className="text-red-400 text-xs mt-1 flex items-center gap-1">
                                    <AlertCircle className="w-3 h-3" />
                                    {t('warehouseFullMsg')}
                                  </div>
                                )}
                              </div>
                            );
                          })()}
                        </div>
                        
                        {/* Patron Badge — removed; the patron is shown on the change-patron button below */}

                        {/* Actions - NO COLLECT BUTTON, businesses produce resources not TON */}
                        {/* "Выбрать оффер" button (T1/T2 only) → Trade → Offers → Актуальные.
                            Hidden in demo mode (offers are not available). */}
                        {biz.config?.tier !== 3 && getGameMode() !== 'demo' && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="w-full mt-1 border-purple-500/30 text-purple-300 hover:bg-purple-500/10 disabled:opacity-40 disabled:cursor-not-allowed"
                            data-testid={`choose-offer-btn-${biz.id}`}
                            disabled={isTutorialActive}
                            onClick={() => {
                              if (isTutorialActive) { blockedTutorialToast(); return; }
                              try { localStorage.setItem('tradingTab', 'offers'); } catch {}
                              try { localStorage.setItem('offersSubTab', 'actual'); } catch {}
                              navigate('/trading?tab=offers&sub=actual');
                            }}
                          >
                            <Scroll className="w-4 h-4 mr-1" />
                            {t('chooseOfferBtn') || 'Выбрать оффер'}
                          </Button>
                        )}

                        <div className="flex gap-2 mt-2">
                          {biz.level < 10 && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="flex-1 border-blue-500/30 text-blue-400 disabled:opacity-40 disabled:cursor-not-allowed"
                              disabled={isTutorialActive}
                              onClick={async () => {
                                if (isTutorialActive) { blockedTutorialToast(); return; }
                                setSelectedBusiness(biz);
                                setShowUpgradeModal(true);
                                // Fetch upgrade cost data (demo mode → isolated endpoint)
                                try {
                                  const url = getGameMode() === 'demo'
                                    ? `${API}/demo/business/upgrade-cost`
                                    : `${API}/business/${biz.id}/upgrade-cost`;
                                  const res = await fetch(url, {
                                    headers: { 'Authorization': `Bearer ${token}` }
                                  });
                                  if (res.ok) {
                                    const data = await res.json();
                                    setSelectedBusiness(prev => ({ ...prev, upgrade_cost_data: data }));
                                  }
                                } catch (e) { console.error('Failed to fetch upgrade cost', e); }
                              }}
                            >
                              <ArrowUp className="w-4 h-4 mr-1" />
                              {t('upgradeBtn')}
                            </Button>
                          )}
                          
                          {/* P1.6: Only show the Repair button once wear exceeds 1%
                              (durability below 99%). Tiny rounding-level wear no
                              longer surfaces a misleading repair action. */}
                          {(biz.durability ?? 100) < 99 && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="flex-1 border-yellow-500/30 text-yellow-400 disabled:opacity-40 disabled:cursor-not-allowed"
                              disabled={isTutorialActive}
                              onClick={async () => {
                                if (isTutorialActive) { blockedTutorialToast(); return; }
                                setSelectedBusiness(biz);
                                setShowRepairModal(true);
                                // Demo mode: fetch the $CITY repair quote from
                                // the isolated demo endpoint (same shape as real
                                // mode's repair_cost_data) so the modal shows the
                                // cost instead of an endless "Loading…".
                                if (getGameMode() === 'demo') {
                                  try {
                                    const dres = await fetch(`${API}/demo/business/repair-cost`, {
                                      headers: { Authorization: `Bearer ${token}` }
                                    });
                                    if (dres.ok) {
                                      const dq = await dres.json();
                                      if (dq && dq.status === 'ok') {
                                        setSelectedBusiness(prev => ({ ...prev, repair_cost_data: {
                                          cost_city: dq.cost_city,
                                          base_cost_city: dq.base_cost_city,
                                          cost_per_pct: dq.cost_per_pct,
                                          missing_pct: dq.missing_pct,
                                        }}));
                                      }
                                    }
                                  } catch (e) { console.error('Failed to fetch demo repair cost', e); }
                                  return;
                                }
                                // Fetch accurate repair cost from backend
                                try {
                                  const res = await fetch(`${API}/business/${biz.id}`, {
                                    headers: { Authorization: `Bearer ${token}` }
                                  });
                                  if (res.ok) {
                                    const data = await res.json();
                                    setSelectedBusiness(prev => ({ ...prev, repair_cost_data: data.repair }));
                                  }
                                } catch (e) { console.error('Failed to fetch repair cost', e); }
                              }}
                            >
                              <Wrench className="w-4 h-4 mr-1" />
                              {t('repairBtn')}
                            </Button>
                          )}
                          
                          {/* Patron is now set through contracts, not standalone */}
                          {/* Tier 3: buff is only shown in details modal */}
                        </div>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            )}


            {/* Storage/Resources Section */}
            <div className="mt-8">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
                <h2 className="text-xl font-bold text-white flex items-center gap-2 whitespace-nowrap">
                  <Package className="w-5 h-5 text-amber-400 shrink-0" />
                  {t('myResources')}
                </h2>
                <label className="flex items-center gap-2 cursor-pointer self-start sm:self-auto">
                  <input
                    type="checkbox"
                    checked={showAllResources}
                    onChange={(e) => setShowAllResources(e.target.checked)}
                    className="rounded border-gray-600 bg-gray-800 text-amber-500 focus:ring-amber-500"
                  />
                  <span className="text-xs text-text-muted">{t('showAllResources') || 'Показать все'}</span>
                </label>
              </div>

              <Card className="glass-panel border-amber-500/20">
                <CardContent className="p-2 sm:p-4">
                  {(() => {
                    const allResourceIds = getAllResources().map(r => r.id);
                    const displayResources = showAllResources
                      ? allResourceIds.reduce((acc, id) => { acc[id] = resourcesFromBusinesses[id] || 0; return acc; }, {})
                      : Object.fromEntries(Object.entries(resourcesFromBusinesses).filter(([_, v]) => v >= 1));

                    return Object.keys(displayResources).length === 0 ? (
                      <div className="text-center py-6 text-text-muted">
                        <Package className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>{t('noAccumulatedResources')}</p>
                        <p className="text-xs mt-1">{t('businessesProduceAutomatically')}</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-1.5 sm:gap-3">
                        {Object.entries(displayResources).map(([resource, amount]) => {
                          // Tutorial-reward variant lives under `<base>_tutorial`
                          // and behaves like a T3 buff resource (same modal),
                          // but with an extra "not for sale" note.
                          const isTutorialReward = typeof resource === 'string' && resource.endsWith('_tutorial');
                          const baseResourceId = isTutorialReward
                            ? resource.slice(0, -'_tutorial'.length)
                            : resource;
                          const isT3Buff = T3_BUFF_RESOURCE_IDS.includes(baseResourceId);
                          // In demo mode T3 resources are treated as plain
                          // upgrade materials — the buff selector modal must
                          // never open from the resource inventory card.
                          const isDemoT3 = getGameMode() === 'demo' && isT3Buff;
                          const buffInfo = isT3Buff ? (resourceBuffsData.buffs || []).find(b => b.resource_id === baseResourceId) : null;
                          const isActive = (resourceBuffsData.active || []).some(a => a.resource_id === baseResourceId);
                          return (
                            <button
                              type="button"
                              key={resource}
                              onClick={() => {
                                if (!isT3Buff || isDemoT3) return;
                                setSelectedBuffResource({
                                  resource_id: baseResourceId,
                                  quantity: Math.floor(amount > 0 ? amount : 0),
                                  buff: buffInfo,
                                  isActive,
                                  isTutorialReward,
                                });
                                setShowResourceBuffModal(true);
                              }}
                              disabled={!isT3Buff || isDemoT3}
                              data-testid={`resource-card-${resource}`}
                              className={`relative bg-white/5 rounded-lg p-1.5 sm:p-3 text-center border transition-all text-left ${
                                amount > 0 ? 'border-white/10 hover:border-amber-500/30' : 'border-white/5 opacity-50'
                              } ${(isT3Buff && !isDemoT3) ? 'cursor-pointer hover:bg-purple-500/10 hover:border-purple-500/40 legendary-gradient' : 'cursor-default'} ${
                                (isActive && !isDemoT3) ? 'ring-2 ring-purple-400/50' : ''
                              }`}
                            >
                              {/* T3 buff badge in top-right corner. When the
                                  resource is activated as a buff we replace
                                  the «БАФ» text with a tiny green dot — UX
                                  request to keep the card uncluttered while
                                  still signalling «this slot is empowered».
                                  Both indicators are hidden in demo mode. */}
                              {isT3Buff && isActive && !isDemoT3 && (
                                <div className="absolute top-0.5 right-0.5 sm:top-1 sm:right-1 w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full bg-green-400 ring-2 ring-green-400/40 shadow-[0_0_6px_rgba(74,222,128,0.7)]" data-testid={`resource-buff-active-dot-${resource}`} />
                              )}
                              {isT3Buff && !isActive && !isDemoT3 && (
                                <div className="absolute top-0.5 right-0.5 sm:top-1 sm:right-1 text-[8px] sm:text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded px-1 py-0.5 font-bold leading-none" data-testid={`resource-buff-badge-${resource}`}>
                                  {t('buffBadge') || 'БАФ'}
                                </div>
                              )}
                              <div className="text-lg sm:text-2xl mb-0.5 sm:mb-1 mt-1">
                                {getResource(resource, lang)?.icon || '📦'}
                              </div>
                              <div className="text-sm sm:text-lg font-bold text-white text-center">{Math.floor(amount > 0 ? amount : 0)}</div>
                              <div className="text-[10px] sm:text-xs text-text-muted capitalize text-center truncate">{getResource(resource, lang)?.name || resource}</div>
                            </button>
                          );
                        })}
                      </div>
                    );
                  })()}
                </CardContent>
              </Card>
            </div>
          </div>
        </ScrollArea>
      </div>

      {/* Upgrade Modal */}
      <Dialog open={showUpgradeModal} onOpenChange={setShowUpgradeModal}>
        <DialogContent className="bg-void border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <ArrowUp className="w-5 h-5 text-blue-400" />
              {t('upgradeBusinessTitle')}
            </DialogTitle>
          </DialogHeader>
          
          {selectedBusiness && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-white/5 rounded-xl">
                <span className="text-3xl">{selectedBusiness.config?.icon}</span>
                <div>
                  <div className="text-white font-bold">
                    {tBusiness(selectedBusiness.business_type, lang) || selectedBusiness.config?.name?.[lang] || selectedBusiness.config?.name?.en || selectedBusiness.business_type}
                  </div>
                  <div className="text-text-muted text-sm">
                    {t('levelLabel')} {selectedBusiness.level} → {selectedBusiness.level + 1}
                  </div>
                </div>
              </div>
              
              <div className="space-y-2">
                {/* Production */}
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">{t('upgradeProduction')}:</span>
                  <span className="text-green-400">
                    {selectedBusiness.upgrade_cost_data?.current_production || '?'} → {selectedBusiness.upgrade_cost_data?.next_production || '?'} {t('unitsShort') || 'ед.'}
                  </span>
                </div>
                {/* Consumption */}
                {selectedBusiness.upgrade_cost_data?.next_consumption && Object.entries(selectedBusiness.upgrade_cost_data.next_consumption).map(([res, amt]) => (
                  <div key={res} className="flex justify-between text-sm">
                    <span className="text-text-muted">{t('upgradeConsumes')} {getResource(res, lang)?.icon} {tResource(res, lang)}:</span>
                    <span className="text-red-400">{amt} {t('unitsPerDayShort')}</span>
                  </div>
                ))}
                {/* Storage */}
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">{t('upgradeStorage')}:</span>
                  <span className="text-white">
                    {selectedBusiness.upgrade_cost_data?.current_storage || '?'} → {selectedBusiness.upgrade_cost_data?.next_storage || '?'}
                  </span>
                </div>
              </div>
              
              <div className="p-3 bg-blue-500/10 rounded-lg space-y-2">
                <div className="text-xs text-text-muted mb-1">{t('upgradeCostLabel')}:</div>
                <div className="flex justify-between items-center">
                  <span className="text-text-muted text-sm">$CITY:</span>
                  <span className="text-xl font-bold text-blue-400">
                    {formatCity(selectedBusiness.upgrade_cost_data?.cost?.city || 0)} $CITY
                  </span>
                </div>
                {/* Resource requirements */}
                {selectedBusiness.upgrade_cost_data?.resource_meta && (
                  <div className="flex justify-between items-center border-t border-white/10 pt-2">
                    <span className="text-text-muted text-sm">
                      {selectedBusiness.upgrade_cost_data.resource_meta.icon} {tResource(selectedBusiness.upgrade_cost_data.cost?.resource_type, lang) || selectedBusiness.upgrade_cost_data.resource_meta.name_ru}:
                    </span>
                    <span className="font-bold text-amber-400">
                      {selectedBusiness.upgrade_cost_data.cost?.resource_amount || 0} {t('piecesShort')}
                    </span>
                  </div>
                )}
                {/* Level-0 → Level-1: MAIN ACCOUNT unlock note (localized, 9 langs) */}
                {selectedBusiness.upgrade_cost_data?.zero_to_one && (
                  <div className="border-t border-white/10 pt-2 text-center text-sm font-bold text-yellow-400 uppercase tracking-wide" data-testid="zero-unlock-note">
                    {ZERO_UNLOCK_I18N[lang] || ZERO_UNLOCK_I18N.en}
                  </div>
                )}
              </div>
            </div>
          )}
          
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button 
              onClick={handleUpgrade} 
              className="bg-blue-600 w-full"
              disabled={isUpgrading}
            >
              {isUpgrading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              {t('upgradeAction')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Repair Modal */}
      <Dialog open={showRepairModal} onOpenChange={setShowRepairModal}>
        <DialogContent className="bg-void border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Wrench className="w-5 h-5 text-yellow-400" />
              {t('repairBusinessTitle')}
            </DialogTitle>
          </DialogHeader>
          
          {selectedBusiness && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-white/5 rounded-xl">
                <span className="text-3xl">{selectedBusiness.config?.icon}</span>
                <div>
                  <div className="text-white font-bold">
                    {tBusiness(selectedBusiness.business_type, lang) || selectedBusiness.config?.name?.[lang] || selectedBusiness.config?.name?.en || selectedBusiness.business_type}
                  </div>
                  <div className="text-red-400 text-sm">
                    {t('durabilityLabel') || 'Прочность'}: {selectedBusiness.durability?.toFixed(1)}%
                  </div>
                </div>
              </div>
              
              <div className="p-3 bg-yellow-500/10 rounded-lg">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-text-muted">{t('currentDurability')}:</span>
                  <span className="text-yellow-400">{selectedBusiness.durability?.toFixed(1)}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">{t('afterRepair')}:</span>
                  <span className="text-green-400">100%</span>
                </div>
              </div>
              
              <div className="p-3 bg-white/5 rounded-lg">
                <div className="text-xs text-text-muted mb-1">{t('repairCostLabel')}:</div>
                {selectedBusiness.repair_cost_data?.cost_city !== undefined ? (
                  <>
                    {selectedBusiness.repair_cost_data?.base_cost_city !== undefined
                      && Math.abs(selectedBusiness.repair_cost_data.base_cost_city - selectedBusiness.repair_cost_data.cost_city) > 0.005 ? (
                      <div className="flex items-baseline gap-2" data-testid="repair-cost-display">
                        <span className="text-sm line-through text-text-muted/70" data-testid="repair-cost-base">
                          {formatCity(selectedBusiness.repair_cost_data.base_cost_city, selectedBusiness.repair_cost_data.base_cost_city < 100 ? 2 : 0)} $CITY
                        </span>
                        <span className="text-xl font-bold text-green-400" data-testid="repair-cost-final">
                          {formatCity(selectedBusiness.repair_cost_data.cost_city, selectedBusiness.repair_cost_data.cost_city < 100 ? 2 : 0)} $CITY
                        </span>
                      </div>
                    ) : (
                      <div className="text-xl font-bold text-yellow-400" data-testid="repair-cost-display">
                        {formatCity(selectedBusiness.repair_cost_data.cost_city, selectedBusiness.repair_cost_data.cost_city < 100 ? 2 : 0)} $CITY
                      </div>
                    )}
                  </>
                ) : (
                  <span className="text-sm text-text-muted">{t('loading') || 'Loading...'}</span>
                )}
                {selectedBusiness.repair_cost_data?.cost_per_pct !== undefined && (
                  <div className="text-xs text-text-muted mt-1">
                    {selectedBusiness.repair_cost_data.cost_per_pct} $CITY × {selectedBusiness.repair_cost_data.missing_pct}%
                  </div>
                )}
                {Array.isArray(selectedBusiness.repair_cost_data?.applied_buffs)
                  && selectedBusiness.repair_cost_data.applied_buffs.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1" data-testid="repair-applied-buffs">
                    {selectedBusiness.repair_cost_data.applied_buffs.map((b, i) => {
                      const localizedName =
                        tBuff(b.id, 'name', lang) ||
                        tResourceBuff(b.id, 'name', lang) ||
                        tContract(b.id, 'name', lang) ||
                        b.name;
                      return (
                      <span
                        key={b.id || i}
                        className="text-[11px] px-2 py-0.5 rounded bg-cyber-cyan/10 text-cyber-cyan border border-cyber-cyan/20"
                      >
                        {b.icon} {localizedName} −{b.percent}%
                      </span>
                    );})}
                  </div>
                )}
              </div>
              
              <p className="text-xs text-text-muted">
                {t('repairProductionStops')}
              </p>
            </div>
          )}
          
          <DialogFooter className="flex-row gap-2 justify-end">
            <Button 
              onClick={handleRepair} 
              className="bg-yellow-600 w-full"
              disabled={isRepairing}
            >
              {isRepairing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              {t('repairAction') || 'Отремонтировать'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Patron modal removed — vassal/patron selection system has been removed. */}

      {/* Details Modal */}
      <Dialog open={showDetailsModal} onOpenChange={setShowDetailsModal}>
        <DialogContent className="bg-void border-white/10 max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-cyber-cyan" />
              {t('businessDetailsTitle')}
            </DialogTitle>
          </DialogHeader>
          
          {selectedBusiness && (
            <div className="space-y-4">
              <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl">
                <span className="text-4xl">{selectedBusiness.config?.icon}</span>
                <div>
                  <h3 className="text-xl font-bold text-white">
                    {selectedBusiness.config?.name?.[lang] || selectedBusiness.config?.name?.en || selectedBusiness.config?.name?.ru || tBusiness(selectedBusiness.business_type, lang)}
                  </h3>
                  <div className="flex gap-2 mt-1">
                    <Badge className={TIER_COLORS[selectedBusiness.config?.tier || 1]}>
                      {t('tierLabel')} {selectedBusiness.config?.tier}
                    </Badge>
                    <Badge variant="outline">{t('levelLabel') || 'Уровень'} {selectedBusiness.level}</Badge>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="text-xs text-text-muted">{t('durabilityLabel')}</div>
                  <div className="text-lg font-bold text-white">
                    {selectedBusiness.durability?.toFixed(1)}%
                  </div>
                </div>
                <div className="p-3 bg-white/5 rounded-lg">
                  <div className="text-xs text-text-muted">{t('taxLabel') || t('tax') || 'Tax'}</div>
                  {(() => {
                    const baseTaxPct = (selectedBusiness.production?.tax_rate || 0.15) * 100;
                    const reductionPct = (activeBuffMults?.trade_tax_reduction ?? 0) * 100;
                    const feeMult = activeBuffMults?.trade_fee_multiplier ?? 1.0;
                    const reduced = Math.max(0, baseTaxPct - reductionPct);
                    const effectivePct = reduced * feeMult;
                    const hasBuff = Math.abs(effectivePct - baseTaxPct) > 0.0001;
                    if (!hasBuff) {
                      return (
                        <div className="text-lg font-bold text-yellow-400" data-testid="biz-tax-display">
                          {baseTaxPct.toFixed(0)}%
                        </div>
                      );
                    }
                    return (
                      <div className="flex items-baseline gap-2" data-testid="biz-tax-display">
                        <span className="text-sm line-through text-text-muted/60">{baseTaxPct.toFixed(0)}%</span>
                        <span className="text-lg font-bold text-emerald-400">{effectivePct.toFixed(2)}%</span>
                      </div>
                    );
                  })()}
                </div>
                <div className="p-3 bg-white/5 rounded-lg col-span-2">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-xs text-text-muted">{t('warehouseLabel')}</div>
                      <div className="text-lg font-bold text-white">
                        {selectedBusiness.storage_info?.used || 0} / {selectedBusiness.storage_info?.capacity || selectedBusiness.storage?.capacity || 0}
                      </div>
                    </div>
                    <SkinPicker
                      business={selectedBusiness}
                      lang={lang}
                      token={token}
                      onApplied={(g) => {
                        setSelectedBusiness((b) => b ? { ...b, skin_group: g } : b);
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* Patron block intentionally removed per UX request — patron is set/changed
                  from the business card "Choose Patron" button, no need to repeat in details. */}

              {/* Bank owner: open commission settings in a dedicated modal (Block A) */}
              {isBankBusiness(selectedBusiness) && (
                <Button
                  variant="outline"
                  size="sm"
                  data-testid="open-bank-settings-btn"
                  className="w-full border-cyber-cyan/30 text-cyber-cyan hover:bg-cyber-cyan/10"
                  onClick={() => {
                    loadBankSettings(selectedBusiness.id);
                    setShowBankSettingsModal(true);
                  }}
                >
                  <Settings2 className="w-4 h-4 mr-2" />
                  {t('bankCommissionSettingsBtn') || 'Настройки комиссий'}
                </Button>
              )}

              {/* (Vassal/buff system removed) — "Баф для вассалов" block and
                  "Посмотреть вассалов" button were removed from T3 details. */}

              {/* Tier 3: Active alliance offers shortcut */}
              {(selectedBusiness.config?.tier || selectedBusiness.tier || 1) === 3 && (
                <>
                  {/* Active contracts → navigate to Trading → Offers → Active */}
                  <Button
                    variant="outline"
                    size="sm"
                    data-testid={`active-contracts-link-${selectedBusiness.id}`}
                    className="w-full border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
                    onClick={() => {
                      setShowDetailsModal(false);
                      try { localStorage.setItem('tradingTab', 'offers'); } catch {}
                      try { localStorage.setItem('offersSubTab', 'active'); } catch {}
                      navigate('/trading?tab=offers&sub=active');
                    }}
                  >
                    <Scroll className="w-4 h-4 mr-2" />
                    Активные контракты {(selectedBusiness.active_alliances_count ?? 0)}/{selectedBusiness.max_alliances ?? 25}
                  </Button>
                </>
              )}

              {/* Vassal contract info */}
              {selectedBusiness.contract_id && selectedBusiness.contract_buff_data && (
                <div className="p-3 bg-purple-500/10 rounded-lg border border-purple-500/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Scroll className="w-4 h-4 text-purple-400" />
                    <span className="text-purple-400 font-medium text-sm">Активный контракт</span>
                  </div>
                  {(() => {
                    const contractInfo = contracts.as_vassal.find(c => c.id === selectedBusiness.contract_id);
                    const buff = selectedBusiness.contract_buff_data || {};
                    const buffDesc = buff.description || buff.desc || '';
                    const buffEffect = buff.effect || {};
                    // Human-friendly effect summary for what the vassal RECEIVES
                    const effectLabels = {
                      production_multiplier: (v) => `+${Math.round((Number(v) - 1) * 100)}% к производству`,
                      consumption_multiplier: (v) => `−${Math.round((1 - Number(v)) * 100)}% потребление сырья`,
                      storage_multiplier: (v) => `+${Math.round((Number(v) - 1) * 100)}% к складу`,
                      withdrawal_fee_multiplier: (v) => `−${Math.round((1 - Number(v)) * 100)}% комиссии вывода`,
                      trade_fee_multiplier: (v) => `−${Math.round((1 - Number(v)) * 100)}% торговой комиссии`,
                      trade_tax_reduction: (v) => `−${(Number(v) * 100).toFixed(1)} п.п. налога продажи`,
                      repair_cost_multiplier: (v) => `−${Math.round((1 - Number(v)) * 100)}% стоимости ремонта`,
                      wear_reduction: (v) => `−${Math.round((1 - Number(v)) * 100)}% износа`,
                      free_cycle_chance: (v) => `${(Number(v) * 100).toFixed(1)}% шанс бесплатного цикла`,
                      crit_chance_bonus: (v) => `+${(Number(v) * 100).toFixed(1)}% шанс крита`,
                      trade_slots_bonus: (v) => `+${Math.round(Number(v))} торговый слот`,
                    };
                    const effectSummary = effectLabels[buffEffect.type] ? effectLabels[buffEffect.type](buffEffect.value) : null;
                    return contractInfo ? (
                      <div className="text-xs space-y-1.5">
                        <p className="text-white font-medium">{CONTRACT_TYPES[contractInfo.type]?.icon} {CONTRACT_TYPES[contractInfo.type]?.name}</p>
                        <div className="text-text-muted">
                          <span className="text-red-300">Вы отдаёте: </span>
                          {CONTRACT_TYPES[contractInfo.type]?.vassal_note || CONTRACT_TYPES[contractInfo.type]?.description}
                        </div>
                        <div className="text-text-muted">
                          <span className="text-emerald-300">Вы получаете: </span>
                          <span className="text-yellow-300 font-medium">{buff.icon} {buff.name}</span>
                          {effectSummary && (
                            <span className="text-emerald-300"> — {effectSummary}</span>
                          )}
                        </div>
                        {buffDesc && (
                          <p className="text-text-muted text-[11px] italic">«{buffDesc}»</p>
                        )}
                        <p className="text-text-muted">Патрон: {contractInfo.patron_username}</p>
                      </div>
                    ) : (
                      <div className="text-xs space-y-1">
                        <div className="text-emerald-300">
                          Вы получаете: <span className="text-yellow-300 font-medium">{buff.icon} {buff.name}</span>
                          {effectSummary && <span> — {effectSummary}</span>}
                        </div>
                        {buffDesc && <p className="text-text-muted text-[11px] italic">«{buffDesc}»</p>}
                      </div>
                    );
                  })()}
                </div>
              )}
              
              <div className="text-xs text-text-muted">
                ID: {selectedBusiness.id}
              </div>
              
              {/* Кнопка продажи или снятия с продажи — скрыто в демо-режиме */}
              {getGameMode() !== 'demo' && (selectedBusiness.on_sale ? (
                <Button 
                  onClick={handleCancelSale}
                  data-testid="cancel-sale-btn"
                  disabled={isCancelingSale}
                  className="w-full bg-green-500/20 text-green-400 hover:bg-green-500/30 border border-green-500/30"
                >
                  {isCancelingSale ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-400 mr-2"></div>
                      {t('cancellingSaleStatus')}
                    </>
                  ) : (
                    <>
                      <Tag className="w-4 h-4 mr-2" />
                      {t('cancelSaleAction')}
                    </>
                  )}
                </Button>
              ) : (
                <Button 
                  onClick={() => {
                    setShowDetailsModal(false);
                    setSellPrice('');
                    setSellTaxInfo(null);
                    setShowSellModal(true);
                    // P1.7: prefetch the minimum price (returns min_price + min_price_city)
                    // so the user sees the minimum upfront in both TON and $CITY.
                    calculateSaleTax(0);
                  }}
                  className="w-full bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30"
                >
                  <Tag className="w-4 h-4 mr-2" />
                  {t('listForSaleAction')}
                </Button>
              ))}
            </div>
          )}
          
        </DialogContent>
      </Dialog>

      {/* Bank commission settings modal (Block A) */}
      <Dialog open={showBankSettingsModal} onOpenChange={setShowBankSettingsModal}>
        <DialogContent className="bg-void border-cyber-cyan/20 max-w-md" data-testid="bank-settings-modal">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Settings2 className="w-5 h-5 text-cyber-cyan" />
              {t('bankCommissionSettingsTitle') || 'Настройки комиссий банка'}
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              {t('bankCommissionSettingsDesc') || 'Задайте проценты для своего банка. Только целые числа.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label className="text-xs text-text-muted">
                {t('bankInterestLabel') || 'Процент по кредиту (макс. 40%)'}
              </Label>
              <div className="relative mt-1">
                <Input
                  type="text"
                  inputMode="numeric"
                  data-testid="bank-interest-input"
                  className="bg-white/5 border-white/10 text-white pr-8 no-spinner"
                  placeholder="0"
                  value={bankSettings.interest_rate_percent}
                  onChange={(e) => setBankSettings((s) => ({ ...s, interest_rate_percent: sanitizeIntField(e.target.value, 40) }))}
                  disabled={bankSettingsLoading || bankSettingsSaving}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">%</span>
              </div>
            </div>

            <div>
              <Label className="text-xs text-text-muted">
                {t('bankInstantFeeLabel') || 'Комиссия за мгновенный вывод (макс. 5%)'}
              </Label>
              <div className="relative mt-1">
                <Input
                  type="text"
                  inputMode="numeric"
                  data-testid="bank-instant-fee-input"
                  className="bg-white/5 border-white/10 text-white pr-8 no-spinner"
                  placeholder="0"
                  value={bankSettings.instant_fee_percent}
                  onChange={(e) => setBankSettings((s) => ({ ...s, instant_fee_percent: sanitizeIntField(e.target.value, 5) }))}
                  disabled={bankSettingsLoading || bankSettingsSaving}
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted text-sm">%</span>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              onClick={saveBankSettings}
              disabled={bankSettingsLoading || bankSettingsSaving}
              data-testid="bank-settings-save-btn"
              className="w-full bg-cyber-cyan/20 text-cyber-cyan hover:bg-cyber-cyan/30 border border-cyber-cyan/30"
            >
              {bankSettingsSaving ? (t('savingStatus') || 'Сохранение...') : (t('saveBankSettingsBtn') || 'Сохранить настройки')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>


      {/* Sell Modal */}
      <Dialog open={showSellModal} onOpenChange={setShowSellModal}>
        <DialogContent className="bg-void border-red-500/20">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-white">
              <Tag className="w-5 h-5 text-red-400" />
              {t('sellBusinessTitle') || 'Sell business'}
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              {t('sellBusinessDesc') || 'The business will be sold together with the land. Set your price.'}
            </DialogDescription>
          </DialogHeader>
          
          {selectedBusiness && (() => {
            // Find plot for this business
            const businessPlot = myPlots.find(p => p.id === selectedBusiness.plot_id);
            const cityName = businessPlot?.island_id === 'ton_island' ? 'GRAM Island' : 
              (typeof businessPlot?.city_name === 'object' ? (businessPlot?.city_name?.ru || businessPlot?.city_name?.en || 'GRAM Island') : (businessPlot?.city_name || 'GRAM Island'));
            const plotPrice = businessPlot?.price || 0;
            const businessCost = selectedBusiness.base_cost_ton || selectedBusiness.config?.base_cost_ton || 0;
            const totalInvested = plotPrice + businessCost;
            const coordinates = selectedBusiness.x !== undefined && selectedBusiness.y !== undefined 
              ? `[${selectedBusiness.x}, ${selectedBusiness.y}]` 
              : (businessPlot ? `[${businessPlot.x}, ${businessPlot.y}]` : 'Неизвестно');
            const businessName = selectedBusiness.config?.name?.[lang] || selectedBusiness.config?.name?.en || selectedBusiness.config?.name?.ru || tBusiness(selectedBusiness.business_type, lang);
            
            return (
            <div className="space-y-4">
              <div className="flex items-center gap-4 p-4 bg-white/5 rounded-xl">
                <span className="text-4xl">{selectedBusiness.config?.icon}</span>
                <div>
                  <h3 className="text-lg font-bold text-white">
                    {businessName}
                  </h3>
                  <Badge variant="outline">{t('levelLabel')} {selectedBusiness.level}</Badge>
                </div>
              </div>
              
              {/* Detailed plot and business info like in MarketplacePage */}
              <div className="p-3 bg-white/5 rounded-lg border border-white/10 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">{t('cityFieldLabel') || t('city') || 'City'}:</span>
                  <span className="text-amber-400">{cityName}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">{t('coordinatesLabel')}:</span>
                  <span className="text-white">{coordinates}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">{t('bizOnPlotLabel') || t('business') || 'Business'}:</span>
                  <span className="text-green-400">{businessName}</span>
                </div>
                {businessCost > 0 && (
                  <div className="flex justify-between text-sm">
                    <span className="text-text-muted">{t('bizCostLabel') || 'Business cost'}:</span>
                    <span className="text-white font-mono">{formatCity(tonToCity(businessCost))} $CITY</span>
                  </div>
                )}
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">{t('produces')}:</span>
                  <span className="text-cyan-400">
                    {getResource(selectedBusiness.config?.produces, lang)?.icon} {getResource(selectedBusiness.config?.produces, lang)?.name || selectedBusiness.config?.produces}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-text-muted">{t('outputPerDay')}:</span>
                  <span className="text-green-400 font-mono">
                    {(() => { const base = selectedBusiness.production?.base_production || 100; const dur = selectedBusiness.durability ?? 100; const m = dur <= 0 ? 0 : dur < 50 ? 0.8 : 1.0; return Math.round(base * m); })()} {t('unitsShort')}
                  </span>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label className="text-white">{t('salePriceLabel') || 'Sale price'} ($CITY)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.1"
                  value={sellPrice}
                  onChange={(e) => {
                    setSellPrice(e.target.value);
                    if (e.target.value) calculateSaleTax(e.target.value);
                  }}
                  placeholder={t('salePricePlaceholder') || 'e.g. 10.00'}
                  className="bg-white/5 border-white/10"
                />
                {/* P1.7: minimum price shown in BOTH $CITY and TON (1 TON = 1000 $CITY) */}
                {sellTaxInfo?.min_price != null && (() => {
                  const priceNum = parseFloat(sellPrice) || 0;
                  const belowMin = priceNum > 0 && priceNum < (sellTaxInfo.min_price_city || 0);
                  return (
                    <div
                      className={`text-xs ${belowMin ? 'text-red-400' : 'text-amber-400'}`}
                      data-testid="sell-min-price-hint"
                    >
                      {belowMin
                        ? (lang === 'ru'
                            ? `Цена ниже минимума: ${formatCity(sellTaxInfo.min_price_city)} $CITY (${sellTaxInfo.min_price.toFixed(2)} TON)`
                            : `Price below minimum: ${formatCity(sellTaxInfo.min_price_city)} $CITY (${sellTaxInfo.min_price.toFixed(2)} TON)`)
                        : `${(lang === 'ru' ? 'Минимальная цена' : 'Minimum price')}: ${formatCity(sellTaxInfo.min_price_city)} $CITY (${sellTaxInfo.min_price.toFixed(2)} TON)`}
                    </div>
                  );
                })()}
              </div>
              
              {sellTaxInfo && sellPrice && parseFloat(sellPrice) > 0 && (
                <div className="p-4 bg-white/5 rounded-xl space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-text-muted">Цена продажи:</span>
                    <span className="text-white font-mono">{formatCity(sellTaxInfo.price)} $CITY</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-text-muted">Налог ({sellTaxInfo.tax_rate_percent}, Tier {sellTaxInfo.tier || 1}):</span>
                    <span className="text-red-400 font-mono">−{formatCity(sellTaxInfo.tax_amount)} $CITY</span>
                  </div>
                  <div className="h-px bg-white/10 my-1" />
                  <div className="flex justify-between font-bold">
                    <span className="text-white">Чистая прибыль:</span>
                    <span className="text-green-400 text-lg font-mono">{formatCity(sellTaxInfo.seller_receives)} $CITY</span>
                  </div>
                </div>
              )}
            </div>
            );
          })()}
          
          <DialogFooter className="flex-col sm:flex-row gap-2">
            <Button 
              onClick={handleSellBusiness}
              disabled={
                !sellPrice ||
                isSelling ||
                (sellTaxInfo?.min_price_city != null &&
                  parseFloat(sellPrice) < sellTaxInfo.min_price_city)
              }
              data-testid="sell-business-submit-btn"
              className="bg-red-500 text-white hover:bg-red-600 w-full sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSelling ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Tag className="w-4 h-4 mr-2" />}
              {t('listForSaleAction') || 'List for sale'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Buff selection modal & Vassals modal removed — vassal/buff system has been removed. */}

      {/* Contract Proposal Modal */}
      <Dialog open={showContractProposalModal} onOpenChange={setShowContractProposalModal}>
        <DialogContent className="bg-void border-purple-500/30 max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Scroll className="w-5 h-5 text-purple-400" />
              Заключить альянс
            </DialogTitle>
            <DialogDescription className="text-text-muted">
              {contractTarget && `Вассал: ${contractTarget.owner_username} · ${contractTarget.business_icon} ${contractTarget.business_name}`}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Contract type selection */}
            <div>
              <Label className="text-white mb-2 block">Тип контракта</Label>
              <div className="space-y-2">
                {Object.entries(CONTRACT_TYPES).map(([id, ct]) => (
                  <button key={id} onClick={() => setProposalType(id)}
                    data-testid={`contract-type-${id}`}
                    className={`w-full text-left p-3 rounded-lg border transition-all ${
                      proposalType === id
                        ? `${ct.border} ${ct.bg}`
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }`}>
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{ct.icon}</span>
                      <div className="flex-1">
                        <div className={`text-sm font-bold ${proposalType === id ? ct.color : 'text-white'}`}>{ct.name}</div>
                        <div className="text-xs text-text-muted">{ct.description}</div>
                        {proposalType === id && (
                          <div className="flex gap-3 mt-1">
                            <span className="text-[10px] text-green-400">Вассал: {ct.vassal_note}</span>
                            <span className="text-[10px] text-purple-400">Патрон: {ct.patron_note}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* V2: Duration selection */}
            <div>
              <Label className="text-white mb-2 block">Длительность контракта</Label>
              <div className="flex gap-2">
                {[7, 14, 30, 60, 90].map(d => (
                  <button key={d} onClick={() => setProposalDuration(d)}
                    className={`flex-1 py-2 text-sm rounded-lg border transition-all ${
                      proposalDuration === d
                        ? 'border-purple-500 bg-purple-500/20 text-purple-300 font-bold'
                        : 'border-white/10 bg-white/5 text-text-muted hover:border-white/20'
                    }`}>
                    {d} дн.
                  </button>
                ))}
              </div>
              <div className="flex items-center gap-2 mt-2">
                <input type="checkbox" checked={proposalAutoRenew}
                  onChange={e => setProposalAutoRenew(e.target.checked)}
                  className="rounded border-gray-600 bg-gray-800 text-purple-500" />
                <span className="text-xs text-text-muted">Автопродление после истечения</span>
              </div>
            </div>

            {/* Buff selection */}
            <div>
              <Label className="text-white mb-2 block">Баф для вассала</Label>
              <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
                {availableBuffs.length === 0 ? (
                  <p className="text-xs text-text-muted">Загрузка бафов...</p>
                ) : availableBuffs.map(buff => (
                  <button key={buff.id} onClick={() => setProposalBuff(buff.id)}
                    data-testid={`proposal-buff-${buff.id}`}
                    className={`w-full text-left p-2.5 rounded-lg border transition-all ${
                      proposalBuff === buff.id
                        ? 'border-yellow-500 bg-yellow-500/15'
                        : 'border-white/10 bg-white/5 hover:border-yellow-500/40'
                    }`}>
                    <div className="flex items-center gap-2">
                      <span>{buff.icon}</span>
                      <div>
                        <div className="text-xs font-bold text-white">{buff.name}</div>
                        <div className="text-xs text-text-muted">{buff.description}</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* V2: Contract summary */}
            {proposalBuff && (
              <div className="p-3 rounded-lg bg-white/5 border border-white/10">
                <div className="text-xs font-medium text-white mb-1">Итого по контракту:</div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="text-text-muted">Тип: <span className="text-white">{CONTRACT_TYPES[proposalType]?.name}</span></div>
                  <div className="text-text-muted">Срок: <span className="text-white">{proposalDuration} дней</span></div>
                  <div className="text-text-muted col-span-2">Штраф при досрочном расторжении: <span className="text-red-400 font-mono">{(proposalDuration * 100).toLocaleString()} $CITY</span></div>
                </div>
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowContractProposalModal(false)} className="border-white/10">
              Отмена
            </Button>
            <Button onClick={handleProposeContract} disabled={isProposing || !proposalBuff}
              className="bg-purple-600 hover:bg-purple-700" data-testid="submit-contract-proposal">
              {isProposing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Scroll className="w-4 h-4 mr-2" />}
              Предложить альянс
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* === T3 Resource Buff Activation Modal === */}
      {/* Safety net: never render the buff modal in demo mode — T3 resources
          in the sandbox are plain upgrade materials, not buff activators. */}
      <Dialog open={showResourceBuffModal && getGameMode() !== 'demo'} onOpenChange={setShowResourceBuffModal}>
        <DialogContent className="glass-panel border-purple-500/30 bg-void max-w-md !rounded-2xl" data-testid="resource-buff-modal">
          <DialogHeader>
            <DialogTitle className="text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-purple-400" />
              {tResourceBuff(selectedBuffResource?.resource_id, 'name', lang) || selectedBuffResource?.buff?.buff_name || tResource(selectedBuffResource?.resource_id, lang)}
            </DialogTitle>
          </DialogHeader>

          {selectedBuffResource && selectedBuffResource.buff && (() => {
            const b = selectedBuffResource.buff;
            const qty = selectedBuffResource.quantity || 0;
            const isActive = selectedBuffResource.isActive;
            const activeCount = (resourceBuffsData.active || []).length;
            const limitReached = activeCount >= 2 && !isActive;
            // v2.1.5: cannot activate without an active (non-tutorial) business
            const noRealBusiness = (businesses || []).filter((bz) => !bz.tutorial).length === 0;
            const canActivate = qty >= 1 && !isActive && !limitReached && !noRealBusiness;
            const localizedName = tResourceBuff(selectedBuffResource.resource_id, 'name', lang) || b.buff_name;
            const localizedDescription = tResourceBuff(selectedBuffResource.resource_id, 'description', lang) || b.buff_description;
            const localizedResourceName = tResource(selectedBuffResource.resource_id, lang) || b.resource_name;

            return (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-purple-500/10 border border-purple-500/30">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="text-4xl">{b.buff_icon}</div>
                    <div>
                      <div className="font-bold text-white text-lg">{localizedName}</div>
                      <div className="text-xs text-purple-300">{localizedResourceName} · {qty} {t('unitsShort')} {t('inStockLabel') || ''}</div>
                    </div>
                  </div>
                  <div className="text-sm text-white/90 mt-2">{localizedDescription}</div>
                  <div className="mt-3 flex items-center justify-between text-xs">
                    <span className="text-text-muted">{t('durationLabel') || 'Duration'}:</span>
                    <span className="font-bold text-purple-300">{b.duration_days} {t('daysShort')} ({b.duration_days * 24}{t('hoursShort') || 'h'})</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-xs">
                    <span className="text-text-muted">{t('expenseLabel')}:</span>
                    <span className="font-bold text-amber-300">{t('oneUnitOnce')}</span>
                  </div>
                </div>

                <div className="text-xs text-text-muted space-y-1">
                  <div>• {t('max2BuffsActive').replace('{n}', '2')}</div>
                  <div>• {t('sameBuffsBlocked')}</div>
                  <div>• {t('currentlyActiveLabel')}: <b className="text-white">{activeCount}</b> / 2.</div>
                </div>

                {isActive && (
                  <div className="text-xs text-green-400 p-2 rounded bg-green-500/10 border border-green-500/30">
                    {t('alreadyActivatedMsg')}
                  </div>
                )}
                {limitReached && (
                  <div className="text-xs text-red-400 p-2 rounded bg-red-500/10 border border-red-500/30">
                    {t('limitReachedWarning')}
                  </div>
                )}
                {qty < 1 && !isActive && (
                  <div className="text-xs text-yellow-400 p-2 rounded bg-yellow-500/10 border border-yellow-500/30">
                    {t('noResourceInStockMsg')}
                  </div>
                )}
                {noRealBusiness && (
                  <div
                    className="text-xs text-amber-300 p-2 rounded bg-amber-500/10 border border-amber-500/30"
                    data-testid="buff-needs-business-warning"
                  >
                    {t('tutorial_buff_needs_business') || 'Для активации T3-баффа требуется активный бизнес. Приобретите свой первый участок, чтобы применить этот ускоритель.'}
                  </div>
                )}
                {selectedBuffResource?.isTutorialReward && (
                  <div
                    className="text-xs text-amber-300 p-2 rounded bg-amber-500/10 border border-amber-500/30"
                    data-testid="tutorial-reward-not-for-sale"
                  >
                    {t('tutorialResourceNotForSale') || 'Этот ресурс получен за обучение — его нельзя выставить на продажу, но вы можете активировать его как баф.'}
                  </div>
                )}

                <DialogFooter className="flex flex-col gap-2">
                  <Button
                    onClick={() => handleActivateResourceBuff(selectedBuffResource.resource_id)}
                    disabled={!canActivate || isActivatingBuff}
                    className="bg-purple-600 hover:bg-purple-700 disabled:opacity-40 w-full"
                    data-testid="resource-buff-activate"
                  >
                    {isActivatingBuff ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Shield className="w-4 h-4 mr-2" />}
                    {t('activateBtn')} ({b.duration_days}{t('daysShort')})
                  </Button>
                </DialogFooter>
              </div>
            );
          })()}
        </DialogContent>
      </Dialog>
    </div>
  );
}
