"""Effects the wiki explains (tables [[table:t3buffs]], [[table:boosters]], [[table:patrons]]): names and what they give,
9 languages. Taken from the game's own texts (frontend lib/translationsExtra.js, translationsMore.js, resourceConfig.js)
so the wiki says exactly what the game shows. Numbers (durations) come from the live configs at show time."""

RES = {
 "energy": {
  "ru": "Энергия",
  "en": "Energy",
  "es": "Energía",
  "zh": "能源",
  "fr": "Énergie",
  "de": "Energie",
  "ja": "エネルギー",
  "ko": "에너지",
  "id": "Energi"
 },
 "scrap": {
  "ru": "Металл",
  "en": "Metal",
  "es": "Metal",
  "zh": "金属",
  "fr": "Métal",
  "de": "Metall",
  "ja": "金属",
  "ko": "금속",
  "id": "Logam"
 },
 "quartz": {
  "ru": "Кварц",
  "en": "Quartz",
  "es": "Cuarzo",
  "zh": "石英",
  "fr": "Quartz",
  "de": "Quarz",
  "ja": "クォーツ",
  "ko": "석영",
  "id": "Kuarsa"
 },
 "cu": {
  "ru": "Вычисления",
  "en": "Computing",
  "es": "Cómputo",
  "zh": "算力",
  "fr": "Calcul",
  "de": "Berechnung",
  "ja": "計算",
  "ko": "컴퓨팅",
  "id": "Komputasi"
 },
 "traffic": {
  "ru": "Трафик",
  "en": "Traffic",
  "es": "Tráfico",
  "zh": "流量",
  "fr": "Trafic",
  "de": "Verkehr",
  "ja": "トラフィック",
  "ko": "트래픽",
  "id": "Trafik"
 },
 "cooling": {
  "ru": "Холод",
  "en": "Cooling",
  "es": "Frío",
  "zh": "冷却",
  "fr": "Froid",
  "de": "Kühlung",
  "ja": "冷却",
  "ko": "냉각",
  "id": "Pendingin"
 },
 "biomass": {
  "ru": "Биомасса",
  "en": "Biomass",
  "es": "Biomasa",
  "zh": "生物质",
  "fr": "Biomasse",
  "de": "Biomasse",
  "ja": "バイオマス",
  "ko": "바이오매스",
  "id": "Biomassa"
 },
 "chips": {
  "ru": "Чип",
  "en": "Chip",
  "es": "Chip",
  "zh": "芯片",
  "fr": "Puce",
  "de": "Chip",
  "ja": "チップ",
  "ko": "칩",
  "id": "Chip"
 },
 "neurocode": {
  "ru": "ИИ-Модель",
  "en": "AI Model",
  "es": "Modelo IA",
  "zh": "AI模型",
  "fr": "Modèle IA",
  "de": "KI-Modell",
  "ja": "AIモデル",
  "ko": "AI 모델",
  "id": "Model AI"
 },
 "nft": {
  "ru": "NFT-Арт",
  "en": "NFT Art",
  "es": "Arte NFT",
  "zh": "NFT艺术",
  "fr": "Art NFT",
  "de": "NFT-Kunst",
  "ja": "NFTアート",
  "ko": "NFT 아트",
  "id": "Seni NFT"
 },
 "vr_experience": {
  "ru": "VR-Контент",
  "en": "VR Content",
  "es": "Contenido VR",
  "zh": "VR内容",
  "fr": "Contenu VR",
  "de": "VR-Inhalt",
  "ja": "VRコンテンツ",
  "ko": "VR 콘텐츠",
  "id": "Konten VR"
 },
 "logistics": {
  "ru": "Топливо",
  "en": "Fuel",
  "es": "Combustible",
  "zh": "燃料",
  "fr": "Carburant",
  "de": "Treibstoff",
  "ja": "燃料",
  "ko": "연료",
  "id": "Bahan Bakar"
 },
 "profit_ton": {
  "ru": "Кибер-фуд",
  "en": "Cyber Food",
  "es": "Ciber-comida",
  "zh": "赛博食品",
  "fr": "Cyber-food",
  "de": "Cyber-Food",
  "ja": "サイバーフード",
  "ko": "사이버 푸드",
  "id": "Cyber Food"
 },
 "repair_kits": {
  "ru": "Ремкомплект",
  "en": "Repair Kit",
  "es": "Kit de reparación",
  "zh": "维修包",
  "fr": "Kit de réparation",
  "de": "Reparaturset",
  "ja": "修理キット",
  "ko": "수리 키트",
  "id": "Kit Perbaikan"
 },
 "neuro_core": {
  "ru": "Нейро-ядро",
  "en": "Neuro Core",
  "es": "Núcleo Neural",
  "zh": "神经核心",
  "fr": "Noyau Neural",
  "de": "Neuro-Kern",
  "ja": "ニューロコア",
  "ko": "뉴로 코어",
  "id": "Neuro Core"
 },
 "gold_bill": {
  "ru": "Золотой вексель",
  "en": "Gold Bill",
  "es": "Billete de Oro",
  "zh": "金票",
  "fr": "Billet d'Or",
  "de": "Goldschein",
  "ja": "ゴールドビル",
  "ko": "골드 빌",
  "id": "Wesel Emas"
 },
 "license_token": {
  "ru": "Лицензия",
  "en": "License",
  "es": "Licencia",
  "zh": "许可证",
  "fr": "Licence",
  "de": "Lizenz",
  "ja": "ライセンス",
  "ko": "라이선스",
  "id": "Lisensi"
 },
 "luck_chip": {
  "ru": "Фишка удачи",
  "en": "Luck Chip",
  "es": "Ficha de Suerte",
  "zh": "幸运筹码",
  "fr": "Jeton de Chance",
  "de": "Glückschip",
  "ja": "ラックチップ",
  "ko": "럭 칩",
  "id": "Chip Keberuntungan"
 },
 "war_protocol": {
  "ru": "Боевой протокол",
  "en": "War Protocol",
  "es": "Protocolo de Guerra",
  "zh": "战争协议",
  "fr": "Protocole de Guerre",
  "de": "Kriegsprotokoll",
  "ja": "ウォープロトコル",
  "ko": "워 프로토콜",
  "id": "Protokol Perang"
 },
 "bio_module": {
  "ru": "Био-модуль",
  "en": "Bio Module",
  "es": "Módulo Bio",
  "zh": "生物模块",
  "fr": "Module Bio",
  "de": "Bio-Modul",
  "ja": "バイオモジュール",
  "ko": "바이오 모듈",
  "id": "Modul Bio"
 },
 "gateway_code": {
  "ru": "Код шлюза",
  "en": "Gateway Code",
  "es": "Código de Portal",
  "zh": "网关代码",
  "fr": "Code Passerelle",
  "de": "Gateway-Code",
  "ja": "ゲートウェイコード",
  "ko": "게이트웨이 코드",
  "id": "Kode Gerbang"
 }
}

T3 = {
 "neuro_core": {
  "ru": "+8% к производству всех бизнесов",
  "en": "+8% production for all businesses",
  "es": "+8% producción de todos los negocios",
  "zh": "所有业务产量 +8%",
  "fr": "+8% de production pour toutes les entreprises",
  "de": "+8% Produktion für alle Geschäfte",
  "ja": "全ビジネスの生産量 +8%",
  "ko": "모든 비즈니스 생산량 +8%",
  "id": "+8% produksi semua bisnis"
 },
 "gold_bill": {
  "ru": "−20% к стоимости ремонта",
  "en": "−20% repair cost",
  "es": "−20% costo de reparación",
  "zh": "维修成本 −20%",
  "fr": "−20% sur le coût de réparation",
  "de": "−20% Reparaturkosten",
  "ja": "修理コスト −20%",
  "ko": "수리 비용 −20%",
  "id": "−20% biaya perbaikan"
 },
 "license_token": {
  "ru": "−15% к торговой комиссии",
  "en": "−15% trading commission",
  "es": "−15% comisión de trading",
  "zh": "交易佣金 −15%",
  "fr": "−15% de commission de trading",
  "de": "−15% Handelsprovision",
  "ja": "取引手数料 −15%",
  "ko": "거래 수수료 −15%",
  "id": "−15% komisi perdagangan"
 },
 "luck_chip": {
  "ru": "+5% шанс ×2 производства",
  "en": "+5% chance for ×2 production",
  "es": "+5% probabilidad de producción ×2",
  "zh": "+5% 概率触发 ×2 生产",
  "fr": "+5% de chance de production ×2",
  "de": "+5% Chance auf ×2 Produktion",
  "ja": "生産量×2のチャンス +5%",
  "ko": "×2 생산 확률 +5%",
  "id": "+5% peluang produksi ×2"
 },
 "war_protocol": {
  "ru": "−25% к скорости износа зданий",
  "en": "−25% building wear rate",
  "es": "−25% velocidad de desgaste",
  "zh": "建筑磨损速度 −25%",
  "fr": "−25% sur l'usure des bâtiments",
  "de": "−25% Verschleißrate",
  "ja": "建物の摩耗速度 −25%",
  "ko": "건물 마모 속도 −25%",
  "id": "−25% laju keausan bangunan"
 },
 "bio_module": {
  "ru": "−10% к потреблению ресурсов",
  "en": "−10% resource consumption",
  "es": "−10% consumo de recursos",
  "zh": "资源消耗 −10%",
  "fr": "−10% de consommation de ressources",
  "de": "−10% Ressourcenverbrauch",
  "ja": "リソース消費 −10%",
  "ko": "자원 소비 −10%",
  "id": "−10% konsumsi sumber daya"
 },
 "gateway_code": {
  "ru": "−25% к комиссии на вывод",
  "en": "−25% withdrawal fee",
  "es": "−25% comisión de retiro",
  "zh": "提现手续费 −25%",
  "fr": "−25% sur les frais de retrait",
  "de": "−25% Auszahlungsgebühr",
  "ja": "出金手数料 −25%",
  "ko": "출금 수수료 −25%",
  "id": "−25% biaya penarikan"
 }
}

PATRON = {
 "repair_discount": {
  "n": {
   "ru": "Ремонтный допуск",
   "en": "Repair Permit",
   "es": "Permiso de reparación",
   "zh": "维修许可",
   "fr": "Permis de réparation",
   "de": "Reparaturgenehmigung",
   "ja": "修理許可",
   "ko": "수리 허가",
   "id": "Izin Perbaikan"
  },
  "d": {
   "ru": "Стоимость починки здания снижена на 25%.",
   "en": "Building repair cost reduced by 25%.",
   "es": "El costo de reparación se reduce un 25%.",
   "zh": "建筑维修费用降低25%。",
   "fr": "Coût de réparation réduit de 25%.",
   "de": "Reparaturkosten um 25% reduziert.",
   "ja": "建物の修理コストが25%減少。",
   "ko": "건물 수리 비용 25% 감소.",
   "id": "Biaya perbaikan bangunan turun 25%."
  }
 },
 "deep_storage": {
  "n": {
   "ru": "Глубокие закрома",
   "en": "Deep Storage",
   "es": "Almacenamiento profundo",
   "zh": "深层仓储",
   "fr": "Stockage profond",
   "de": "Tieflager",
   "ja": "深層倉庫",
   "ko": "깊은 창고",
   "id": "Gudang Dalam"
  },
  "d": {
   "ru": "+10% к объёму общего склада.",
   "en": "+10% to total warehouse capacity.",
   "es": "+10% a la capacidad total del almacén.",
   "zh": "总仓库容量 +10%。",
   "fr": "+10% à la capacité totale du stockage.",
   "de": "+10% Gesamtlagerkapazität.",
   "ja": "総倉庫容量 +10%。",
   "ko": "전체 창고 용량 +10%.",
   "id": "+10% kapasitas gudang total."
  }
 },
 "stakhanovets": {
  "n": {
   "ru": "Стахановец",
   "en": "Stakhanovite",
   "es": "Estajanovista",
   "zh": "劳模",
   "fr": "Stakhanoviste",
   "de": "Stachanowez",
   "ja": "スタハノフ運動家",
   "ko": "스타하노프",
   "id": "Stakhanovis"
  },
  "d": {
   "ru": "+7% к объёму выпуска при том же потреблении.",
   "en": "+7% output at the same consumption.",
   "es": "+7% de producción con el mismo consumo.",
   "zh": "在相同消耗下产出 +7%。",
   "fr": "+7% de production à consommation égale.",
   "de": "+7% Produktion bei gleichem Verbrauch.",
   "ja": "同じ消費量で出力 +7%。",
   "ko": "동일한 소비로 출력 +7%.",
   "id": "+7% hasil produksi dengan konsumsi yang sama."
  }
 },
 "lean_production": {
  "n": {
   "ru": "Бережливое производство",
   "en": "Lean Production",
   "es": "Producción ajustada",
   "zh": "精益生产",
   "fr": "Production allégée",
   "de": "Schlanke Produktion",
   "ja": "リーン生産",
   "ko": "린 생산",
   "id": "Produksi Ramping"
  },
  "d": {
   "ru": "Потребление сырья снижено на 5%.",
   "en": "Raw material consumption reduced by 5%.",
   "es": "Consumo de materia prima reducido en 5%.",
   "zh": "原料消耗降低5%。",
   "fr": "Consommation de matières premières réduite de 5%.",
   "de": "Rohstoffverbrauch um 5% reduziert.",
   "ja": "原材料の消費量が5%減少。",
   "ko": "원자재 소비량 5% 감소.",
   "id": "Konsumsi bahan baku turun 5%."
  }
 },
 "second_chance": {
  "n": {
   "ru": "Второй шанс",
   "en": "Second Chance",
   "es": "Segunda oportunidad",
   "zh": "第二次机会",
   "fr": "Seconde chance",
   "de": "Zweite Chance",
   "ja": "セカンドチャンス",
   "ko": "두 번째 기회",
   "id": "Kesempatan Kedua"
  },
  "d": {
   "ru": "2% шанс, что здание отработает цикл, не потратив сырьё.",
   "en": "2% chance the building completes a cycle without spending raw materials.",
   "es": "2% de probabilidad de completar un ciclo sin gastar materiales.",
   "zh": "2% 几率：建筑完成一次生产周期而不消耗原料。",
   "fr": "2% de chance qu'un bâtiment effectue un cycle sans matières premières.",
   "de": "2% Chance, dass ein Gebäude einen Zyklus ohne Rohstoffe abschließt.",
   "ja": "2%の確率で建物が原料を消費せずにサイクルを完了。",
   "ko": "2% 확률로 건물이 원자재를 소모하지 않고 한 사이클을 수행.",
   "id": "Peluang 2% bangunan menyelesaikan siklus tanpa memakai bahan baku."
  }
 },
 "offshore_zone": {
  "n": {
   "ru": "Оффшорная зона",
   "en": "Offshore Zone",
   "es": "Zona offshore",
   "zh": "离岸区",
   "fr": "Zone offshore",
   "de": "Offshore-Zone",
   "ja": "オフショアゾーン",
   "ko": "역외 지역",
   "id": "Zona Offshore"
  },
  "d": {
   "ru": "−1.5% к торговой комиссии при продаже.",
   "en": "−1.5% trading commission on sale.",
   "es": "−1.5% de comisión comercial en la venta.",
   "zh": "出售时交易佣金 −1.5%。",
   "fr": "−1.5% de commission de trading sur la vente.",
   "de": "−1.5% Handelsprovision beim Verkauf.",
   "ja": "販売時の取引手数料 −1.5%。",
   "ko": "판매 시 거래 수수료 −1.5%.",
   "id": "−1,5% komisi perdagangan saat menjual."
  }
 },
 "trade_attache": {
  "n": {
   "ru": "Торговый атташе",
   "en": "Trade Attaché",
   "es": "Agregado comercial",
   "zh": "商务参赞",
   "fr": "Attaché commercial",
   "de": "Handelsattaché",
   "ja": "通商アタッシェ",
   "ko": "무역 공사",
   "id": "Atase Dagang"
  },
  "d": {
   "ru": "Увеличивает лимит активных торговых слотов на +1.",
   "en": "Increases active trading slot limit by +1.",
   "es": "Aumenta el límite de espacios de comercio activos en +1.",
   "zh": "活动交易栏位上限 +1。",
   "fr": "Augmente la limite de slots de trading actifs de +1.",
   "de": "Erhöht das Limit aktiver Handelsslots um +1.",
   "ja": "アクティブな取引スロット上限を +1。",
   "ko": "활성 거래 슬롯 한도 +1.",
   "id": "Batas slot perdagangan aktif +1."
  }
 },
 "sensor_control": {
  "n": {
   "ru": "Сенсорный контроль",
   "en": "Sensor Control",
   "es": "Control sensorial",
   "zh": "传感控制",
   "fr": "Contrôle capteur",
   "de": "Sensorsteuerung",
   "ja": "センサー制御",
   "ko": "센서 제어",
   "id": "Kontrol Sensor"
  },
  "d": {
   "ru": "+3% к шансу на критическое производство (x2 выпуск).",
   "en": "+3% chance for critical production (×2 output).",
   "es": "+3% de probabilidad de producción crítica (×2 producción).",
   "zh": "+3% 几率触发暴击生产（×2 产出）。",
   "fr": "+3% de chance de production critique (×2 sortie).",
   "de": "+3% Chance auf kritische Produktion (×2 Ausstoß).",
   "ja": "クリティカル生産の確率 +3%（出力×2）。",
   "ko": "치명적 생산 확률 +3% (산출 ×2).",
   "id": "+3% peluang produksi kritis (hasil ×2)."
  }
 },
 "tax_break": {
  "n": {
   "ru": "Налоговая льгота",
   "en": "Tax Break",
   "es": "Exención fiscal",
   "zh": "税收减免",
   "fr": "Allègement fiscal",
   "de": "Steuervorteil",
   "ja": "税制優遇",
   "ko": "세금 감면",
   "id": "Keringanan Pajak"
  },
  "d": {
   "ru": "−17% комиссии на вывод средств.",
   "en": "−17% withdrawal commission.",
   "es": "−17% de comisión de retiro.",
   "zh": "提现手续费 −17%。",
   "fr": "−17% de commission de retrait.",
   "de": "−17% Auszahlungsgebühr.",
   "ja": "出金手数料 −17%。",
   "ko": "출금 수수료 −17%.",
   "id": "−17% komisi penarikan."
  }
 }
}

BOOST = {
 "auto_shift": {
  "n": {
   "ru": "Автозапуск смен",
   "en": "Auto-shift",
   "es": "Turnos automáticos",
   "zh": "自动开班",
   "fr": "Lancement auto des postes",
   "de": "Auto-Schicht",
   "ja": "シフト自動開始",
   "ko": "교대 자동 시작",
   "id": "Shift otomatis"
  },
  "d": {
   "ru": "Смены всех ваших бизнесов, включая уровень 0, перезапускаются сами всё это время.",
   "en": "Shifts of all your businesses, level 0 included, restart by themselves for this time.",
   "es": "Los turnos de todos tus negocios, incluido el nivel 0, se reinician solos durante este tiempo.",
   "zh": "在此期间，你所有企业（包括 0 级）的轮班都会自动重启。",
   "fr": "Les quarts de toutes vos entreprises, niveau 0 compris, redémarrent seuls pendant ce temps.",
   "de": "Die Schichten aller deiner Unternehmen, auch Stufe 0, starten in dieser Zeit von selbst neu.",
   "ja": "この期間、Lv.0を含むすべてのビジネスのシフトが自動で再開されます。",
   "ko": "이 기간 동안 레벨 0을 포함한 모든 사업의 교대가 자동으로 다시 시작됩니다.",
   "id": "Shift semua bisnis Anda, termasuk level 0, dimulai ulang otomatis selama waktu ini."
  }
 },
 "warehouse_guard": {
  "n": {
   "ru": "Защита склада",
   "en": "Warehouse guard",
   "es": "Protección del almacén",
   "zh": "仓库保护",
   "fr": "Protection de l’entrepôt",
   "de": "Lagerschutz",
   "ja": "倉庫保護",
   "ko": "창고 보호",
   "id": "Perlindungan gudang"
  },
  "d": {
   "ru": "Товары на складе не портятся всё это время.",
   "en": "Goods in your warehouse do not spoil during this time.",
   "es": "Los bienes de tu almacén no se estropean durante este tiempo.",
   "zh": "在此期间，仓库中的货物不会变质。",
   "fr": "Les marchandises de votre entrepôt ne se gâtent pas pendant ce temps.",
   "de": "Die Waren in deinem Lager verderben in dieser Zeit nicht.",
   "ja": "この間、倉庫の商品は傷みません。",
   "ko": "이 기간 동안 창고의 상품이 상하지 않습니다.",
   "id": "Barang di gudangmu tidak rusak selama waktu ini."
  }
 },
 "repair_all": {
  "n": {
   "ru": "Ремонт всех бизнесов",
   "en": "Repair all businesses",
   "es": "Reparar todos los negocios",
   "zh": "修理所有企业",
   "fr": "Réparer toutes les entreprises",
   "de": "Alle Businesses reparieren",
   "ja": "全ビジネスを修理",
   "ko": "모든 사업 수리",
   "id": "Perbaiki semua bisnis"
  },
  "d": {
   "ru": "Сразу чинит все ваши бизнесы до 100%.",
   "en": "Repairs all your businesses to 100 % right away.",
   "es": "Repara todos tus negocios al 100 % al instante.",
   "zh": "立即将你所有企业修复到 100%。",
   "fr": "Répare immédiatement toutes vos entreprises à 100 %.",
   "de": "Repariert sofort alle deine Businesses auf 100 %.",
   "ja": "すべてのビジネスを即座に100%まで修理します。",
   "ko": "모든 사업을 즉시 100%로 수리합니다.",
   "id": "Langsung memperbaiki semua bisnismu hingga 100%."
  }
 },
 "xp_x2": {
  "n": {
   "ru": "×2 опыт City Pass",
   "en": "×2 City Pass XP",
   "es": "XP ×2 de City Pass",
   "zh": "City Pass 双倍经验",
   "fr": "XP City Pass ×2",
   "de": "×2 City-Pass-EP",
   "ja": "City Pass 経験値2倍",
   "ko": "City Pass 경험치 ×2",
   "id": "XP City Pass ×2"
  },
  "d": {
   "ru": "Весь опыт City Pass удваивается на это время.",
   "en": "All City Pass XP is doubled for this time.",
   "es": "Toda la XP de City Pass se duplica durante este tiempo.",
   "zh": "在此期间，所有 City Pass 经验翻倍。",
   "fr": "Toute l’XP du City Pass est doublée pendant ce temps.",
   "de": "Alle City-Pass-EP werden in dieser Zeit verdoppelt.",
   "ja": "この間、City Pass の経験値がすべて2倍になります。",
   "ko": "이 시간 동안 City Pass 경험치가 모두 두 배가 됩니다.",
   "id": "Semua XP City Pass berlipat dua selama waktu ini."
  }
 },
 "streak_shield": {
  "n": {
   "ru": "Щит серии",
   "en": "Streak shield",
   "es": "Escudo de racha",
   "zh": "连签护盾",
   "fr": "Bouclier de série",
   "de": "Serienschild",
   "ja": "連続シールド",
   "ko": "연속 보호막",
   "id": "Perisai rangkaian"
  },
  "d": {
   "ru": "Сохраняет серию входов, если пропустили один день. Хранится не больше двух.",
   "en": "Keeps your login streak if you miss one day. You can hold up to two.",
   "es": "Mantiene tu racha de entradas si faltas un día. Puedes tener hasta dos.",
   "zh": "缺勤一天时保住连续登录记录。最多持有两个。",
   "fr": "Garde votre série de connexions si vous manquez un jour. Deux au maximum.",
   "de": "Hält deine Login-Serie, wenn du einen Tag verpasst. Höchstens zwei.",
   "ja": "1日休んでもログイン連続記録を守ります。最大2つまで。",
   "ko": "하루를 빠져도 연속 접속 기록을 지켜 줍니다. 최대 2개까지.",
   "id": "Menjaga rangkaian login jika Anda melewatkan satu hari. Maksimal dua."
  }
 }
}


# business names exactly as the game shows them (frontend lib/translationsExtra.js businessI18n)
BIZ = {
 "helios": {
  "ru": "Солнечная станция",
  "en": "Solar Station",
  "es": "Estación solar",
  "zh": "太阳能站",
  "fr": "Station solaire",
  "de": "Solarstation",
  "ja": "ソーラーステーション",
  "ko": "태양광 발전소",
  "id": "Stasiun Surya"
 },
 "nano_dc": {
  "ru": "Дата-центр",
  "en": "Data Center",
  "es": "Centro de datos",
  "zh": "数据中心",
  "fr": "Centre de données",
  "de": "Rechenzentrum",
  "ja": "データセンター",
  "ko": "데이터 센터",
  "id": "Pusat Data"
 },
 "quartz_mine": {
  "ru": "Шахта Кварца",
  "en": "Quartz Mine",
  "es": "Mina de cuarzo",
  "zh": "石英矿",
  "fr": "Mine de quartz",
  "de": "Quarzmine",
  "ja": "クォーツ鉱山",
  "ko": "석영 광산",
  "id": "Tambang Kuarsa"
 },
 "signal_tower": {
  "ru": "Вышка Трафика",
  "en": "Signal Tower",
  "es": "Torre de señal",
  "zh": "信号塔",
  "fr": "Tour de signal",
  "de": "Signalturm",
  "ja": "シグナルタワー",
  "ko": "신호 타워",
  "id": "Menara Sinyal"
 },
 "hydro_cooling": {
  "ru": "Хладокомбинат",
  "en": "Hydro Cooling",
  "es": "Hidrorefrigeración",
  "zh": "水冷设施",
  "fr": "Refroidissement hydro",
  "de": "Hydro-Kühlanlage",
  "ja": "ハイドロ冷却",
  "ko": "수냉 시설",
  "id": "Pendingin Hidro"
 },
 "bio_farm": {
  "ru": "Био-ферма",
  "en": "Bio Farm",
  "es": "Bio-granja",
  "zh": "生物农场",
  "fr": "Bio-ferme",
  "de": "Bio-Farm",
  "ja": "バイオファーム",
  "ko": "바이오 농장",
  "id": "Bio Farm"
 },
 "scrap_yard": {
  "ru": "Свалка",
  "en": "Scrap Yard",
  "es": "Chatarrería",
  "zh": "废料场",
  "fr": "Casse",
  "de": "Schrottplatz",
  "ja": "廃品置き場",
  "ko": "폐품장",
  "id": "Tempat Rongsokan"
 },
 "chips_factory": {
  "ru": "Завод Микросхем",
  "en": "Chips Factory",
  "es": "Fábrica de chips",
  "zh": "芯片厂",
  "fr": "Usine de puces",
  "de": "Chip-Fabrik",
  "ja": "チップ工場",
  "ko": "칩 공장",
  "id": "Pabrik Chip"
 },
 "nft_studio": {
  "ru": "NFT-студия",
  "en": "NFT Studio",
  "es": "Estudio NFT",
  "zh": "NFT 工作室",
  "fr": "Studio NFT",
  "de": "NFT-Studio",
  "ja": "NFTスタジオ",
  "ko": "NFT 스튜디오",
  "id": "Studio NFT"
 },
 "ai_lab": {
  "ru": "AI-лаборатория",
  "en": "AI Lab",
  "es": "Laboratorio IA",
  "zh": "AI 实验室",
  "fr": "Labo IA",
  "de": "KI-Labor",
  "ja": "AIラボ",
  "ko": "AI 연구소",
  "id": "Lab AI"
 },
 "logistics_hub": {
  "ru": "Логистический хаб",
  "en": "Logistics Hub",
  "es": "Hub logístico",
  "zh": "物流中心",
  "fr": "Hub logistique",
  "de": "Logistik-Hub",
  "ja": "ロジスティクスハブ",
  "ko": "물류 허브",
  "id": "Pusat Logistik"
 },
 "cyber_cafe": {
  "ru": "Кибер-кафе",
  "en": "Cyber Cafe",
  "es": "Cibercafé",
  "zh": "网吧",
  "fr": "Cybercafé",
  "de": "Cybercafé",
  "ja": "サイバーカフェ",
  "ko": "사이버 카페",
  "id": "Kafe Siber"
 },
 "repair_shop": {
  "ru": "Ремонтная мастерская",
  "en": "Repair Shop",
  "es": "Taller",
  "zh": "维修店",
  "fr": "Atelier",
  "de": "Werkstatt",
  "ja": "修理店",
  "ko": "수리점",
  "id": "Bengkel Perbaikan"
 },
 "vr_club": {
  "ru": "VR-клуб",
  "en": "VR Club",
  "es": "Club VR",
  "zh": "VR 俱乐部",
  "fr": "Club VR",
  "de": "VR-Club",
  "ja": "VRクラブ",
  "ko": "VR 클럽",
  "id": "Klub VR"
 },
 "validator": {
  "ru": "Валидатор",
  "en": "Validator",
  "es": "Validador",
  "zh": "验证者",
  "fr": "Validateur",
  "de": "Validator",
  "ja": "バリデーター",
  "ko": "검증자",
  "id": "Validator"
 },
 "gram_bank": {
  "ru": "Банк Gram",
  "en": "Gram Bank",
  "es": "Banco Gram",
  "zh": "Gram 银行",
  "fr": "Banque Gram",
  "de": "Gram-Bank",
  "ja": "Gram銀行",
  "ko": "Gram 은행",
  "id": "Gram Bank"
 },
 "dex": {
  "ru": "DEX-биржа",
  "en": "DEX",
  "es": "DEX",
  "zh": "DEX",
  "fr": "DEX",
  "de": "DEX",
  "ja": "DEX",
  "ko": "DEX",
  "id": "DEX"
 },
 "casino": {
  "ru": "Казино",
  "en": "Casino",
  "es": "Casino",
  "zh": "赌场",
  "fr": "Casino",
  "de": "Casino",
  "ja": "カジノ",
  "ko": "카지노",
  "id": "Kasino"
 },
 "arena": {
  "ru": "Арена",
  "en": "Arena",
  "es": "Arena",
  "zh": "竞技场",
  "fr": "Arène",
  "de": "Arena",
  "ja": "アリーナ",
  "ko": "아레나",
  "id": "Arena"
 },
 "incubator": {
  "ru": "Инкубатор",
  "en": "Incubator",
  "es": "Incubadora",
  "zh": "孵化器",
  "fr": "Incubateur",
  "de": "Inkubator",
  "ja": "インキュベーター",
  "ko": "인큐베이터",
  "id": "Inkubator"
 },
 "bridge": {
  "ru": "Мост",
  "en": "Bridge",
  "es": "Puente",
  "zh": "桥梁",
  "fr": "Pont",
  "de": "Brücke",
  "ja": "ブリッジ",
  "ko": "브리지",
  "id": "Jembatan"
 }
}
