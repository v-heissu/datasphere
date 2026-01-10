"""
LLM service for classification and enrichment.
Supports both Gemini (recommended - FREE) and Claude (fallback).
"""

import json
import re
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from config import (
    LLM_PROVIDER,
    GOOGLE_API_KEY, GEMINI_MODEL_CLASSIFY, GEMINI_MODEL_PICKS,
    CLAUDE_API_KEY, CLAUDE_MODEL_CLASSIFY, CLAUDE_MODEL_PICKS,
    DASHBOARD_URL
)
from database import (
    get_config, get_recent_items, save_item, get_pending_items_for_picks,
    get_stats_last_7_days, save_daily_picks, get_item_by_id
)
from models import ItemClassification, DailyPicksResult

logger = logging.getLogger(__name__)

# Initialize clients based on provider
gemini_model_classify = None
gemini_model_picks = None
claude_client = None

if LLM_PROVIDER == "gemini" and GOOGLE_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model_classify = genai.GenerativeModel(GEMINI_MODEL_CLASSIFY)
        gemini_model_picks = genai.GenerativeModel(GEMINI_MODEL_PICKS)
        logger.info(f"Initialized Gemini models: {GEMINI_MODEL_CLASSIFY}, {GEMINI_MODEL_PICKS}")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")

if LLM_PROVIDER == "claude" and CLAUDE_API_KEY:
    try:
        import anthropic
        claude_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        logger.info(f"Initialized Claude client")
    except Exception as e:
        logger.error(f"Failed to initialize Claude: {e}")

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
2. Estrai/inferisci il titolo corretto (es: se l'utente scrive "blade runner" -> "Blade Runner 2049" o "Blade Runner")
3. Suggerisci link utili (IMDb per film, Goodreads/Amazon per libri, Wikipedia per concetti, Spotify per musica)
4. Stima tempo necessario per consumare
5. Assegna priorità basata su interesse/urgenza

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

# Gemini-specific prompt with search instruction
CLASSIFY_PROMPT_GEMINI = """
Sei un assistente per una persona con ADHD che cattura pensieri velocemente.

USER BACKGROUND:
{user_background}

RECENT CONTEXT (ultimi 5 pensieri):
{recent_items}

INPUT UTENTE:
"{verbatim_input}"

TASK:
1. CERCA SU WEB per identificare esattamente cosa sia l'input
2. Classifica il tipo di pensiero
3. Estrai/inferisci il titolo corretto (es: se l'utente scrive "blade runner" -> "Blade Runner 2049" o "Blade Runner")
4. Fornisci link utili REALI trovati nella ricerca (IMDb, Goodreads, Wikipedia, Spotify, etc)
5. Stima tempo necessario per consumare
6. Assegna priorità basata su interesse/urgenza

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
- CERCA SEMPRE prima di classificare
- Sii generoso nell'interpretazione (preferisci classificare che "other")
- Se ambiguo, usa il background utente per disambiguare
- Link da fonti autorevoli trovate nella ricerca
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


async def classify_with_gemini(prompt: str) -> Optional[Dict]:
    """Classify using Gemini with Google Search grounding."""
    if not gemini_model_classify:
        logger.error("Gemini model not initialized")
        return None

    try:
        import google.generativeai as genai

        # Use Google Search grounding for better results
        # Gemini 2.0 requires using genai.protos for google_search tool
        google_search_tool = genai.protos.Tool(
            google_search=genai.protos.GoogleSearch()
        )
        response = gemini_model_classify.generate_content(
            prompt,
            tools=[google_search_tool],
            generation_config=genai.GenerationConfig(
                max_output_tokens=2000,
                temperature=0.7
            )
        )

        if response.text:
            return extract_json(response.text)
        return None

    except Exception as e:
        logger.error(f"Gemini classification error: {e}")
        return None


async def classify_with_claude(prompt: str) -> Optional[Dict]:
    """Classify using Claude with web search."""
    if not claude_client:
        logger.error("Claude client not initialized")
        return None

    try:
        import anthropic

        response = claude_client.messages.create(
            model=CLAUDE_MODEL_CLASSIFY,
            max_tokens=2000,
            tools=[
                {"type": "web_search_20250305", "name": "web_search"}
            ],
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        for block in response.content:
            if block.type == "text":
                result = extract_json(block.text)
                if result:
                    return result
        return None

    except Exception as e:
        logger.error(f"Claude classification error: {e}")
        return None


async def generate_picks_with_gemini(prompt: str) -> Optional[Dict]:
    """Generate daily picks using Gemini."""
    if not gemini_model_picks:
        logger.error("Gemini model not initialized")
        return None

    try:
        import google.generativeai as genai

        response = gemini_model_picks.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=1500,
                temperature=0.7
            )
        )

        if response.text:
            return extract_json(response.text)
        return None

    except Exception as e:
        logger.error(f"Gemini picks error: {e}")
        return None


async def generate_picks_with_claude(prompt: str) -> Optional[Dict]:
    """Generate daily picks using Claude."""
    if not claude_client:
        logger.error("Claude client not initialized")
        return None

    try:
        response = claude_client.messages.create(
            model=CLAUDE_MODEL_PICKS,
            max_tokens=1500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        for block in response.content:
            if block.type == "text":
                result = extract_json(block.text)
                if result:
                    return result
        return None

    except Exception as e:
        logger.error(f"Claude picks error: {e}")
        return None


async def classify_and_enrich(verbatim: str, msg_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Classifica e arricchisce un pensiero usando l'LLM configurato.
    """
    # Check if any provider is available
    if LLM_PROVIDER == "gemini" and not gemini_model_classify:
        logger.error("Gemini not initialized - missing GOOGLE_API_KEY")
        return await create_fallback_result(verbatim, msg_id)
    elif LLM_PROVIDER == "claude" and not claude_client:
        logger.error("Claude not initialized - missing CLAUDE_API_KEY")
        return await create_fallback_result(verbatim, msg_id)

    try:
        # Get context
        user_background = await get_config('user_background', '')
        recent_items = await get_recent_items(limit=5)

        # Get custom prompt if configured, otherwise use default
        custom_prompt = await get_config('classify_prompt', '')

        # Use Gemini-specific prompt if using Gemini (includes search instruction)
        if LLM_PROVIDER == "gemini":
            prompt_template = custom_prompt if custom_prompt else CLASSIFY_PROMPT_GEMINI
        else:
            prompt_template = custom_prompt if custom_prompt else CLASSIFY_PROMPT

        # Format prompt
        prompt = prompt_template.format(
            user_background=user_background or "Nessun background impostato",
            recent_items=json.dumps(recent_items, indent=2, ensure_ascii=False) if recent_items else "Nessun item recente",
            verbatim_input=verbatim
        )

        # Call appropriate LLM
        if LLM_PROVIDER == "gemini":
            result = await classify_with_gemini(prompt)
        else:
            result = await classify_with_claude(prompt)

        if not result:
            logger.warning(f"Failed to parse LLM response for: {verbatim[:50]}")
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
    # Check if any provider is available
    if LLM_PROVIDER == "gemini" and not gemini_model_picks:
        logger.error("Gemini not initialized - missing GOOGLE_API_KEY")
        return None
    elif LLM_PROVIDER == "claude" and not claude_client:
        logger.error("Claude not initialized - missing CLAUDE_API_KEY")
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

        # Call appropriate LLM
        if LLM_PROVIDER == "gemini":
            result = await generate_picks_with_gemini(prompt)
        else:
            result = await generate_picks_with_claude(prompt)

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
