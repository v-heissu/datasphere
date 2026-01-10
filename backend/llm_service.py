"""
LLM service for classification and enrichment.
Supports both Gemini (recommended - FREE) and Claude (fallback).

FIXED VERSION - Working Gemini API calls
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

logger = logging.getLogger(__name__)

# Initialize clients based on provider
gemini_model = None
claude_client = None

if LLM_PROVIDER == "gemini" and GOOGLE_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        gemini_model = genai.GenerativeModel(GEMINI_MODEL_CLASSIFY)
        logger.info(f"Initialized Gemini: {GEMINI_MODEL_CLASSIFY}")
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
2. Classifica il tipo di pensiero basandoti sui risultati della ricerca
3. Estrai titolo corretto e informazioni reali trovate online
4. Fornisci link REALI da fonti autorevoli (IMDb, Spotify, Wikipedia, Bandcamp, etc)
5. Stima tempo e priorità

OUTPUT (SOLO JSON, NO markdown, NO testo aggiuntivo):
{{
  "type": "film|book|concept|music|art|todo|other",
  "title": "titolo esatto trovato nella ricerca",
  "description": "cosa significa (1-2 frasi basate su ricerca)",
  "links": [
    {{"url": "link reale trovato", "type": "imdb|spotify|wikipedia|bandcamp|..."}}
  ],
  "estimated_minutes": 30,
  "priority": 3,
  "tags": ["tag1", "tag2", "tag3"],
  "consumption_suggestion": "quando/come consumarlo"
}}

REGOLE CRITICHE:
- USA web search per trovare informazioni accurate
- Link SOLO da ricerca (no invenzioni)
- Se ricerca non trova nulla → type: "other", description: "Richiede chiarimento"
- Priorità: 5=urgente/evento, 4=interessante, 3=normale, 2=bassa, 1=archivio
- RISPONDI SOLO CON JSON PURO
"""

CLASSIFY_PROMPT_CLAUDE = """
Sei un assistente per una persona con ADHD che cattura pensieri velocemente.

USER BACKGROUND:
{user_background}

RECENT CONTEXT (ultimi 5 pensieri):
{recent_items}

INPUT UTENTE:
"{verbatim_input}"

TASK:
1. USA web_search tool per identificare cosa sia l'input
2. Classifica basandoti sui risultati
3. Estrai informazioni reali trovate
4. Fornisci link autorevoli

OUTPUT (SOLO JSON):
{{
  "type": "film|book|concept|music|art|todo|other",
  "title": "titolo esatto",
  "description": "cosa significa (1-2 frasi)",
  "links": [{{"url": "...", "type": "..."}}],
  "estimated_minutes": 30,
  "priority": 3,
  "tags": ["tag1", "tag2"],
  "consumption_suggestion": "quando/come"
}}

REGOLE:
- Cerca SEMPRE prima di rispondere
- Link solo da fonti reali
- RISPONDI SOLO JSON
"""

DAILY_PICKS_PROMPT = """
Sei un assistente per persona ADHD.

USER BACKGROUND:
{user_background}

PENDING ITEMS:
{pending_items}

CONTEXT:
- Oggi: {day_of_week}
- Ora: {current_time}
- Ultimi 7gg: consumati {recent_consumed}, catturati {recent_captured}

TASK:
Seleziona 3-5 item appropriati per oggi.

OUTPUT (SOLO JSON):
{{
  "picks": [
    {{"item_id": 123, "reason": "perché oggi"}}
  ],
  "total_estimated_time": 120,
  "message": "messaggio motivazionale (1 frase)"
}}

REGOLE:
- Bilanciati per tipo e tempo
- Priorità a vecchi (>7gg)
- Max 2-3 ore totali
- SOLO JSON
"""


def extract_json(text: str) -> Optional[Dict]:
    """Extract JSON from text, handling markdown and extra text."""
    text = text.strip()
    
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Find JSON object in text
    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None


async def classify_with_gemini(prompt: str) -> Optional[Dict]:
    """Classify using Gemini with Google Search grounding."""
    if not gemini_model:
        logger.error("Gemini model not initialized")
        return None

    try:
        import google.generativeai as genai

        # Generation config - NOTE: Cannot use response_mime_type="application/json"
        # together with search grounding. The extract_json() function will parse
        # the JSON from the text response instead.
        generation_config = genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=2000
        )

        # Enable Google Search grounding
        # This is the CORRECT syntax for the stable library
        tools = [{"google_search_retrieval": {}}]

        # Generate content
        response = gemini_model.generate_content(
            prompt,
            generation_config=generation_config,
            tools=tools
        )
        
        if not response or not response.text:
            logger.error("Empty response from Gemini")
            return None
        
        # Parse JSON from response
        result = extract_json(response.text)
        
        if not result:
            logger.warning(f"Failed to parse Gemini JSON: {response.text[:200]}")
            return None
        
        logger.info(f"Successfully classified with Gemini: {result.get('title', 'unknown')}")
        return result
        
    except Exception as e:
        logger.error(f"Gemini classification error: {e}", exc_info=True)
        return None


async def classify_with_claude(prompt: str) -> Optional[Dict]:
    """Classify using Claude with web search."""
    if not claude_client:
        logger.error("Claude client not initialized")
        return None

    try:
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
                    logger.info(f"Successfully classified with Claude: {result.get('title', 'unknown')}")
                    return result
        
        logger.warning("No valid JSON in Claude response")
        return None

    except Exception as e:
        logger.error(f"Claude classification error: {e}", exc_info=True)
        return None


async def generate_picks_with_gemini(prompt: str) -> Optional[Dict]:
    """Generate daily picks using Gemini (no search needed)."""
    if not gemini_model:
        logger.error("Gemini model not initialized")
        return None

    try:
        import google.generativeai as genai
        
        # Use picks model
        picks_model = genai.GenerativeModel(GEMINI_MODEL_PICKS)
        
        generation_config = genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=1500,
            response_mime_type="application/json"
        )
        
        response = picks_model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        if response and response.text:
            return extract_json(response.text)
        return None

    except Exception as e:
        logger.error(f"Gemini picks error: {e}", exc_info=True)
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
        logger.error(f"Claude picks error: {e}", exc_info=True)
        return None


async def classify_and_enrich(verbatim: str, msg_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Classifica e arricchisce un pensiero usando l'LLM configurato.
    """
    logger.info(f"Classifying: {verbatim[:50]}... with {LLM_PROVIDER}")
    
    # Check if any provider is available
    if LLM_PROVIDER == "gemini" and not gemini_model:
        logger.error("Gemini not initialized - missing GOOGLE_API_KEY")
        return await create_fallback_result(verbatim, msg_id)
    elif LLM_PROVIDER == "claude" and not claude_client:
        logger.error("Claude not initialized - missing CLAUDE_API_KEY")
        return await create_fallback_result(verbatim, msg_id)

    try:
        # Get context
        user_background = await get_config('user_background', '')
        recent_items = await get_recent_items(limit=5)

        # Format prompt
        if LLM_PROVIDER == "gemini":
            prompt_template = CLASSIFY_PROMPT_GEMINI
        else:
            prompt_template = CLASSIFY_PROMPT_CLAUDE

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
            logger.warning(f"Failed to get valid result for: {verbatim[:50]}")
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
        logger.info(f"Successfully saved item {item_id}: {result['title']}")
        return result

    except Exception as e:
        logger.error(f"Error classifying thought: {e}", exc_info=True)
        return await create_fallback_result(verbatim, msg_id)


def normalize_classification(result: Dict) -> Dict:
    """Normalize and validate classification result."""
    valid_types = ['film', 'book', 'concept', 'music', 'art', 'todo', 'other']

    return {
        'type': result.get('type', 'other') if result.get('type') in valid_types else 'other',
        'title': result.get('title', '')[:200],
        'description': result.get('description', ''),
        'links': result.get('links', [])[:10],
        'estimated_minutes': min(max(result.get('estimated_minutes', 15), 1), 600),
        'priority': min(max(result.get('priority', 3), 1), 5),
        'tags': result.get('tags', [])[:5],
        'consumption_suggestion': result.get('consumption_suggestion', '')
    }


async def create_fallback_result(verbatim: str, msg_id: Optional[int] = None) -> Dict[str, Any]:
    """Create fallback result when classification fails."""
    logger.warning(f"Creating fallback for: {verbatim[:50]}")
    
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
    """Genera suggerimenti giornalieri."""
    logger.info(f"Generating daily picks with {LLM_PROVIDER}")
    
    if LLM_PROVIDER == "gemini" and not gemini_model:
        logger.error("Gemini not initialized")
        return None
    elif LLM_PROVIDER == "claude" and not claude_client:
        logger.error("Claude not initialized")
        return None

    try:
        user_background = await get_config('user_background', '')
        pending_items = await get_pending_items_for_picks(limit=50)

        if not pending_items:
            logger.info("No pending items for daily picks")
            return None

        recent_stats = await get_stats_last_7_days()

        prompt = DAILY_PICKS_PROMPT.format(
            user_background=user_background or "Nessun background impostato",
            pending_items=json.dumps(pending_items, indent=2, ensure_ascii=False),
            day_of_week=datetime.now().strftime('%A'),
            current_time=datetime.now().strftime('%H:%M'),
            recent_consumed=recent_stats['consumed'],
            recent_captured=recent_stats['captured']
        )

        if LLM_PROVIDER == "gemini":
            result = await generate_picks_with_gemini(prompt)
        else:
            result = await generate_picks_with_claude(prompt)

        if not result or 'picks' not in result:
            logger.warning("Failed to parse daily picks response")
            return None

        # Validate picks
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

        today = datetime.now().strftime('%Y-%m-%d')
        await save_daily_picks(
            date=today,
            picks=[{'item_id': p['item_id'], 'reason': p['reason']} for p in valid_picks],
            total_time=total_time,
            message=result.get('message', '')
        )

        logger.info(f"Generated {len(valid_picks)} picks for {today}")
        return {
            'date': today,
            'picks': valid_picks,
            'total_estimated_time': total_time,
            'message': result.get('message', 'Buona giornata!')
        }

    except Exception as e:
        logger.error(f"Error generating daily picks: {e}", exc_info=True)
        return None


async def get_daily_picks_with_items(date: str) -> Optional[Dict[str, Any]]:
    """Get daily picks with full item details."""
    from database import get_daily_picks_for_date

    picks_data = await get_daily_picks_for_date(date)
    if not picks_data:
        return None

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


async def debug_classify(verbatim: str) -> Dict[str, Any]:
    """
    Debug classification - returns raw response, parsed JSON, and grounding metadata.
    Used by the debug API tab in settings.
    """
    from config import LLM_PROVIDER, GEMINI_MODEL_CLASSIFY

    # Build prompt
    user_background = await get_config('user_background', '')
    recent_items = await get_recent_items(limit=5)

    if LLM_PROVIDER == "gemini":
        prompt_template = CLASSIFY_PROMPT_GEMINI
    else:
        prompt_template = CLASSIFY_PROMPT_CLAUDE

    prompt = prompt_template.format(
        user_background=user_background or "Nessun background impostato",
        recent_items=json.dumps(recent_items, indent=2, ensure_ascii=False) if recent_items else "Nessun item recente",
        verbatim_input=verbatim
    )

    result = {
        'model': GEMINI_MODEL_CLASSIFY if LLM_PROVIDER == "gemini" else CLAUDE_MODEL_CLASSIFY,
        'prompt_preview': prompt[:500] + ('...' if len(prompt) > 500 else ''),
        'raw_response': None,
        'parsed_json': None,
        'grounding_metadata': None
    }

    if LLM_PROVIDER == "gemini":
        if not gemini_model:
            raise Exception("Gemini model not initialized")

        import google.generativeai as genai

        # Generation config - NO JSON mode when using search grounding
        generation_config = genai.GenerationConfig(
            temperature=0.7,
            max_output_tokens=2000
        )

        # Enable Google Search grounding
        tools = [{"google_search_retrieval": {}}]

        # Generate content
        response = gemini_model.generate_content(
            prompt,
            generation_config=generation_config,
            tools=tools
        )

        if response and response.text:
            result['raw_response'] = response.text
            result['parsed_json'] = extract_json(response.text)

        # Extract grounding metadata if available
        if response and hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                gm = candidate.grounding_metadata
                grounding_info = {
                    'search_queries': [],
                    'sources': [],
                    'grounding_chunks': 0
                }

                # Extract search queries
                if hasattr(gm, 'web_search_queries') and gm.web_search_queries:
                    grounding_info['search_queries'] = list(gm.web_search_queries)

                # Extract grounding chunks/sources
                if hasattr(gm, 'grounding_chunks') and gm.grounding_chunks:
                    grounding_info['grounding_chunks'] = len(gm.grounding_chunks)
                    for chunk in gm.grounding_chunks:
                        if hasattr(chunk, 'web') and chunk.web:
                            grounding_info['sources'].append({
                                'uri': chunk.web.uri if hasattr(chunk.web, 'uri') else '',
                                'title': chunk.web.title if hasattr(chunk.web, 'title') else ''
                            })

                # Alternative: grounding_supports may contain source info
                if hasattr(gm, 'grounding_supports') and gm.grounding_supports:
                    for support in gm.grounding_supports:
                        if hasattr(support, 'grounding_chunk_indices'):
                            pass  # Info already in grounding_chunks

                if grounding_info['search_queries'] or grounding_info['sources']:
                    result['grounding_metadata'] = grounding_info

    else:
        # Claude path
        if not claude_client:
            raise Exception("Claude client not initialized")

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
                result['raw_response'] = block.text
                result['parsed_json'] = extract_json(block.text)
                break

    return result
