# GRAM City wiki — English.
A = {
    "quick-start": dict(
        t="Quick start",
        s="Five steps from your first visit to a business of your own for good.",
        b="""GRAM City is an economy game: businesses produce resources, you sell them to the City and to players, and you grow.
1. Take a business for free: Map → «For sale». It is yours for {{lease_days}} days.
2. Start a shift — the business works for {{shift_hours}} hours and puts goods into the warehouse.
3. Sell the goods: Trading → «My» → «Sell resource».
4. Repair the business before durability drops below 50%.
5. Before the lease ends, upgrade the business to level 1 — it stays yours for good.
> Below is a check of your account: what is done and what comes next.""",
    ),
    "balances": dict(
        t="Currencies and balances",
        s="$CITY, GRAM and three accounts: main, bonus and frozen.",
        b="""Everything in the game is counted in **$CITY**: 1 GRAM = {{city_per_gram}} $CITY. GRAM is the TON coin — top up with TON only.
- **Main** account — you top it up and withdraw from it. Sales of businesses of level 1 and higher land here.
- **Bonus** — game rewards and sales of a level-0 business. Spent in the game, cannot be withdrawn.
- **Frozen** — money held for your deals: tenders, rentals. It comes back or goes out with the deal.
> Every purchase takes the bonus account first, then the main one. Bonuses get used, and what you can withdraw stays with you.""",
        show=["Tap the balance — all three accounts and the top-up and withdraw buttons open."],
    ),
    "earning": dict(
        t="Ways to earn",
        s="Sales, contracts, rentals and growing your business.",
        b="""- **Selling resources** on the market — to players and the City. The main income.
- **Tenders** — a daily supply deal: the resource goes out by itself, money comes in without lots.
- **Rental** — rent out a business of level 1 or higher by the day.
- **Upgrades** — the higher the level, the more goods per shift.
- **Chains** — tier-1 resources feed tier-2 businesses, and those feed tier 3. Buy inputs cheaper, sell goods higher.
> Mind the tax: every sale pays a tax by the resource's tier — see [[taxes|Taxes]].""",
    ),
    "interface": dict(
        t="The interface",
        s="The bottom menu, the ☰ menu and the «?» button on screens.",
        b="""At the bottom — five sections:
- **Map** — cities and plots.
- **Warehouse** — your resources and boosters.
- **Businesses** — your production: shifts, repairs, upgrades.
- **Trading** — the market, your lots, tenders.
- **Community** — leagues, alliances, chat.
The ☰ menu holds the Wiki, History, Game rewards, Marketplace, Settings, Help, Rules and Roadmap.
> Every screen except «Businesses» has a «?» button in its header — it opens the articles about that screen.""",
        show=["The five sections of the game. On a computer they are in the left sidebar.", "The ☰ menu: Wiki, History, Settings, Help and more."],
    ),
    "first-days": dict(
        t='The plan for your first 3 days',
        s='What to do so that the free business stays yours for good.',
        b="""The free business is yours for {{lease_days}} days. To keep it:
1. Take a business on the map.
2. Start a shift and get the first batch of goods.
3. Sell the goods.
4. Start a shift every {{shift_hours}} hours — we will remind you.
5. Repair when durability drops.
6. Before the lease ends, upgrade the business to level 1 with $CITY from the main account.
> The reward for the plan is a tier-3 resource of your choice. It goes to the warehouse: it cannot be sold; switch its buff on yourself whenever you like — or spend it on an upgrade.""",
    ),
    "notifications": dict(
        t="Notifications and settings",
        s="What to remind you about, quiet hours, the Telegram bot and language.",
        b="""In Settings choose what to be reminded about: the end of a shift, wear below 50%, the warehouse before spoilage, prices, sales.
- **Quiet hours** — no notifications at night.
- **Telegram bot** — notifications also come to Telegram.
- **«First days»** — tips for newcomers, no more than 3 a day.
- The game language and «Take the guide again» are here too.""",
        show=["Turn notifications on and off by topic here."],
    ),
    "maps": dict(
        t="Maps and cities",
        s="How to read the map: filters, zoom, mini-map, «For sale».",
        b="""**GRAM Island** is open now; the other cities are being built.
- **Filter** — by business type; **★** — fly over your businesses; **%** — keep only what is for sale.
- **+ / −** — zoom, **⌂** — back to the centre.
- **Mini-map** — tap it and the camera flies there.
- **«For sale»** at the bottom — every business you can take or buy now.
- **🌙** — night mode; your choice is remembered.""",
        show=["Choose a city — its map opens."],
    ),
    "zero-business": dict(
        t="Level-0 business",
        s="A free business from the City for {{lease_days}} days — how it works.",
        b="""The City gives a newcomer one business for free: Map → «For sale» → «Claim for free».
- It is yours for **{{lease_days}} days**. To keep it for good, upgrade it to level 1. The price is that business's map price, from the main account only.
- The goods price is the **system price** and cannot be changed. Sales money goes to the bonus account.
- While the business is level 0, another player can buy it at the map price ×{{zero_mult}}. It then becomes theirs, and you can take a new one.
- If you do not upgrade before the term ends, the business goes back to the City and the plot is freed. We warn you 24, 12 and 2 hours before.
> You can take a free business only if you never had a level-1 business.""",
        show=["Tap «For sale» — the list of businesses the City gives for free opens."],
    ),
    "plots": dict(
        t="Plots",
        s="Every business stands on its own spot on the map.",
        b="""The map is split into spots, each with a business of a set type. The type shows on the map and in the spot's card.
- A free spot can be taken (free for {{lease_days}} days) or bought.
- The price depends on the business type and the spot: closer to the centre costs more.
- The spot's card shows what the business produces and uses, and the production chain.""",
    ),
    "buy-business": dict(
        t="Buying a business",
        s="A level-1 business is yours for good, with income to the main account at once.",
        b="""Buy on the map (a free spot) or on the Marketplace (another player's business).
- A bought business is level 1 at once and yours for good.
- Payment: the bonus account first, then the main one.
- While you hold a level-0 business you cannot buy others — upgrade it first.
- Choose by chain: what you will buy as inputs and who will buy your goods.""",
        show=["The Marketplace: players' businesses for sale, your listings and rentals."],
    ),
    "districts": dict(
        t="Districts and spots for sale",
        s="Why not every spot on the map can be bought.",
        b="""The city opens district by district. You can buy only a spot in an open district and only among those already put up for sale.
- New districts and spots open over time — watch «For sale» and the announcements.
- A closed district shows on the map, but nothing there can be bought yet.""",
    ),
    "tiers": dict(
        t="Business tiers",
        s="Tiers 1, 2 and 3: what they produce and how they differ.",
        b="""All businesses and resources fall into three tiers.
- **Tier 1** — basic resources: energy, metal, quartz, biomass and more. The City buys them too.
- **Tier 2** — products made of tier-1 resources: chips, AI models and more. Players buy them.
- **Tier 3** — rare resources that switch on buffs.
The higher the tier, the pricier the goods and repairs, and the more warehouse space they take.
[[table:taxes]]""",
    ),
    "shift": dict(
        t="Shift",
        s="A business produces only during a shift — {{shift_hours}} hours.",
        b="""Without a shift the business stands still: no production and no wear.
1. Businesses → the business card → «Start shift».
2. For {{shift_hours}} hours the business makes goods and uses inputs every minute.
3. When the shift ends we remind you — start the next one.
> To have shifts start by themselves, turn on the «Auto-shift» booster (Warehouse → Boosters).""",
        show=["The business status: working or idle.", "The shift button is here."],
    ),
    "raw-materials": dict(
        t="Inputs",
        s="What a business uses and where to get it.",
        b="""During a shift a business uses inputs — resources of other businesses. How much shows in the card: on the right, «per day».
- Buy inputs on the market: Trading → «Buy».
- Or set up a tender — inputs arrive every day by themselves.
- Without inputs the business produces less.
> A newcomer gets a day's worth of inputs with the business.""",
        show=["How much the business makes per hour.", "How much input it uses per day."],
    ),
    "durability": dict(
        t="Durability and repair",
        s="The 50% line: below it, fewer goods and repairs cost double.",
        b="""During a shift the building wears out.
[[table:durability]]
You pay for each missing percent. Percents below 50% cost double: at 1 $CITY per %, a repair from 46% is 50 + 4×2 = **58 $CITY**.
[[table:repair]]
> When durability drops below 50% you get a notice — in the game and in Telegram.""",
        show=["The building's durability now.", "The repair button — you pay only for the missing percents."],
    ),
    "upgrade": dict(
        t='Upgrade',
        s='A higher level means more goods and a bigger warehouse; level 1 makes the business yours for good.',
        b="""- **Level 0 → 1** costs the business’s map price, from the main account only. After that the business is yours for good and income goes to the main account.
- Then levels up to 10: more goods per shift and a bigger warehouse, but more inputs too.
- An upgrade to level 2 and higher also needs a tier-3 resource — each business type has its own:
[[table:upgrade_res]]
- A reward resource that cannot be sold counts too.
- The price of the next level is on the «Upgrade» button.
> A rented business cannot be upgraded.""",
        show=['The upgrade button and its price.'],
    ),
    "chains": dict(
        t="Production chains",
        s="What is made from what.",
        b="""Tier-1 resources are inputs for tier 2, and tier-2 resources are inputs for tier 3.
- A spot's card on the map has a «Production chain»: what the business uses and where its goods go.
- Build along a chain: buy inputs from your chain neighbours and sell to those who need your goods.""",
    ),
    "patron-buffs": dict(
        t='Business buffs and patrons',
        s='A tier-3 business can become a patron and give a buff to its wards.',
        b="""Any business can choose a patron — a tier-3 business.
- The patron’s owner picks one of the buffs below for the wards.
- The patron gets 1% of the wards’ income.
- The patron can be changed only after a pause.
[[table:patrons]]
- A business’s buff shows in its card.
- Tier-3 resource buffs are a different thing: they are switched on in the warehouse, see [[t3-buffs|Tier-3 resource buffs]].""",
    ),
    "skins": dict(
        t="Skins",
        s="A different look for a business on the map.",
        b="""A skin changes how the building looks on the map; it does not affect the business.
- Skins are given for partner tasks.
- A skin is chosen for each business separately.
- A rented business cannot change its skin.""",
    ),
    "business-sale": dict(
        t="Selling a business",
        s="How to sell a business on the Marketplace and what tax is taken.",
        b="""A business of level 1 or higher can be listed on the Marketplace at your price.
- The seller pays a tax by the business's tier:
[[table:taxes]]
- If the business secures a loan, repay the loan first.
- A business rented out cannot be sold while the rental lasts.
> A level-0 business cannot be sold: it is not yours until you upgrade it.""",
        show=["The Marketplace: the tab with your listings — a business is listed here."],
    ),
    "rental": dict(
        t="Rental",
        s="Rent out a business by the day or rent someone else's.",
        b="""The owner of a business of level 1 or higher can rent it out: a price per day and a term of up to {{rent_max_days}} days.
- The renter freezes the rent for the whole term plus a deposit at once. Every day the owner gets a day's rent minus a {{rent_fee}}% commission.
- During the rental the business works for the renter: goods, inputs and repairs are theirs.
- A rented business cannot be sold, upgraded or re-skinned.
- The deposit goes back to the renter unless the business was badly worn.""",
    ),
    "seizure": dict(
        t="Seizure",
        s="When the City takes a business away.",
        b="""A business is seized in two cases.
- **No activity.** In any {{act_days}} days you need to buy {{act_buy}} units or sell {{act_sell}} units on the market — see [[activity-rule|Activity rule]].
- **A loan debt.** The loan is overdue and there has been no payment for {{credit_days}} days. Any payment clears the overdue status.
GRAM CITY puts a seized business up for sale. The sale first pays off the debt; the rest goes to the former owner.
> We remind you in the game and in Telegram 3 days before a seizure.""",
    ),
    "resources": dict(
        t="Resources",
        s="What is in the warehouse and how resources differ.",
        b="""The warehouse holds everything your businesses made and everything you bought.
[[table:weights]]
- Under each resource — what it is worth now.
- Tier-3 resources can be sold or switched on as a buff.
- A resource received as a reward is kept apart: it cannot be sold.""",
        show=["The warehouse: the space and the value of your resources."],
    ),
    "capacity": dict(
        t="Capacity and weights",
        s="How much fits into the warehouse.",
        b="""Warehouse space is limited. The capacity is the sum of the warehouses of all your businesses; a higher level gives a bigger warehouse.
[[table:weights]]
- Lots on the market take space too.
- Whatever does not fit spoils faster — see [[spoilage|Spoilage]].""",
        show=["Used and free warehouse space."],
    ),
    "warehouse-value": dict(
        t="Estimated warehouse value",
        s="What everything you hold is worth.",
        b="""Above the resource list is the estimated warehouse value: what all your resources would cost at current prices.
- Under each resource — its value.
- It is an estimate: the real price is what you sell for.""",
        show=["The estimated value of the whole warehouse."],
    ),
    "spoilage": dict(
        t="Spoilage at {{spoil_time}}",
        s="Every day part of the goods in the warehouse spoils.",
        b="""Every day at **{{spoil_time}} Moscow time** **{{spoil_in}}%** of the goods in the warehouse spoil, and **{{spoil_over}}%** of whatever is over the limit.
- Spoilage affects all resources the same way.
- Lots on the market do not spoil.
- The «Warehouse guard» booster protects the warehouse.
> Do not hoard — sell before {{spoil_time}}. We send a reminder in the evening.""",
        show=["The warehouse: what lies here spoils at {{spoil_time}}."],
    ),
    "boosters": dict(
        t='Boosters',
        s='Auto-shift, warehouse guard, repair all, ×2 XP — what they give.',
        b="""Boosters are switched on in Warehouse → Boosters. They cannot be sold.
[[table:boosters]]
- Tier-3 resources are switched on here too — each with its own buff, see [[t3-buffs|Tier-3 resource buffs]].
- No more than two boosters and buffs work at the same time.
> Boosters are City Pass rewards: one on every level, more on the premium track.""",
        show=['The «Boosters» tab: what you have and what is active now.'],
    ),
    "t3-buffs": dict(
        t='Tier-3 resource buffs',
        s='What each tier-3 resource gives and how to switch it on.',
        b="""Every tier-3 resource can be switched on as a buff — a temporary effect on all your businesses.
[[table:t3buffs]]
1. Warehouse → Boosters.
2. Tap «Activate» next to the resource — 1 unit is used.
3. The buff lasts the time shown; the time left is under «Active now».
- Where to get them: tier-3 businesses produce them, players sell them on the market, City Pass gives them as rewards. One is free for the [[first-days|3-day plan]].
- A reward resource cannot be sold, but it can be switched on as a buff or spent on a business [[upgrade|upgrade]].
- The same buff cannot run twice; no more than two boosters and buffs at the same time.
> A resource never switches on by itself: it waits in the warehouse until you tap «Activate».""",
        show=['The «Boosters» tab: tier-3 resources and the «Activate» button.'],
    ),
    "buy": dict(
        t="Buying a resource",
        s="Players' lots, filters and paying.",
        b="""Trading → «Buy» — lots of other players and of the City.
1. Find a resource: filter by resource, price and amount.
2. Tap a lot and enter the amount — any number of units.
3. Check the total and confirm.
- The price is **per unit**.
- Payment: the bonus account first, then the main one.
- The resource goes straight to the warehouse — check there is room.""",
        show=["The «Buy» tab — players' lots.", "Filters: resource, price, amount."],
    ),
    "sell": dict(
        t="Selling a resource",
        s="A lot, the price, the tax, {{lot_hours}} hours.",
        b="""List goods from your warehouse — every player sees them. A player or the City can buy.
1. Trading → the «My» tab.
2. «Sell resource» and pick the goods.
3. Enter the amount — any number of units. The price is per unit; tier 1 to the cent.
4. Check the price and the net amount.
5. «List».
[[table:taxes]]
> An unsold lot returns to the warehouse after {{lot_hours}} hours. While on the market it takes warehouse space but does not spoil.""",
        show=["Tap «Sell resource» — the sale window opens."],
    ),
    "edit-lot": dict(
        t="Editing or cancelling a lot",
        s="Change the amount and price without cancelling.",
        b="""In the «My» tab each lot has two buttons.
- **«Edit»** — change the amount or the price. Any amount from 1 unit.
- **«Cancel»** — take the lot down; the goods return to the warehouse.
- The number of lots is limited: one slot per business you own, one if you have none.
> A level-0 business cannot change the price — it is the system price.""",
        show=["Your lots: «Edit» and «Cancel»."],
    ),
    "city-market": dict(
        t="The City on the market",
        s="What the City buys and when.",
        b="""The City Market is a safety net for newcomers and a thin market. It buys below and sells above the table price — trading with players pays more.
- The City buys **tier-1** resources only.
- It buys a newcomer's first sale almost at once.
- It buys lots of a level-0 business at the system price — the money goes to the bonus account.
- For businesses of level 1 and higher — lots priced at or below the City's price; the money goes to the main account.
- Everything the City buys it puts back on the market.""",
    ),
    "tenders": dict(
        t="Tenders",
        s="A deal for daily supply.",
        b="""A tender is an order: «I need X units of a resource per day at this price».
1. Trading → «Contracts» → «Exchange»: players' open orders.
2. Send an offer. Without an answer it closes after 72 h.
3. If it is accepted, the resource goes out every day by itself and money comes in without lots (minus tax).
- «Purchases» — your orders, «Supplies» — your deals.
> If resources or money run short, there are 24 hours to fix it; then the deal breaks with a penalty.""",
        show=["Open «Contracts».", "«Exchange» — players' open orders."],
    ),
    "contracts": dict(
        t="Cooperation contracts",
        s="Supply between businesses — and the patron's buff.",
        b="""A cooperation contract is a daily supply of a resource from one business to another for up to 90 days.
- The supplier sets the resource, the amount per day, the price and the term.
- If the supplier is a tier-3 business, its buff works on the receiving business while the contract lasts.
- It can be cancelled at any time; what was delivered stays with the receiver.""",
    ),
    "analytics": dict(
        t="Price analytics",
        s="Charts, trends, volumes.",
        b="""Analytics — price charts for every resource.
- Where it pays to sell and what is cheaper to buy.
- How much sells per day and how the price moves.
- Opened with the «Analytics» button on the «Businesses» screen.""",
        show=["Tap «Analytics» — the price charts open."],
    ),
    "taxes": dict(
        t="Taxes",
        s="Rates by tier and where the tax goes.",
        b="""Every resource sale pays a tax by the resource's tier. The administration sets the rates; the current ones are below.
[[table:taxes]]
- You see the net amount before you list a lot.
- A share of the tax ({{ref_pct}}% of the deal) goes to whoever invited the seller — the seller loses nothing.
- Tier-3 resource buffs can lower the trade fee.""",
    ),
    "deposit": dict(
        t="Top-up",
        s="How to put GRAM on the main account.",
        b="""1. Tap the balance → «Top up».
2. Connect a wallet: Tonkeeper, Telegram Wallet or another.
3. Send GRAM. **GRAM is the TON coin — send TON only.**
4. The money arrives on the main account: 1 GRAM = {{city_per_gram}} $CITY.
> Send only from the wallet connected to your account.""",
        show=["Tap the balance — «Top up» is there."],
    ),
    "withdraw": dict(
        t="Withdrawal",
        s="What can be withdrawn and what it takes.",
        b="""Only the **main** account can be withdrawn; the bonus one cannot.
1. Tap the balance → «Withdraw».
2. Enter the amount (from {{withdraw_min}} GRAM) and confirm with a 2FA code or a Passkey.
3. The request is reviewed and sent to your wallet.
- The fee is {{withdraw_fee}}%. Through a player's bank it is faster, with the bank's own fee (up to {{instant_fee_max}}%).""",
        show=["Tap the balance — «Withdraw» is there."],
    ),
    "security": dict(
        t="Why 2FA and Passkey",
        s="Withdrawals need them — here is why.",
        b="""The withdrawal wallet is changed in the settings. Someone who gets into your account — your phone, e-mail or Telegram — could link their own.
- **2FA** — a code from an authenticator app.
- **Passkey** — a fingerprint or face on your device.
Without the code or Passkey a withdrawal does not go through.
> Support never asks for codes, passwords or a seed phrase.""",
        show=["Turn on 2FA — a code from an app.", "Or add a Passkey — a fingerprint or face."],
    ),
    "history": dict(
        t="Transaction history",
        s="Every purchase, sale, tax and reward.",
        b="""☰ menu → History — every operation with your balance.
- Filter by type: purchases, sales, taxes, rewards, top-ups, withdrawals.
- Each operation shows the amount, the account (main or bonus) and the time.""",
        show=["Filter by operation type."],
    ),
    "credit": dict(
        t="A loan secured by a business",
        s="Money now, part of the income pays it back.",
        b="""Take $CITY secured by a business — from the state or a player's bank. Part of your income pays it back by itself.
- Only against a business of level 1 or higher, up to {{credit_max}}% of its value.
[[table:credit]]
- No payment for {{credit_days}} days (a bank sets its own term) — the loan is overdue and the rate doubles.
- {{credit_days}} more overdue days without a single payment — the business is seized. Any payment clears the overdue status.
- A seized business is sold; the loan and double interest are taken from the sale: a {{credit_rate}}% rate → loan × {{credit_back}}. The rest is yours.""",
        show=["The «Take a loan» button."],
    ),
    "banks": dict(
        t="Players' banks",
        s="GRAM Bank: loans and fast withdrawals from players.",
        b="""The owner of a GRAM Bank business is a bank.
- It lends to players at its own rate (no more than {{bank_rate_max}}%).
- It runs fast withdrawals with its own fee (up to {{instant_fee_max}}%).
- Only banks with durability of 50% or more work.""",
    ),
    "daily-login": dict(
        t="Daily login",
        s="The reward grows {{daily_days}} days in a row.",
        b="""Come every day — the reward grows: from {{daily_first}} to {{daily_last}} $CITY on day {{daily_days}}.
- To claim it, complete one goal of the day.
- Miss a day and the streak starts over. A streak shield saves one missed day.
- Rewards go to the bonus account.""",
        show=["The daily login card."],
    ),
    "quests": dict(
        t="Tasks and goals",
        s="The newcomer path, daily and weekly goals.",
        b="""- **Newcomer path** — 7 goals in a row: business, shift, purchase, lot, sale, repair, upgrade.
- **Daily goals** — 3 every day, **weekly goals** — 3 more.
- Progress counts by itself — just tap «Claim».
- Rewards go to the bonus account and City Pass XP. All weekly goals earn a streak shield.""",
        show=["Goals of the day."],
    ),
    "partner-tasks": dict(
        t="Partner tasks",
        s="Subscriptions and actions with partners — for $CITY and skins.",
        b="""Tasks → «Partners»: subscribe to a channel, open a partner's app and more.
- The reward is $CITY on the bonus account, sometimes a skin.
- Some tasks need a connected Telegram.""",
        show=["The partner tasks tab."],
    ),
    "city-pass": dict(
        t="City Pass",
        s="A season of {{pass_levels}} levels: XP and rewards.",
        b="""City Pass is a season of {{pass_levels}} levels.
- XP comes from daily and weekly goals, shifts, repairs, sales to players and the login streak.
- **Free track** — a reward on every level: boosters, tier-3 resources, shields.
- **Premium** — extra rewards on levels 1, 5, 10…; bought from the main account.
- Take rewards with the «Claim» button.""",
        show=["Your level and season XP."],
    ),
    "referrals": dict(
        t="Referrals",
        s="Invite friends — get part of the tax on their sales.",
        b="""The 👥 button at the top of «Businesses» holds your link.
- A friend plays via your link — you get {{ref_pct}}% of the amount of their market sales.
- It is part of the tax: your friend loses nothing.
- The list of invited friends and what they brought is there too.""",
        show=["Tap 👥 — your link and your friends open."],
    ),
    "chat": dict(
        t="Chat",
        s="The common chat and the alliance chat.",
        b="""The common chat of all players and your alliance's chat.
- Arrange deals and share tips.
- Any message can be translated with a button.
- Do not follow strangers' links and never share codes — see [[safety|Safety]].""",
        show=["Chat channels: common and alliance."],
    ),
    "leagues": dict(
        t="Leagues",
        s="A weekly contest among equals.",
        b="""Every week you are in a group of players of equal strength.
- Points for goals, shifts, repairs, sales to players and the login streak.
- The best move up: Bronze → Silver → Gold → Platinum → Diamond.
- **‹ ›** — other leagues, **«Whole division»** — all players, search and friends.
- Weekly rewards — $CITY on the bonus account and streak shields.
> Sales to the City and between linked accounts do not count.""",
        show=["Browse leagues with the arrows.", "The ratings switch."],
    ),
    "alliances": dict(
        t="Alliances",
        s="Teams of players: treasury, chat, levels.",
        b="""An alliance is a team of players: a shared treasury, a chat, levels.
- You can join at once — open, by request or by invitation.
- To create one: City Pass level {{alliance_level}}, a business and {{alliance_cost}} $CITY.
- Alliance XP is 10% of members' City Pass XP; you lose nothing.
- Payouts from the treasury go to the bonus account.""",
        show=["The «Alliance» tab."],
    ),
    "leaderboard": dict(
        t="Leaderboard",
        s="Top players by balance, income, businesses and trading.",
        b="""The leaderboard is the top of players. Sort:
- by balance, by income, by number of businesses, by number of plots, by trading volume.
- Your place shows at the bottom of the list.""",
    ),
    "profile": dict(
        t="Player profile",
        s="Stats, alliance, Founder Pass.",
        b="""Tap your avatar — your profile opens: stats, alliance, City Pass level.
- Other players' profiles open from the chat and the ratings.""",
        show=["Your profile."],
    ),
    "activity-rule": dict(
        t="Activity rule",
        s="The City takes businesses from those who do not trade.",
        b="""In any **{{act_days}} days** you need to **buy {{act_buy}} units** or **sell {{act_sell}} units** on the market — one of the two is enough.
- If 3 days are left before a seizure, we remind you in the game and in Telegram.
- Below — your numbers for the last {{act_days}} days.""",
    ),
    "zero-limits": dict(
        t="Level-0 limits",
        s="What you cannot do while the business is level 0.",
        b="""While you hold a level-0 business:
- you cannot buy another business or take a loan;
- the goods price is the system price, sales money goes to the bonus account;
- you cannot sell the business or rent it out;
- another player can buy it at the map price ×{{zero_mult}}.
Upgrading to level 1 lifts all limits.""",
    ),
    "safety": dict(
        t="Safety and scams",
        s="How not to lose your account and money.",
        b="""- Support **never** asks for 2FA codes, passwords or a seed phrase.
- Do not follow links from private messages «from the administration».
- Turn on 2FA or a Passkey — withdrawals need them.
- Deal only through the market and tenders: «send me money and I will send the resource» is a scam.
> A suspicious message — report it in the chat or write to support.""",
    ),
    "faq": dict(
        t="FAQ",
        s="Short answers to the main questions.",
        b="""# Why did my goods disappear?
Every day at {{spoil_time}} Moscow time part of the goods spoils — see [[spoilage|Spoilage]]. An unsold lot returns to the warehouse after {{lot_hours}} hours.
# Why is my business not producing?
No shift, no inputs or durability at 0%.
# Why can't I withdraw bonuses?
The bonus account is spent only in the game.
# Why didn't the City buy my lot?
The City buys tier 1 only and only at or below its price.
# Where did my free business go?
The {{lease_days}}-day lease ended without an upgrade, or another player bought it.""",
    ),
    "glossary": dict(
        t="Glossary",
        s="Game words in plain language.",
        b="""= Alliance | A team of players with a treasury and chat
= Bonus account | Game rewards: spent in the game, cannot be withdrawn
= Buff | A temporary bonus: more goods or lower costs
= Booster | A temporary effect: auto-shift, warehouse guard and more
= Escrow | Money frozen for a deal
= GRAM | The TON coin in the game
= Lot | Your listing of a resource on the market
= Main account | Money you can top up and withdraw
= Patron | A tier-3 business whose buff works on its contract partners
= Seizure | The City takes a business for inactivity or debt
= Shift | {{shift_hours}} hours while a business produces and wears
= Spoilage | The daily loss of part of the goods at {{spoil_time}} Moscow time
= Stake a claim | Take a free level-0 business for {{lease_days}} days
= System price | The fixed goods price of a level-0 business
= Tender | An order for the daily supply of a resource
= Tier | A group of businesses and resources: 1, 2 or 3
= $CITY | The game currency: 1 GRAM = {{city_per_gram}} $CITY""",
    ),
    "support": dict(
        t="Support",
        s="Willy GRAM and live agents.",
        b="""☰ menu → Help — the support chat.
- **Willy GRAM** answers first — an assistant working from the answer base. It checks your account and sends a link to the article.
- A person joins when needed.
- Write in your language — the answer comes in it too.
> Support never asks for codes or a seed phrase.""",
        show=["The ☰ menu — «Help» is there."],
    ),
}
