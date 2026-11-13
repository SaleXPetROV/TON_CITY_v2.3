# GRAM City Handbuch — Deutsch.
A = {
    "quick-start": dict(
        t="Schnellstart",
        s="Fünf Schritte vom ersten Besuch bis zum eigenen Unternehmen für immer.",
        b="""GRAM City ist ein Wirtschaftsspiel: Unternehmen produzieren Ressourcen, du verkaufst sie an die Stadt und an Spieler und wächst.
1. Nimm dir kostenlos ein Unternehmen: Karte → «Im Verkauf». Es gehört dir {{lease_days}} Tage.
2. Starte eine Schicht: das Unternehmen arbeitet {{shift_hours}} Stunden und legt Ware ins Lager.
3. Verkaufe die Ware: Handel → «Meine» → «Ressource verkaufen».
4. Repariere das Unternehmen, bevor die Haltbarkeit unter 50 % fällt.
5. Bring das Unternehmen vor Ende der Pacht auf Stufe 1 — dann gehört es dir für immer.
> Unten siehst du die Prüfung deines Kontos: was erledigt ist und was als Nächstes kommt.""",
    ),
    "balances": dict(
        t="Währungen und Guthaben",
        s="$CITY, GRAM und drei Konten: Haupt-, Bonus- und eingefrorenes Konto.",
        b="""Im Spiel wird alles in **$CITY** gerechnet: 1 GRAM = {{city_per_gram}} $CITY. GRAM ist die TON-Münze — lade nur mit TON auf.
- **Hauptkonto** — du lädst es auf und zahlst davon aus. Verkäufe von Unternehmen ab Stufe 1 landen hier.
- **Bonus** — Spielbelohnungen und Verkäufe eines Unternehmens der Stufe 0. Wird im Spiel ausgegeben, nicht auszahlbar.
- **Eingefroren** — Geld für deine Geschäfte: Ausschreibungen, Pachten. Es kommt zurück oder geht mit dem Geschäft.
> Jeder Kauf zieht zuerst das Bonuskonto ab, dann das Hauptkonto. So werden Boni genutzt, und was du auszahlen kannst, bleibt dir.""",
        show=["Tippe auf das Guthaben — alle drei Konten und die Tasten zum Aufladen und Abheben öffnen sich."],
    ),
    "earning": dict(
        t="Womit du verdienst",
        s="Verkäufe, Verträge, Pachten und Wachstum.",
        b="""- **Ressourcen verkaufen** auf dem Markt — an Spieler und die Stadt. Das Haupteinkommen.
- **Ausschreibungen** — ein Vertrag über tägliche Lieferung: die Ressource geht von selbst raus, das Geld kommt ohne Angebote.
- **Pacht** — verpachte ein Unternehmen ab Stufe 1 tageweise.
- **Upgrades** — je höher die Stufe, desto mehr Ware pro Schicht.
- **Ketten** — Ressourcen der Stufe 1 versorgen Unternehmen der Stufe 2, die wiederum Stufe 3. Kauf Rohstoffe günstiger, verkaufe teurer.
> Denk an die Steuer: jeder Verkauf zahlt eine Steuer nach Stufe der Ressource — siehe [[taxes|Steuern]].""",
    ),
    "interface": dict(
        t="Die Oberfläche",
        s="Das untere Menü, das Menü ☰ und die «?»-Taste auf den Bildschirmen.",
        b="""Unten gibt es fünf Bereiche:
- **Karte** — Städte und Grundstücke.
- **Lager** — deine Ressourcen und Booster.
- **Unternehmen** — deine Produktion: Schichten, Reparaturen, Upgrades.
- **Handel** — der Markt, deine Angebote, Ausschreibungen.
- **Community** — Ligen, Allianzen, Chat.
Im Menü ☰: Handbuch, Verlauf, Belohnungen, Marktplatz, Einstellungen, Hilfe, Regeln, Roadmap.
> Jeder Bildschirm außer «Unternehmen» hat oben eine «?»-Taste — sie öffnet die Artikel zu genau diesem Bildschirm.""",
        show=["Die fünf Bereiche des Spiels. Am Computer stehen sie links in der Seitenleiste.", "Das Menü ☰: Handbuch, Verlauf, Einstellungen, Hilfe und mehr."],
    ),
    "first-days": dict(
        t='Der Plan für deine ersten 3 Tage',
        s='Was zu tun ist, damit das Gratis-Unternehmen für immer dir gehört.',
        b="""Das Gratis-Unternehmen gehört dir {{lease_days}} Tage. Um es zu behalten:
1. Nimm ein Unternehmen auf der Karte.
2. Starte eine Schicht und hol dir die erste Charge Ware.
3. Verkaufe die Ware.
4. Starte alle {{shift_hours}} Stunden eine Schicht — wir erinnern dich.
5. Repariere, wenn die Haltbarkeit sinkt.
6. Bring das Unternehmen vor Ende der Pacht mit $CITY vom Hauptkonto auf Stufe 1.
> Die Belohnung für den Plan ist eine Ressource der Stufe 3 nach Wahl. Sie kommt ins Lager: nicht verkäuflich; den Effekt aktivierst du selbst, wann du willst — oder du gibst sie für ein Upgrade aus.""",
    ),
    "notifications": dict(
        t="Benachrichtigungen und Einstellungen",
        s="Woran erinnert wird, Ruhezeiten, der Telegram-Bot und die Sprache.",
        b="""In den Einstellungen wählst du die Erinnerungen: Schichtende, Verschleiß unter 50 %, Lager vor dem Verderb, Preise, Verkäufe.
- **Ruhezeiten** — nachts keine Benachrichtigungen.
- **Telegram-Bot** — Benachrichtigungen kommen auch in Telegram.
- **«Erste Tage»** — Tipps für Neulinge, höchstens 3 am Tag.
- Hier sind auch die Spielsprache und «Guide wiederholen».""",
        show=["Hier schaltest du Benachrichtigungen nach Thema an und aus."],
    ),
    "maps": dict(
        t="Karten und Städte",
        s="So liest du die Karte: Filter, Zoom, Minikarte, «Im Verkauf».",
        b="""Offen ist jetzt die **GRAM-Insel**; die anderen Städte werden gebaut.
- **Filter** nach Unternehmenstyp; **★** — zu deinen Unternehmen fliegen; **%** — nur zeigen, was zum Verkauf steht.
- **+ / −** — Zoom, **⌂** — zurück zur Mitte.
- **Minikarte** — antippen, und die Kamera fliegt dorthin.
- **«Im Verkauf»** unten — alle Unternehmen, die du jetzt übernehmen oder kaufen kannst.
- **🌙** — Nachtmodus; deine Wahl wird gespeichert.""",
        show=["Wähle eine Stadt — ihre Karte öffnet sich."],
    ),
    "zero-business": dict(
        t="Unternehmen der Stufe 0",
        s="Ein Gratis-Unternehmen von der Stadt für {{lease_days}} Tage — so funktioniert es.",
        b="""Jeder Neuling bekommt von der Stadt ein Unternehmen gratis: Karte → «Im Verkauf» → «Kostenlos übernehmen».
- Es gehört dir **{{lease_days}} Tage**. Um es zu behalten, bring es auf Stufe 1. Der Preis ist der Kartenpreis dieses Unternehmens, nur vom Hauptkonto.
- Der Warenpreis ist der **Systempreis** und lässt sich nicht ändern. Das Geld aus Verkäufen geht aufs Bonuskonto.
- Solange es Stufe 0 hat, kann ein anderer Spieler es zum Kartenpreis ×{{zero_mult}} kaufen. Dann gehört es ihm, und du kannst ein neues nehmen.
- Ohne Upgrade bis zum Ende geht das Unternehmen an die Stadt zurück und das Grundstück wird frei. Wir warnen 24, 12 und 2 Stunden vorher.
> Ein Gratis-Unternehmen kannst du nur nehmen, wenn du noch nie eines der Stufe 1 hattest.""",
        show=["Tippe auf «Im Verkauf» — die Liste der Gratis-Unternehmen der Stadt öffnet sich."],
    ),
    "plots": dict(
        t="Grundstücke",
        s="Jedes Unternehmen hat seinen Platz auf der Karte.",
        b="""Die Karte ist in Plätze geteilt, jeder mit einem Unternehmen eines festen Typs. Den Typ siehst du auf der Karte und in der Platzkarte.
- Einen freien Platz kannst du übernehmen ({{lease_days}} Tage gratis) oder kaufen.
- Der Preis hängt vom Unternehmenstyp und vom Platz ab: näher am Zentrum ist teurer.
- Die Platzkarte zeigt, was das Unternehmen produziert und verbraucht, und die Produktionskette.""",
    ),
    "buy-business": dict(
        t="Ein Unternehmen kaufen",
        s="Ein Unternehmen der Stufe 1 gehört dir für immer, mit Einnahmen aufs Hauptkonto.",
        b="""Kaufen kannst du auf der Karte (ein freier Platz) oder auf dem Marktplatz (das Unternehmen eines anderen Spielers).
- Ein gekauftes Unternehmen hat sofort Stufe 1 und gehört dir für immer.
- Bezahlung: zuerst Bonuskonto, dann Hauptkonto.
- Solange du ein Unternehmen der Stufe 0 hast, kannst du keine anderen kaufen — erst upgraden.
- Wähle nach der Kette: was du als Rohstoff kaufst und wer deine Ware abnimmt.""",
        show=["Der Marktplatz: Unternehmen von Spielern, deine Anzeigen und Pachten."],
    ),
    "districts": dict(
        t="Bezirke und Plätze im Verkauf",
        s="Warum nicht jeder Platz der Karte gekauft werden kann.",
        b="""Die Stadt öffnet sich Bezirk für Bezirk. Kaufen kannst du nur einen Platz in einem offenen Bezirk und nur unter denen, die schon im Verkauf sind.
- Neue Bezirke und Plätze kommen nach und nach — achte auf «Im Verkauf» und die Ankündigungen.
- Ein geschlossener Bezirk ist auf der Karte zu sehen, aber dort kann noch nichts gekauft werden.""",
    ),
    "tiers": dict(
        t="Unternehmensstufen",
        s="Stufen 1, 2 und 3: was sie produzieren und wie sie sich unterscheiden.",
        b="""Alle Unternehmen und Ressourcen gehören zu drei Stufen.
- **Stufe 1** — Grundressourcen: Energie, Metall, Quarz, Biomasse u. a. Die Stadt kauft sie auch.
- **Stufe 2** — Produkte aus Ressourcen der Stufe 1: Chips, KI-Modelle u. a. Spieler kaufen sie.
- **Stufe 3** — seltene Ressourcen, die Effekte auslösen.
Je höher die Stufe, desto teurer Ware und Reparatur, und desto mehr Lagerplatz.
[[table:taxes]]""",
    ),
    "shift": dict(
        t="Schicht",
        s="Ein Unternehmen produziert nur während einer Schicht — {{shift_hours}} Stunden.",
        b="""Ohne Schicht steht das Unternehmen still: keine Produktion, kein Verschleiß.
1. Unternehmen → Karte des Unternehmens → «Schicht starten».
2. {{shift_hours}} Stunden lang produziert es und verbraucht jede Minute Rohstoffe.
3. Am Schichtende erinnern wir dich — starte die nächste.
> Damit Schichten von selbst starten, aktiviere den Booster «Schicht-Autostart» (Lager → Booster).""",
        show=["Der Status: arbeitet oder steht still.", "Hier ist die Schicht-Taste."],
    ),
    "raw-materials": dict(
        t="Rohstoffe",
        s="Was ein Unternehmen verbraucht und woher du es bekommst.",
        b="""Während der Schicht verbraucht das Unternehmen Rohstoffe — Ressourcen anderer Unternehmen. Wie viel, steht in der Karte rechts, «pro Tag».
- Kauf Rohstoffe auf dem Markt: Handel → «Kaufen».
- Oder schließ eine Ausschreibung ab — die Rohstoffe kommen jeden Tag von selbst.
- Ohne Rohstoffe produziert das Unternehmen weniger.
> Neulinge bekommen mit dem Unternehmen Rohstoffe für einen Tag.""",
        show=["Wie viel das Unternehmen pro Stunde produziert.", "Wie viel Rohstoff es pro Tag verbraucht."],
    ),
    "durability": dict(
        t="Haltbarkeit und Reparatur",
        s="Die 50-%-Grenze: darunter weniger Ware und doppelt teure Reparatur.",
        b="""Während der Schicht nutzt sich das Gebäude ab.
[[table:durability]]
Du zahlst für jeden fehlenden Prozentpunkt. Punkte unter 50 % kosten das Doppelte: bei 1 $CITY pro % kostet die Reparatur ab 46 % 50 + 4×2 = **58 $CITY**.
[[table:repair]]
> Fällt die Haltbarkeit unter 50 %, bekommst du einen Hinweis — im Spiel und in Telegram.""",
        show=["Die aktuelle Haltbarkeit des Gebäudes.", "Die Reparatur-Taste — du zahlst nur die fehlenden Punkte."],
    ),
    "upgrade": dict(
        t='Upgrade',
        s='Höhere Stufe, mehr Ware und Lager; ab Stufe 1 gehört das Unternehmen dir für immer.',
        b="""- **Stufe 0 → 1** kostet den Kartenpreis des Unternehmens, nur vom Hauptkonto. Danach gehört es dir für immer, und die Einnahmen gehen aufs Hauptkonto.
- Dann Stufen bis 10: mehr Ware pro Schicht und ein größeres Lager, aber auch mehr Rohstoffe.
- Ein Upgrade auf Stufe 2 und höher braucht zusätzlich eine Ressource der Stufe 3 — jeder Unternehmenstyp eine eigene:
[[table:upgrade_res]]
- Eine unverkäufliche Belohnungsressource zählt auch.
- Der Preis der nächsten Stufe steht auf der Taste «Upgrade».
> Ein gepachtetes Unternehmen kann nicht verbessert werden.""",
        show=['Die Upgrade-Taste und ihr Preis.'],
    ),
    "chains": dict(
        t="Produktionsketten",
        s="Was woraus entsteht.",
        b="""Ressourcen der Stufe 1 sind Rohstoffe für Stufe 2, und die der Stufe 2 für Stufe 3.
- Die Platzkarte auf der Karte hat eine «Produktionskette»: was das Unternehmen verbraucht und wohin seine Ware geht.
- Bau entlang einer Kette: kauf Rohstoffe bei deinen Kettennachbarn und verkaufe an die, die deine Ware brauchen.""",
    ),
    "patron-buffs": dict(
        t='Unternehmens-Effekte und Förderer',
        s='Ein Unternehmen der Stufe 3 kann Förderer werden und seinen Schützlingen einen Effekt geben.',
        b="""Jedes Unternehmen kann einen Förderer wählen — ein Unternehmen der Stufe 3.
- Der Besitzer des Förderers wählt für die Schützlinge einen der Effekte unten.
- Der Förderer bekommt 1 % der Einnahmen seiner Schützlinge.
- Den Förderer kannst du erst nach einer Pause wechseln.
[[table:patrons]]
- Der Effekt eines Unternehmens steht in seiner Karte.
- Effekte der Ressourcen der Stufe 3 sind etwas anderes: sie werden im Lager aktiviert — siehe [[t3-buffs|Effekte der Ressourcen der Stufe 3]].""",
    ),
    "skins": dict(
        t="Skins",
        s="Ein anderes Aussehen des Unternehmens auf der Karte.",
        b="""Ein Skin ändert nur das Aussehen des Gebäudes auf der Karte, nicht das Unternehmen.
- Skins gibt es für Partneraufgaben.
- Er wird für jedes Unternehmen einzeln gewählt.
- Ein gepachtetes Unternehmen kann den Skin nicht wechseln.""",
    ),
    "business-sale": dict(
        t="Ein Unternehmen verkaufen",
        s="So verkaufst du ein Unternehmen auf dem Marktplatz, und welche Steuer anfällt.",
        b="""Ein Unternehmen ab Stufe 1 kannst du zu deinem Preis auf den Marktplatz stellen.
- Der Verkäufer zahlt eine Steuer nach der Stufe des Unternehmens:
[[table:taxes]]
- Sichert das Unternehmen einen Kredit, zahl zuerst den Kredit zurück.
- Ein verpachtetes Unternehmen kann während der Pacht nicht verkauft werden.
> Ein Unternehmen der Stufe 0 ist nicht verkäuflich: es gehört dir erst nach dem Upgrade.""",
        show=["Der Marktplatz: der Reiter mit deinen Anzeigen — hier stellst du ein Unternehmen ein."],
    ),
    "rental": dict(
        t="Pacht",
        s="Verpachte dein Unternehmen tageweise oder pachte ein fremdes.",
        b="""Der Besitzer eines Unternehmens ab Stufe 1 kann es verpachten: Preis pro Tag und Dauer bis {{rent_max_days}} Tage.
- Der Pächter friert sofort die Pacht für die ganze Dauer plus eine Kaution ein. Jeden Tag bekommt der Besitzer die Tagespacht abzüglich {{rent_fee}} % Provision.
- Während der Pacht arbeitet das Unternehmen für den Pächter: Ware, Rohstoffe und Reparaturen sind seine.
- Ein gepachtetes Unternehmen kann nicht verkauft, verbessert oder umgeskinnt werden.
- Die Kaution geht an den Pächter zurück, wenn das Unternehmen nicht stark abgenutzt wurde.""",
    ),
    "seizure": dict(
        t="Beschlagnahme",
        s="Wann die Stadt ein Unternehmen einzieht.",
        b="""Ein Unternehmen wird in zwei Fällen beschlagnahmt.
- **Keine Aktivität.** In beliebigen {{act_days}} Tagen musst du {{act_buy}} Stück kaufen oder {{act_sell}} Stück auf dem Markt verkaufen — siehe [[activity-rule|Aktivitätsregel]].
- **Kreditschulden.** Der Kredit ist überfällig und seit {{credit_days}} Tagen gab es keine Zahlung. Jede Zahlung hebt den Verzug auf.
GRAM CITY stellt das beschlagnahmte Unternehmen zum Verkauf. Der Erlös tilgt zuerst die Schuld, der Rest geht an den früheren Besitzer.
> 3 Tage vor einer Beschlagnahme erinnern wir dich im Spiel und in Telegram.""",
    ),
    "resources": dict(
        t="Ressourcen",
        s="Was im Lager liegt und wie sich Ressourcen unterscheiden.",
        b="""Im Lager liegt alles, was deine Unternehmen produziert und du gekauft hast.
[[table:weights]]
- Unter jeder Ressource — was sie jetzt wert ist.
- Ressourcen der Stufe 3 kannst du verkaufen oder als Effekt aktivieren.
- Eine als Belohnung erhaltene Ressource liegt getrennt: sie ist nicht verkäuflich.""",
        show=["Das Lager: Platz und Wert deiner Ressourcen."],
    ),
    "capacity": dict(
        t="Kapazität und Gewichte",
        s="Wie viel ins Lager passt.",
        b="""Der Lagerplatz ist begrenzt. Die Kapazität ist die Summe der Lager all deiner Unternehmen; höhere Stufe, größeres Lager.
[[table:weights]]
- Angebote auf dem Markt belegen ebenfalls Platz.
- Was nicht hineinpasst, verdirbt schneller — siehe [[spoilage|Verderb]].""",
        show=["Belegter und freier Lagerplatz."],
    ),
    "warehouse-value": dict(
        t="Geschätzter Lagerwert",
        s="Was alles, was du hast, wert ist.",
        b="""Über der Ressourcenliste steht der geschätzte Lagerwert: was alle deine Ressourcen zu aktuellen Preisen kosten würden.
- Unter jeder Ressource ihr Wert.
- Es ist eine Schätzung: der echte Preis ist der, zu dem du verkaufst.""",
        show=["Der geschätzte Wert des ganzen Lagers."],
    ),
    "spoilage": dict(
        t="Verderb um {{spoil_time}}",
        s="Jeden Tag verdirbt ein Teil der Ware im Lager.",
        b="""Jeden Tag um **{{spoil_time}} Uhr Moskauer Zeit** verderben **{{spoil_in}} %** der Ware im Lager und **{{spoil_over}} %** von allem über dem Limit.
- Der Verderb trifft alle Ressourcen gleich.
- Angebote auf dem Markt verderben nicht.
- Der Booster «Lagerschutz» verhindert ihn.
> Nicht horten — verkaufe vor {{spoil_time}} Uhr. Abends schicken wir eine Erinnerung.""",
        show=["Das Lager: was hier liegt, verdirbt um {{spoil_time}} Uhr."],
    ),
    "boosters": dict(
        t='Booster',
        s='Schicht-Autostart, Lagerschutz, alles reparieren, ×2 EP — was sie bringen.',
        b="""Booster aktivierst du unter Lager → Booster. Sie sind nicht verkäuflich.
[[table:boosters]]
- Ressourcen der Stufe 3 werden auch hier aktiviert — jede mit eigenem Effekt, siehe [[t3-buffs|Effekte der Ressourcen der Stufe 3]].
- Höchstens zwei Booster und Effekte wirken gleichzeitig.
> Booster sind Belohnungen des City Pass: einer auf jeder Stufe, auf dem Premium-Pfad mehr.""",
        show=['Der Reiter «Booster»: was du hast und was gerade wirkt.'],
    ),
    "t3-buffs": dict(
        t='Effekte der Ressourcen der Stufe 3',
        s='Was jede Ressource der Stufe 3 bringt und wie du sie aktivierst.',
        b="""Jede Ressource der Stufe 3 lässt sich als Effekt aktivieren — ein zeitweiser Vorteil für alle deine Unternehmen.
[[table:t3buffs]]
1. Lager → Booster.
2. Tippe neben der Ressource auf «Aktivieren» — 1 Stück wird verbraucht.
3. Der Effekt wirkt die angegebene Zeit; die Restzeit steht unter «Gerade aktiv».
- Woher: Unternehmen der Stufe 3 produzieren sie, Spieler verkaufen sie auf dem Markt, der City Pass gibt sie als Belohnung. Eine gibt es gratis für den [[first-days|3-Tage-Plan]].
- Eine Belohnungsressource ist nicht verkäuflich, lässt sich aber als Effekt aktivieren oder für ein [[upgrade|Upgrade]] ausgeben.
- Derselbe Effekt kann nicht doppelt laufen; höchstens zwei Booster und Effekte gleichzeitig.
> Eine Ressource aktiviert sich nie von selbst: sie wartet im Lager, bis du «Aktivieren» tippst.""",
        show=['Der Reiter «Booster»: Ressourcen der Stufe 3 und die Taste «Aktivieren».'],
    ),
    "buy": dict(
        t="Eine Ressource kaufen",
        s="Angebote der Spieler, Filter und Bezahlung.",
        b="""Handel → «Kaufen» — Angebote anderer Spieler und der Stadt.
1. Such eine Ressource: Filter nach Ressource, Preis und Menge.
2. Tippe auf ein Angebot und gib die Menge ein — beliebig viele Stück.
3. Prüfe die Summe und bestätige.
- Der Preis gilt **pro Stück**.
- Bezahlung: zuerst Bonuskonto, dann Hauptkonto.
- Die Ressource kommt direkt ins Lager — prüfe, ob Platz ist.""",
        show=["Der Reiter «Kaufen» — Angebote der Spieler.", "Filter: Ressource, Preis, Menge."],
    ),
    "sell": dict(
        t="Eine Ressource verkaufen",
        s="Ein Angebot, der Preis, die Steuer, {{lot_hours}} Stunden.",
        b="""Stell Ware aus dem Lager ein — alle Spieler sehen sie. Ein Spieler oder die Stadt kann kaufen.
1. Handel → Reiter «Meine».
2. «Ressource verkaufen» und die Ware wählen.
3. Menge eingeben – beliebig viele Stück. Der Preis gilt pro Stück; Stufe 1 auf den Cent.
4. Preis und Nettobetrag prüfen.
5. «Einstellen».
[[table:taxes]]
> Ein unverkauftes Angebot kommt nach {{lot_hours}} Stunden ins Lager zurück. Auf dem Markt belegt es Lagerplatz, verdirbt aber nicht.""",
        show=["Tippe auf «Ressource verkaufen» — das Verkaufsfenster öffnet sich."],
    ),
    "edit-lot": dict(
        t="Angebot ändern oder zurückziehen",
        s="Menge und Preis ändern, ohne das Angebot zurückzuziehen.",
        b="""Im Reiter «Meine» hat jedes Angebot zwei Tasten.
- **«Ändern»** — Menge oder Preis ändern. Beliebige Menge ab 1 Stück.
- **«Abbrechen»** — Angebot zurückziehen; die Ware geht ins Lager zurück.
- Die Zahl der Angebote ist begrenzt: ein Platz pro Unternehmen, ohne Unternehmen einer.
> Bei einem Unternehmen der Stufe 0 ist der Preis fest — es ist der Systempreis.""",
        show=["Deine Angebote: «Ändern» und «Abbrechen»."],
    ),
    "city-market": dict(
        t="Die Stadt auf dem Markt",
        s="Was die Stadt kauft und wann.",
        b="""Der Stadtmarkt ist ein Sicherheitsnetz für Neulinge und einen dünnen Markt. Er kauft unter und verkauft über dem Tabellenpreis — mit Spielern verdienst du mehr.
- Die Stadt kauft nur Ressourcen der **Stufe 1**.
- Den ersten Verkauf eines Neulings kauft sie fast sofort.
- Angebote eines Unternehmens der Stufe 0 kauft sie zum Systempreis — das Geld geht aufs Bonuskonto.
- Ab Stufe 1: Angebote zu ihrem Preis oder darunter; das Geld geht aufs Hauptkonto.
- Alles Gekaufte stellt die Stadt wieder auf den Markt.""",
    ),
    "tenders": dict(
        t="Ausschreibungen",
        s="Ein Vertrag über tägliche Lieferung.",
        b="""Eine Ausschreibung ist eine Bestellung: «ich brauche X Stück einer Ressource pro Tag zu diesem Preis».
1. Handel → «Verträge» → «Börse»: offene Bestellungen der Spieler.
2. Schick ein Angebot. Ohne Antwort schließt es nach 72 Std.
3. Wird es angenommen, geht die Ressource täglich von selbst raus und das Geld kommt ohne Angebote (abzüglich Steuer).
- «Einkäufe» — deine Bestellungen, «Lieferungen» — deine Verträge.
> Fehlt Ware oder Geld, hast du 24 Stunden Zeit; danach platzt der Vertrag mit einer Strafe.""",
        show=["Öffne «Verträge».", "«Börse» — offene Bestellungen der Spieler."],
    ),
    "contracts": dict(
        t="Kooperationsverträge",
        s="Lieferung zwischen Unternehmen — und der Effekt des Förderers.",
        b="""Ein Kooperationsvertrag ist eine tägliche Lieferung einer Ressource von einem Unternehmen an ein anderes, bis zu 90 Tage.
- Der Lieferant legt Ressource, Tagesmenge, Preis und Dauer fest.
- Ist der Lieferant ein Unternehmen der Stufe 3, wirkt sein Effekt auf das empfangende Unternehmen, solange der Vertrag läuft.
- Er kann jederzeit gekündigt werden; Geliefertes bleibt beim Empfänger.""",
    ),
    "analytics": dict(
        t="Preisanalyse",
        s="Diagramme, Trends, Volumen.",
        b="""Analyse — Preisdiagramme für jede Ressource.
- Wo der Verkauf lohnt und was günstiger zu kaufen ist.
- Wie viel pro Tag verkauft wird und wie sich der Preis bewegt.
- Öffnet sich mit der Taste «Analyse» auf dem Bildschirm «Unternehmen».""",
        show=["Tippe auf «Analyse» — die Preisdiagramme öffnen sich."],
    ),
    "taxes": dict(
        t="Steuern",
        s="Sätze nach Stufe und wohin die Steuer geht.",
        b="""Jeder Ressourcenverkauf zahlt eine Steuer nach Stufe der Ressource. Die Verwaltung legt die Sätze fest; unten die aktuellen.
[[table:taxes]]
- Den Nettobetrag siehst du vor dem Einstellen.
- Ein Teil der Steuer ({{ref_pct}} % des Geschäfts) geht an den, der den Verkäufer eingeladen hat — der Verkäufer verliert nichts.
- Effekte von Ressourcen der Stufe 3 können die Handelsgebühr senken.""",
    ),
    "deposit": dict(
        t="Aufladen",
        s="So kommen GRAM aufs Hauptkonto.",
        b="""1. Tippe auf das Guthaben → «Aufladen».
2. Verbinde eine Wallet: Tonkeeper, Telegram Wallet oder eine andere.
3. Sende GRAM. **GRAM ist die TON-Münze — sende nur TON.**
4. Das Geld kommt aufs Hauptkonto: 1 GRAM = {{city_per_gram}} $CITY.
> Sende nur von der Wallet, die mit deinem Konto verbunden ist.""",
        show=["Tippe auf das Guthaben — dort ist «Aufladen»."],
    ),
    "withdraw": dict(
        t="Auszahlung",
        s="Was auszahlbar ist und was du dafür brauchst.",
        b="""Auszahlbar ist nur das **Hauptkonto**, das Bonuskonto nicht.
1. Tippe auf das Guthaben → «Abheben».
2. Gib den Betrag ein (ab {{withdraw_min}} GRAM) und bestätige mit einem 2FA-Code oder Passkey.
3. Der Antrag wird geprüft und an deine Wallet geschickt.
- Die Gebühr beträgt {{withdraw_fee}} %. Über die Bank eines Spielers geht es schneller, mit der Gebühr der Bank (bis {{instant_fee_max}} %).""",
        show=["Tippe auf das Guthaben — dort ist «Abheben»."],
    ),
    "security": dict(
        t="Warum 2FA und Passkey",
        s="Ohne sie keine Auszahlung — und das ist der Grund.",
        b="""Die Auszahlungs-Wallet wird in den Einstellungen geändert. Wer in dein Konto gelangt — Telefon, E-Mail oder Telegram —, könnte seine eigene verknüpfen.
- **2FA** — ein Code aus einer Authenticator-App.
- **Passkey** — Fingerabdruck oder Gesicht auf deinem Gerät.
Ohne Code oder Passkey geht keine Auszahlung durch.
> Der Support fragt nie nach Codes, Passwörtern oder der Seed-Phrase.""",
        show=["Schalte 2FA ein — ein Code aus einer App.", "Oder füge einen Passkey hinzu — Fingerabdruck oder Gesicht."],
    ),
    "history": dict(
        t="Verlauf",
        s="Jeder Kauf, Verkauf, jede Steuer und Belohnung.",
        b="""Menü ☰ → Verlauf — alle Vorgänge auf deinem Guthaben.
- Filter nach Typ: Käufe, Verkäufe, Steuern, Belohnungen, Aufladungen, Auszahlungen.
- Jeder Vorgang zeigt Betrag, Konto (Haupt- oder Bonuskonto) und Uhrzeit.""",
        show=["Filter nach Vorgangstyp."],
    ),
    "credit": dict(
        t="Kredit gegen ein Unternehmen",
        s="Geld jetzt, ein Teil der Einnahmen zahlt ihn zurück.",
        b="""Nimm $CITY mit einem Unternehmen als Sicherheit auf — beim Staat oder bei der Bank eines Spielers. Ein Teil deiner Einnahmen tilgt ihn von selbst.
- Nur gegen ein Unternehmen ab Stufe 1, bis {{credit_max}} % seines Werts.
[[table:credit]]
- {{credit_days}} Tage keine Zahlung (eine Bank legt ihre eigene Frist fest) — der Kredit ist überfällig, der Zins verdoppelt sich.
- Weitere {{credit_days}} Tage Verzug ohne eine Zahlung — das Unternehmen wird beschlagnahmt. Jede Zahlung hebt den Verzug auf.
- Das beschlagnahmte Unternehmen wird verkauft; aus dem Erlös gehen Kredit und doppelter Zins ab: Zins {{credit_rate}} % → Kredit × {{credit_back}}. Der Rest gehört dir.""",
        show=["Die Taste «Kredit aufnehmen»."],
    ),
    "banks": dict(
        t="Banken der Spieler",
        s="GRAM Bank: Kredite und schnelle Auszahlungen von Spielern.",
        b="""Der Besitzer eines GRAM-Bank-Unternehmens ist eine Bank.
- Er verleiht an Spieler zu seinem Zins (höchstens {{bank_rate_max}} %).
- Er wickelt schnelle Auszahlungen mit eigener Gebühr ab (bis {{instant_fee_max}} %).
- Es arbeiten nur Banken mit mindestens 50 % Haltbarkeit.""",
    ),
    "daily-login": dict(
        t="Täglicher Login",
        s="Die Belohnung wächst {{daily_days}} Tage in Folge.",
        b="""Komm jeden Tag — die Belohnung wächst: von {{daily_first}} bis {{daily_last}} $CITY am Tag {{daily_days}}.
- Um sie abzuholen, erfülle ein Tagesziel.
- Verpasst du einen Tag, beginnt die Serie neu. Ein Serienschild rettet einen verpassten Tag.
- Belohnungen gehen aufs Bonuskonto.""",
        show=["Die Karte des täglichen Logins."],
    ),
    "quests": dict(
        t="Aufgaben und Ziele",
        s="Einsteigerweg, Tages- und Wochenziele.",
        b="""- **Einsteigerweg** — 7 Ziele nacheinander: Unternehmen, Schicht, Kauf, Angebot, Verkauf, Reparatur, Upgrade.
- **Tagesziele** — 3 pro Tag, **Wochenziele** — 3 weitere.
- Der Fortschritt zählt sich selbst — tippe nur auf «Abholen».
- Belohnungen aufs Bonuskonto und als City-Pass-EP. Alle Wochenziele bringen einen Serienschild.""",
        show=["Die Ziele des Tages."],
    ),
    "partner-tasks": dict(
        t="Partneraufgaben",
        s="Abos und Aktionen bei Partnern — für $CITY und Skins.",
        b="""Aufgaben → «Partner»: einen Kanal abonnieren, die App eines Partners öffnen u. a.
- Die Belohnung sind $CITY aufs Bonuskonto, manchmal ein Skin.
- Manche Aufgaben brauchen ein verbundenes Telegram.""",
        show=["Der Reiter mit Partneraufgaben."],
    ),
    "city-pass": dict(
        t="City Pass",
        s="Eine Saison mit {{pass_levels}} Stufen: EP und Belohnungen.",
        b="""City Pass ist eine Saison mit {{pass_levels}} Stufen.
- EP gibt es für Tages- und Wochenziele, Schichten, Reparaturen, Verkäufe an Spieler und die Login-Serie.
- **Gratis-Pfad** — eine Belohnung auf jeder Stufe: Booster, Ressourcen der Stufe 3, Schilde.
- **Premium** — zusätzliche Belohnungen auf den Stufen 1, 5, 10…; wird vom Hauptkonto gekauft.
- Hol Belohnungen mit der Taste «Abholen» ab.""",
        show=["Deine Stufe und die Saison-EP."],
    ),
    "referrals": dict(
        t="Empfehlungen",
        s="Lade Freunde ein — bekomm einen Teil der Steuer auf ihre Verkäufe.",
        b="""Die Taste 👥 oben auf «Unternehmen» enthält deinen Link.
- Ein Freund spielt über deinen Link — du bekommst {{ref_pct}} % der Summe seiner Marktverkäufe.
- Das ist ein Teil der Steuer: dein Freund verliert nichts.
- Dort siehst du auch die Eingeladenen und was sie gebracht haben.""",
        show=["Tippe auf 👥 — dein Link und deine Freunde öffnen sich."],
    ),
    "chat": dict(
        t="Chat",
        s="Der allgemeine Chat und der Allianz-Chat.",
        b="""Der allgemeine Chat aller Spieler und der Chat deiner Allianz.
- Verabrede Geschäfte und teile Tipps.
- Jede Nachricht lässt sich per Taste übersetzen.
- Folge keinen fremden Links und teile nie Codes — siehe [[safety|Sicherheit]].""",
        show=["Chat-Kanäle: allgemein und Allianz."],
    ),
    "leagues": dict(
        t="Ligen",
        s="Ein wöchentlicher Wettbewerb unter Gleichen.",
        b="""Jede Woche bist du in einer Gruppe gleich starker Spieler.
- Punkte für Ziele, Schichten, Reparaturen, Verkäufe an Spieler und die Login-Serie.
- Die Besten steigen auf: Bronze → Silber → Gold → Platin → Diamant.
- **‹ ›** — andere Ligen, **«Ganze Division»** — alle Spieler, Suche und Freunde.
- Wochenpreise — $CITY aufs Bonuskonto und Serienschilde.
> Verkäufe an die Stadt und zwischen verknüpften Konten zählen nicht.""",
        show=["Blättere mit den Pfeilen durch die Ligen.", "Der Ranglisten-Schalter."],
    ),
    "alliances": dict(
        t="Allianzen",
        s="Teams von Spielern: Kasse, Chat, Stufen.",
        b="""Eine Allianz ist ein Team: gemeinsame Kasse, Chat und Stufen.
- Beitreten kannst du sofort — offen, auf Anfrage oder per Einladung.
- Eine eigene gründen: City Pass Stufe {{alliance_level}}, ein Unternehmen und {{alliance_cost}} $CITY.
- Allianz-EP sind 10 % der City-Pass-EP der Mitglieder; du verlierst nichts.
- Auszahlungen aus der Kasse gehen aufs Bonuskonto.""",
        show=["Der Reiter «Allianz»."],
    ),
    "leaderboard": dict(
        t="Rangliste",
        s="Die Besten nach Guthaben, Einnahmen, Unternehmen und Handel.",
        b="""Die Rangliste zeigt die besten Spieler. Sortierung:
- nach Guthaben, Einnahmen, Zahl der Unternehmen, Zahl der Grundstücke, Handelsvolumen.
- Dein Platz steht unten in der Liste.""",
    ),
    "profile": dict(
        t="Spielerprofil",
        s="Statistik, Allianz, Founder Pass.",
        b="""Tippe auf deinen Avatar — dein Profil öffnet sich: Statistik, Allianz, City-Pass-Stufe.
- Profile anderer Spieler öffnen sich aus dem Chat und den Ranglisten.""",
        show=["Dein Profil."],
    ),
    "activity-rule": dict(
        t="Aktivitätsregel",
        s="Die Stadt nimmt Unternehmen von denen, die nicht handeln.",
        b="""In beliebigen **{{act_days}} Tagen** musst du **{{act_buy}} Stück kaufen** oder **{{act_sell}} Stück verkaufen** auf dem Markt — eines von beiden reicht.
- Bleiben 3 Tage bis zur Beschlagnahme, erinnern wir dich im Spiel und in Telegram.
- Unten deine Zahlen der letzten {{act_days}} Tage.""",
    ),
    "zero-limits": dict(
        t="Grenzen der Stufe 0",
        s="Was nicht geht, solange das Unternehmen Stufe 0 hat.",
        b="""Solange du ein Unternehmen der Stufe 0 hast:
- kannst du kein anderes Unternehmen kaufen und keinen Kredit aufnehmen;
- ist der Warenpreis der Systempreis, Verkaufserlöse gehen aufs Bonuskonto;
- kannst du das Unternehmen weder verkaufen noch verpachten;
- kann ein anderer Spieler es zum Kartenpreis ×{{zero_mult}} kaufen.
Das Upgrade auf Stufe 1 hebt alle Grenzen auf.""",
    ),
    "safety": dict(
        t="Sicherheit und Betrug",
        s="So verlierst du weder Konto noch Geld.",
        b="""- Der Support fragt **nie** nach 2FA-Codes, Passwörtern oder der Seed-Phrase.
- Folge keinen Links aus privaten Nachrichten «von der Verwaltung».
- Schalte 2FA oder einen Passkey ein — ohne sie keine Auszahlung.
- Handle nur über den Markt und Ausschreibungen: «schick mir Geld, ich schick dir die Ressource» ist Betrug.
> Verdächtige Nachricht? Melde sie im Chat oder schreib dem Support.""",
    ),
    "faq": dict(
        t="Häufige Fragen",
        s="Kurze Antworten auf das Wichtigste.",
        b="""# Warum ist meine Ware verschwunden?
Jeden Tag um {{spoil_time}} Uhr Moskauer Zeit verdirbt ein Teil — siehe [[spoilage|Verderb]]. Ein unverkauftes Angebot kommt nach {{lot_hours}} Stunden ins Lager zurück.
# Warum produziert mein Unternehmen nicht?
Keine Schicht, keine Rohstoffe oder Haltbarkeit bei 0 %.
# Warum kann ich Boni nicht auszahlen?
Das Bonuskonto wird nur im Spiel ausgegeben.
# Warum hat die Stadt mein Angebot nicht gekauft?
Die Stadt kauft nur Stufe 1 und nur zu ihrem Preis oder darunter.
# Wo ist mein Gratis-Unternehmen?
Die Pacht von {{lease_days}} Tagen lief ohne Upgrade ab, oder ein anderer Spieler hat es gekauft.""",
    ),
    "glossary": dict(
        t="Glossar",
        s="Spielbegriffe in einfacher Sprache.",
        b="""= Allianz | Ein Team von Spielern mit Kasse und Chat
= Angebot | Deine Verkaufsanzeige für eine Ressource auf dem Markt
= Ausschreibung | Eine Bestellung über die tägliche Lieferung einer Ressource
= Beschlagnahme | Die Stadt nimmt ein Unternehmen wegen Inaktivität oder Schulden
= Bonuskonto | Spielbelohnungen: im Spiel ausgegeben, nicht auszahlbar
= Booster | Ein zeitweiser Effekt: Schicht-Autostart, Lagerschutz u. a.
= Effekt | Ein zeitweiser Vorteil: mehr Ware oder weniger Kosten
= Escrow | Für ein Geschäft eingefrorenes Geld
= Förderer | Ein Unternehmen der Stufe 3, dessen Effekt auf Vertragspartner wirkt
= GRAM | Die TON-Münze im Spiel
= Hauptkonto | Geld, das du aufladen und auszahlen kannst
= Schicht | {{shift_hours}} Stunden, in denen ein Unternehmen produziert und verschleißt
= Stufe | Gruppe von Unternehmen und Ressourcen: 1, 2 oder 3
= Systempreis | Der feste Warenpreis eines Unternehmens der Stufe 0
= Übernehmen | Ein Gratis-Unternehmen der Stufe 0 für {{lease_days}} Tage nehmen
= Verderb | Der tägliche Verlust eines Teils der Ware um {{spoil_time}} Uhr Moskauer Zeit
= $CITY | Die Spielwährung: 1 GRAM = {{city_per_gram}} $CITY""",
    ),
    "support": dict(
        t="Support",
        s="Willy GRAM und echte Mitarbeiter.",
        b="""Menü ☰ → Hilfe — der Support-Chat.
- Zuerst antwortet **Willy GRAM** — ein Assistent mit der Antwortdatenbank. Er prüft dein Konto und schickt den Link zum Artikel.
- Bei Bedarf übernimmt ein Mensch.
- Schreib in deiner Sprache — die Antwort kommt in derselben.
> Der Support fragt nie nach Codes oder der Seed-Phrase.""",
        show=["Das Menü ☰ — dort ist «Hilfe»."],
    ),
}
