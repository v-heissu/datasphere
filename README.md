# ADHD Thought Capture

Sistema personale per catturare pensieri destrutturati via Telegram, classificarli automaticamente con Claude AI, e presentarli in una dashboard consumabile.

**Principio guida**: "Meglio sporco che perso, ma meglio consumato che accumulato."

## Features

- **Cattura frictionless**: Manda un messaggio Telegram, fatto
- **Supporto foto**: Invia screenshot, copertine di libri, locandine di film - l'AI analizza le immagini
- **Classificazione AI**: Gemini 2.0 Flash (gratuito) o Claude come fallback
- **Ricerca full-text**: Cerca tra tutti i tuoi pensieri con autocomplete intelligente
- **Arricchimento automatico**: Link rilevanti (IMDb, Spotify, Wikipedia, Amazon, Bandcamp), stima tempo
- **Daily picks**: Suggerimenti personalizzati ogni mattina
- **Weekly digest**: Email settimanale con recap e statistiche
- **3 Modalità vista**: Cards, Tabella, Accordion
- **Auto-archive**: I pensieri vecchi vengono archiviati dopo 30 giorni (configurabile)
- **Dark mode**: Interfaccia dark responsive e mobile-friendly

## Quick Start

### 1. Prerequisiti

- Docker e Docker Compose
- Token Telegram Bot (da [@BotFather](https://t.me/BotFather))
- API Key Gemini (gratuita, da [aistudio.google.com](https://aistudio.google.com/apikey)) **oppure**
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
DASHBOARD_URL=https://tuo-dominio.it

# Scegli UNO dei due provider AI:
GEMINI_API_KEY=your_gemini_api_key    # Gratuito! 1500 req/giorno
# oppure
CLAUDE_API_KEY=your_claude_api_key    # ~$0.02-0.05/pensiero
```

> **Raccomandato**: Usa Gemini, è gratuito e funziona benissimo. Claude viene usato come fallback se configurato.

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

**Testo** - Basta mandare un messaggio:
- `Blade Runner 2049` → Film, link IMDb
- `Thinking Fast and Slow` → Libro, link Amazon
- `filosofia stoica` → Concetto, link Wikipedia
- `ascoltare boards of canada` → Musica, link Spotify/Bandcamp
- `comprare latte` → Todo

**Foto** - Invia un'immagine e l'AI la analizza:
- Screenshot di un libro/film → Classificato automaticamente
- Copertina di un album → Musica, link Spotify
- Locandina di un evento → Evento, dettagli estratti
- Puoi aggiungere una didascalia per contesto extra

### Dashboard

- **Ricerca** - Barra di ricerca con autocomplete su tutti i campi
- **Vista Cards/Table/Accordion** - Toggle in alto a destra
- **Filtri** - Status (Coda, Fatti, Archivio) e tipo
- **Daily Picks** - Suggerimenti AI bilanciati per tipo/tempo
- **Settings** - Profilo utente, system prompt, test email, debug API
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
| `/api/search` | GET | Ricerca full-text (FTS5) |
| `/api/search/suggest` | GET | Autocomplete suggerimenti |
| `/api/search/rebuild-index` | POST | Ricostruisci indice FTS |
| `/api/stats` | GET | Statistiche utente |
| `/api/daily-picks` | GET | Picks del giorno |
| `/api/daily-picks/regenerate` | POST | Rigenera picks |
| `/api/config` | GET | Tutte le configurazioni |
| `/api/config/{key}` | GET/POST | Singola configurazione |
| `/api/email/test` | POST | Invia email di test |
| `/api/debug/test-classify` | POST | Test classificazione LLM |

> API docs interattive disponibili su `/docs` (Swagger UI)

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
│  │  (testo + foto)         │   │
│  └───────────┬─────────────┘   │
│              ▼                  │
│  ┌─────────────────────────┐   │
│  │     LLM Service         │   │
│  │  - Gemini 2.0 Flash     │   │
│  │  - Gemini 2.5 (immagini)│   │
│  │  - Claude (fallback)    │   │
│  └───────────┬─────────────┘   │
│              ▼                  │
│  ┌─────────────────────────┐   │
│  │  SQLite + FTS5 Search   │   │
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
│  │  (Gmail SMTP / Resend)  │   │
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
│   ├── main.py           # FastAPI app + API endpoints
│   ├── config.py         # Configuration
│   ├── database.py       # SQLite + FTS5 search
│   ├── llm_service.py    # Gemini/Claude AI service
│   ├── telegram_bot.py   # Telegram bot (testo + foto)
│   ├── email_service.py  # Email (Gmail SMTP / Resend)
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
│   │       │   ├── SearchBar.svelte
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

- **Backend**: FastAPI, Python 3.11, SQLite (aiosqlite), FTS5
- **AI**: Gemini 2.0/2.5 Flash (gratuito, raccomandato) oppure Claude (fallback)
- **Messaging**: python-telegram-bot (polling)
- **Email**: Gmail SMTP oppure Resend API
- **Scheduling**: APScheduler
- **Frontend**: Svelte 4, SvelteKit 2, TailwindCSS, Lucide icons
- **Deploy**: Docker, Docker Compose, Railway

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
- Verifica `GEMINI_API_KEY` o `CLAUDE_API_KEY`
- Gemini: limite 1500 req/giorno (gratuito)
- Claude: verifica quota API Anthropic

### Email non arriva
- `EMAIL_ENABLED=true`?
- Per Gmail usa App Password
- Test: `POST /api/email/test`

### Foto non classificata
- Verifica che `GEMINI_API_KEY` sia configurata (richiesta per le immagini)
- Formati supportati: JPEG, PNG, WebP
- Immagini troppo grandi vengono ridimensionate automaticamente

### Ricerca non funziona
- L'indice FTS viene creato al primo avvio
- Se corrotto: `POST /api/search/rebuild-index` oppure usa il bottone in Settings → Debug

### Database perso dopo deploy
- Configura volume persistente su `/data`
- NON usare `docker-compose down -v`

## Costs

**Gemini (raccomandato)**: Gratuito! 1500 richieste/giorno incluse.

**Claude (fallback)**: ~$0.02-0.05/pensiero → Per 20 pensieri/giorno ≈ $12-30/mese

## License

MIT
