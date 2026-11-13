/**
 * FirstLanguagePicker — the very first thing a new player sees after entering the game:
 * «Choose your language» with every language of the project. Tapping a language previews the
 * window in it; «Let's go» saves the choice (PUT /api/auth/update-language {chosen: true}) and
 * closes. Shown until the player picked a language once (user.language_chosen on the server,
 * or ton_city_lang_explicit on this device). The tutorial waits for this window.
 */
import { useEffect, useMemo, useState } from 'react';
import { Check, Languages, Zap } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';

export const LANG_OPTIONS = [
  { code: 'en', flag: '🇬🇧', name: 'English' },
  { code: 'ru', flag: '🇷🇺', name: 'Русский' },
  { code: 'es', flag: '🇪🇸', name: 'Español' },
  { code: 'zh', flag: '🇨🇳', name: '中文' },
  { code: 'fr', flag: '🇫🇷', name: 'Français' },
  { code: 'de', flag: '🇩🇪', name: 'Deutsch' },
  { code: 'ja', flag: '🇯🇵', name: '日本語' },
  { code: 'ko', flag: '🇰🇷', name: '한국어' },
  { code: 'id', flag: '🇮🇩', name: 'Bahasa Indonesia' },
];

const TXT = {
  title: { en: 'Choose your language', ru: 'Выберите язык', es: 'Elige tu idioma', zh: '选择语言', fr: 'Choisissez votre langue', de: 'Wähle deine Sprache', ja: '言語を選択', ko: '언어를 선택하세요', id: 'Pilih bahasa' },
  sub: {
    en: 'You can change it in the settings at any time.', ru: 'Его можно сменить в настройках в любой момент.',
    es: 'Puedes cambiarlo en los ajustes en cualquier momento.', zh: '你可以随时在设置中更改。',
    fr: 'Vous pouvez la changer à tout moment dans les paramètres.', de: 'Du kannst sie jederzeit in den Einstellungen ändern.',
    ja: '設定からいつでも変更できます。', ko: '설정에서 언제든지 변경할 수 있습니다.', id: 'Bisa diganti kapan saja di pengaturan.',
  },
  go: { en: 'Let’s go', ru: 'Поехали', es: '¡Vamos!', zh: '开始', fr: 'C’est parti', de: 'Los geht’s', ja: 'はじめる', ko: '시작하기', id: 'Ayo mulai' },
};

const EXPLICIT_KEY = 'ton_city_lang_explicit';
const API = `${process.env.REACT_APP_BACKEND_URL || ''}/api`;

function explicitHere() {
  try { return localStorage.getItem(EXPLICIT_KEY) === '1'; } catch (_) { return false; }
}

export default function FirstLanguagePicker({ user, onDone }) {
  const { language, setLang } = useLanguage();
  const [sel, setSel] = useState(language || 'en');
  const [closed, setClosed] = useState(false);

  // chosen on this device before the server knew about it → tell the server, don't ask again
  useEffect(() => {
    if (!user?.id || user.language_chosen || !explicitHere()) return;
    const token = localStorage.getItem('token');
    if (!token) return;
    fetch(`${API}/auth/update-language`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ language: language || 'en', chosen: true }),
    }).catch(() => {});
  }, [user?.id, user?.language_chosen]); // eslint-disable-line react-hooks/exhaustive-deps

  const open = !!user?.id && !user.language_chosen && !explicitHere() && !closed;
  useEffect(() => { if (open) setSel(language || 'en'); }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const tr = useMemo(() => (k) => TXT[k][sel] || TXT[k].en, [sel]);
  if (!open) return null;

  const confirm = () => {
    setLang(sel);                                   // saves locally + PUT update-language {chosen: true}
    setClosed(true);
    if (onDone) onDone(sel);
  };

  return (
    <div className="fixed inset-0 z-[200] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4" data-testid="first-language-picker">
      <div className="relative w-full max-w-md rounded-[28px] border border-cyber-cyan/30 bg-gradient-to-b from-[#0f1a2e] to-[#080d18] p-5 sm:p-6 shadow-2xl shadow-cyber-cyan/10 max-h-[92vh] overflow-y-auto">
        <div className="pointer-events-none absolute inset-0 rounded-[28px] bg-[radial-gradient(ellipse_at_top,rgba(0,240,255,0.14),transparent_60%)]" />
        <div className="relative flex flex-col items-center text-center">
          <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-cyber-cyan to-blue-600 flex items-center justify-center shadow-lg shadow-cyber-cyan/30 mb-4">
            <Languages className="w-10 h-10 text-[#05060A]" />
          </div>
          <h2 className="font-unbounded text-2xl font-bold text-white leading-tight">{tr('title')}</h2>
          <p className="text-sm text-text-muted mt-2 mb-5">{tr('sub')}</p>
        </div>

        <div className="relative grid grid-cols-2 gap-2.5" role="radiogroup">
          {LANG_OPTIONS.map((l) => {
            const active = sel === l.code;
            return (
              <button
                key={l.code} type="button" role="radio" aria-checked={active} onClick={() => setSel(l.code)}
                data-testid={`first-lang-${l.code}`}
                className={`flex items-center gap-2.5 rounded-2xl border px-3 py-3 text-left transition-all active:scale-[0.98] ${
                  active ? 'bg-cyber-cyan/15 border-cyber-cyan shadow-md shadow-cyber-cyan/20' : 'bg-white/[0.04] border-white/10 hover:border-white/25'}`}
              >
                <span className="text-2xl leading-none shrink-0">{l.flag}</span>
                <span className={`flex-1 min-w-0 truncate font-semibold text-sm ${active ? 'text-white' : 'text-white/85'}`}>{l.name}</span>
                {active && <span className="w-5 h-5 rounded-full bg-cyber-cyan flex items-center justify-center shrink-0"><Check className="w-3.5 h-3.5 text-[#05060A]" /></span>}
              </button>
            );
          })}
        </div>

        <button
          type="button" onClick={confirm} data-testid="first-lang-go"
          className="relative w-full mt-5 py-3.5 rounded-2xl bg-gradient-to-r from-cyber-cyan to-emerald-400 text-[#05060A] font-bold text-lg flex items-center justify-center gap-2 shadow-lg shadow-cyber-cyan/30 active:scale-[0.99] transition-all"
        >
          {tr('go')} <Zap className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
}
