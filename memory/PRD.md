# PRD — TON CITY v2.3 (GRAM CITY)

## Исходная задача
Склонировать https://github.com/SaleXPetROV/TON_CITY_v2.3.git, запустить, внести только запрошенные правки:
1. Аватар владельца в панели информации о бизнесе на карте показывался как «битая» картинка.
2. В Кошельке Telegram при подключении не отображалась иконка проекта (в OKX — отображалась). Использовать `favicon_512.png`, домен prod — https://gramcity.app.
3. (доп.) Если у пользователя есть бизнес Ур.0 — он не должен иметь возможность купить другой бизнес через карту.
Ничего лишнего не трогать.

## Архитектура
React (CRA/craco) + FastAPI (`backend/server.py`, `backend/routes/*`) + MongoDB. TON Connect через `@tonconnect/ui-react` (LazyTonProvider).

## Что сделано (2026-06)
- **Аватар**: `TonIslandPage.jsx` — `<img src={avatar}>` заменён на `SmartAvatar` (аватар хранится объектом `{type:'url'|'initials'}` → был `[object Object]`). В `SmartAvatar.jsx` добавлен `onError` → фолбэк на инициалы.
- **TON Connect**: `server.py` — манифест и иконка принимают `GET` и `HEAD` (раньше HEAD → 405, из-за чего Telegram Wallet считал иконку битой). Новый манифест `/api/tonconnect-manifest-v6.json`, иконка `/api/tonconnect-icon-v3.png` (`backend/static/tonconnect-icon-gramcity.png` — 512×512 RGB из `favicon_512.png`), CORS `*`. Фронт: `App.js`, `tonconnect-lazy.js` → v6. Статические `public/tonconnect-manifest*.json` → новая iconUrl.
- **Ур.0 гейт**: `TonIslandPage.jsx` — при наличии бизнеса level 0 / `is_zero_business` кнопка «Купить» заменяется на disabled `zero-locked-buy` с текстом подсказки; `handleBuyClick` показывает toast. Бэкенд-гейт (423 `zero_locked`) уже существовал.
- Тесты: `test_reports/iteration_1.json` — backend 11/11, frontend 3/3.

## Заметки для prod
После деплоя Telegram Wallet может держать старый манифест в кэше — новый URL v6 его сбрасывает. Проверить: `curl -I https://gramcity.app/api/tonconnect-icon-v3.png` → 200.

## Backlog
- Нет открытых задач от пользователя.
