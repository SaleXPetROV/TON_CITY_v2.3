/** «Выкуп городом через N мин» on the player's own lots / sell orders (GET /market/my-listings and
 *  /market/my-orders → city_buyout, computed by market_maker.seller_hints). Also the tax / credit words of the lot card. */
export const CITY_BUYOUT_TXT = {
  en: { in: 'City buyback in', min: 'min', sec: 'sec', soon: 'City buyback: within 5 min', later: 'City buyback: tomorrow — today’s limit is used up', price: 'The City will not buy at this price. It buys at {p} $CITY', tax: 'tax', credit: 'credit' },
  ru: { in: 'Выкуп городом через', min: 'мин', sec: 'сек', soon: 'Выкуп городом: в ближайшие 5 мин', later: 'Выкуп городом: завтра — дневной лимит исчерпан', price: 'По этой цене Город не выкупит. Он выкупает по {p} $CITY', tax: 'налог', credit: 'кредит' },
  es: { in: 'Recompra de la Ciudad en', min: 'min', sec: 's', soon: 'Recompra de la Ciudad: en 5 min', later: 'Recompra de la Ciudad: mañana — se agotó el límite de hoy', price: 'La Ciudad no comprará a este precio. Compra a {p} $CITY', tax: 'impuesto', credit: 'crédito' },
  zh: { in: '城市回购倒计时', min: '分钟', sec: '秒', soon: '城市回购：5 分钟内', later: '城市回购：明天——今日额度已用完', price: '此价格城市不会回购。回购价为 {p} $CITY', tax: '税', credit: '贷款' },
  fr: { in: 'Rachat par la Ville dans', min: 'min', sec: 's', soon: 'Rachat par la Ville : sous 5 min', later: 'Rachat par la Ville : demain — limite du jour atteinte', price: 'La Ville n’achète pas à ce prix. Elle rachète à {p} $CITY', tax: 'taxe', credit: 'crédit' },
  de: { in: 'Rückkauf durch die Stadt in', min: 'Min.', sec: 'Sek.', soon: 'Rückkauf durch die Stadt: in 5 Min.', later: 'Rückkauf durch die Stadt: morgen – Tageslimit erreicht', price: 'Zu diesem Preis kauft die Stadt nicht. Sie zahlt {p} $CITY', tax: 'Steuer', credit: 'Kredit' },
  ja: { in: '街の買取まで', min: '分', sec: '秒', soon: '街の買取：5分以内', later: '街の買取：明日（本日の上限に達しました）', price: 'この価格では街は買い取りません。買取価格は {p} $CITY', tax: '税', credit: 'ローン' },
  ko: { in: '도시 매입까지', min: '분', sec: '초', soon: '도시 매입: 5분 이내', later: '도시 매입: 내일 — 오늘 한도 소진', price: '이 가격으로는 도시가 매입하지 않습니다. 매입가 {p} $CITY', tax: '세금', credit: '대출' },
  id: { in: 'Dibeli Kota dalam', min: 'mnt', sec: 'dtk', soon: 'Dibeli Kota: dalam 5 mnt', later: 'Dibeli Kota: besok — batas hari ini habis', price: 'Kota tidak membeli dengan harga ini. Kota membeli di {p} $CITY', tax: 'pajak', credit: 'kredit' },
};
export default function CityBuyoutLine({ info, lang, nowMs, id }) {
  const tx = CITY_BUYOUT_TXT[lang] || CITY_BUYOUT_TXT.en;
  if (!info) return null;
  let text = null;
  let mins = null;
  let unit = tx.min;
  if (info.state === 'wait' && info.eta_at) {
    const secs = Math.ceil((new Date(info.eta_at).getTime() - nowMs) / 1000);
    if (secs <= 0) text = tx.soon;
    else if (secs < 60) { mins = secs; unit = tx.sec; }       // the last minute counts down in seconds
    else mins = Math.ceil(secs / 60);
  } else if (info.state === 'soon') {
    text = tx.soon;
  } else if (info.state === 'later') {
    text = tx.later;
  } else if (info.state === 'never' && info.code === 'price' && info.price_city != null) {
    text = tx.price.replace('{p}', Number(info.price_city).toLocaleString('ru-RU', { maximumFractionDigits: 2 }));
  }
  if (text == null && mins == null) return null;
  const bad = info.state === 'never' || info.state === 'later';
  return (
    <div className={`mt-2.5 w-full rounded-lg border px-3 py-1.5 text-xs flex items-center justify-center gap-1.5 text-center ${bad ? 'border-amber-500/25 bg-amber-500/10 text-amber-200' : 'border-cyan-500/25 bg-cyan-500/10 text-cyan-100'}`}
      data-testid={`lot-city-buyout-${id}`}>
      <span aria-hidden>🏙️</span>
      {text != null ? <span>{text}</span> : <span>{tx.in} <b className="font-mono text-white">{mins}</b> {unit}</span>}
    </div>
  );
}

