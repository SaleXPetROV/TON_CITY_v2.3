# Guía de GRAM City — español.
A = {
    "quick-start": dict(
        t="Inicio rápido",
        s="Cinco pasos desde tu primera visita hasta un negocio tuyo para siempre.",
        b="""GRAM City es un juego de economía: los negocios producen recursos, tú los vendes a la Ciudad y a otros jugadores, y creces.
1. Toma un negocio gratis: Mapa → «En venta». Es tuyo durante {{lease_days}} días.
2. Inicia un turno: el negocio trabaja {{shift_hours}} horas y deja mercancía en el almacén.
3. Vende la mercancía: Comercio → «Mis» → «Vender recurso».
4. Repara el negocio antes de que la durabilidad baje del 50%.
5. Antes de que termine el alquiler, sube el negocio a nivel 1: será tuyo para siempre.
> Abajo está la comprobación de tu cuenta: qué ya está hecho y qué viene después.""",
    ),
    "balances": dict(
        t="Monedas y saldos",
        s="$CITY, GRAM y tres cuentas: principal, bonus y congelada.",
        b="""Todo en el juego se cuenta en **$CITY**: 1 GRAM = {{city_per_gram}} $CITY. GRAM es la moneda TON: recarga solo con TON.
- Cuenta **principal**: la recargas y retiras desde ella. Aquí llegan las ventas de negocios de nivel 1 o superior.
- **Bonus**: recompensas del juego y ventas de un negocio de nivel 0. Se gasta en el juego, no se puede retirar.
- **Congelado**: dinero reservado para tus acuerdos: licitaciones, alquileres. Vuelve o sale según el acuerdo.
> Cada compra gasta primero la cuenta bonus y después la principal. Así los bonus se usan y lo que puedes retirar se queda contigo.""",
        show=["Toca el saldo: se abren las tres cuentas y los botones de recargar y retirar."],
    ),
    "earning": dict(
        t="Formas de ganar",
        s="Ventas, contratos, alquileres y crecimiento del negocio.",
        b="""- **Vender recursos** en el mercado, a jugadores y a la Ciudad. El ingreso principal.
- **Licitaciones**: un acuerdo de suministro diario; el recurso sale solo y el dinero llega sin lotes.
- **Alquiler**: alquila un negocio de nivel 1 o superior por días.
- **Mejoras**: cuanto más alto el nivel, más mercancía por turno.
- **Cadenas**: los recursos de nivel 1 alimentan negocios de nivel 2, y estos al nivel 3. Compra insumos más baratos y vende más caro.
> Ojo con el impuesto: cada venta paga un impuesto según el nivel del recurso; mira [[taxes|Impuestos]].""",
    ),
    "interface": dict(
        t="La interfaz",
        s="El menú inferior, el menú ☰ y el botón «?» de las pantallas.",
        b="""Abajo hay cinco secciones:
- **Mapa**: ciudades y parcelas.
- **Almacén**: tus recursos y potenciadores.
- **Negocios**: tu producción: turnos, reparaciones, mejoras.
- **Comercio**: el mercado, tus lotes, licitaciones.
- **Comunidad**: ligas, alianzas, chat.
En el menú ☰ están la Wiki, Historial, Recompensas, Marketplace, Ajustes, Ayuda, Reglas y Hoja de ruta.
> Todas las pantallas salvo «Negocios» tienen un botón «?» en la cabecera: abre los artículos sobre esa pantalla.""",
        show=["Las cinco secciones del juego. En el ordenador están en la barra lateral izquierda.", "El menú ☰: Wiki, Historial, Ajustes, Ayuda y más."],
    ),
    "first-days": dict(
        t='El plan de tus 3 primeros días',
        s='Qué hacer para que el negocio gratis sea tuyo para siempre.',
        b="""El negocio gratis es tuyo durante {{lease_days}} días. Para quedártelo:
1. Toma un negocio en el mapa.
2. Inicia un turno y consigue el primer lote de mercancía.
3. Vende la mercancía.
4. Inicia un turno cada {{shift_hours}} horas; te lo recordaremos.
5. Repara cuando baje la durabilidad.
6. Antes de que termine el alquiler, sube el negocio a nivel 1 con $CITY de la cuenta principal.
> La recompensa del plan es un recurso de nivel 3 a elegir. Va al almacén: no se puede vender; activa su efecto tú mismo cuando quieras (no sirve para mejoras).""",
    ),
    "notifications": dict(
        t="Avisos y ajustes",
        s="Qué recordarte, horas de silencio, el bot de Telegram y el idioma.",
        b="""En Ajustes elige qué recordarte: fin de turno, desgaste por debajo del 50%, el almacén antes del deterioro, precios, ventas.
- **Horas de silencio**: sin avisos por la noche.
- **Bot de Telegram**: los avisos llegan también a Telegram.
- **«Primeros días»**: consejos para novatos, no más de 3 al día.
- Aquí también están el idioma y «Repetir la guía».""",
        show=["Aquí se activan y desactivan los avisos por tema."],
    ),
    "maps": dict(
        t="Mapas y ciudades",
        s="Cómo leer el mapa: filtros, zoom, minimapa, «En venta».",
        b="""Ahora está abierta la **Isla GRAM**; las demás ciudades están en construcción.
- **Filtro** por tipo de negocio; **★**: vuela por tus negocios; **%**: deja solo lo que está en venta.
- **+ / −**: zoom, **⌂**: volver al centro.
- **Minimapa**: tócalo y la cámara vuela allí.
- **«En venta»** abajo: todos los negocios que puedes tomar o comprar ahora.
- **🌙**: modo noche; se recuerda tu elección.""",
        show=["Elige una ciudad: se abre su mapa."],
    ),
    "zero-business": dict(
        t="Negocio de nivel 0",
        s="Un negocio gratis de la Ciudad durante {{lease_days}} días: cómo funciona.",
        b="""La Ciudad da a cada novato un negocio gratis: Mapa → «En venta» → «Ocupar gratis».
- Es tuyo durante **{{lease_days}} días**. Para quedártelo, súbelo a nivel 1. El precio es el de ese negocio en el mapa, solo desde la cuenta principal.
- El precio de la mercancía lo pones tú, como todos. La Ciudad compra a su **precio de recompra**, el mismo para todos. El dinero de las ventas va a la cuenta bonus.
- Mientras sea de nivel 0, otro jugador puede comprarlo al precio del mapa ×{{zero_mult}}. Entonces será suyo y tú podrás tomar otro.
- Si no lo mejoras a tiempo, el negocio vuelve a la Ciudad y la parcela queda libre. Avisamos 24, 12 y 2 horas antes.
> Solo puedes tomar un negocio gratis si nunca tuviste uno de nivel 1.""",
        show=["Toca «En venta»: se abre la lista de negocios que la Ciudad da gratis."],
    ),
    "plots": dict(
        t="Parcelas",
        s="Cada negocio está en su propio lugar del mapa.",
        b="""El mapa está dividido en lugares, cada uno con un negocio de un tipo fijo. El tipo se ve en el mapa y en la ficha del lugar.
- Un lugar libre se puede ocupar (gratis durante {{lease_days}} días) o comprar.
- El precio depende del tipo de negocio y del lugar: cuanto más cerca del centro, más caro.
- La ficha muestra qué produce y qué consume el negocio, y la cadena de producción.""",
    ),
    "buy-business": dict(
        t="Comprar un negocio",
        s="Un negocio de nivel 1 es tuyo para siempre y sus ingresos van a la cuenta principal.",
        b="""Compra en el mapa (un lugar libre) o en el Marketplace (el negocio de otro jugador).
- El negocio comprado es de nivel 1 y tuyo para siempre.
- Pago: primero la cuenta bonus, luego la principal.
- Mientras tengas un negocio de nivel 0 no puedes comprar otros: primero mejóralo.
- Elige por cadena: qué comprarás como insumo y quién comprará tu mercancía.""",
        show=["El Marketplace: negocios de jugadores en venta, tus anuncios y alquileres."],
    ),
    "districts": dict(
        t="Distritos y lugares en venta",
        s="Por qué no se puede comprar cualquier lugar del mapa.",
        b="""La ciudad se abre por distritos. Solo puedes comprar un lugar de un distrito abierto y solo entre los que ya están a la venta.
- Los distritos y lugares nuevos se abren poco a poco: sigue «En venta» y los anuncios.
- Un distrito cerrado se ve en el mapa, pero allí aún no se puede comprar.""",
    ),
    "tiers": dict(
        t="Niveles de negocio",
        s="Niveles 1, 2 y 3: qué producen y en qué se diferencian.",
        b="""Todos los negocios y recursos se dividen en tres niveles.
- **Nivel 1**: recursos básicos: energía, metal, cuarzo, biomasa y más. También los compra la Ciudad.
- **Nivel 2**: productos hechos con recursos de nivel 1: chips, modelos de IA y más. Los compran los jugadores.
- **Nivel 3**: recursos raros que activan efectos.
Cuanto más alto el nivel, más caras la mercancía y las reparaciones, y más espacio ocupan en el almacén.
[[table:taxes]]""",
    ),
    "shift": dict(
        t="Turno",
        s="Un negocio solo produce durante un turno: {{shift_hours}} horas.",
        b="""Sin turno, el negocio está parado: ni produce ni se desgasta.
1. Negocios → ficha del negocio → «Iniciar turno».
2. Durante {{shift_hours}} horas produce mercancía y gasta insumos cada minuto.
3. Al terminar el turno te avisamos: inicia el siguiente.
> Para que los turnos se inicien solos, activa el potenciador «Inicio automático de turnos» (Almacén → Potenciadores).""",
        show=["Estado del negocio: trabajando o parado.", "Aquí está el botón del turno."],
    ),
    "raw-materials": dict(
        t="Insumos",
        s="Qué consume un negocio y dónde conseguirlo.",
        b="""Durante el turno el negocio consume insumos: recursos de otros negocios. Cuánto, se ve en la ficha: a la derecha, «por día».
- Compra insumos en el mercado: Comercio → «Comprar».
- O haz una licitación: los insumos llegarán solos cada día.
- Sin insumos, el negocio produce menos.
> Al novato le damos insumos para un día junto con el negocio.""",
        show=["Cuánto produce el negocio por hora.", "Cuántos insumos consume al día."],
    ),
    "durability": dict(
        t="Durabilidad y reparación",
        s="La línea del 50%: por debajo, menos mercancía y reparación al doble.",
        b="""Durante el turno el edificio se desgasta.
[[table:durability]]
Pagas por cada punto que falta. Los puntos por debajo del 50% cuestan el doble: a 1 $CITY por %, reparar desde el 46% cuesta 50 + 4×2 = **58 $CITY**.
[[table:repair]]
> Cuando la durabilidad baja del 50% recibes un aviso, en el juego y en Telegram.""",
        show=["Durabilidad actual del edificio.", "El botón de reparar: pagas solo los puntos que faltan."],
    ),
    "upgrade": dict(
        t='Mejora',
        s='Más nivel, más mercancía y almacén; con el nivel 1 el negocio es tuyo para siempre.',
        b="""- **Nivel 0 → 1** cuesta el precio del negocio en el mapa, solo desde la cuenta principal. Después, el negocio es tuyo para siempre y los ingresos van a la cuenta principal.
- Luego, niveles hasta el 10: más mercancía por turno y más almacén, pero también más insumos.
- Mejorar al nivel 2 y superiores también pide un recurso de nivel 3; cada tipo de negocio tiene el suyo:
[[table:upgrade_res]]
- Un recurso de recompensa de nivel 3 (del plan o del City Pass) no sirve para mejorar: hace falta uno propio; el de recompensa solo se activa como efecto.
- El precio del siguiente nivel está en el botón «Mejorar».
- La recuperación en condiciones ideales (turnos sin parar, durabilidad desde 50 %, materias y producción a precio de mercado) está en el botón «Se recupera en ~N d» de la pantalla del negocio; la ventana de mejora dice en cuántos días se recupera la mejora. Es un cálculo, no una promesa.
> Un negocio alquilado no se puede mejorar.""",
        show=['El botón de mejora y su precio.'],
    ),
    "chains": dict(
        t="Cadenas de producción",
        s="Qué se hace con qué.",
        b="""Los recursos de nivel 1 son insumos del nivel 2, y los del nivel 2, del nivel 3.
- La ficha de un lugar en el mapa tiene «Cadena de producción»: qué consume el negocio y adónde va su mercancía.
- Construye siguiendo una cadena: compra insumos a tus vecinos de cadena y vende a quien necesita tu mercancía.""",
    ),
    "patron-buffs": dict(
        t='Efectos de negocio y patrocinadores',
        s='Un negocio de nivel 3 puede ser patrocinador y dar un efecto a sus protegidos.',
        b="""Cualquier negocio puede elegir un patrocinador: un negocio de nivel 3.
- El dueño del patrocinador elige para sus protegidos uno de los efectos de abajo.
- El patrocinador recibe el 1% de los ingresos de sus protegidos.
- El patrocinador solo se puede cambiar tras una pausa.
[[table:patrons]]
- El efecto de un negocio aparece en su ficha.
- Los efectos de recursos de nivel 3 son otra cosa: se activan en el almacén; mira [[t3-buffs|Efectos de recursos de nivel 3]].""",
    ),
    "skins": dict(
        t="Aspectos",
        s="Otro aspecto del negocio en el mapa.",
        b="""Un aspecto cambia cómo se ve el edificio en el mapa; no afecta al negocio.
- Se dan por tareas de socios.
- Se elige para cada negocio por separado.
- Un negocio alquilado no puede cambiar de aspecto.""",
    ),
    "business-sale": dict(
        t="Vender un negocio",
        s="Cómo vender un negocio en el Marketplace y qué impuesto se cobra.",
        b="""Un negocio de nivel 1 o superior se puede poner en el Marketplace a tu precio.
- El vendedor paga un impuesto según el nivel del negocio:
[[table:taxes]]
- Si el negocio garantiza un préstamo, primero devuelve el préstamo.
- Un negocio alquilado no se puede vender mientras dure el alquiler.
> Un negocio de nivel 0 no se puede vender: no es tuyo hasta que lo mejores.""",
        show=["El Marketplace: la pestaña con tus anuncios; aquí se pone un negocio en venta."],
    ),
    "rental": dict(
        t="Alquiler",
        s="Alquila tu negocio por días o alquila el de otro.",
        b="""El dueño de un negocio de nivel 1 o superior puede alquilarlo: precio por día y plazo de hasta {{rent_max_days}} días.
- El inquilino congela al instante el alquiler de todo el plazo y una fianza. Cada día el dueño recibe el alquiler del día menos una comisión del {{rent_fee}}%.
- Durante el alquiler el negocio trabaja para el inquilino: mercancía, insumos y reparaciones son suyos.
- Un negocio alquilado no se puede vender, mejorar ni cambiar de aspecto.
- La fianza vuelve al inquilino salvo que el negocio quede muy desgastado.""",
    ),
    "seizure": dict(
        t="Embargo",
        s="Cuándo la Ciudad se queda con un negocio.",
        b="""Un negocio se embarga en dos casos.
- **Sin actividad.** En cualquier periodo de {{act_days}} días hay que comprar {{act_buy}} uds. o vender {{act_sell}} uds. en el mercado; mira [[activity-rule|Regla de actividad]].
- **Deuda de préstamo.** El préstamo está vencido y no hay ningún pago en {{credit_days}} días. Cualquier pago quita el vencimiento.
GRAM CITY pone a la venta el negocio embargado. La venta paga primero la deuda; el resto va al antiguo dueño.
> Te avisamos en el juego y en Telegram 3 días antes del embargo.""",
    ),
    "resources": dict(
        t="Recursos",
        s="Qué hay en el almacén y en qué se diferencian los recursos.",
        b="""El almacén guarda todo lo que produjeron tus negocios y todo lo que compraste.
[[table:weights]]
- Debajo de cada recurso: cuánto vale ahora.
- Los recursos de nivel 3 se pueden vender o activar como efecto.
- Un recurso recibido como recompensa se guarda aparte: no se puede vender.""",
        show=["El almacén: espacio y valor de tus recursos."],
    ),
    "capacity": dict(
        t="Capacidad y pesos",
        s="Cuánto cabe en el almacén.",
        b="""El espacio del almacén es limitado. La capacidad es la suma de los almacenes de todos tus negocios; más nivel, más almacén.
[[table:weights]]
- Los lotes del mercado también ocupan espacio.
- Lo que no cabe se estropea más rápido; mira [[spoilage|Deterioro]].""",
        show=["Espacio usado y libre del almacén."],
    ),
    "warehouse-value": dict(
        t="Valor estimado del almacén",
        s="Cuánto vale todo lo que tienes.",
        b="""Encima de la lista de recursos está el valor estimado del almacén: lo que costarían todos tus recursos a precios actuales.
- Debajo de cada recurso, su valor.
- Es una estimación: el precio real es aquel al que vendas.""",
        show=["Valor estimado de todo el almacén."],
    ),
    "spoilage": dict(
        t="Deterioro a las {{spoil_time}}",
        s="Cada día se estropea parte de la mercancía del almacén.",
        b="""Cada día a las **{{spoil_time}} (hora de Moscú)** se estropea el **{{spoil_in}}%** de la mercancía del almacén, y el **{{spoil_over}}%** de lo que supera el límite. Se cuenta en unidades enteras; los recursos de nivel 3 no se estropean.
- El deterioro afecta igual a todos los recursos.
- Los lotes del mercado no se estropean.
- El potenciador «Protección del almacén» lo evita.
> No acumules: vende antes de las {{spoil_time}}. Por la tarde te enviamos un recordatorio.""",
        show=["El almacén: lo que está aquí se estropea a las {{spoil_time}}."],
    ),
    "boosters": dict(
        t='Potenciadores',
        s='Inicio automático de turnos, protección del almacén, reparar todo, XP ×2: qué dan.',
        b="""Los potenciadores se activan en Almacén → Potenciadores. No se pueden vender.
[[table:boosters]]
- Los recursos de nivel 3 también se activan aquí, cada uno con su efecto; mira [[t3-buffs|Efectos de recursos de nivel 3]].
- No funcionan más de dos potenciadores y efectos a la vez.
> Los potenciadores son recompensas de City Pass: uno en cada nivel, más en la vía premium.""",
        show=['La pestaña «Potenciadores»: qué tienes y qué está activo ahora.'],
    ),
    "t3-buffs": dict(
        t='Efectos de recursos de nivel 3',
        s='Qué da cada recurso de nivel 3 y cómo activarlo.',
        b="""Cada recurso de nivel 3 puede activarse como efecto: una ventaja temporal para todos tus negocios.
[[table:t3buffs]]
1. Almacén → Potenciadores.
2. Toca «Activar» junto al recurso: se gasta 1 unidad.
3. El efecto dura el tiempo indicado; lo que queda aparece en «Activos ahora».
- Dónde conseguirlos: los producen los negocios de nivel 3, los venden jugadores en el mercado y son recompensas de City Pass. Uno es gratis por el [[first-days|plan de 3 días]].
- Un recurso de recompensa no se puede vender ni gastar en una [[upgrade|mejora]] del negocio: solo se puede activar como efecto.
- El mismo efecto no puede funcionar dos veces; como máximo dos potenciadores y efectos a la vez.
> Un recurso nunca se activa solo: espera en el almacén hasta que toques «Activar».""",
        show=['La pestaña «Potenciadores»: recursos de nivel 3 y el botón «Activar».'],
    ),
    "buy": dict(
        t='Comprar un recurso',
        s='El libro de órdenes, orden limitada y de mercado.',
        b="""Comercio → «Comercio» — el libro de órdenes del recurso. Elige el recurso arriba.
1. Toca «Comprar».
2. Orden **limitada**: indica un precio — compra todo lo que se vende a ese precio o menos; el resto espera en el libro. El dinero del resto queda congelado y vuelve al cancelar.
3. Orden **de mercado**: compra al momento del libro, del precio más bajo hacia arriba; lo que no se encuentra no se guarda.
4. La cantidad son unidades enteras; valor = precio × cantidad, se recalculan entre sí.
5. «Compra máx.» cuenta tu dinero y el espacio del almacén.
- La operación se hace al precio de la orden que ya estaba en el libro: si tu límite es mayor, la diferencia vuelve al instante.
- Pago: primero el saldo de bonificación, luego el principal. «+» junto al saldo — recargar.
- Puedes comprar cuando tienes un negocio propio.""",
        show=['Arriba el recurso, a la derecha el libro.', 'A la izquierda, el formulario.'],
    ),
    "sell": dict(
        t='Vender un recurso',
        s='Orden de venta, precio, impuesto, {{lot_hours}} horas.',
        b="""Comercio → «Comercio» → «Vender». Los bienes salen del almacén al momento y esperan comprador en el libro.
1. Elige el recurso arriba.
2. Orden **limitada**: tu precio por unidad (con céntimos). Si en el libro hay compradores a ese precio o más, una parte se vende al instante, a su precio.
3. Orden **de mercado**: vende al momento a los compradores del libro, del precio más alto hacia abajo; lo no vendido vuelve al almacén.
4. Indica la cantidad y toca «Vender». El impuesto y el neto están sobre el botón.
[[table:taxes]]
> Una orden sin vender en {{lot_hours}} horas vuelve al almacén. El precio lo pones tú, también con un negocio de nivel 0.""",
        show=['«Vender» — venta desde el almacén.'],
    ),
    "edit-lot": dict(
        t='Mis órdenes',
        s='Progreso, cancelar, historial.',
        b="""Bajo el libro, todas tus órdenes abiertas, de compra y de venta.
- Ves el precio, cuánto se ha ejecutado y qué está congelado (dinero o bienes).
- **«Cancelar»** retira la orden: vuelve el resto del dinero o de los bienes.
- El botón a la derecha de «Órdenes» — tu historial de operaciones.
- Órdenes de venta: una por cada negocio (una sin negocio); de compra: hasta 10.""",
        show=['Tus órdenes: progreso y «Cancelar».'],
    ),
    "city-market": dict(
        t="La Ciudad en el mercado",
        s="Qué compra la Ciudad y cuándo.",
        b="""El Mercado de la Ciudad es una red de seguridad para novatos y un mercado poco activo. Compra por debajo y vende por encima del precio de tabla: con jugadores se gana más.
- La Ciudad solo compra recursos de **nivel 1**.
- Compra la primera venta de un novato casi al momento.
- A un negocio de nivel 0 la Ciudad le compra al mismo precio de recompra (la orden de la Ciudad en el libro); el dinero va a la cuenta bonus.
- Para negocios de nivel 1 o superior: lotes a precio igual o menor que el de la Ciudad; el dinero va a la cuenta principal.
- Todo lo que compra, la Ciudad lo vuelve a poner en el mercado.""",
    ),
    "tenders": dict(
        t="Licitaciones",
        s="Un acuerdo de suministro diario.",
        b="""Una licitación es un pedido: «necesito X uds. de un recurso al día a este precio».
1. Comercio → «Contratos» → «Bolsa»: pedidos abiertos de jugadores.
2. Envía una oferta. Sin respuesta se cierra a las 72 h.
3. Si la aceptan, el recurso sale solo cada día y el dinero llega sin lotes (menos impuesto).
- «Compras»: tus pedidos; «Suministros»: tus acuerdos.
- Entrega: a la hora de entrega la mercancía sale del almacén del proveedor y viaja hacia ti por las calles de la isla: de {{dl_min}} a {{dl_max}} min según el camino. Todos ven el camión; su ruta solo la ven tú y el proveedor.
- Un camión en camino se puede «Entregar ahora»: {{dl_speed}} $CITY por cada minuto que falta (mínimo {{dl_fee}}). Puede pagar el comprador o el proveedor.
- Un apagón solo ocurre cuando lo anuncia la administración (normalmente la ciudad está iluminada). Durante un apagón el camión tarda 1,5 veces más por un distrito a oscuras: no se detiene, va más lento y su hora de llegada se retrasa. Si la carga no cabe en el almacén, espera en la puerta y se descarga sola cuando haya sitio.
> Si falta recurso o dinero, hay 24 horas para corregirlo; luego el acuerdo se rompe con penalización.""",
        show=["Abre «Contratos».", "«Bolsa»: pedidos abiertos de jugadores."],
    ),
    "contracts": dict(
        t="Contratos de cooperación",
        s="Suministro entre negocios y el efecto del patrocinador.",
        b="""Un contrato de cooperación es un suministro diario de un recurso de un negocio a otro durante hasta 90 días.
- El proveedor fija el recurso, la cantidad diaria, el precio y el plazo.
- Si el proveedor es un negocio de nivel 3, su efecto actúa sobre el negocio receptor mientras dure el contrato.
- Se puede cancelar en cualquier momento; lo entregado se queda con el receptor.""",
    ),
    "analytics": dict(
        t="Analítica de precios",
        s="Gráficos, tendencias, volúmenes.",
        b="""Analítica: gráficos de precios de cada recurso.
- Dónde conviene vender y qué es más barato comprar.
- Cuánto se vende al día y cómo cambia el precio.
- Se abre con el botón «Analítica» de la pantalla «Negocios».""",
        show=["Toca «Analítica»: se abren los gráficos de precios."],
    ),
    "taxes": dict(
        t="Impuestos",
        s="Tipos por nivel y adónde va el impuesto.",
        b="""Cada venta de un recurso paga un impuesto según el nivel del recurso. La administración fija los tipos; abajo están los actuales.
[[table:taxes]]
- Ves el importe neto antes de publicar el lote.
- Una parte del impuesto ({{ref_pct}}% del acuerdo) va a quien invitó al vendedor: el vendedor no pierde nada.
- Los efectos de recursos de nivel 3 pueden bajar la comisión de comercio.""",
    ),
    "deposit": dict(
        t="Recarga",
        s="Cómo poner GRAM en la cuenta principal.",
        b="""1. Toca el saldo → «Recargar».
2. Conecta una billetera: Tonkeeper, Telegram Wallet u otra.
3. Envía GRAM. **GRAM es la moneda TON: envía solo TON.**
4. El dinero llega a la cuenta principal: 1 GRAM = {{city_per_gram}} $CITY.
> Envía solo desde la billetera conectada a tu cuenta.""",
        show=["Toca el saldo: ahí está «Recargar»."],
    ),
    "withdraw": dict(
        t="Retiro",
        s="Qué se puede retirar y qué hace falta.",
        b="""Solo se retira la cuenta **principal**; la bonus no.
1. Toca el saldo → «Retirar».
2. Indica el importe (desde {{withdraw_min}} GRAM) y confirma con un código 2FA o una Passkey.
3. La solicitud se revisa y se envía a tu billetera.
- La comisión es del {{withdraw_fee}}%. Con el banco de un jugador es más rápido, con la comisión propia del banco (hasta el {{instant_fee_max}}%).""",
        show=["Toca el saldo: ahí está «Retirar»."],
    ),
    "security": dict(
        t="Por qué 2FA y Passkey",
        s="Sin ellas no hay retiros, y este es el motivo.",
        b="""La billetera de retiro se cambia en los ajustes. Quien entre en tu cuenta (tu teléfono, correo o Telegram) podría vincular la suya.
- **2FA**: un código de una app de autenticación.
- **Passkey**: huella o cara en tu dispositivo.
Sin el código o la Passkey, el retiro no se hace.
> El soporte nunca pide códigos, contraseñas ni la frase semilla.""",
        show=["Activa 2FA: un código de una app.", "O añade una Passkey: huella o cara."],
    ),
    "history": dict(
        t="Historial de operaciones",
        s="Cada compra, venta, impuesto y recompensa.",
        b="""Menú ☰ → Historial: todas las operaciones con tu saldo.
- Filtra por tipo: compras, ventas, impuestos, recompensas, recargas, retiros.
- Cada operación muestra el importe, la cuenta (principal o bonus) y la hora.""",
        show=["Filtro por tipo de operación."],
    ),
    "credit": dict(
        t="Préstamo con garantía de un negocio",
        s="Dinero ahora; parte de los ingresos lo devuelve.",
        b="""Pide $CITY con un negocio como garantía, al Estado o al banco de un jugador. Parte de tus ingresos lo devuelve sola.
- Solo con un negocio de nivel 1 o superior, hasta el {{credit_max}}% de su valor.
[[table:credit]]
- Sin ningún pago en {{credit_days}} días (un banco fija su propio plazo): el préstamo vence y el tipo se duplica.
- {{credit_days}} días más vencido sin un solo pago: el negocio se embarga. Cualquier pago quita el vencimiento.
- El negocio embargado se vende; de la venta se toman el préstamo y el doble de interés: tipo del {{credit_rate}}% → préstamo × {{credit_back}}. El resto es tuyo.""",
        show=["El botón «Obtener crédito»."],
    ),
    "banks": dict(
        t="Bancos de jugadores",
        s="GRAM Bank: préstamos y retiros rápidos de jugadores.",
        b="""El dueño de un negocio GRAM Bank es un banco.
- Presta a jugadores a su propio tipo (no más del {{bank_rate_max}}%).
- Hace retiros rápidos con su propia comisión (hasta el {{instant_fee_max}}%).
- Solo funcionan bancos con durabilidad del 50% o más.""",
    ),
    "daily-login": dict(
        t="Entrada diaria",
        s="La recompensa crece {{daily_days}} días seguidos.",
        b="""Entra cada día y la recompensa crece: de {{daily_first}} a {{daily_last}} $CITY el día {{daily_days}}.
- Para reclamarla, cumple un objetivo del día.
- Si faltas un día, la racha empieza de nuevo. Un escudo de racha salva un día perdido.
- Las recompensas van a la cuenta bonus.""",
        show=["La tarjeta de entrada diaria."],
    ),
    "quests": dict(
        t="Tareas y objetivos",
        s="Camino del novato, objetivos diarios y semanales.",
        b="""- **Camino del novato**: 7 objetivos seguidos: negocio, turno, compra, lote, venta, reparación, mejora.
- **Objetivos diarios**: 3 cada día; **semanales**: 3 más.
- El progreso se cuenta solo: basta con tocar «Reclamar».
- Recompensas a la cuenta bonus y XP de City Pass. Todos los semanales dan un escudo de racha.""",
        show=["Objetivos del día."],
    ),
    "partner-tasks": dict(
        t="Tareas de socios",
        s="Suscripciones y acciones con socios, a cambio de $CITY y aspectos.",
        b="""Tareas → «Socios»: suscribirse a un canal, abrir la app de un socio y más.
- La recompensa es $CITY en la cuenta bonus y a veces un aspecto.
- Algunas tareas requieren Telegram conectado.""",
        show=["La pestaña de tareas de socios."],
    ),
    "city-pass": dict(
        t="City Pass",
        s="Una temporada de {{pass_levels}} niveles: XP y recompensas.",
        b="""City Pass es una temporada de {{pass_levels}} niveles.
- La XP llega de objetivos diarios y semanales, turnos, reparaciones, ventas a jugadores y la racha de entradas.
- **Vía gratuita**: una recompensa en cada nivel: potenciadores, recursos de nivel 3, escudos.
- **Premium**: recompensas extra en los niveles 1, 5, 10…; se compra con la cuenta principal.
- Recoge las recompensas con el botón «Reclamar».""",
        show=["Tu nivel y la XP de la temporada."],
    ),
    "referrals": dict(
        t="Referidos",
        s="Invita amigos y recibe parte del impuesto de sus ventas.",
        b="""El botón 👥 arriba en «Negocios» tiene tu enlace.
- Un amigo juega con tu enlace: recibes el {{ref_pct}}% del importe de sus ventas en el mercado.
- Sale del impuesto: tu amigo no pierde nada.
- Ahí también está la lista de invitados y lo que aportaron.""",
        show=["Toca 👥: se abren tu enlace y tus amigos."],
    ),
    "chat": dict(
        t="Chat",
        s="El chat general y el de la alianza.",
        b="""El chat general de todos los jugadores y el de tu alianza.
- Acuerda tratos y comparte consejos.
- Cualquier mensaje se puede traducir con un botón.
- No sigas enlaces de desconocidos ni compartas códigos; mira [[safety|Seguridad]].""",
        show=["Canales del chat: general y alianza."],
    ),
    "leagues": dict(
        t="Ligas",
        s="Una competición semanal entre iguales.",
        b="""Cada semana estás en un grupo de jugadores de fuerza parecida.
- Puntos por objetivos, turnos, reparaciones, ventas a jugadores y la racha de entradas.
- Los mejores suben: Bronce → Plata → Oro → Platino → Diamante.
- **‹ ›**: otras ligas; **«Toda la división»**: todos los jugadores, búsqueda y amigos.
- Premios semanales: $CITY en la cuenta bonus y escudos de racha.
> No cuentan las ventas a la Ciudad ni entre cuentas vinculadas.""",
        show=["Recorre las ligas con las flechas.", "El selector de clasificaciones."],
    ),
    "alliances": dict(
        t="Alianzas",
        s="Equipos de jugadores: tesoro, chat, niveles.",
        b="""Una alianza es un equipo de jugadores: tesoro común, chat y niveles.
- Puedes unirte al momento: abierta, por solicitud o por invitación.
- Para crear una: nivel {{alliance_level}} de City Pass, un negocio y {{alliance_cost}} $CITY.
- La XP de la alianza es el 10% de la XP de City Pass de sus miembros; tú no pierdes nada.
- Los pagos del tesoro van a la cuenta bonus.""",
        show=["La pestaña «Alianza»."],
    ),
    "leaderboard": dict(
        t="Ranking",
        s="Los mejores por saldo, ingresos, negocios y comercio.",
        b="""El ranking muestra a los mejores jugadores. Ordena:
- por saldo, por ingresos, por número de negocios, por número de parcelas, por volumen de comercio.
- Tu puesto aparece al final de la lista.""",
    ),
    "profile": dict(
        t="Perfil del jugador",
        s="Estadísticas, alianza, Founder Pass.",
        b="""Toca tu avatar: se abre tu perfil con estadísticas, alianza y nivel de City Pass.
- Los perfiles de otros jugadores se abren desde el chat y las clasificaciones.""",
        show=["Tu perfil."],
    ),
    "activity-rule": dict(
        t="Regla de actividad",
        s="La Ciudad se queda con los negocios de quien no comercia.",
        b="""En cualquier periodo de **{{act_days}} días** hay que **comprar {{act_buy}} uds.** o **vender {{act_sell}} uds.** en el mercado: basta una de las dos.
- Si quedan 3 días para el embargo, te avisamos en el juego y en Telegram.
- Abajo están tus cifras de los últimos {{act_days}} días.""",
    ),
    "zero-limits": dict(
        t="Límites del nivel 0",
        s="Qué no puedes hacer mientras el negocio sea de nivel 0.",
        b="""Mientras tengas un negocio de nivel 0:
- no puedes comprar otro negocio ni pedir un préstamo;
- el dinero de las ventas va a la cuenta bonus;
- no puedes vender ni alquilar el negocio;
- otro jugador puede comprarlo al precio del mapa ×{{zero_mult}}.
Subirlo a nivel 1 quita todos los límites.""",
    ),
    "safety": dict(
        t="Seguridad y estafas",
        s="Cómo no perder tu cuenta ni tu dinero.",
        b="""- El soporte **nunca** pide códigos 2FA, contraseñas ni la frase semilla.
- No sigas enlaces de mensajes privados «de la administración».
- Activa 2FA o una Passkey: sin ellas no hay retiros.
- Comercia solo por el mercado y las licitaciones: «mándame el dinero y te envío el recurso» es una estafa.
> ¿Un mensaje sospechoso? Denúncialo en el chat o escribe al soporte.""",
    ),
    "faq": dict(
        t="Preguntas frecuentes",
        s="Respuestas breves a lo principal.",
        b="""# ¿Por qué desapareció mi mercancía?
Cada día a las {{spoil_time}} (hora de Moscú) se estropea una parte; mira [[spoilage|Deterioro]]. Un lote sin vender vuelve al almacén a las {{lot_hours}} horas.
# ¿Por qué mi negocio no produce?
No hay turno, faltan insumos o la durabilidad está al 0%.
# ¿Por qué no puedo retirar los bonus?
La cuenta bonus solo se gasta en el juego.
# ¿Por qué la Ciudad no compró mi lote?
La Ciudad solo compra nivel 1 y solo a su precio o menos.
# ¿Dónde está mi negocio gratis?
El alquiler de {{lease_days}} días terminó sin mejora, u otro jugador lo compró.""",
    ),
    "glossary": dict(
        t="Glosario",
        s="Las palabras del juego en lenguaje sencillo.",
        b="""= Alianza | Un equipo de jugadores con tesoro y chat
= Cuenta bonus | Recompensas del juego: se gastan en el juego, no se retiran
= Cuenta principal | El dinero que puedes recargar y retirar
= Deterioro | La pérdida diaria de parte de la mercancía a las {{spoil_time}} (hora de Moscú)
= Efecto | Una ventaja temporal: más mercancía o menos gastos
= Embargo | La Ciudad se queda con un negocio por inactividad o deuda
= Escrow | Dinero congelado para un acuerdo
= GRAM | La moneda TON en el juego
= Licitación | Un pedido de suministro diario de un recurso
= Lote | Tu anuncio de venta de un recurso en el mercado
= Nivel | Grupo de negocios y recursos: 1, 2 o 3
= Ocupar | Tomar un negocio gratis de nivel 0 durante {{lease_days}} días
= Patrocinador | Negocio de nivel 3 cuyo efecto actúa sobre sus socios de contrato
= Potenciador | Un efecto temporal: inicio automático de turnos, protección del almacén y más
= Precio de recompra | El precio al que la Ciudad compra un recurso; el mismo para todos
= Turno | {{shift_hours}} horas en las que un negocio produce y se desgasta
= $CITY | La moneda del juego: 1 GRAM = {{city_per_gram}} $CITY""",
    ),
    "support": dict(
        t="Soporte",
        s="Willy GRAM y agentes humanos.",
        b="""Menú ☰ → Ayuda: el chat de soporte.
- Primero responde **Willy GRAM**, un asistente que trabaja con la base de respuestas. Revisa tu cuenta y te envía el enlace al artículo.
- Si hace falta, se une una persona.
- Escribe en tu idioma: la respuesta llega en él.
> El soporte nunca pide códigos ni la frase semilla.""",
        show=["El menú ☰: ahí está «Ayuda»."],
    ),
    "blackout": dict(
        t='Apagón de la isla',
        s='La isla se apaga: los jugadores encienden los distritos juntos entregando recursos.',
        b="""A veces la isla GRAM se apaga durante {{bo_hours}} horas. Cada uno de los 4 distritos tiene su propia lista de recursos que necesita la red.
1. Abre «Apagón»: desde la franja de arriba de la pantalla o desde el menú del negocio. Tu distrito aparece como «tu distrito».
2. Elige un distrito y pulsa «Entregar»: el recurso pasa de tu almacén a la red.
3. Si no tienes suficiente, compra en el mercado o firma un contrato con un jugador que lo produzca.
- El distrito se enciende solo en cuanto recibe todo. Todos los que entregaron reciben el {{bo_reward}}% del valor en $CITY de bonificación y XP de City Pass.
- Los {{bo_top}} principales proveedores del distrito aparecen en la torre y sus edificios tienen marco dorado en el mapa. El distrito obtiene +{{bo_lit}}% de producción durante {{bo_lit_days}} días.
- Si se acaba el tiempo, el distrito queda a oscuras: su producción baja un {{bo_fail}}% durante {{bo_fail_days}} días y a quienes entregaron se les devuelve el {{bo_refund}}% del valor.
> «Isla encendida N%» indica qué parte de todo lo que necesita la isla ya se entregó. La producción no depende de este número.""",
    ),
}
