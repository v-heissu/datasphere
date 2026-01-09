# ADHD Thought Capture

Sistema personale per catturare pensieri destrutturati via Telegram, classificarli automaticamente con Claude AI, e presentarli in una dashboard consumabile.

**Principio guida**: "Meglio sporco che perso, ma meglio consumato che accumulato."

## Features

- **Cattura frictionless**: Manda un messaggio Telegram, fatto
- **Classificazione AI**: Claude Sonnet 4.5 con web_search capisce cosa intendi
- **Arricchimento automatico**: Link rilevanti (IMDb, Spotify, Wikipedia), stima tempo, suggerimenti
- **Daily picks**: Suggerimenti personalizzati ogni mattina (Claude Haiku)
- **Weekly digest**: Email settimanale con recap e statistiche
- **3 Modalità vista**: Cards, Tabella, Accordion
- **Auto-archive**: I pensieri vecchi vengono archiviati, non persi
- **Dark mode**: Interfaccia dark responsive e mobile-friendly

## Quick Start

### 1. Prerequisiti

- Docker e Docker Compose
- Token Telegram Bot (da [@BotFather](https://t.me/BotFather))
- API Key Anthropic (da [console.anthropic.com](https://console.anthropic.com))

### 2. Setup

```bash
# Clone repository
git clone <repository-url>
cd datasphere

# Copia e configura environment
cp .env.example .env
nano .env
```

### 3. Configura `.env`

**Obbligatorie:**
```bash
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
CLAUDE_API_KEY=your_claude_api_key
DASHBOARD_URL=https://tuo-dominio.it
```

**Opzionali:**
```bash
DAILY_PICKS_TIME=08:00
DECAY_DAYS=30
NOTIFICATION_ENABLED=true
```

**Email (opzionale):**
```bash
EMAIL_ENABLED=true
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=tuaemail@gmail.com
EMAIL_PASSWORD=app_password_gmail  # App Password, non password normale!
EMAIL_FROM=tuaemail@gmail.com
EMAIL_TO=tuaemail@gmail.com
WEEKLY_DIGEST_TIME=08:00
WEEKLY_DIGEST_DAY=sat
```

> **Gmail**: Genera una App Password su https://myaccount.google.com/apppasswords

### 4. Run con Docker

```bash
# Build e avvia
docker-compose up -d --build

# Verifica logs
docker-compose logs -f
```

Dashboard disponibile su `http://localhost:8000`

## Usage

### Telegram Commands

- `/start` - Inizia e registra il tuo account
- `/background` - Imposta interessi e preferenze
- `/stats` - Statistiche personali
- `/today` - Picks del giorno
- `/help` - Aiuto

### Inviare pensieri

Basta mandare un messaggio:
- `Blade Runner 2049` → Film, link IMDb
- `Thinking Fast and Slow` → Libro, link Amazon
- `filosofia stoica` → Concetto, link Wikipedia
- `ascoltare boards of canada` → Musica, link Spotify
- `comprare latte` → Todo

### Dashboard

- **Vista Cards/Table/Accordion** - Toggle in alto a destra
- **Filtri** - Status (Coda, Fatti, Archivio) e tipo
- **Daily Picks** - Suggerimenti AI bilanciati per tipo/tempo
- **Settings** - Profilo utente, system prompt, test email
- **Copia** - Bottone su ogni card (hover)
- **Auto-refresh** - Aggiornamento automatico ogni 30s

## Deploy su Railway

### 1. Setup

1. [railway.app](https://railway.app) → New Project → GitHub repo
2. Configura le variabili in Settings → Variables

### 2. Persistenza Database (IMPORTANTE)

Il database deve persistere tra i deploy:

**Opzione A - Railway Volume:**
1. Settings → Volumes
2. Add volume montato su `/data`
3. Database salvato in `/data/adhd.db`

**Opzione B - Database esterno:**
Usa PostgreSQL (Railway, Supabase, etc.) modificando `database.py`

### 3. Custom Domain

1. Settings → Domains
2. Add custom domain
3. Configura DNS

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/items` | GET | Lista items (filtri: status, item_type, limit) |
| `/api/items/{id}` | GET | Singolo item |
| `/api/items/{id}` | PATCH | Aggiorna status/feedback |
| `/api/items/{id}` | DELETE | Elimina item |
| `/api/stats` | GET | Statistiche utente |
| `/api/daily-picks` | GET | Picks del giorno |
| `/api/daily-picks/regenerate` | POST | Rigenera picks |
| `/api/config` | GET | Tutte le configurazioni |
| `/api/config/{key}` | GET/POST | Singola configurazione |
| `/api/email/test` | POST | Invia email di test |

## Architecture

```
┌─────────────┐
│  Telegram   │
│     Bot     │
└──────┬──────┘
       │ (polling)
       ▼
┌─────────────────────────────────┐
│      FastAPI Backend            │
│  ┌─────────────────────────┐   │
│  │  Telegram Handler       │   │
│  └───────────┬─────────────┘   │
│              ▼                  │
│  ┌─────────────────────────┐   │
│  │  Claude AI Service      │   │
│  │  - Sonnet + web_search  │   │
│  │  - Haiku for picks      │   │
│  └───────────┬─────────────┘   │
│              ▼                  │
│  ┌─────────────────────────┐   │
│  │    SQLite Database      │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │   Scheduler (APScheduler)│  │
│  │   - Daily picks (8:00)  │   │
│  │   - Auto-archive (2:00) │   │
│  │   - Weekly email (Sat)  │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │    Email Service        │   │
│  │    (Gmail SMTP)         │   │
│  └─────────────────────────┘   │
└──────────────┼─────────────────┘
               │ HTTP
               ▼
      ┌─────────────────┐
      │ Svelte Frontend │
      │   Dashboard     │
      └─────────────────┘
```

## Project Structure

```
datasphere/
├── backend/
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   ├── database.py       # SQLite operations
│   ├── claude_service.py # Claude AI (Sonnet + Haiku)
│   ├── telegram_bot.py   # Telegram bot
│   ├── email_service.py  # Weekly digest email
│   ├── scheduler.py      # APScheduler jobs
│   └── models.py         # Pydantic models
├── frontend/
│   ├── src/
│   │   ├── routes/       # SvelteKit pages
│   │   └── lib/
│   │       ├── components/
│   │       │   ├── ItemCard.svelte
│   │       │   ├── ItemTable.svelte
│   │       │   ├── ItemAccordion.svelte
│   │       │   ├── DailyPicks.svelte
│   │       │   ├── StatsWidget.svelte
│   │       │   └── SettingsModal.svelte
│   │       ├── stores.js
│   │       └── api.js
│   └── static/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Tech Stack

- **Backend**: FastAPI, Python 3.11, SQLite (aiosqlite)
- **AI**: Claude Sonnet 4.5 (classify + web_search), Claude Haiku (picks)
- **Messaging**: python-telegram-bot (polling)
- **Email**: smtplib (Gmail SMTP)
- **Scheduling**: APScheduler
- **Frontend**: Svelte, SvelteKit, TailwindCSS
- **Deploy**: Docker, Docker Compose

## Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Troubleshooting

### Bot non risponde
- Verifica `TELEGRAM_BOT_TOKEN`
- Check logs: `docker-compose logs -f`

### Classificazione fallisce
- Verifica `CLAUDE_API_KEY` valido
- Check quota API Anthropic

### Email non arriva
- `EMAIL_ENABLED=true`?
- Per Gmail usa App Password
- Test: `POST /api/email/test`

### Database perso dopo deploy
- Configura volume persistente su `/data`
- NON usare `docker-compose down -v`

## Costs

Claude API con web_search: ~$0.02-0.05/pensiero
Per 20 pensieri/giorno ≈ $12-30/mese

## License

MIT
