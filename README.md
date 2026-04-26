# AI-Repair Estimator

Gotowy projekt backend + widget chatowy do wycen i zbierania leadów dla serwisu napraw.

## Co jest w środku

- FastAPI backend
- widget React/Vite jako jeden `widget.js`
- panel `Control Center`
- chat leadowy po polsku
- obsługa zdjęć i video
- wyceny z Gemini

## Szybki start lokalnie

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd frontend
npm install
npm run build
cd ..
uvicorn app.main:app --reload
```

Potem otwórz:

- `http://127.0.0.1:8000`
- `http://127.0.0.1:8000/control-center`

## Szybki deploy

Najprostszy wariant jest opisany w:

- `DEPLOY.md`

W skrócie:

```bash
docker compose up -d --build
```

## Wymagane zmienne `.env`

```env
GEMINI_API_KEY=your_real_key
GEMINI_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///./repair_estimator.db
DEFAULT_MARKUP_FACTOR=1.8
```

## Podłączenie widżetu

```html
<script
  src="https://YOUR_DOMAIN/static/widget.js"
  data-api-base-url="https://YOUR_DOMAIN"
></script>
```

## Ważne

Nie wrzucaj do repo:

- `.env`
- `instance/runtime_config.json`
- `uploads/`
- `repair_estimator.db`
