/**
 * Static metadata for the 7 Tier-3 resources awarded as the tutorial-completion
 * (or tutorial-skip) reward. This file is the FRONTEND MIRROR of
 * `RESOURCE_BUFFS` in `/app/backend/routes/buffs.py` — the SAME buff card the
 * user sees when they click a T3 resource in "My Resources" (see picture 2 in
 * the bug report). Icons and effect descriptions MUST match RESOURCE_BUFFS.
 *
 * Whenever `RESOURCE_BUFFS` changes on the backend, this table must be
 * updated in lockstep to avoid the mismatch bug reported by the user.
 *
 * For every resource we provide:
 *   - icon: emoji used in selects / cards (kept in sync with backend)
 *   - fallback: bonus description per language (mirror of backend `description`)
 *
 * Picking a resource auto-activates the linked buff on the user's *first*
 * real business purchase (backend hook in `routes/tutorial.py`).
 */
export const T3_REWARD_INFO = {
  neuro_core: {
    days: 7,
    icon: '🔮',
    fallback: {
      en: '+8% production for all businesses',
      ru: '+8% к производству всех бизнесов',
      es: '+8% producción de todos los negocios',
      zh: '所有业务产量 +8%',
      fr: '+8% de production pour toutes les entreprises',
      de: '+8% Produktion für alle Geschäfte',
      ja: '全ビジネスの生産量 +8%',
      ko: '모든 비즈니스 생산량 +8%',
      id: '+8% produksi semua bisnis',
    },
  },
  gold_bill: {
    days: 7,
    icon: '📜',
    fallback: {
      en: '−20% repair cost',
      ru: '−20% к стоимости ремонта',
      es: '−20% costo de reparación',
      zh: '维修成本 −20%',
      fr: '−20% sur le coût de réparation',
      de: '−20% Reparaturkosten',
      ja: '修理コスト −20%',
      ko: '수리 비용 −20%',
      id: '−20% biaya perbaikan',
    },
  },
  license_token: {
    days: 5,
    icon: '🎫',
    fallback: {
      en: '−15% trading commission',
      ru: '−15% к торговой комиссии',
      es: '−15% comisión de trading',
      zh: '交易佣金 −15%',
      fr: '−15% de commission de trading',
      de: '−15% Handelsprovision',
      ja: '取引手数料 −15%',
      ko: '거래 수수료 −15%',
      id: '−15% komisi perdagangan',
    },
  },
  luck_chip: {
    days: 5,
    icon: '🎲',
    fallback: {
      en: '+5% chance for ×2 production',
      ru: '+5% шанс ×2 производства',
      es: '+5% probabilidad de producción ×2',
      zh: '+5% 概率触发 ×2 生产',
      fr: '+5% de chance de production ×2',
      de: '+5% Chance auf ×2 Produktion',
      ja: '生産量×2のチャンス +5%',
      ko: '×2 생산 확률 +5%',
      id: '+5% peluang produksi ×2',
    },
  },
  war_protocol: {
    days: 7,
    icon: '⚔️',
    fallback: {
      en: '−25% building wear rate',
      ru: '−25% к скорости износа зданий',
      es: '−25% velocidad de desgaste',
      zh: '建筑磨损速度 −25%',
      fr: '−25% sur l\'usure des bâtiments',
      de: '−25% Verschleißrate',
      ja: '建物の摩耗速度 −25%',
      ko: '건물 마모 속도 −25%',
      id: '−25% laju keausan bangunan',
    },
  },
  bio_module: {
    days: 5,
    icon: '🧬',
    fallback: {
      en: '−10% resource consumption',
      ru: '−10% к потреблению ресурсов',
      es: '−10% consumo de recursos',
      zh: '资源消耗 −10%',
      fr: '−10% de consommation de ressources',
      de: '−10% Ressourcenverbrauch',
      ja: 'リソース消費 −10%',
      ko: '자원 소비 −10%',
      id: '−10% konsumsi sumber daya',
    },
  },
  gateway_code: {
    days: 7,
    icon: '🔑',
    fallback: {
      en: '−25% withdrawal fee',
      ru: '−25% к комиссии на вывод',
      es: '−25% comisión de retiro',
      zh: '提现手续费 −25%',
      fr: '−25% sur les frais de retrait',
      de: '−25% Auszahlungsgebühr',
      ja: '出金手数料 −25%',
      ko: '출금 수수료 −25%',
      id: '−25% biaya penarikan',
    },
  },
};

export const T3_REWARD_OPTIONS = Object.keys(T3_REWARD_INFO);

/** Return the localized bonus description for a T3 resource id. */
export function getT3BonusDescription(resourceId, lang = 'en') {
  const info = T3_REWARD_INFO[resourceId];
  if (!info) return '';
  return info.fallback[lang] || info.fallback.en || info.fallback.ru || '';
}

/** How many days the bonus lasts (mirror of RESOURCE_BUFFS.duration_days). */
export function getT3Days(resourceId) {
  return T3_REWARD_INFO[resourceId]?.days || 7;
}

export function getT3Icon(resourceId) {
  return T3_REWARD_INFO[resourceId]?.icon || '🎁';
}
