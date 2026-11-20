"""Player-facing errors of lot edit / cancel (server.edit_listing, server.cancel_listing), in every project language."""

TEXT = {
    "gone": {
        "ru": "Лот уже продан или снят с продажи.", "en": "This lot has already been sold or taken off sale.",
        "es": "Este lote ya se vendió o se retiró de la venta.", "zh": "该商品已售出或已下架。",
        "fr": "Ce lot a déjà été vendu ou retiré de la vente.", "de": "Dieses Los wurde bereits verkauft oder zurückgezogen.",
        "ja": "この出品はすでに売れたか、取り下げられています。", "ko": "이 판매 물품은 이미 팔렸거나 판매가 취소되었습니다.",
        "id": "Lot ini sudah terjual atau ditarik dari penjualan."},
    "not_editable": {
        "ru": "Этот лот нельзя изменить.", "en": "This lot cannot be changed.", "es": "Este lote no se puede modificar.",
        "zh": "该商品无法修改。", "fr": "Ce lot ne peut pas être modifié.", "de": "Dieses Los kann nicht geändert werden.",
        "ja": "この出品は変更できません。", "ko": "이 판매 물품은 변경할 수 없습니다.", "id": "Lot ini tidak dapat diubah."},
    "amount_positive": {
        "ru": "Количество должно быть больше 0.", "en": "The amount must be greater than 0.", "es": "La cantidad debe ser mayor que 0.",
        "zh": "数量必须大于 0。", "fr": "La quantité doit être supérieure à 0.", "de": "Die Menge muss größer als 0 sein.",
        "ja": "数量は0より大きくしてください。", "ko": "수량은 0보다 커야 합니다.", "id": "Jumlah harus lebih dari 0."},
    "tens": {   # the minimum lot of a tier-1 resource (any number from {n})
        "ru": "Лот ресурса первого эшелона — от {n} шт.",
        "en": "A tier-1 resource lot must be at least {n} units.",
        "es": "Un lote de recurso de nivel 1 debe tener al menos {n} uds.",
        "zh": "一级资源的每个出售批次至少 {n} 个。",
        "fr": "Un lot de ressource de niveau 1 doit compter au moins {n} unités.",
        "de": "Ein Los einer Stufe-1-Ressource muss mindestens {n} Einheiten haben.",
        "ja": "第1階層の資源は1回の出品につき{n}個以上です。",
        "ko": "1단계 자원은 판매 물품당 최소 {n}개입니다.",
        "id": "Lot sumber daya tingkat 1 minimal {n} unit."},
    "not_enough": {
        "ru": "Не хватает ресурса: в лоте и на складе вместе {n} ед.", "en": "Not enough of this resource: {n} units in the lot and warehouse together.",
        "es": "No hay suficiente recurso: {n} ud. entre el lote y el almacén.", "zh": "资源不足：商品与仓库合计 {n} 单位。",
        "fr": "Ressource insuffisante : {n} u. au total dans le lot et l'entrepôt.", "de": "Nicht genug Ressource: zusammen {n} Einh. im Los und im Lager.",
        "ja": "資源が足りません：出品と倉庫の合計 {n} 単位です。", "ko": "자원이 부족합니다: 판매 물품과 창고를 합쳐 {n}개입니다.",
        "id": "Sumber daya tidak cukup: total {n} unit di lot dan gudang."},
    "no_business_cap": {
        "ru": "Без бизнеса в одном лоте можно продать не больше {n} ед.", "en": "Without a business you can sell at most {n} units in one lot.",
        "es": "Sin negocio puedes vender como máximo {n} ud. en un lote.", "zh": "没有企业时，每个商品最多出售 {n} 单位。",
        "fr": "Sans entreprise, vous pouvez vendre au maximum {n} u. par lot.", "de": "Ohne Unternehmen kannst du höchstens {n} Einh. pro Los verkaufen.",
        "ja": "ビジネスがない場合、1つの出品で販売できるのは最大 {n} 単位です。", "ko": "사업체가 없으면 한 번에 최대 {n}개까지 판매할 수 있습니다.",
        "id": "Tanpa bisnis, Anda bisa menjual paling banyak {n} unit per lot."},
}


def text(key: str, lang: str, **kw) -> str:
    d = TEXT.get(key) or {}
    s = d.get(lang) or d.get("en") or key
    try:
        return s.format(**kw)
    except (KeyError, IndexError, ValueError):
        return s
