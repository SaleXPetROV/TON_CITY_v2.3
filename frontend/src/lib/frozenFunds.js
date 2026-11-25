// «Заморожено в контрактах» in the balance views (balance window, sidebar), in every language of the project.
// The amount is the escrow of the player's active contracts (backend: frozen_tenders.effective_frozen_city,
// returned by /api/auth/me as frozen_for_tenders_city / frozen_for_tenders_ton).
const L = {
  frozen: { ru: 'Заморожено в контрактах поставки', en: 'Frozen in supply contracts', es: 'Congelado en contratos de suministro', zh: '供货合约冻结', fr: 'Bloqué dans les contrats d’approvisionnement', de: 'In Lieferverträgen gesperrt', ja: '供給契約で凍結中', ko: '공급 계약에 동결됨', id: 'Dibekukan di kontrak pasokan' },
  hint: {
    ru: 'Залог по действующим контрактам поставки (тендеры). Входит в основной баланс, но потратить или вывести его нельзя, пока контракт не завершится.',
    en: 'Deposit held by your active supply contracts (tenders). It is part of your main balance but cannot be spent or withdrawn until the contract ends.',
    es: 'Depósito retenido por tus contratos activos. Vuelve a tu saldo principal cuando el contrato termina.',
    zh: '这是您进行中合约的押金，合约结束后将退回主余额。',
    fr: 'Caution retenue par vos contrats en cours. Elle revient sur votre solde principal à la fin du contrat.',
    de: 'Kaution deiner laufenden Verträge. Sie kommt nach Vertragsende auf dein Hauptguthaben zurück.',
    ja: '進行中の契約の保証金です。契約が終わるとメイン残高に戻ります。',
    ko: '진행 중인 계약의 보증금입니다. 계약이 끝나면 기본 잔액으로 돌아옵니다.',
    id: 'Jaminan untuk kontrak aktif Anda. Kembali ke saldo utama saat kontrak berakhir.',
  },
  rent: { ru: 'Заморожено в аренде бизнеса', en: 'Frozen in business rentals', es: 'Congelado en alquileres de negocios', zh: '企业租赁冻结', fr: 'Bloqué dans les locations d’entreprises', de: 'In Unternehmensmieten gesperrt', ja: 'ビジネス賃貸で凍結中', ko: '사업체 임대에 동결됨', id: 'Dibekukan di sewa bisnis' },
  rentHint: {
    ru: 'Оплата аренды за оставшиеся дни и залог. Не входит в баланс выше: каждый день списывается оплата за день, остаток и залог вернутся на основной баланс, когда аренда закончится.',
    en: 'Rent for the remaining days plus the deposit. Not included in the balance above: one day’s rent is taken each day; the rest and the deposit return to your main balance when the rental ends.',
    es: 'El alquiler de los días restantes y el depósito. No se incluye en el saldo de arriba: cada día se cobra un día; el resto y el depósito vuelven a tu saldo principal al terminar el alquiler.',
    zh: '剩余天数的租金和押金，不计入上方余额：每天扣除一天租金，租赁结束后剩余部分和押金退回主余额。',
    fr: 'Le loyer des jours restants et la caution. Non inclus dans le solde ci-dessus : un jour est prélevé chaque jour ; le reste et la caution reviennent sur votre solde principal à la fin de la location.',
    de: 'Miete für die restlichen Tage plus Kaution. Nicht im Guthaben oben enthalten: Jeden Tag wird ein Tag abgebucht; Rest und Kaution kommen nach Mietende auf dein Hauptguthaben zurück.',
    ja: '残りの日数分の賃料と保証金です。上の残高には含まれません。毎日1日分が引かれ、賃貸終了時に残りと保証金がメイン残高に戻ります。',
    ko: '남은 기간의 임대료와 보증금입니다. 위 잔액에는 포함되지 않습니다. 매일 하루치가 차감되고, 임대가 끝나면 남은 금액과 보증금이 기본 잔액으로 돌아옵니다.',
    id: 'Sewa untuk hari tersisa plus jaminan. Tidak termasuk dalam saldo di atas: sewa satu hari dipotong setiap hari; sisanya dan jaminan kembali ke saldo utama saat sewa berakhir.',
  },
  available: { ru: 'Доступно сейчас', en: 'Available now', es: 'Disponible ahora', zh: '当前可用', fr: 'Disponible maintenant', de: 'Jetzt verfügbar', ja: '現在利用可能', ko: '현재 사용 가능', id: 'Tersedia sekarang' },
};
export const frozenText = (key, lang) => (L[key] && (L[key][lang] || L[key].en)) || '';
/** Frozen escrow of a /auth/me user object, in TON (0 when none). */
export const frozenTonOf = (u) => {
  const ton = Number(u?.frozen_for_tenders_ton);
  if (Number.isFinite(ton) && ton > 0) return ton;
  const city = Number(u?.frozen_for_tenders_city);
  return Number.isFinite(city) && city > 0 ? city / 1000 : 0;
};

/** Money frozen in business rentals (unpaid days + deposit), in TON — NOT inside balance_ton. */
export const frozenRentTonOf = (u) => {
  const ton = Number(u?.frozen_rent_ton);
  return Number.isFinite(ton) && ton > 0 ? ton : 0;
};
