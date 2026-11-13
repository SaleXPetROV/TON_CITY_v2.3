// Willy GRAM — the support assistant: the player-side words of the chat, 9 languages.
const W = {
  helped: { ru: 'Помогло', en: 'Helped', es: 'Me ayudó', zh: '有帮助', fr: 'Utile', de: 'Hat geholfen', ja: '役に立った', ko: '도움이 됐어요', id: 'Membantu' },
  notHelped: { ru: 'Не помогло', en: "Didn't help", es: 'No me ayudó', zh: '没有帮助', fr: 'Pas utile', de: 'Hat nicht geholfen', ja: '役に立たなかった', ko: '도움이 안 됐어요', id: 'Tidak membantu' },
  thanks: { ru: 'Спасибо за оценку', en: 'Thanks for the feedback', es: 'Gracias por tu opinión', zh: '感谢反馈', fr: 'Merci pour votre avis', de: 'Danke für die Rückmeldung', ja: 'ご評価ありがとうございます', ko: '평가해 주셔서 감사합니다', id: 'Terima kasih atas penilaiannya' },
  human: { ru: 'Позвать человека', en: 'Call a human', es: 'Llamar a una persona', zh: '转人工', fr: 'Appeler un humain', de: 'Mitarbeiter rufen', ja: '担当者を呼ぶ', ko: '상담원 연결', id: 'Panggil manusia' },
  article: { ru: 'Статья', en: 'Article', es: 'Artículo', zh: '文章', fr: 'Article', de: 'Artikel', ja: '記事', ko: '문서', id: 'Artikel' },
  show: { ru: 'Показать на деле', en: 'Show me', es: 'Muéstramelo', zh: '实际演示', fr: 'Me montrer', de: 'Zeig es mir', ja: '実際に見る', ko: '직접 보기', id: 'Tunjukkan' },
  open: { ru: 'Открыть экран', en: 'Open the screen', es: 'Abrir la pantalla', zh: '打开页面', fr: "Ouvrir l'écran", de: 'Bildschirm öffnen', ja: '画面を開く', ko: '화면 열기', id: 'Buka layar' },
  status: { ru: 'Willy GRAM', en: 'Willy GRAM', es: 'Willy GRAM', zh: 'Willy GRAM', fr: 'Willy GRAM', de: 'Willy GRAM', ja: 'Willy GRAM', ko: 'Willy GRAM', id: 'Willy GRAM' },
  role: { ru: 'помощник поддержки', en: 'support assistant', es: 'asistente de soporte', zh: '客服助手', fr: 'assistant du support', de: 'Support-Assistent', ja: 'サポートアシスタント', ko: '지원 도우미', id: 'asisten dukungan' },
  hint: {
    ru: 'Сначала ответит Willy GRAM — помощник поддержки. Если нужно, подключится человек. Пишите на своём языке.',
    en: 'Willy GRAM, the support assistant, answers first. A person joins if needed. Write in your language.',
    es: 'Primero responde Willy GRAM, el asistente de soporte. Si hace falta, se une una persona. Escribe en tu idioma.',
    zh: '先由客服助手 Willy GRAM 回答，需要时会有真人接入。请用你的语言提问。',
    fr: "Willy GRAM, l'assistant du support, répond d'abord. Un humain intervient si besoin. Écrivez dans votre langue.",
    de: 'Zuerst antwortet Willy GRAM, der Support-Assistent. Bei Bedarf kommt ein Mensch dazu. Schreib in deiner Sprache.',
    ja: 'まずサポートアシスタントの Willy GRAM が回答します。必要に応じて担当者が対応します。ご自分の言語でどうぞ。',
    ko: '먼저 지원 도우미 Willy GRAM이 답변합니다. 필요하면 상담원이 연결됩니다. 편한 언어로 써 주세요.',
    id: 'Willy GRAM, asisten dukungan, menjawab lebih dulu. Jika perlu, manusia akan bergabung. Tulis dalam bahasa Anda.',
  },
  waiting: { ru: 'Ждём оператора', en: 'Waiting for an operator', es: 'Esperando a un operador', zh: '等待客服', fr: 'En attente d’un opérateur', de: 'Warten auf Mitarbeiter', ja: 'オペレーター待ち', ko: '상담원 대기 중', id: 'Menunggu operator' },
  hidden: { ru: 'Сообщение скрыто', en: 'Message hidden', es: 'Mensaje oculto', zh: '消息已隐藏', fr: 'Message masqué', de: 'Nachricht ausgeblendet', ja: 'メッセージは非表示', ko: '메시지 숨김', id: 'Pesan disembunyikan' },
};

export const wl = (key, lang) => (W[key] && (W[key][lang] || W[key].en)) || key;
