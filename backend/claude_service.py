"""
Claude AI service for classification and enrichment.
"""

import json
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import anthropic

from config import CLAUDE_API_KEY, CLAUDE_MODEL, DASHBOARD_URL
from database import (
    get_config, get_recent_items, save_item, get_pending_items_for_picks,
    get_stats_last_7_days, save_daily_picks, get_item_by_id
)
from models import ItemClassification, DailyPicksResult

logger = logging.getLogger(__name__)

# Initialize Claude client
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None

# Prompt templates
CLASSIFY_PROMPT = """
Sei un assistente per una persona con ADHD che cattura pensieri velocemente.

USER BACKGROUND:
{user_background}

RECENT CONTEXT (ultimi 5 pensieri):
{recent_items}

INPUT UTENTE:
"{verbatim_input}"

TASK:
1. Classifica il tipo di pensiero
2. Usa web_search per arricchire con info rilevanti (titoli film, autori libri, link Wikipedia, etc.)
3. Trova link diretti dove consumare/approfondire
4. Stima tempo necessario
5. Assegna priorità

OUTPUT (JSON puro, senza markdown):
{{
  "type": "film|book|concept|music|art|todo|other",
  "title": "titolo estratto/inferito",
  "description": "cosa significa questo pensiero (1-2 frasi)",
  "links": [
    {{"url": "...", "type": "imdb|spotify|wikipedia|article|..."}}
  ],
  "estimated_minutes": 30,
  "priority": 3,
  "tags": ["tag1", "tag2"],
  "consumption_suggestion": "come/quando consumarlo"
}}

REGOLE:
- Sii generoso nell'interpretazione (preferisci classificare che "other")
- Se ambiguo, usa il background utente per disambiguare
- Trova almeno 1-2 link utili (IMDb, Spotify, Wikipedia, articoli, etc)
- Stima tempo realisticamente (film=120min, concept=15-30min, libro=varie ore)
- Priorità basata su: urgenza inferita, complessità, interesse utente
- Tag: max 3-4, semantici (es: "sci-fi", "philosophy", "ambient-music")
- RISPONDI SOLO CON IL JSON, niente altro testo prima o dopo
"""

DAILY_PICKS_PROMPT = """
Sei un assistente che aiuta una persona ADHD a consumare contenuti in modo sostenibile.

USER BACKGROUND:
{user_background}

PENDING ITEMS:
{pending_items}

CONTEXT:
- Oggi è: {day_of_week}
- Ora: {current_time}
- Ultimi 7 giorni: consumati {recent_consumed}, catturati {recent_captured}

TASK:
Seleziona 3-5 item dalla lista pending che siano:
1. Appropriati per il giorno/ora (weekend=film lunghi, feriale=concept brevi)
2. Bilanciati per tipo (non tutti film o tutti concept)
3. Sostenibili come tempo totale (max 2-3 ore cumulative)
4. Interessanti basandosi sul background utente

OUTPUT (JSON puro, senza markdown):
{{
  "picks": [
    {{
      "item_id": 123,
      "reason": "perché lo suggerisci oggi"
    }}
  ],
  "total_estimated_time": 120,
  "message": "messaggio motivazionale per l'utente (1 frase)"
}}

REGOLE:
- Priorità a item vecchi (>7gg) per evitare accumulo
- Varia i tipi (non tutti dello stesso tipo)
- Considera il mood del giorno (venerdì sera ≠ lunedì mattina)
- Messaggio positivo, mai giudicante
- RISPONDI SOLO CON IL JSON, niente altro testo prima o dopo
"""


def extract_json(text: str) -> Optional[Dict]:
    """Extract JSON from text, handling markdown code blocks."""
    # Try direct parse first
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    json_match = re.search(r'```(?:json)?\n?(.*?)\n?```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding JSON object pattern
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


async def classify_and_enrich(verbatim: str, msg_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Classifica e arricchisce un pensiero usando Claude con tool use.
    """
    if not client:
        logger.error("Claude client not initialized - missing API key")
        return create_fallback_result(verbatim, msg_id)

    try:
        # Get context
        user_background = await get_config('user_background', '')
        recent_items = await get_recent_items(limit=5)

        # Format prompt
        prompt = CLASSIFY_PROMPT.format(
            user_background=user_background or "Nessun background impostato",
            recent_items=json.dumps(recent_items, indent=2, ensure_ascii=False) if recent_items else "Nessun item recente",
            verbatim_input=verbatim
        )

        # Call Claude with web search tool
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            tools=[
                {"type": "web_search_20250305", "name": "web_search"}
            ],
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Extract result from response
        result = None
        for block in response.content:
            if block.type == "text":
                result = extract_json(block.text)
                if result:
                    break

        if not result:
            logger.warning(f"Failed to parse Claude response for: {verbatim[:50]}")
            return await create_fallback_result(verbatim, msg_id)

        # Validate and normalize result
        result = normalize_classification(result)

        # Save to database
        item_id = await save_item(
            telegram_message_id=msg_id,
            verbatim_input=verbatim,
            item_type=result['type'],
            title=result['title'],
            description=result['description'],
            enrichment={
                'links': result['links'],
                'consumption_suggestion': result['consumption_suggestion']
            },
            priority=result['priority'],
            estimated_minutes=result['estimated_minutes'],
            tags=result['tags']
        )

        result['id'] = item_id
        return result

    except anthropic.APIError as e:
        logger.error(f"Claude API error: {e}")
        return await create_fallback_result(verbatim, msg_id)
    except Exception as e:
        logger.error(f"Error classifying thought: {e}")
        return await create_fallback_result(verbatim, msg_id)


def normalize_classification(result: Dict) -> Dict:
    """Normalize and validate classification result."""
    valid_types = ['film', 'book', 'concept', 'music', 'art', 'todo', 'other']

    return {
        'type': result.get('type', 'other') if result.get('type') in valid_types else 'other',
        'title': result.get('title', '')[:200],
        'description': result.get('description', ''),
        'links': result.get('links', [])[:10],  # Limit links
        'estimated_minutes': min(max(result.get('estimated_minutes', 15), 1), 600),  # 1-600 min
        'priority': min(max(result.get('priority', 3), 1), 5),  # 1-5
        'tags': result.get('tags', [])[:5],  # Limit tags
        'consumption_suggestion': result.get('consumption_suggestion', '')
    }


async def create_fallback_result(verbatim: str, msg_id: Optional[int] = None) -> Dict[str, Any]:
    """Create fallback result when classification fails."""
    result = {
        'type': 'other',
        'title': verbatim[:50] + ('...' if len(verbatim) > 50 else ''),
        'description': 'Classificazione fallita, richiede review manuale',
        'links': [],
        'estimated_minutes': 15,
        'priority': 3,
        'tags': ['uncategorized'],
        'consumption_suggestion': ''
    }

    # Still save to database
    item_id = await save_item(
        telegram_message_id=msg_id,
        verbatim_input=verbatim,
        item_type=result['type'],
        title=result['title'],
        description=result['description'],
        enrichment={
            'links': [],
            'consumption_suggestion': ''
        },
        priority=result['priority'],
        estimated_minutes=result['estimated_minutes'],
        tags=result['tags']
    )

    result['id'] = item_id
    return result


async def generate_daily_picks() -> Optional[Dict[str, Any]]:
    """
    Genera suggerimenti giornalieri.
    """
    if not client:
        logger.error("Claude client not initialized - missing API key")
        return None

    try:
        # Get context
        user_background = await get_config('user_background', '')
        pending_items = await get_pending_items_for_picks(limit=50)

        if not pending_items:
            logger.info("No pending items for daily picks")
            return None

        recent_stats = await get_stats_last_7_days()

        # Format prompt
        prompt = DAILY_PICKS_PROMPT.format(
            user_background=user_background or "Nessun background impostato",
            pending_items=json.dumps(pending_items, indent=2, ensure_ascii=False),
            day_of_week=datetime.now().strftime('%A'),
            current_time=datetime.now().strftime('%H:%M'),
            recent_consumed=recent_stats['consumed'],
            recent_captured=recent_stats['captured']
        )

        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        result = None
        for block in response.content:
            if block.type == "text":
                result = extract_json(block.text)
                if result:
                    break

        if not result or 'picks' not in result:
            logger.warning("Failed to parse daily picks response")
            return None

        # Validate picks exist in database
        valid_picks = []
        total_time = 0

        for pick in result.get('picks', []):
            item = await get_item_by_id(pick.get('item_id'))
            if item and item['status'] == 'pending':
                valid_picks.append({
                    'item_id': pick['item_id'],
                    'reason': pick.get('reason', ''),
                    'item': item
                })
                total_time += item.get('estimated_minutes', 0)

        if not valid_picks:
            logger.warning("No valid picks generated")
            return None

        # Save picks
        today = datetime.now().strftime('%Y-%m-%d')
        await save_daily_picks(
            date=today,
            picks=[{'item_id': p['item_id'], 'reason': p['reason']} for p in valid_picks],
            total_time=total_time,
            message=result.get('message', '')
        )

        return {
            'date': today,
            'picks': valid_picks,
            'total_estimated_time': total_time,
            'message': result.get('message', 'Buona giornata!')
        }

    except anthropic.APIError as e:
        logger.error(f"Claude API error generating picks: {e}")
        return None
    except Exception as e:
        logger.error(f"Error generating daily picks: {e}")
        return None


async def get_daily_picks_with_items(date: str) -> Optional[Dict[str, Any]]:
    """Get daily picks with full item details."""
    from database import get_daily_picks_for_date

    picks_data = await get_daily_picks_for_date(date)
    if not picks_data:
        return None

    # Enrich picks with item data
    enriched_picks = []
    for pick in picks_data.get('picks', []):
        item = await get_item_by_id(pick.get('item_id'))
        if item:
            enriched_picks.append({
                **pick,
                'item': item
            })

    return {
        'date': date,
        'picks': enriched_picks,
        'total_estimated_time': picks_data.get('total_estimated_time', 0),
        'message': picks_data.get('message', '')
    }
