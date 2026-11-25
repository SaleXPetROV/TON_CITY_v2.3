#!/usr/bin/env bash
# Willy GRAM — установка поиска по смыслу на сервер (без Docker), Ubuntu 22.04/24.04.
#   sudo bash deploy/willy/install.sh [путь к backend/.env]
# Повторный запуск безопасен: обновит код сервиса и перезапустит его, модель второй раз не качает.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
root="$(cd "$here/../.." && pwd)"
envfile="${1:-$root/backend/.env}"
[ "$(id -u)" = 0 ] || { echo "запустите через sudo"; exit 1; }

echo "1/6 пакеты"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip curl >/dev/null

echo "2/6 пользователь и папки"
id willy >/dev/null 2>&1 || useradd --system --home /opt/willy --shell /usr/sbin/nologin willy
install -d -o willy -g willy /opt/willy /opt/willy/app /opt/willy/models /var/lib/willy
install -m 644 -o willy -g willy "$root/willy_service/app.py" /opt/willy/app/app.py

echo "3/6 окружение сервиса (без torch, ~250 МБ)"
[ -x /opt/willy/venv/bin/python ] || python3 -m venv /opt/willy/venv
/opt/willy/venv/bin/pip install -q --upgrade pip
/opt/willy/venv/bin/pip install -q -r "$root/willy_service/requirements.txt"

echo "4/6 модель multilingual-e5-small → ONNX int8 (один раз, ~5 мин)"
if [ ! -f /opt/willy/models/e5.onnx ]; then
  python3 -m venv /opt/willy/export-venv
  /opt/willy/export-venv/bin/pip install -q --upgrade pip
  /opt/willy/export-venv/bin/pip install -q -r "$root/willy_service/requirements-export.txt"
  /opt/willy/export-venv/bin/python "$root/willy_service/export_model.py" /opt/willy/models
  rm -rf /opt/willy/export-venv          # torch больше не нужен: освобождаем ~1,5 ГБ
  chown -R willy:willy /opt/willy/models
else
  echo "   модель уже есть — пропускаю"
fi

echo "5/6 служба systemd"
install -m 644 "$here/willy.service" /etc/systemd/system/willy.service
systemctl daemon-reload
systemctl enable --now willy.service
systemctl restart willy.service
for i in $(seq 1 60); do curl -sf http://127.0.0.1:8090/health >/dev/null && break; sleep 2; done
curl -s http://127.0.0.1:8090/health && echo

echo "6/6 адрес сервиса для backend"
if [ -f "$envfile" ]; then
  grep -q '^WILLY_URL=' "$envfile" || echo 'WILLY_URL=http://127.0.0.1:8090' >> "$envfile"
  echo "   $envfile: $(grep '^WILLY_URL=' "$envfile")"
else
  echo "   ВНИМАНИЕ: $envfile не найден — добавьте в .env backend строку WILLY_URL=http://127.0.0.1:8090"
fi
echo
echo "Готово. Перезапустите backend — при старте он сам соберёт индекс ответов в сервисе."
echo "Проверка: Админка → Поддержка → Willy GRAM → Статистика → «Поиск по смыслу: работает»."
