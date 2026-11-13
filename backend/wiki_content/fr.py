# Wiki de GRAM City — français.
A = {
    "quick-start": dict(
        t="Démarrage rapide",
        s="Cinq étapes, de votre première visite à une entreprise à vous pour toujours.",
        b="""GRAM City est un jeu d’économie : les entreprises produisent des ressources, vous les vendez à la Ville et aux joueurs, et vous grandissez.
1. Prenez une entreprise gratuitement : Carte → « En vente ». Elle est à vous pour {{lease_days}} jours.
2. Lancez un quart : l’entreprise travaille {{shift_hours}} heures et dépose des marchandises à l’entrepôt.
3. Vendez-les : Commerce → « Mes » → « Vendre une ressource ».
4. Réparez l’entreprise avant que la durabilité passe sous 50 %.
5. Avant la fin du bail, passez l’entreprise au niveau 1 : elle reste à vous pour toujours.
> Ci-dessous, la vérification de votre compte : ce qui est fait et la suite.""",
    ),
    "balances": dict(
        t="Monnaies et soldes",
        s="$CITY, GRAM et trois comptes : principal, bonus et gelé.",
        b="""Tout le jeu se compte en **$CITY** : 1 GRAM = {{city_per_gram}} $CITY. GRAM est la monnaie TON : rechargez uniquement en TON.
- Compte **principal** : vous le rechargez et retirez depuis lui. Les ventes des entreprises de niveau 1 et plus y arrivent.
- **Bonus** : récompenses du jeu et ventes d’une entreprise de niveau 0. Dépensé dans le jeu, non retirable.
- **Gelé** : l’argent réservé à vos accords : appels d’offres, locations. Il revient ou part selon l’accord.
> Chaque achat prend d’abord le compte bonus, puis le principal. Les bonus servent, et ce que vous pouvez retirer vous reste.""",
        show=["Touchez le solde : les trois comptes et les boutons de recharge et de retrait s’ouvrent."],
    ),
    "earning": dict(
        t="Comment gagner",
        s="Ventes, contrats, locations et croissance de l’entreprise.",
        b="""- **Vendre des ressources** sur le marché, aux joueurs et à la Ville. Le revenu principal.
- **Appels d’offres** : un accord de livraison quotidienne ; la ressource part seule, l’argent arrive sans lots.
- **Location** : louez une entreprise de niveau 1 ou plus à la journée.
- **Améliorations** : plus le niveau est haut, plus il y a de marchandises par quart.
- **Chaînes** : les ressources d’échelon 1 alimentent l’échelon 2, qui alimente l’échelon 3. Achetez les intrants moins cher, vendez plus cher.
> Attention à la taxe : chaque vente paie une taxe selon l’échelon de la ressource ; voir [[taxes|Taxes]].""",
    ),
    "interface": dict(
        t="L’interface",
        s="Le menu du bas, le menu ☰ et le bouton « ? » des écrans.",
        b="""En bas, cinq sections :
- **Carte** : villes et parcelles.
- **Entrepôt** : vos ressources et boosts.
- **Entreprises** : votre production : quarts, réparations, améliorations.
- **Commerce** : le marché, vos lots, les appels d’offres.
- **Communauté** : ligues, alliances, chat.
Le menu ☰ contient le Wiki, l’Historique, les Récompenses, le Marketplace, les Réglages, l’Aide, les Règles et la Feuille de route.
> Chaque écran sauf « Entreprises » a un bouton « ? » dans l’en-tête : il ouvre les articles sur cet écran.""",
        show=["Les cinq sections du jeu. Sur ordinateur, elles sont dans la barre latérale gauche.", "Le menu ☰ : Wiki, Historique, Réglages, Aide et plus."],
    ),
    "first-days": dict(
        t='Le plan de vos 3 premiers jours',
        s='Que faire pour que l’entreprise gratuite reste à vous pour toujours.',
        b="""L’entreprise gratuite est à vous pour {{lease_days}} jours. Pour la garder :
1. Prenez une entreprise sur la carte.
2. Lancez un quart et obtenez le premier lot de marchandises.
3. Vendez les marchandises.
4. Lancez un quart toutes les {{shift_hours}} heures ; nous vous le rappellerons.
5. Réparez quand la durabilité baisse.
6. Avant la fin du bail, passez l’entreprise au niveau 1 avec des $CITY du compte principal.
> La récompense du plan est une ressource d’échelon 3 au choix. Elle va à l’entrepôt : invendable ; activez son effet vous-même quand vous voulez, ou utilisez-la pour une amélioration.""",
    ),
    "notifications": dict(
        t="Notifications et réglages",
        s="Les rappels, les heures calmes, le bot Telegram et la langue.",
        b="""Dans les Réglages, choisissez vos rappels : fin de quart, usure sous 50 %, entrepôt avant la détérioration, prix, ventes.
- **Heures calmes** : pas de notifications la nuit.
- **Bot Telegram** : les notifications arrivent aussi dans Telegram.
- **« Premiers jours »** : des conseils pour débutants, pas plus de 3 par jour.
- La langue du jeu et « Refaire le guide » sont aussi ici.""",
        show=["Activez ou coupez les notifications par thème ici."],
    ),
    "maps": dict(
        t="Cartes et villes",
        s="Lire la carte : filtres, zoom, mini-carte, « En vente ».",
        b="""L’**Île GRAM** est ouverte ; les autres villes sont en construction.
- **Filtre** par type d’entreprise ; **★** : survoler vos entreprises ; **%** : ne garder que ce qui est en vente.
- **+ / −** : zoom, **⌂** : retour au centre.
- **Mini-carte** : touchez-la et la caméra s’y rend.
- **« En vente »** en bas : toutes les entreprises que vous pouvez occuper ou acheter maintenant.
- **🌙** : mode nuit ; votre choix est mémorisé.""",
        show=["Choisissez une ville : sa carte s’ouvre."],
    ),
    "zero-business": dict(
        t="Entreprise de niveau 0",
        s="Une entreprise gratuite de la Ville pour {{lease_days}} jours : comment ça marche.",
        b="""La Ville offre une entreprise à chaque débutant : Carte → « En vente » → « Occuper gratuitement ».
- Elle est à vous pour **{{lease_days}} jours**. Pour la garder, passez-la au niveau 1. Le prix est celui de cette entreprise sur la carte, depuis le compte principal uniquement.
- Le prix des marchandises est le **prix système** et ne change pas. L’argent des ventes va au compte bonus.
- Tant qu’elle est au niveau 0, un autre joueur peut l’acheter au prix de la carte ×{{zero_mult}}. Elle devient alors la sienne et vous pouvez en prendre une autre.
- Sans amélioration avant la fin, l’entreprise revient à la Ville et la parcelle est libérée. Nous prévenons 24, 12 et 2 heures avant.
> Vous ne pouvez prendre une entreprise gratuite que si vous n’avez jamais eu d’entreprise de niveau 1.""",
        show=["Touchez « En vente » : la liste des entreprises offertes par la Ville s’ouvre."],
    ),
    "plots": dict(
        t="Parcelles",
        s="Chaque entreprise a sa place sur la carte.",
        b="""La carte est divisée en emplacements, chacun avec une entreprise d’un type donné. Le type se voit sur la carte et dans la fiche de l’emplacement.
- Un emplacement libre peut être occupé (gratuit pour {{lease_days}} jours) ou acheté.
- Le prix dépend du type d’entreprise et de l’emplacement : plus c’est près du centre, plus c’est cher.
- La fiche montre ce que l’entreprise produit et consomme, et la chaîne de production.""",
    ),
    "buy-business": dict(
        t="Acheter une entreprise",
        s="Une entreprise de niveau 1 est à vous pour toujours, avec les revenus sur le compte principal.",
        b="""Achetez sur la carte (un emplacement libre) ou sur le Marketplace (l’entreprise d’un autre joueur).
- L’entreprise achetée est aussitôt de niveau 1 et à vous pour toujours.
- Paiement : d’abord le compte bonus, puis le principal.
- Tant que vous avez une entreprise de niveau 0, vous ne pouvez pas en acheter d’autres : améliorez-la d’abord.
- Choisissez selon la chaîne : ce que vous achèterez comme intrants et qui achètera vos marchandises.""",
        show=["Le Marketplace : entreprises de joueurs à vendre, vos annonces et les locations."],
    ),
    "districts": dict(
        t="Quartiers et emplacements en vente",
        s="Pourquoi on ne peut pas acheter n’importe quel emplacement.",
        b="""La ville s’ouvre quartier par quartier. Vous ne pouvez acheter qu’un emplacement d’un quartier ouvert, parmi ceux déjà mis en vente.
- Les nouveaux quartiers et emplacements s’ouvrent peu à peu : suivez « En vente » et les annonces.
- Un quartier fermé se voit sur la carte, mais rien ne s’y achète encore.""",
    ),
    "tiers": dict(
        t="Échelons d’entreprise",
        s="Échelons 1, 2 et 3 : ce qu’ils produisent et leurs différences.",
        b="""Entreprises et ressources se répartissent en trois échelons.
- **Échelon 1** : ressources de base : énergie, métal, quartz, biomasse… La Ville les achète aussi.
- **Échelon 2** : produits faits de ressources d’échelon 1 : puces, modèles d’IA… Les joueurs les achètent.
- **Échelon 3** : ressources rares qui activent des effets.
Plus l’échelon est haut, plus marchandises et réparations coûtent cher, et plus elles prennent de place à l’entrepôt.
[[table:taxes]]""",
    ),
    "shift": dict(
        t="Quart",
        s="Une entreprise ne produit que pendant un quart : {{shift_hours}} heures.",
        b="""Sans quart, l’entreprise est à l’arrêt : ni production ni usure.
1. Entreprises → fiche de l’entreprise → « Démarrer le quart ».
2. Pendant {{shift_hours}} heures elle produit et consomme des intrants chaque minute.
3. À la fin du quart, nous vous prévenons : lancez le suivant.
> Pour que les quarts démarrent seuls, activez le boost « Démarrage auto des quarts » (Entrepôt → Boosts).""",
        show=["L’état de l’entreprise : en marche ou à l’arrêt.", "Le bouton du quart est ici."],
    ),
    "raw-materials": dict(
        t="Intrants",
        s="Ce qu’une entreprise consomme et où le trouver.",
        b="""Pendant le quart, l’entreprise consomme des intrants : les ressources d’autres entreprises. La quantité figure dans la fiche, à droite, « par jour ».
- Achetez-les sur le marché : Commerce → « Acheter ».
- Ou passez un appel d’offres : ils arriveront seuls chaque jour.
- Sans intrants, l’entreprise produit moins.
> Le débutant reçoit une journée d’intrants avec l’entreprise.""",
        show=["Ce que l’entreprise produit par heure.", "Ce qu’elle consomme par jour."],
    ),
    "durability": dict(
        t="Durabilité et réparation",
        s="Le seuil de 50 % : en dessous, moins de marchandises et réparation au double.",
        b="""Pendant le quart, le bâtiment s’use.
[[table:durability]]
Vous payez chaque point manquant. Les points sous 50 % coûtent double : à 1 $CITY le %, réparer depuis 46 % coûte 50 + 4×2 = **58 $CITY**.
[[table:repair]]
> Quand la durabilité passe sous 50 %, vous recevez un avis, dans le jeu et dans Telegram.""",
        show=["La durabilité actuelle du bâtiment.", "Le bouton de réparation : vous ne payez que les points manquants."],
    ),
    "upgrade": dict(
        t='Amélioration',
        s='Plus de niveau, plus de marchandises et d’entrepôt ; au niveau 1, l’entreprise est à vous pour toujours.',
        b="""- **Niveau 0 → 1** coûte le prix de l’entreprise sur la carte, depuis le compte principal uniquement. Ensuite, elle est à vous pour toujours et les revenus vont au compte principal.
- Puis des niveaux jusqu’à 10 : plus de marchandises par quart et un plus grand entrepôt, mais aussi plus d’intrants.
- Passer au niveau 2 et au-delà demande aussi une ressource d’échelon 3 ; chaque type d’entreprise a la sienne :
[[table:upgrade_res]]
- Une ressource de récompense invendable compte aussi.
- Le prix du niveau suivant figure sur le bouton « Améliorer ».
> Une entreprise louée ne peut pas être améliorée.""",
        show=['Le bouton d’amélioration et son prix.'],
    ),
    "chains": dict(
        t="Chaînes de production",
        s="Ce qui se fabrique avec quoi.",
        b="""Les ressources d’échelon 1 servent d’intrants à l’échelon 2, et celles de l’échelon 2 à l’échelon 3.
- La fiche d’un emplacement sur la carte a une « Chaîne de production » : ce que l’entreprise consomme et où va sa production.
- Construisez le long d’une chaîne : achetez vos intrants à vos voisins de chaîne et vendez à ceux qui ont besoin de vos marchandises.""",
    ),
    "patron-buffs": dict(
        t='Effets d’entreprise et mécènes',
        s='Une entreprise d’échelon 3 peut devenir mécène et donner un effet à ses protégées.',
        b="""Toute entreprise peut choisir un mécène : une entreprise d’échelon 3.
- Le propriétaire du mécène choisit pour ses protégées un des effets ci-dessous.
- Le mécène reçoit 1 % des revenus de ses protégées.
- Le mécène ne peut être changé qu’après une pause.
[[table:patrons]]
- L’effet d’une entreprise se voit dans sa fiche.
- Les effets des ressources d’échelon 3 sont autre chose : ils s’activent dans l’entrepôt ; voir [[t3-buffs|Effets des ressources d’échelon 3]].""",
    ),
    "skins": dict(
        t="Apparences",
        s="Un autre aspect de l’entreprise sur la carte.",
        b="""Une apparence change l’aspect du bâtiment sur la carte, sans effet sur l’entreprise.
- On les obtient avec les tâches partenaires.
- Elle se choisit pour chaque entreprise séparément.
- Une entreprise louée ne peut pas changer d’apparence.""",
    ),
    "business-sale": dict(
        t="Vendre une entreprise",
        s="Vendre une entreprise sur le Marketplace et la taxe prélevée.",
        b="""Une entreprise de niveau 1 ou plus peut être mise en vente sur le Marketplace à votre prix.
- Le vendeur paie une taxe selon l’échelon de l’entreprise :
[[table:taxes]]
- Si l’entreprise garantit un prêt, remboursez d’abord le prêt.
- Une entreprise louée ne peut pas être vendue pendant la location.
> Une entreprise de niveau 0 ne se vend pas : elle n’est pas à vous tant que vous ne l’améliorez pas.""",
        show=["Le Marketplace : l’onglet de vos annonces ; c’est ici qu’on met une entreprise en vente."],
    ),
    "rental": dict(
        t="Location",
        s="Louez votre entreprise à la journée ou celle d’un autre.",
        b="""Le propriétaire d’une entreprise de niveau 1 ou plus peut la louer : un prix par jour et une durée jusqu’à {{rent_max_days}} jours.
- Le locataire gèle aussitôt le loyer de toute la durée plus un dépôt. Chaque jour, le propriétaire reçoit le loyer du jour moins {{rent_fee}} % de commission.
- Pendant la location, l’entreprise travaille pour le locataire : marchandises, intrants et réparations sont à lui.
- Une entreprise louée ne peut être ni vendue, ni améliorée, ni changer d’apparence.
- Le dépôt revient au locataire sauf si l’entreprise est très usée.""",
    ),
    "seizure": dict(
        t="Saisie",
        s="Quand la Ville reprend une entreprise.",
        b="""Une entreprise est saisie dans deux cas.
- **Pas d’activité.** Sur toute période de {{act_days}} jours, il faut acheter {{act_buy}} unités ou en vendre {{act_sell}} sur le marché ; voir [[activity-rule|Règle d’activité]].
- **Dette de prêt.** Le prêt est en retard et aucun paiement depuis {{credit_days}} jours. Tout paiement lève le retard.
GRAM CITY met l’entreprise saisie en vente. La vente rembourse d’abord la dette ; le reste va à l’ancien propriétaire.
> Nous prévenons dans le jeu et dans Telegram 3 jours avant une saisie.""",
    ),
    "resources": dict(
        t="Ressources",
        s="Ce qu’il y a dans l’entrepôt et en quoi les ressources diffèrent.",
        b="""L’entrepôt contient tout ce que vos entreprises ont produit et tout ce que vous avez acheté.
[[table:weights]]
- Sous chaque ressource : sa valeur actuelle.
- Les ressources d’échelon 3 se vendent ou s’activent comme effet.
- Une ressource reçue en récompense est rangée à part : elle ne se vend pas.""",
        show=["L’entrepôt : la place et la valeur de vos ressources."],
    ),
    "capacity": dict(
        t="Capacité et poids",
        s="Ce qui tient dans l’entrepôt.",
        b="""La place est limitée. La capacité est la somme des entrepôts de toutes vos entreprises ; plus de niveau, plus d’entrepôt.
[[table:weights]]
- Les lots sur le marché prennent aussi de la place.
- Ce qui ne tient pas se détériore plus vite ; voir [[spoilage|Détérioration]].""",
        show=["La place occupée et libre de l’entrepôt."],
    ),
    "warehouse-value": dict(
        t="Valeur estimée de l’entrepôt",
        s="Ce que vaut tout ce que vous possédez.",
        b="""Au-dessus de la liste figure la valeur estimée de l’entrepôt : ce que coûteraient toutes vos ressources aux prix actuels.
- Sous chaque ressource, sa valeur.
- C’est une estimation : le vrai prix est celui auquel vous vendez.""",
        show=["La valeur estimée de tout l’entrepôt."],
    ),
    "spoilage": dict(
        t="Détérioration à {{spoil_time}}",
        s="Chaque jour, une partie des marchandises se détériore.",
        b="""Chaque jour à **{{spoil_time}} (heure de Moscou)**, **{{spoil_in}} %** des marchandises de l’entrepôt se détériorent, et **{{spoil_over}} %** de ce qui dépasse la limite.
- Toutes les ressources sont touchées de la même façon.
- Les lots sur le marché ne se détériorent pas.
- Le boost « Protection de l’entrepôt » l’empêche.
> Ne stockez pas : vendez avant {{spoil_time}}. Nous envoyons un rappel le soir.""",
        show=["L’entrepôt : ce qui s’y trouve se détériore à {{spoil_time}}."],
    ),
    "boosters": dict(
        t='Boosts',
        s='Démarrage auto des quarts, protection de l’entrepôt, réparer tout, XP ×2 : ce qu’ils donnent.',
        b="""Les boosts s’activent dans Entrepôt → Boosts. Ils ne se vendent pas.
[[table:boosters]]
- Les ressources d’échelon 3 s’activent aussi ici, chacune avec son effet ; voir [[t3-buffs|Effets des ressources d’échelon 3]].
- Pas plus de deux boosts et effets à la fois.
> Les boosts sont des récompenses du City Pass : un à chaque niveau, davantage sur la voie premium.""",
        show=['L’onglet « Boosts » : ce que vous avez et ce qui est actif.'],
    ),
    "t3-buffs": dict(
        t='Effets des ressources d’échelon 3',
        s='Ce que donne chaque ressource d’échelon 3 et comment l’activer.',
        b="""Chaque ressource d’échelon 3 peut s’activer comme effet : un avantage temporaire pour toutes vos entreprises.
[[table:t3buffs]]
1. Entrepôt → Boosts.
2. Touchez « Activer » à côté de la ressource : 1 unité est consommée.
3. L’effet dure le temps indiqué ; le temps restant est sous « Actifs maintenant ».
- Où les trouver : les entreprises d’échelon 3 les produisent, des joueurs les vendent sur le marché, le City Pass en donne. Une est gratuite pour le [[first-days|plan de 3 jours]].
- Une ressource de récompense ne se vend pas, mais elle peut s’activer comme effet ou servir à une [[upgrade|amélioration]].
- Le même effet ne peut pas tourner deux fois ; pas plus de deux boosts et effets à la fois.
> Une ressource ne s’active jamais seule : elle attend dans l’entrepôt que vous touchiez « Activer ».""",
        show=['L’onglet « Boosts » : les ressources d’échelon 3 et le bouton « Activer ».'],
    ),
    "buy": dict(
        t="Acheter une ressource",
        s="Lots des joueurs, filtres et paiement.",
        b="""Commerce → « Acheter » : les lots des autres joueurs et de la Ville.
1. Trouvez une ressource : filtres par ressource, prix et quantité.
2. Touchez un lot et indiquez la quantité, n’importe quel nombre d’unités.
3. Vérifiez le total et confirmez.
- Le prix est **à l’unité**.
- Paiement : d’abord le compte bonus, puis le principal.
- La ressource va directement à l’entrepôt : vérifiez la place.""",
        show=["L’onglet « Acheter » : les lots des joueurs.", "Filtres : ressource, prix, quantité."],
    ),
    "sell": dict(
        t="Vendre une ressource",
        s="Un lot, le prix, la taxe, {{lot_hours}} heures.",
        b="""Mettez en vente des marchandises de l’entrepôt : tous les joueurs les voient. Un joueur ou la Ville peut acheter.
1. Commerce → onglet « Mes ».
2. « Vendre une ressource » et choisissez la marchandise.
3. Indiquez la quantité : n’importe quel nombre d’unités. Le prix est à l’unité ; l’échelon 1 au centime près.
4. Vérifiez le prix et le montant net.
5. « Publier ».
[[table:taxes]]
> Un lot invendu revient à l’entrepôt après {{lot_hours}} heures. Sur le marché, il occupe l’entrepôt mais ne se détériore pas.""",
        show=["Touchez « Vendre une ressource » : la fenêtre de vente s’ouvre."],
    ),
    "edit-lot": dict(
        t="Modifier ou retirer un lot",
        s="Changer la quantité et le prix sans retirer le lot.",
        b="""Dans l’onglet « Mes », chaque lot a deux boutons.
- **« Modifier »** : changer la quantité ou le prix. N’importe quelle quantité dès 1 unité.
- **« Annuler »** : retirer le lot ; les marchandises reviennent à l’entrepôt.
- Le nombre de lots est limité : un emplacement par entreprise, un seul si vous n’en avez pas.
> Une entreprise de niveau 0 ne peut pas changer le prix : c’est le prix système.""",
        show=["Vos lots : « Modifier » et « Annuler »."],
    ),
    "city-market": dict(
        t="La Ville sur le marché",
        s="Ce que la Ville achète, et quand.",
        b="""Le Marché de la Ville est un filet de sécurité pour les débutants et un marché peu actif. Il achète sous le prix de référence et vend au-dessus : commercer entre joueurs rapporte plus.
- La Ville n’achète que l’**échelon 1**.
- Elle achète la première vente d’un débutant presque tout de suite.
- Elle achète les lots d’une entreprise de niveau 0 au prix système ; l’argent va au compte bonus.
- Pour le niveau 1 et plus : les lots à son prix ou moins ; l’argent va au compte principal.
- Tout ce que la Ville achète, elle le remet sur le marché.""",
    ),
    "tenders": dict(
        t="Appels d’offres",
        s="Un accord de livraison quotidienne.",
        b="""Un appel d’offres est une commande : « il me faut X unités d’une ressource par jour à ce prix ».
1. Commerce → « Contrats » → « Bourse » : les commandes ouvertes des joueurs.
2. Envoyez une offre. Sans réponse, elle se ferme après 72 h.
3. Si elle est acceptée, la ressource part seule chaque jour et l’argent arrive sans lots (moins la taxe).
- « Achats » : vos commandes ; « Livraisons » : vos accords.
> S’il manque des ressources ou de l’argent, vous avez 24 heures pour corriger ; ensuite l’accord est rompu avec une pénalité.""",
        show=["Ouvrez « Contrats ».", "« Bourse » : les commandes ouvertes des joueurs."],
    ),
    "contracts": dict(
        t="Contrats de coopération",
        s="La livraison entre entreprises et l’effet du mécène.",
        b="""Un contrat de coopération est une livraison quotidienne d’une ressource d’une entreprise à une autre, jusqu’à 90 jours.
- Le fournisseur fixe la ressource, la quantité par jour, le prix et la durée.
- Si le fournisseur est une entreprise d’échelon 3, son effet agit sur l’entreprise destinataire tant que dure le contrat.
- On peut l’annuler à tout moment ; ce qui a été livré reste au destinataire.""",
    ),
    "analytics": dict(
        t="Analyse des prix",
        s="Graphiques, tendances, volumes.",
        b="""Analyse : les graphiques de prix de chaque ressource.
- Où vendre au mieux et quoi acheter moins cher.
- Combien se vend par jour et comment le prix évolue.
- S’ouvre avec le bouton « Analyse » de l’écran « Entreprises ».""",
        show=["Touchez « Analyse » : les graphiques de prix s’ouvrent."],
    ),
    "taxes": dict(
        t="Taxes",
        s="Les taux par échelon et où va la taxe.",
        b="""Chaque vente de ressource paie une taxe selon son échelon. L’administration fixe les taux ; voici les taux actuels.
[[table:taxes]]
- Vous voyez le montant net avant de publier le lot.
- Une part de la taxe ({{ref_pct}} % de l’accord) va à celui qui a invité le vendeur : le vendeur ne perd rien.
- Les effets des ressources d’échelon 3 peuvent baisser la commission de commerce.""",
    ),
    "deposit": dict(
        t="Recharge",
        s="Comment mettre des GRAM sur le compte principal.",
        b="""1. Touchez le solde → « Recharger ».
2. Connectez un portefeuille : Tonkeeper, Telegram Wallet ou un autre.
3. Envoyez des GRAM. **GRAM est la monnaie TON : envoyez uniquement des TON.**
4. L’argent arrive sur le compte principal : 1 GRAM = {{city_per_gram}} $CITY.
> N’envoyez que depuis le portefeuille connecté à votre compte.""",
        show=["Touchez le solde : « Recharger » s’y trouve."],
    ),
    "withdraw": dict(
        t="Retrait",
        s="Ce qu’on peut retirer et ce qu’il faut.",
        b="""Seul le compte **principal** se retire ; le bonus, non.
1. Touchez le solde → « Retirer ».
2. Indiquez le montant (à partir de {{withdraw_min}} GRAM) et confirmez par un code 2FA ou une Passkey.
3. La demande est vérifiée puis envoyée à votre portefeuille.
- La commission est de {{withdraw_fee}} %. Via la banque d’un joueur, c’est plus rapide, avec la commission propre de la banque (jusqu’à {{instant_fee_max}} %).""",
        show=["Touchez le solde : « Retirer » s’y trouve."],
    ),
    "security": dict(
        t="Pourquoi la 2FA et la Passkey",
        s="Les retraits en ont besoin, et voici pourquoi.",
        b="""Le portefeuille de retrait se change dans les réglages. Quelqu’un qui entre dans votre compte (téléphone, e-mail ou Telegram) pourrait y lier le sien.
- **2FA** : un code d’une application d’authentification.
- **Passkey** : une empreinte ou votre visage sur l’appareil.
Sans le code ou la Passkey, le retrait ne passe pas.
> Le support ne demande jamais de codes, de mots de passe ni de phrase secrète.""",
        show=["Activez la 2FA : un code d’une application.", "Ou ajoutez une Passkey : empreinte ou visage."],
    ),
    "history": dict(
        t="Historique des opérations",
        s="Chaque achat, vente, taxe et récompense.",
        b="""Menu ☰ → Historique : toutes les opérations sur votre solde.
- Filtre par type : achats, ventes, taxes, récompenses, recharges, retraits.
- Chaque opération indique le montant, le compte (principal ou bonus) et l’heure.""",
        show=["Le filtre par type d’opération."],
    ),
    "credit": dict(
        t="Prêt garanti par une entreprise",
        s="De l’argent maintenant ; une part des revenus le rembourse.",
        b="""Empruntez des $CITY contre une entreprise en garantie, à l’État ou à la banque d’un joueur. Une part de vos revenus rembourse seule.
- Seulement contre une entreprise de niveau 1 ou plus, jusqu’à {{credit_max}} % de sa valeur.
[[table:credit]]
- Aucun paiement pendant {{credit_days}} jours (une banque fixe son propre délai) : le prêt est en retard et le taux double.
- Encore {{credit_days}} jours de retard sans un seul paiement : l’entreprise est saisie. Tout paiement lève le retard.
- L’entreprise saisie est vendue ; on prélève le prêt et le double des intérêts : taux de {{credit_rate}} % → prêt × {{credit_back}}. Le reste est à vous.""",
        show=["Le bouton « Prendre un crédit »."],
    ),
    "banks": dict(
        t="Banques des joueurs",
        s="GRAM Bank : prêts et retraits rapides proposés par des joueurs.",
        b="""Le propriétaire d’une entreprise GRAM Bank est une banque.
- Il prête aux joueurs à son propre taux (pas plus de {{bank_rate_max}} %).
- Il assure des retraits rapides avec sa propre commission (jusqu’à {{instant_fee_max}} %).
- Seules les banques à 50 % de durabilité ou plus fonctionnent.""",
    ),
    "daily-login": dict(
        t="Connexion quotidienne",
        s="La récompense grandit {{daily_days}} jours de suite.",
        b="""Venez chaque jour : la récompense grandit, de {{daily_first}} à {{daily_last}} $CITY au jour {{daily_days}}.
- Pour la récupérer, remplissez un objectif du jour.
- Un jour manqué et la série recommence. Un bouclier de série sauve un jour manqué.
- Les récompenses vont au compte bonus.""",
        show=["La carte de connexion quotidienne."],
    ),
    "quests": dict(
        t="Tâches et objectifs",
        s="Le parcours du débutant, les objectifs du jour et de la semaine.",
        b="""- **Parcours du débutant** : 7 objectifs d’affilée : entreprise, quart, achat, lot, vente, réparation, amélioration.
- **Objectifs du jour** : 3 chaque jour ; **de la semaine** : 3 de plus.
- La progression se compte seule : il reste à toucher « Récupérer ».
- Récompenses sur le compte bonus et en XP City Pass. Tous les objectifs de la semaine donnent un bouclier de série.""",
        show=["Les objectifs du jour."],
    ),
    "partner-tasks": dict(
        t="Tâches partenaires",
        s="Abonnements et actions chez les partenaires, contre des $CITY et des apparences.",
        b="""Tâches → « Partenaires » : s’abonner à une chaîne, ouvrir l’application d’un partenaire, etc.
- La récompense : des $CITY sur le compte bonus, parfois une apparence.
- Certaines tâches demandent un Telegram connecté.""",
        show=["L’onglet des tâches partenaires."],
    ),
    "city-pass": dict(
        t="City Pass",
        s="Une saison de {{pass_levels}} niveaux : XP et récompenses.",
        b="""Le City Pass est une saison de {{pass_levels}} niveaux.
- L’XP vient des objectifs du jour et de la semaine, des quarts, des réparations, des ventes aux joueurs et de la série de connexions.
- **Voie gratuite** : une récompense à chaque niveau : boosts, ressources d’échelon 3, boucliers.
- **Premium** : des récompenses en plus aux niveaux 1, 5, 10… ; s’achète avec le compte principal.
- Récupérez les récompenses avec le bouton « Récupérer ».""",
        show=["Votre niveau et l’XP de la saison."],
    ),
    "referrals": dict(
        t="Parrainage",
        s="Invitez des amis et recevez une part de la taxe sur leurs ventes.",
        b="""Le bouton 👥 en haut de « Entreprises » contient votre lien.
- Un ami joue via votre lien : vous recevez {{ref_pct}} % du montant de ses ventes sur le marché.
- C’est une part de la taxe : votre ami ne perd rien.
- La liste des invités et ce qu’ils ont rapporté s’y trouve aussi.""",
        show=["Touchez 👥 : votre lien et vos amis s’ouvrent."],
    ),
    "chat": dict(
        t="Chat",
        s="Le chat général et celui de l’alliance.",
        b="""Le chat général de tous les joueurs et celui de votre alliance.
- Négociez des affaires et partagez des conseils.
- Tout message se traduit d’un bouton.
- Ne suivez pas les liens d’inconnus et ne partagez jamais vos codes ; voir [[safety|Sécurité]].""",
        show=["Les canaux du chat : général et alliance."],
    ),
    "leagues": dict(
        t="Ligues",
        s="Une compétition hebdomadaire entre égaux.",
        b="""Chaque semaine, vous êtes dans un groupe de joueurs de force égale.
- Des points pour les objectifs, quarts, réparations, ventes aux joueurs et la série de connexions.
- Les meilleurs montent : Bronze → Argent → Or → Platine → Diamant.
- **‹ ›** : les autres ligues ; **« Toute la division »** : tous les joueurs, la recherche et les amis.
- Récompenses de la semaine : $CITY sur le compte bonus et boucliers de série.
> Les ventes à la Ville et entre comptes liés ne comptent pas.""",
        show=["Parcourez les ligues avec les flèches.", "Le sélecteur de classements."],
    ),
    "alliances": dict(
        t="Alliances",
        s="Des équipes de joueurs : trésor, chat, niveaux.",
        b="""Une alliance est une équipe : trésor commun, chat et niveaux.
- Vous pouvez rejoindre tout de suite : ouverte, sur demande ou sur invitation.
- Pour en créer une : niveau {{alliance_level}} du City Pass, une entreprise et {{alliance_cost}} $CITY.
- L’XP de l’alliance vaut 10 % de l’XP City Pass de ses membres ; vous ne perdez rien.
- Les versements du trésor vont au compte bonus.""",
        show=["L’onglet « Alliance »."],
    ),
    "leaderboard": dict(
        t="Classement",
        s="Les meilleurs par solde, revenus, entreprises et commerce.",
        b="""Le classement montre les meilleurs joueurs. Tri :
- par solde, par revenus, par nombre d’entreprises, par nombre de parcelles, par volume de commerce.
- Votre place s’affiche en bas de la liste.""",
    ),
    "profile": dict(
        t="Profil du joueur",
        s="Statistiques, alliance, Founder Pass.",
        b="""Touchez votre avatar : votre profil s’ouvre avec les statistiques, l’alliance et le niveau City Pass.
- Les profils des autres joueurs s’ouvrent depuis le chat et les classements.""",
        show=["Votre profil."],
    ),
    "activity-rule": dict(
        t="Règle d’activité",
        s="La Ville reprend les entreprises de ceux qui ne commercent pas.",
        b="""Sur toute période de **{{act_days}} jours**, il faut **acheter {{act_buy}} unités** ou **en vendre {{act_sell}}** sur le marché : l’un des deux suffit.
- S’il reste 3 jours avant une saisie, nous prévenons dans le jeu et dans Telegram.
- Ci-dessous, vos chiffres des {{act_days}} derniers jours.""",
    ),
    "zero-limits": dict(
        t="Limites du niveau 0",
        s="Ce qui est impossible tant que l’entreprise est au niveau 0.",
        b="""Tant que vous avez une entreprise de niveau 0 :
- impossible d’acheter une autre entreprise ou de prendre un prêt ;
- le prix des marchandises est le prix système, l’argent des ventes va au compte bonus ;
- impossible de vendre ou de louer l’entreprise ;
- un autre joueur peut l’acheter au prix de la carte ×{{zero_mult}}.
Passer au niveau 1 lève toutes ces limites.""",
    ),
    "safety": dict(
        t="Sécurité et arnaques",
        s="Comment ne pas perdre son compte ni son argent.",
        b="""- Le support ne demande **jamais** de codes 2FA, de mots de passe ni de phrase secrète.
- Ne suivez pas les liens de messages privés « de l’administration ».
- Activez la 2FA ou une Passkey : les retraits en ont besoin.
- Commercez uniquement via le marché et les appels d’offres : « envoie l’argent, je t’envoie la ressource » est une arnaque.
> Un message suspect ? Signalez-le dans le chat ou écrivez au support.""",
    ),
    "faq": dict(
        t="Questions fréquentes",
        s="Des réponses courtes à l’essentiel.",
        b="""# Pourquoi mes marchandises ont-elles disparu ?
Chaque jour à {{spoil_time}} (heure de Moscou), une partie se détériore ; voir [[spoilage|Détérioration]]. Un lot invendu revient à l’entrepôt après {{lot_hours}} heures.
# Pourquoi mon entreprise ne produit-elle pas ?
Pas de quart, pas d’intrants ou une durabilité à 0 %.
# Pourquoi ne puis-je pas retirer mes bonus ?
Le compte bonus ne se dépense que dans le jeu.
# Pourquoi la Ville n’a-t-elle pas acheté mon lot ?
La Ville n’achète que l’échelon 1, et seulement à son prix ou moins.
# Où est passée mon entreprise gratuite ?
Le bail de {{lease_days}} jours s’est terminé sans amélioration, ou un autre joueur l’a achetée.""",
    ),
    "glossary": dict(
        t="Glossaire",
        s="Les mots du jeu en langage simple.",
        b="""= Alliance | Une équipe de joueurs avec un trésor et un chat
= Appel d’offres | Une commande de livraison quotidienne d’une ressource
= Boost | Un effet temporaire : démarrage auto des quarts, protection de l’entrepôt…
= Compte bonus | Récompenses du jeu : dépensées dans le jeu, non retirables
= Compte principal | L’argent que vous pouvez recharger et retirer
= Détérioration | La perte quotidienne d’une partie des marchandises à {{spoil_time}} (heure de Moscou)
= Échelon | Un groupe d’entreprises et de ressources : 1, 2 ou 3
= Effet | Un avantage temporaire : plus de production ou moins de frais
= Escrow | L’argent gelé pour un accord
= GRAM | La monnaie TON dans le jeu
= Lot | Votre annonce de vente d’une ressource sur le marché
= Mécène | Une entreprise d’échelon 3 dont l’effet agit sur ses partenaires de contrat
= Occuper | Prendre une entreprise gratuite de niveau 0 pour {{lease_days}} jours
= Prix système | Le prix fixe des marchandises d’une entreprise de niveau 0
= Quart | {{shift_hours}} heures pendant lesquelles une entreprise produit et s’use
= Saisie | La Ville reprend une entreprise pour inactivité ou dette
= $CITY | La monnaie du jeu : 1 GRAM = {{city_per_gram}} $CITY""",
    ),
    "support": dict(
        t="Support",
        s="Willy GRAM et des agents humains.",
        b="""Menu ☰ → Aide : le chat de support.
- **Willy GRAM** répond d’abord : un assistant qui s’appuie sur la base de réponses. Il vérifie votre compte et envoie le lien vers l’article.
- Une personne prend le relais si besoin.
- Écrivez dans votre langue : la réponse arrive dans la même.
> Le support ne demande jamais de codes ni de phrase secrète.""",
        show=["Le menu ☰ : « Aide » s’y trouve."],
    ),
}
