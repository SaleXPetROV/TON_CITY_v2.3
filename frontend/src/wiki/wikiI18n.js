/**
 * Interface strings of «Справочник» (the articles themselves come from the server, GET /api/wiki/...).
 * {n} {total} {title} … are filled by fill(). Other languages fall back to English.
 */
const ru = {
  title: 'Справочник', sub: 'Всё о GRAM City — с кнопкой «Показать на деле»', search: 'Поиск: смена, налог, вывод…',
  route: 'Маршрут новичка', routeOf: '{n} из {total}', routeNext: 'Дальше: {title}', routeGo: 'Продолжить', routeDone: 'Гид пройден', routeAgain: 'Пройти заново',
  articles: '{n} статей', updated: 'обновлено {d}', article: 'Статья', minutes: '{n} мин чтения', howto: 'Как это сделать',
  need: 'Что нужно', checked: 'проверено только что', show: 'Показать на деле', first: 'Сначала: {title}', back: 'После этого вернёмся сюда',
  backTo: '← Вернуться: {title}', related: 'Читайте также', helped: 'Статья помогла?', yes: 'Да', no: 'Нет', thanks: 'Спасибо за ответ',
  found: 'Нашлось статей: {n}', notFound: 'Ничего не нашлось', noAnswer: 'Не нашли ответ?', askText: 'Спросите поддержку — Willy GRAM ответит по базе ответов и проверит ваш аккаунт.', ask: 'Спросить',
  openAll: 'Открыть весь Справочник', screen: 'Справочник: {title}', step: 'Шаг {n}/{total}', tapHint: 'Нажмите на подсветку ✦', next: 'Далее', done: 'Готово',
  toArticle: '← К статье', kindTap: 'Действие', kindLook: 'Показ', missing: 'Эта кнопка сейчас не на экране — переходим дальше.',
  login: 'Войдите в игру, чтобы проверить свой аккаунт.', openGame: 'Открыть в GRAM City', allSections: 'Все разделы', isNew: 'новое',
  glossary: 'Словарик', words: '{n} слов', help: 'Справочник', loading: 'Загрузка…', error: 'Не удалось загрузить. Проверьте соединение.',
  screens: { map: 'Карта', maps: 'Карты', resources: 'Склад', trading: 'Торговля', community: 'Общение', chat: 'Чат', tasks: 'Задания', 'city-pass': 'City Pass', credit: 'Кредит', history: 'История', settings: 'Настройки', security: 'Безопасность', marketplace: 'Маркетплейс', leaderboard: 'Рейтинг', analytics: 'Аналитика' },
};
const en = {
  title: 'Wiki', sub: 'All about GRAM City — with a «Show me» button', search: 'Search: shift, tax, withdrawal…',
  route: 'Newcomer route', routeOf: '{n} of {total}', routeNext: 'Next: {title}', routeGo: 'Continue', routeDone: 'Guide completed', routeAgain: 'Take it again',
  articles: '{n} articles', updated: 'updated {d}', article: 'Article', minutes: '{n} min read', howto: 'How to do it',
  need: 'What you need', checked: 'checked just now', show: 'Show me', first: 'First: {title}', back: 'We will come back here after that',
  backTo: '← Back to: {title}', related: 'Read also', helped: 'Was this helpful?', yes: 'Yes', no: 'No', thanks: 'Thanks for the answer',
  found: 'Articles found: {n}', notFound: 'Nothing found', noAnswer: 'No answer found?', askText: 'Ask support — Willy GRAM answers from the answer base and checks your account.', ask: 'Ask',
  openAll: 'Open the whole wiki', screen: 'Wiki: {title}', step: 'Step {n}/{total}', tapHint: 'Tap the highlight ✦', next: 'Next', done: 'Done',
  toArticle: '← To the article', kindTap: 'Action', kindLook: 'Look', missing: 'This button is not on the screen right now — moving on.',
  login: 'Sign in to the game to check your account.', openGame: 'Open in GRAM City', allSections: 'All sections', isNew: 'new',
  glossary: 'Glossary', words: '{n} words', help: 'Wiki', loading: 'Loading…', error: 'Could not load. Check the connection.',
  screens: { map: 'Map', maps: 'Maps', resources: 'Warehouse', trading: 'Trading', community: 'Community', chat: 'Chat', tasks: 'Tasks', 'city-pass': 'City Pass', credit: 'Credit', history: 'History', settings: 'Settings', security: 'Security', marketplace: 'Marketplace', leaderboard: 'Leaderboard', analytics: 'Analytics' },
};
const es = {
  title: 'Wiki', sub: 'Todo sobre GRAM City, con el botón «Muéstramelo»', search: 'Buscar: turno, impuesto, retiro…',
  route: 'Ruta del novato', routeOf: '{n} de {total}', routeNext: 'Siguiente: {title}', routeGo: 'Continuar', routeDone: 'Guía completada', routeAgain: 'Repetir',
  articles: '{n} artículos', updated: 'actualizado {d}', article: 'Artículo', minutes: '{n} min de lectura', howto: 'Cómo hacerlo',
  need: 'Qué necesitas', checked: 'comprobado ahora', show: 'Muéstramelo', first: 'Primero: {title}', back: 'Después volveremos aquí',
  backTo: '← Volver a: {title}', related: 'Lee también', helped: '¿Te ha ayudado?', yes: 'Sí', no: 'No', thanks: 'Gracias por responder',
  found: 'Artículos encontrados: {n}', notFound: 'No se encontró nada', noAnswer: '¿No encontraste la respuesta?', askText: 'Pregunta a soporte: Willy GRAM responde con la base de respuestas y revisa tu cuenta.', ask: 'Preguntar',
  openAll: 'Abrir toda la Wiki', screen: 'Wiki: {title}', step: 'Paso {n}/{total}', tapHint: 'Toca lo resaltado ✦', next: 'Siguiente', done: 'Listo',
  toArticle: '← Al artículo', kindTap: 'Acción', kindLook: 'Vista', missing: 'Este botón no está en pantalla ahora: seguimos.',
  login: 'Entra en el juego para revisar tu cuenta.', openGame: 'Abrir en GRAM City', allSections: 'Todas las secciones', isNew: 'nuevo',
  glossary: 'Glosario', words: '{n} palabras', help: 'Wiki', loading: 'Cargando…', error: 'No se pudo cargar. Revisa la conexión.',
  screens: { map: 'Mapa', maps: 'Mapas', resources: 'Almacén', trading: 'Comercio', community: 'Comunidad', chat: 'Chat', tasks: 'Tareas', 'city-pass': 'City Pass', credit: 'Crédito', history: 'Historial', settings: 'Ajustes', security: 'Seguridad', marketplace: 'Mercado', leaderboard: 'Ranking', analytics: 'Analítica' },
};
const zh = {
  title: '百科', sub: 'GRAM City 的一切——附「演示给我看」按钮', search: '搜索：班次、税、提现…',
  route: '新手路线', routeOf: '{n}/{total}', routeNext: '下一步：{title}', routeGo: '继续', routeDone: '引导已完成', routeAgain: '重新开始',
  articles: '{n} 篇文章', updated: '更新于 {d}', article: '文章', minutes: '阅读 {n} 分钟', howto: '怎么做',
  need: '所需条件', checked: '刚刚检查', show: '演示给我看', first: '先：{title}', back: '完成后我们会回到这里',
  backTo: '← 返回：{title}', related: '延伸阅读', helped: '这篇文章有帮助吗？', yes: '有', no: '没有', thanks: '感谢反馈',
  found: '找到 {n} 篇文章', notFound: '没有找到', noAnswer: '没找到答案？', askText: '问客服——Willy GRAM 会根据答案库回复并检查你的账户。', ask: '提问',
  openAll: '打开整部百科', screen: '百科：{title}', step: '第 {n}/{total} 步', tapHint: '点击高亮处 ✦', next: '下一步', done: '完成',
  toArticle: '← 返回文章', kindTap: '操作', kindLook: '查看', missing: '这个按钮现在不在屏幕上——继续下一步。',
  login: '登录游戏即可检查你的账户。', openGame: '在 GRAM City 中打开', allSections: '全部分区', isNew: '新',
  glossary: '词汇表', words: '{n} 个词', help: '百科', loading: '加载中…', error: '加载失败，请检查网络。',
  screens: { map: '地图', maps: '地图', resources: '仓库', trading: '交易', community: '社区', chat: '聊天', tasks: '任务', 'city-pass': 'City Pass', credit: '贷款', history: '历史', settings: '设置', security: '安全', marketplace: '市场', leaderboard: '排行榜', analytics: '分析' },
};
const fr = {
  title: 'Wiki', sub: 'Tout sur GRAM City, avec le bouton « Montrez-moi »', search: 'Rechercher : service, taxe, retrait…',
  route: 'Parcours du débutant', routeOf: '{n} sur {total}', routeNext: 'Ensuite : {title}', routeGo: 'Continuer', routeDone: 'Guide terminé', routeAgain: 'Recommencer',
  articles: '{n} articles', updated: 'mis à jour le {d}', article: 'Article', minutes: '{n} min de lecture', howto: 'Comment faire',
  need: 'Ce qu’il faut', checked: 'vérifié à l’instant', show: 'Montrez-moi', first: 'D’abord : {title}', back: 'Ensuite, nous reviendrons ici',
  backTo: '← Retour : {title}', related: 'À lire aussi', helped: 'Cet article vous a aidé ?', yes: 'Oui', no: 'Non', thanks: 'Merci pour votre réponse',
  found: 'Articles trouvés : {n}', notFound: 'Rien trouvé', noAnswer: 'Pas de réponse ?', askText: 'Demandez au support : Willy GRAM répond à partir de la base de réponses et vérifie votre compte.', ask: 'Demander',
  openAll: 'Ouvrir tout le Wiki', screen: 'Wiki : {title}', step: 'Étape {n}/{total}', tapHint: 'Touchez la zone en surbrillance ✦', next: 'Suivant', done: 'Terminé',
  toArticle: '← Vers l’article', kindTap: 'Action', kindLook: 'Aperçu', missing: 'Ce bouton n’est pas à l’écran pour l’instant — on continue.',
  login: 'Connectez-vous au jeu pour vérifier votre compte.', openGame: 'Ouvrir dans GRAM City', allSections: 'Toutes les sections', isNew: 'nouveau',
  glossary: 'Glossaire', words: '{n} mots', help: 'Wiki', loading: 'Chargement…', error: 'Chargement impossible. Vérifiez la connexion.',
  screens: { map: 'Carte', maps: 'Cartes', resources: 'Entrepôt', trading: 'Commerce', community: 'Communauté', chat: 'Chat', tasks: 'Tâches', 'city-pass': 'City Pass', credit: 'Crédit', history: 'Historique', settings: 'Paramètres', security: 'Sécurité', marketplace: 'Marché', leaderboard: 'Classement', analytics: 'Analyses' },
};
const de = {
  title: 'Handbuch', sub: 'Alles über GRAM City – mit «Zeig es mir»', search: 'Suche: Schicht, Steuer, Auszahlung…',
  route: 'Einsteigerweg', routeOf: '{n} von {total}', routeNext: 'Weiter: {title}', routeGo: 'Fortsetzen', routeDone: 'Guide abgeschlossen', routeAgain: 'Noch einmal',
  articles: '{n} Artikel', updated: 'aktualisiert {d}', article: 'Artikel', minutes: '{n} Min. Lesezeit', howto: 'So geht’s',
  need: 'Was du brauchst', checked: 'gerade geprüft', show: 'Zeig es mir', first: 'Zuerst: {title}', back: 'Danach kommen wir hierher zurück',
  backTo: '← Zurück zu: {title}', related: 'Lies auch', helped: 'War der Artikel hilfreich?', yes: 'Ja', no: 'Nein', thanks: 'Danke für die Antwort',
  found: 'Gefundene Artikel: {n}', notFound: 'Nichts gefunden', noAnswer: 'Keine Antwort gefunden?', askText: 'Frag den Support – Willy GRAM antwortet aus der Antwortdatenbank und prüft dein Konto.', ask: 'Fragen',
  openAll: 'Ganzes Handbuch öffnen', screen: 'Handbuch: {title}', step: 'Schritt {n}/{total}', tapHint: 'Tippe auf die Markierung ✦', next: 'Weiter', done: 'Fertig',
  toArticle: '← Zum Artikel', kindTap: 'Aktion', kindLook: 'Ansicht', missing: 'Diese Schaltfläche ist gerade nicht auf dem Bildschirm – weiter.',
  login: 'Melde dich im Spiel an, um dein Konto zu prüfen.', openGame: 'In GRAM City öffnen', allSections: 'Alle Bereiche', isNew: 'neu',
  glossary: 'Glossar', words: '{n} Begriffe', help: 'Handbuch', loading: 'Wird geladen…', error: 'Laden fehlgeschlagen. Prüfe die Verbindung.',
  screens: { map: 'Karte', maps: 'Karten', resources: 'Lager', trading: 'Handel', community: 'Community', chat: 'Chat', tasks: 'Aufgaben', 'city-pass': 'City Pass', credit: 'Kredit', history: 'Verlauf', settings: 'Einstellungen', security: 'Sicherheit', marketplace: 'Marktplatz', leaderboard: 'Rangliste', analytics: 'Analyse' },
};
const ja = {
  title: 'ガイドブック', sub: 'GRAM City のすべて——「実際に見る」ボタン付き', search: '検索：シフト、税金、出金…',
  route: '初心者ルート', routeOf: '{total}中{n}', routeNext: '次：{title}', routeGo: '続ける', routeDone: 'ガイド完了', routeAgain: 'もう一度',
  articles: '{n} 記事', updated: '{d} 更新', article: '記事', minutes: '{n}分で読めます', howto: 'やり方',
  need: '必要なもの', checked: 'たった今確認', show: '実際に見る', first: 'まず：{title}', back: 'その後ここに戻ります',
  backTo: '← 戻る：{title}', related: 'あわせて読む', helped: 'この記事は役に立ちましたか？', yes: 'はい', no: 'いいえ', thanks: 'ご回答ありがとうございます',
  found: '{n} 件の記事', notFound: '見つかりませんでした', noAnswer: '答えが見つからない？', askText: 'サポートに質問——Willy GRAM が回答ベースから答え、アカウントを確認します。', ask: '質問する',
  openAll: 'ガイドブック全体を開く', screen: 'ガイドブック：{title}', step: 'ステップ {n}/{total}', tapHint: 'ハイライトをタップ ✦', next: '次へ', done: '完了',
  toArticle: '← 記事へ', kindTap: '操作', kindLook: '表示', missing: 'このボタンは今画面にありません——次へ進みます。',
  login: 'アカウントを確認するにはゲームにログインしてください。', openGame: 'GRAM City で開く', allSections: 'すべてのセクション', isNew: '新着',
  glossary: '用語集', words: '{n} 語', help: 'ガイドブック', loading: '読み込み中…', error: '読み込めませんでした。接続を確認してください。',
  screens: { map: 'マップ', maps: 'マップ', resources: '倉庫', trading: '取引', community: 'コミュニティ', chat: 'チャット', tasks: 'タスク', 'city-pass': 'City Pass', credit: 'ローン', history: '履歴', settings: '設定', security: 'セキュリティ', marketplace: 'マーケット', leaderboard: 'ランキング', analytics: '分析' },
};
const ko = {
  title: '가이드북', sub: 'GRAM City의 모든 것 — «직접 보기» 버튼 포함', search: '검색: 교대, 세금, 출금…',
  route: '초보자 루트', routeOf: '{total} 중 {n}', routeNext: '다음: {title}', routeGo: '계속', routeDone: '가이드 완료', routeAgain: '다시 하기',
  articles: '글 {n}개', updated: '{d} 업데이트', article: '글', minutes: '{n}분 분량', howto: '방법',
  need: '필요한 것', checked: '방금 확인함', show: '직접 보기', first: '먼저: {title}', back: '그다음 여기로 돌아옵니다',
  backTo: '← 돌아가기: {title}', related: '함께 읽기', helped: '도움이 되었나요?', yes: '예', no: '아니요', thanks: '응답해 주셔서 감사합니다',
  found: '찾은 글: {n}', notFound: '찾지 못했습니다', noAnswer: '답을 못 찾으셨나요?', askText: '지원팀에 물어보세요 — Willy GRAM이 답변 베이스로 답하고 계정을 확인합니다.', ask: '질문하기',
  openAll: '가이드북 전체 열기', screen: '가이드북: {title}', step: '{n}/{total}단계', tapHint: '강조된 곳을 누르세요 ✦', next: '다음', done: '완료',
  toArticle: '← 글로', kindTap: '동작', kindLook: '보기', missing: '이 버튼은 지금 화면에 없습니다 — 다음으로 넘어갑니다.',
  login: '계정을 확인하려면 게임에 로그인하세요.', openGame: 'GRAM City에서 열기', allSections: '모든 섹션', isNew: '새 글',
  glossary: '용어집', words: '{n}개 용어', help: '가이드북', loading: '불러오는 중…', error: '불러오지 못했습니다. 연결을 확인하세요.',
  screens: { map: '지도', maps: '지도', resources: '창고', trading: '거래', community: '커뮤니티', chat: '채팅', tasks: '과제', 'city-pass': 'City Pass', credit: '대출', history: '기록', settings: '설정', security: '보안', marketplace: '마켓', leaderboard: '랭킹', analytics: '분석' },
};
const id = {
  title: 'Wiki', sub: 'Semua tentang GRAM City — dengan tombol «Tunjukkan»', search: 'Cari: shift, pajak, penarikan…',
  route: 'Rute pemula', routeOf: '{n} dari {total}', routeNext: 'Berikutnya: {title}', routeGo: 'Lanjutkan', routeDone: 'Panduan selesai', routeAgain: 'Ulangi',
  articles: '{n} artikel', updated: 'diperbarui {d}', article: 'Artikel', minutes: '{n} menit baca', howto: 'Cara melakukannya',
  need: 'Yang diperlukan', checked: 'baru saja dicek', show: 'Tunjukkan', first: 'Dulu: {title}', back: 'Setelah itu kita kembali ke sini',
  backTo: '← Kembali ke: {title}', related: 'Baca juga', helped: 'Artikel ini membantu?', yes: 'Ya', no: 'Tidak', thanks: 'Terima kasih atas jawabannya',
  found: 'Artikel ditemukan: {n}', notFound: 'Tidak ada hasil', noAnswer: 'Tidak menemukan jawaban?', askText: 'Tanya dukungan — Willy GRAM menjawab dari basis jawaban dan memeriksa akun Anda.', ask: 'Tanya',
  openAll: 'Buka seluruh Wiki', screen: 'Wiki: {title}', step: 'Langkah {n}/{total}', tapHint: 'Ketuk sorotan ✦', next: 'Lanjut', done: 'Selesai',
  toArticle: '← Ke artikel', kindTap: 'Aksi', kindLook: 'Lihat', missing: 'Tombol ini sedang tidak ada di layar — lanjut.',
  login: 'Masuk ke game untuk memeriksa akun Anda.', openGame: 'Buka di GRAM City', allSections: 'Semua bagian', isNew: 'baru',
  glossary: 'Glosarium', words: '{n} istilah', help: 'Wiki', loading: 'Memuat…', error: 'Gagal memuat. Periksa koneksi.',
  screens: { map: 'Peta', maps: 'Peta', resources: 'Gudang', trading: 'Perdagangan', community: 'Komunitas', chat: 'Obrolan', tasks: 'Tugas', 'city-pass': 'City Pass', credit: 'Kredit', history: 'Riwayat', settings: 'Pengaturan', security: 'Keamanan', marketplace: 'Pasar', leaderboard: 'Peringkat', analytics: 'Analitik' },
};

export const WIKI_I18N = { ru, en, es, zh, fr, de, ja, ko, id };
export const wt = (lang) => (k) => {
  const L = WIKI_I18N[lang] || en;
  return k.split('.').reduce((o, p) => (o ? o[p] : undefined), L) ?? k.split('.').reduce((o, p) => (o ? o[p] : undefined), en) ?? k;
};
export const fill = (s, v = {}) => String(s ?? '').replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? String(v[k]) : m));
