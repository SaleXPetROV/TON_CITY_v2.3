# Willy GRAM на сервере — установка без Docker

Сервер: Ubuntu 22.04 / 24.04, проект в `/opt/gram-city` (если путь другой — подставьте свой).
Всё ставится рядом с работающей игрой и не мешает ей: поиск по смыслу — отдельная служба `willy`
(1 ядро, до 1 ГБ памяти), переводы — LibreTranslate. Внешних ИИ-сервисов нет.

Что из чего состоит:

| Часть | Где работает | Нужна ли |
|---|---|---|
| Willy GRAM (правила, база ответов, поиск по словам, передача человеку) | внутри backend | да, уже в коде |
| База из 3 020 ответов | MongoDB, коллекция `willy_answers` | заливается сама при старте backend |
| Поиск по смыслу (txtai + multilingual-e5-small, ONNX int8) | служба `willy`, порт 127.0.0.1:8090 | желательно; без неё работает поиск по словам |
| Переводы вопрос ↔ ответ | LibreTranslate, порт 127.0.0.1:5000 | да, для игроков не на русском |

---

## 1. Обновить код игры

```bash
cd /opt/gram-city
# распакуйте архив TON_CITY_v2.3_full.zip поверх (backend/.env и frontend/.env в архиве нет — ваши останутся)

# backend: новые пакеты (в том числе snowballstemmer для поиска по словам)
/путь/к/venv/backend/bin/pip install -r backend/requirements.txt

# frontend
cd frontend && yarn install && yarn build && cd ..
```

Перезапустите backend так, как он у вас запущен, например `sudo systemctl restart gram-backend`
или `sudo supervisorctl restart backend`.

При первом старте backend сам:
- зальёт базу ответов (3 020 ответов, ~1 с) — в логе строка `🤖 Willy GRAM: 3020 answer(s) seeded`;
- вернёт игрокам наградные ресурсы эшелона 3, исправит размеры тендеров, обновит статьи Справочника.

С этого момента Willy GRAM уже отвечает (поиском по словам).

## 2. LibreTranslate (переводы)

Проверьте, работает ли он уже:

```bash
curl -s http://127.0.0.1:5000/languages | head -c 200
```

Если ответил списком языков — в `backend/.env` должна быть строка
`LIBRETRANSLATE_URL=http://127.0.0.1:5000`, и этот шаг пропускайте.

Если нет — установка (≈ 2 ГБ памяти в работе, модели ≈ 1,5 ГБ на диске):

```bash
sudo useradd --system --home /opt/libretranslate --shell /usr/sbin/nologin libretranslate
sudo install -d -o libretranslate -g libretranslate /opt/libretranslate
sudo -u libretranslate python3 -m venv /opt/libretranslate/venv
sudo -u libretranslate /opt/libretranslate/venv/bin/pip install libretranslate
sudo install -m 644 /opt/gram-city/deploy/willy/libretranslate.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now libretranslate
# первый запуск скачивает модели 9 языков — 5–15 минут:
journalctl -u libretranslate -f
```

Добавьте в `backend/.env` строку `LIBRETRANSLATE_URL=http://127.0.0.1:5000` и перезапустите backend.

## 3. Поиск по смыслу (служба willy)

Одна команда:

```bash
sudo bash /opt/gram-city/deploy/willy/install.sh /opt/gram-city/backend/.env
```

Что делает скрипт:
1. ставит python3-venv;
2. создаёт пользователя `willy`, папки `/opt/willy` и `/var/lib/willy`;
3. ставит окружение службы (без torch, ≈ 250 МБ);
4. один раз скачивает модель multilingual-e5-small и сохраняет её в ONNX int8
   (`/opt/willy/models`, ≈ 120 МБ); временные пакеты для этого (torch) потом удаляет;
5. ставит и запускает службу `willy` (systemd, 1 ядро, 1 ГБ памяти, автозапуск после перезагрузки и сбоя);
6. дописывает в `backend/.env` строку `WILLY_URL=http://127.0.0.1:8090`.

Перезапустите backend: при старте он сам соберёт индекс в службе (3 020 ответов, ~25 000 формулировок,
несколько минут на одном ядре в фоне — игра в это время работает, Willy отвечает поиском по словам).

Повторный запуск `install.sh` безопасен: обновит код службы, модель второй раз не качает.

## 4. Проверка

```bash
systemctl status willy --no-pager
curl -s http://127.0.0.1:8090/health      # {"ok":true,"phrasings":…,"answers":3020}
```

В админке: **Поддержка → Willy GRAM**:
- **Статистика** → внизу «Поиск по смыслу: работает · N формулировок»;
- **Проверить вопрос** → напишите «куда пропали ресурсы со склада», потом то же по-английски —
  должно быть «Ответ» и тема «Почему пропал товар».

Пороги для поиска по смыслу (Правила → «Поиск по смыслу») стоят 0,87 / 0,83. Проверьте 10–20 вопросов
во вкладке «Проверить вопрос»: если хорошие ответы попадают в «О чём вопрос?», снизьте пороги на 0,01–0,02.

## 5. Обслуживание

- Правки в админке подхватываются сразу; ночью в 04:00 МСК, если были правки, индекс пересобирается полностью.
- Кнопка «Пересобрать индекс» (Статистика) — то же вручную.
- Логи: `journalctl -u willy -f`.
- Выключить Willy GRAM целиком: Правила → снять «Willy GRAM отвечает первым» (чаты сразу идут агентам, как раньше).
- Выключить только поиск по смыслу: убрать `WILLY_URL` из `backend/.env`, перезапустить backend,
  `sudo systemctl disable --now willy`.

## Память сервера (8 ГБ)

| Что | Сколько |
|---|---|
| MongoDB | ~2 ГБ |
| backend + бот + фоновые задачи | ~1 ГБ |
| LibreTranslate (9 языков, 2 потока) | ~1,5–2 ГБ |
| служба willy | ~0,5 ГБ (предел 1 ГБ) |
| запас | ~2,5 ГБ |
