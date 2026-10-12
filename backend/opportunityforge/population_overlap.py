"""
Population Overlap Checker — Layer 1.5 of the linker.

For each dataset pair, samples entity names and computes real-world
population overlap via fuzzy matching. Pairs with < 5% overlap are
HARD KILLED — they never reach the evaluation layer.

This fixes the structural linker's blind spot: matching field names
like "company_name" = "company_name" without checking whether the
same companies actually appear in both datasets.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from difflib import SequenceMatcher
from typing import Any
from uuid import UUID

# ── Entity normalization ────────────────────────────────────────

# Legal suffixes to strip
_SUFFIXES = re.compile(
    r'\b(Inc\.?|Incorporated|Corp\.?|Corporation|LLC|L\.?L\.?C\.?|'
    r'LP|L\.?P\.?|Ltd\.?|Limited|Co\.?|Company|PLC|GmbH|S\.?A\.?|'
    r'AG|B\.?V\.?|N\.?V\.?|Pty\.?\s*Ltd\.?|KK|OY|AB|ApS|Sarl|SAS|'
    r'SPA|d/b/a|DBA|a division of|a subsidiary of)\b',
    re.IGNORECASE,
)

_PUNCTUATION = re.compile(r'[,.]\s*')
_WHITESPACE = re.compile(r'\s+')
_NON_ENTITY = {
    '', 'n/a', 'na', 'none', 'unknown', 'tbd', '---', '--',
    'not available', 'not provided', 'see above', 'various',
    'multiple', 'no data', 'null', 'nil', '0', '-',
}


def normalize_entity(name: str) -> str:
    """Normalize a company/entity name for fuzzy comparison.

    Steps:
    1. Lowercase
    2. Strip legal suffixes (Inc, LLC, Corp, etc.)
    3. Strip punctuation
    4. Collapse whitespace
    5. Trim

    Returns empty string if name is a known non-entity sentinel.
    """
    if not name or not isinstance(name, str):
        return ''

    n = name.strip().lower()
    if n in _NON_ENTITY or len(n) < 2:
        return ''

    # Remove d/b/a sections — keep the primary name
    n = re.split(r'\bd/b/a\b|\bDBA\b|\bdba\b', n, maxsplit=1)[0]

    n = _SUFFIXES.sub('', n)
    n = _PUNCTUATION.sub(' ', n)
    n = _WHITESPACE.sub(' ', n)
    return n.strip()


def fuzzy_match(a: str, b: str, threshold: float = 0.85) -> bool:
    """Check if two normalized entity names likely refer to the same entity.

    Uses a combination of:
    - Token sort ratio (order-independent word matching)
    - Sequence match ratio (character-level similarity)
    - Exact match on normalized form
    - Subset match (one name fully contained in the other)
    """
    if not a or not b:
        return False

    # Exact match after normalization
    if a == b:
        return True

    # One is a substring of the other (e.g., "Covidien" in "Covidien LP")
    if a in b or b in a:
        # Only if the shorter is at least 60% of the longer
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))
        if shorter / longer >= 0.6:
            return True

    # Token sort: split into words, sort, compare
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if tokens_a and tokens_b:
        token_overlap = len(tokens_a & tokens_b) / len(tokens_a | tokens_b)
        if token_overlap >= threshold:
            return True

    # Sequence matcher for fuzzy string similarity
    seq_ratio = SequenceMatcher(None, a, b).ratio()
    return seq_ratio >= threshold


def compute_overlap(
    entities_a: list[str],
    entities_b: list[str],
    match_threshold: float = 0.85,
) -> dict[str, Any]:
    """Compute population overlap between two entity lists.

    Returns:
        dict with:
        - overlap_count: number of matched pairs
        - overlap_pct: percentage of the smaller list that matched
        - total_a, total_b: deduplicated entity counts
        - matched_pairs: list of (a, b, score) for matched pairs
        - killed: True if overlap_pct < 0.05
    """
    norm_a = [n for n in (normalize_entity(e) for e in entities_a) if n]
    norm_b = [n for n in (normalize_entity(e) for e in entities_b) if n]

    # Deduplicate within each list
    unique_a = list(dict.fromkeys(norm_a))
    unique_b = list(dict.fromkeys(norm_b))

    matched_pairs: list[tuple[str, str, float]] = []
    matched_b_indices: set[int] = set()

    for a in unique_a:
        for j, b in enumerate(unique_b):
            if j in matched_b_indices:
                continue
            ratio = SequenceMatcher(None, a, b).ratio()
            if ratio >= match_threshold:
                matched_pairs.append((a, b, round(ratio, 3)))
                matched_b_indices.add(j)
                break  # One match per entity A

    overlap_count = len(matched_pairs)
    smaller_population = min(len(unique_a), len(unique_b))
    overlap_pct = round(overlap_count / smaller_population, 4) if smaller_population > 0 else 0.0

    return {
        'overlap_count': overlap_count,
        'overlap_pct': overlap_pct,
        'total_a': len(unique_a),
        'total_b': len(unique_b),
        'matched_pairs': matched_pairs[:10],  # Top 10 for inspection
        'killed': overlap_pct < 0.05,
    }


# ── Dataset-specific entity fetchers ─────────────────────────────

def sample_fda_food(limit: int = 100) -> list[str]:
    """Sample entity names from FDA food enforcement API."""
    import json
    import urllib.request
    entities: list[str] = []
    url = f'https://api.fda.gov/food/enforcement.json?limit={limit}'
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            for r in json.loads(resp.read()).get('results', []):
                firm = r.get('recalling_firm', '')
                if firm:
                    entities.append(firm)
    except Exception:
        pass
    return entities


def sample_fda_device(limit: int = 100) -> list[str]:
    """Sample entity names from FDA device enforcement API."""
    import json
    import urllib.request
    entities: list[str] = []
    url = f'https://api.fda.gov/device/enforcement.json?limit={limit}'
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            for r in json.loads(resp.read()).get('results', []):
                firm = r.get('recalling_firm', '')
                if firm:
                    entities.append(firm)
    except Exception:
        pass
    return entities


def sample_fda_enforcement(limit: int = 100) -> list[str]:
    """Sample entity names from FDA enforcement API (food or device)."""
    import json
    import urllib.request

    entities: list[str] = []
    for endpoint in ('food', 'device'):
        url = f'https://api.fda.gov/{endpoint}/enforcement.json?limit={limit}'
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                data = json.loads(resp.read())
                for r in data.get('results', []):
                    firm = r.get('recalling_firm', '')
                    if firm:
                        entities.append(firm)
        except Exception:
            continue
    
    return entities


def sample_sec_edgar(query: str = "Form 4", limit: int = 50) -> list[str]:
    """Sample company names from SEC EDGAR full-text search."""
    import json
    import urllib.request
    from urllib.parse import quote

    url = (
        f'https://efts.sec.gov/LATEST/search-index'
        f'?q={quote(query)}'
        f'&dateRange=custom'
        f'&startdt=2026-01-01'
        f'&enddt=2026-07-01'
        f'&from=0&size={limit}'
    )
    entities: list[str] = []
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'OpportunityForge/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            for hit in data.get('hits', {}).get('hits', []):
                src = hit.get('_source', {})
                for name in src.get('display_names', []):
                    if name and len(name) > 3:
                        entities.append(name)
    except Exception:
        pass

    return entities


def sample_entity_list(dataset_id: str, dataset_title: str) -> list[str]:
    """Get entity samples for a dataset, falling back to known patterns."""
    title_lower = dataset_title.lower()

    if 'fda' in title_lower and ('food' in title_lower or 'device' in title_lower):
        return sample_fda_enforcement(100)

    if 'sec' in title_lower and '13d' in title_lower:
        return sample_sec_edgar('Schedule 13D', 50)

    if 'sec' in title_lower and 'form 4' in title_lower:
        return sample_sec_edgar('Form 4', 50)

    # Fallback: return empty list — we can't sample this dataset
    # (will be handled by the linker as "unknown overlap")
    return []


# ── Linker integration ──────────────────────────────────────────

def population_overlap_gate(
    source_id: str,
    target_id: str,
    source_title: str,
    target_title: str,
) -> dict[str, Any]:
    """Gate check for a dataset pair. Returns overlap data + kill decision."""
    entities_a = sample_entity_list(source_id, source_title)
    entities_b = sample_entity_list(target_id, target_title)

    if not entities_a or not entities_b:
        return {
            'overlap_count': 0,
            'overlap_pct': 0.0,
            'total_a': len(entities_a),
            'total_b': len(entities_b),
            'matched_pairs': [],
            'killed': False,
            'unknown': True,
            'reason': 'insufficient samples — cannot determine',
        }

    result = compute_overlap(entities_a, entities_b)
    result['unknown'] = False
    result['reason'] = (
        f'overlap {result["overlap_pct"]:.1%} '
        f'({"< 5% → KILLED" if result["killed"] else "≥ 5% → survives"})'
    )
    return result
