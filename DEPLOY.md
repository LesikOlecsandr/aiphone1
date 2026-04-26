# Deploy

## 1. Что загрузить на GitHub

Загружайте весь проект, кроме файлов из `.gitignore`.

Важно:
- `.env` не загружать
- `instance/runtime_config.json` не загружать
- `uploads/` не загружать
- локальную базу `repair_estimator.db` не загружать

## 2. Быстрый запуск на VPS через Docker

На сервере:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
cp .env.example .env
```

Заполните `.env`:

```env
GEMINI_API_KEY=your_real_key
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///./repair_estimator.db
DEFAULT_MARKUP_FACTOR=1.8
```

Потом запустите:

```bash
docker compose up -d --build
```

Сервис откроется на:

```text
http://SERVER_IP:8000
```

## 3. Как подключить виджет на сайт

Вставьте на сайт:

```html
<script
  src="https://YOUR_DOMAIN/static/widget.js"
  data-api-base-url="https://YOUR_DOMAIN"
></script>
```

## 4. Что сделать после первого запуска

1. Откройте `https://YOUR_DOMAIN/control-center`
2. Задайте пароль администратора
3. Введите Gemini API key
4. Заполните базовые данные сервиса
5. Добавьте популярные ремонты в раздел `Naprawy`

## 5. Рекомендованный продакшен

Лучше запускать проект за reverse proxy:

- Nginx Proxy Manager
- Coolify
- Dokploy
- Nginx + Let's Encrypt

Если VPS уже обслуживает сайт, проксируйте домен на `127.0.0.1:8000`.
