# ADHD Thought Capture

Sistema personale per catturare pensieri destrutturati via Telegram, classificarli automaticamente con Claude AI, e presentarli in una dashboard consumabile.

**Principio guida**: "Meglio sporco che perso, ma meglio consumato che accumulato."

## Features

- **Cattura frictionless**: Manda un messaggio Telegram, fatto
- **Classificazione AI**: Claude capisce cosa intendi (film, libro, concetto, musica, todo...)
- **Arricchimento automatico**: Link rilevanti, stima tempo, suggerimenti
- **Daily picks**: Suggerimenti personalizzati ogni mattina
- **Auto-archive**: I pensieri vecchi vengono archiviati, non persi
- **Dashboard**: Interfaccia pulita per consumare e gestire

## Quick Start

### 1. Setup

```bash
# Clone repository
git clone <repository-url>
cd adhd-thought-capture

# Copia e configura environment
cp .env.example .env
```

### 2. Configura `.env`

```bash
# Token Telegram (ottienilo da @BotFather)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# API Key Claude (da console.anthropic.com)
CLAUDE_API_KEY=your_claude_api_key

# Optional
DAILY_PICKS_TIME=08:00
DECAY_DAYS=30
DASHBOARD_URL=https://tuo-dominio.it
```

### 3. Run con Docker

```bash
# Build e avvia
docker-compose up -d

# Verifica logs
docker-compose logs -f
```

### 4. Setup Telegram Bot

1. Trova il tuo bot su Telegram (quello creato con @BotFather)
2. Invia `/start`
3. Il bot salverà automaticamente il tuo chat_id

## Usage

### Telegram Commands

- `/start` - Inizia e registra il tuo account
- `/background` - Imposta interessi e preferenze (migliora la classificazione)
- `/stats` - Statistiche personali
- `/today` - Picks del giorno
- `/help` - Aiuto

### Inviare pensieri

Basta mandare un messaggio:
- `Blade Runner 2049` → classificato come film, link IMDb
- `Thinking Fast and Slow` → libro, link Amazon/Goodreads
- `filosofia stoica` → concetto, link Wikipedia/articoli
- `comprare latte` → todo

### Dashboard

Accedi a `http://localhost:8000` (o il tuo dominio) per:
- Vedere tutti i pensieri catturati
- Marcare come "consumato" o "archiviato"
- Filtrare per tipo/status
- Vedere statistiche e streak

## Development

### Backend

```bash
cd backend
pip install -r ../requirements.txt
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Dev con Docker

```bash
docker-compose -f docker-compose.dev.yml up
```

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
│  │  - Classify             │   │
│  │  - Enrich (web search)  │   │
│  │  - Generate picks       │   │
│  └───────────┬─────────────┘   │
│              ▼                  │
│  ┌─────────────────────────┐   │
│  │    SQLite Database      │   │
│  └─────────────────────────┘   │
│                                 │
│  ┌─────────────────────────┐   │
│  │   Scheduler (APScheduler)│  │
│  │   - Daily picks         │   │
│  │   - Auto-archive        │   │
│  └─────────────────────────┘   │
└──────────────┼─────────────────┘
               │ HTTP
               ▼
      ┌─────────────────┐
      │ Svelte Frontend │
      │   Dashboard     │
      └─────────────────┘
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/items` | GET | Lista items (filtri: status, item_type) |
| `/api/items/{id}` | GET | Singolo item |
| `/api/items/{id}` | PATCH | Aggiorna status/feedback |
| `/api/stats` | GET | Statistiche utente |
| `/api/daily-picks` | GET | Picks del giorno |
| `/api/config/{key}` | GET/POST | Configurazione |

## Tech Stack

- **Backend**: FastAPI, Python 3.11, SQLite
- **AI**: Anthropic Claude API (Sonnet) con web search
- **Messaging**: python-telegram-bot (polling)
- **Scheduling**: APScheduler
- **Frontend**: Svelte, SvelteKit, TailwindCSS
- **Deploy**: Docker, Docker Compose

## Configuration

### user_background

Imposta con `/background` su Telegram. Esempio:

> "Amo cinema d'autore, sci-fi cerebrale tipo Blade Runner, musica elettronica ambient, filosofia continentale. Odio action stupidi e pop commerciale."

Questo migliora significativamente la classificazione e i suggerimenti.

### Daily Picks

- Generati automaticamente all'ora configurata (`DAILY_PICKS_TIME`)
- 3-5 items bilanciati per tipo e tempo
- Priorità a items vecchi per evitare accumulo

### Auto-Archive

Items pending da più di `DECAY_DAYS` (default 30) vengono automaticamente archiviati. Non persi, solo organizzati.

## Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name adhd.tuodominio.it;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# SSL con Certbot
sudo certbot --nginx -d adhd.tuodominio.it
```

## Costs

Claude API con web search: ~$0.02/pensiero. Per 20 pensieri/giorno ≈ $12/mese.

## License

MIT
