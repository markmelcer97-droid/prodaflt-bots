"""
PRODAFLT Content Researcher Pipeline — Content Classifier
Maps scraped content to 9 gambling-creative formats + detects viral patterns.
Uses lightweight heuristics + optional Kimi LLM enrichment.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional

import config


# ---------------------------------------------------------------------------
# 9 Gambling Creative Formats (from SCALE approach)
# ---------------------------------------------------------------------------

FORMAT_DEFINITIONS = {
    "newsjacking": {
        "description": "Exploits breaking news / viral events to grab attention.",
        "signals": ["breaking", "news", "trending", "viral", "just happened", "urgent"],
        "visual": ["news overlay", "ticker", "headline graphic", "shocked face"],
    },
    "fake_podcast": {
        "description": "Simulates podcast/TV interview with authority figure.",
        "signals": ["podcast", "interview", "expert", "host", "guest", "studio", "mic"],
        "visual": ["split screen", "studio background", "microphone", "headphones"],
    },
    "ugc_testimonial": {
        "description": "User-generated content showing 'real' win or experience.",
        "signals": ["i won", "my story", "honest review", "real user", "testimonial", "life changed"],
        "visual": ["phone screen recording", "selfie", "casual setting", "genuine reaction"],
    },
    "money_counter": {
        "description": "Visual counter / stack growing rapidly.",
        "signals": ["counter", "stack", "balance", "$", "€", "deposit", "withdraw"],
        "visual": ["animated counter", "cash stack", "bank app screenshot", "growing numbers"],
    },
    "fake_live": {
        "description": "Simulates live stream with fake comments and reactions.",
        "signals": ["live", "streaming now", "join chat", "real time", "🔴"],
        "visual": ["live badge", "comment feed", "reaction emojis", "viewer count"],
    },
    "challenge": {
        "description": "Social challenge with progression and reward promise.",
        "signals": ["challenge", "bet", "try this", "level", "mission", "quest", "task"],
        "visual": ["progress bar", "level up", "reward chest", "timer", "leaderboard"],
    },
    "transformation": {
        "description": "Before/after lifestyle transformation linked to gambling win.",
        "signals": ["before", "after", "changed my life", "from broke", "new car", "vacation"],
        "visual": ["split screen", "progression timeline", "luxury items", "travel"],
    },
    "fomo_urgency": {
        "description": "Scarcity / limited-time offer creating FOMO.",
        "signals": ["limited", "expires", "only today", "last chance", "hurry", "⌛", "⏰"],
        "visual": ["countdown timer", "burning offer", "running out", "exclusive badge"],
    },
    "educational_hook": {
        "description": "Teaches a 'strategy' or 'secret' then pivots to CTA.",
        "signals": ["secret", "strategy", "how to", "tutorial", "tip", "hack", "method"],
        "visual": ["whiteboard", "chart", "diagram", "step numbers", "checklist"],
    },
}


# ---------------------------------------------------------------------------
# Pattern definitions (viral hooks, CTAs, visual motifs)
# ---------------------------------------------------------------------------

PATTERN_CATALOG = {
    "pattern_shock_face": {
        "description": "Extreme facial reaction in first 1-3 seconds.",
        "keywords": ["shocked", "surprised", "omg", "no way", "unbelievable"],
    },
    "pattern_fast_cut": {
        "description": "Rapid cuts (<1s per shot) in opening 5 seconds.",
        "keywords": ["fast", "quick", "cut", "jump", "rapid"],
    },
    "pattern_text_overlay": {
        "description": "Large bold text overlay on video for readability without sound.",
        "keywords": ["text", "caption", "overlay", "subtitle", "captioned"],
    },
    "pattern_voiceover": {
        "description": "Voice-over narration driving the narrative.",
        "keywords": ["voice", "narrator", "story", "tell", "explain"],
    },
    "pattern_music_drop": {
        "description": "Music build-up + drop synchronized with visual reveal.",
        "keywords": ["music", "beat", "drop", "build", "sound"],
    },
    "pattern_cta_screen": {
        "description": "End-screen with explicit click/download CTA.",
        "keywords": ["download", "click", "get", "install", "register", "bonus"],
    },
    "pattern_social_proof": {
        "description": "Shows numbers of winners, reviews, or ratings.",
        "keywords": ["rated", "reviews", "winners", "players", "joined", "members"],
    },
    "pattern_localization": {
        "description": "Geo-specific elements (currency, language, landmarks).",
        "keywords": ["local", "city", "country", "language", "currency", "region"],
    },
}


# ---------------------------------------------------------------------------
# Classification logic
# ---------------------------------------------------------------------------

@dataclass
class ClassificationResult:
    format_name: str
    format_confidence: float  # 0-1
    detected_patterns: List[str]
    hook_text: Optional[str]
    cta_text: Optional[str]
    visual_tags: List[str]
    reasoning: str


def _normalize(text: Optional[str]) -> str:
    return (text or "").lower()


def _score_format(text: str, fmt: Dict) -> float:
    """Simple keyword overlap scoring for format detection."""
    signals = fmt.get("signals", [])
    visual = fmt.get("visual", [])
    all_kw = [s.lower() for s in signals + visual]
    if not all_kw:
        return 0.0
    hits = sum(1 for kw in all_kw if kw in text)
    return min(hits / max(len(all_kw) * 0.3, 1.0), 1.0)


def _detect_patterns(text: str) -> List[str]:
    """Return list of pattern names found in text."""
    found = []
    for pat_name, pat_data in PATTERN_CATALOG.items():
        keywords = pat_data.get("keywords", [])
        if any(kw in text for kw in keywords):
            found.append(pat_name)
    return found


def _extract_hook(text: str) -> Optional[str]:
    """Heuristic: first sentence ending with ! or ? or first 80 chars."""
    if not text:
        return None
    # Try first exclamation or question sentence
    m = re.search(r'^[^.!?]*[!?]', text)
    if m:
        return m.group(0).strip()
    return text[:120].strip()


def _extract_cta(text: str) -> Optional[str]:
    """Heuristic: find CTA phrases near end of text."""
    if not text:
        return None
    cta_phrases = [
        "download", "get", "install", "register", "sign up", "join",
        "click", "tap", "claim", "bonus", "free", "now", "today",
    ]
    sentences = re.split(r'[.!?\n]', text)
    # Check last 3 sentences
    for sent in reversed(sentences[-3:]):
        sent_lower = sent.lower()
        if any(p in sent_lower for p in cta_phrases):
            return sent.strip()
    return None


def _extract_visual_tags(meta: Dict) -> List[str]:
    """Infer visual tags from metadata and description."""
    tags = []
    desc = _normalize(meta.get("description", ""))
    title = _normalize(meta.get("title", ""))
    combined = f"{title} {desc}"

    visual_keywords = {
        "animation": ["animation", "animated", "motion", "cartoon"],
        "screen_recording": ["screen", "recording", "phone", "mobile"],
        "real_footage": ["real", "live action", "filmed", "camera"],
        "slideshow": ["slideshow", "photos", "images", "gallery"],
        "split_screen": ["split", "dual", "side by side"],
        "greenscreen": ["green screen", "chroma", "background replacement"],
        "3d": ["3d", "cgi", "render", "vfx"],
    }
    for tag, kws in visual_keywords.items():
        if any(kw in combined for kw in kws):
            tags.append(tag)
    return tags


def classify_content(
    title: Optional[str],
    description: Optional[str],
    transcript: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> ClassificationResult:
    """
    Classify scraped content into one of 9 formats + patterns.
    Uses lightweight keyword heuristics; can be enhanced with LLM.
    """
    meta = metadata or {}
    full_text = f"{_normalize(title)} {_normalize(description)} {_normalize(transcript)}"

    # Score each format
    format_scores = {}
    for fmt_name, fmt_def in FORMAT_DEFINITIONS.items():
        format_scores[fmt_name] = _score_format(full_text, fmt_def)

    # Pick best format
    best_format = max(format_scores, key=format_scores.get)  # type: ignore[arg-type]
    best_score = format_scores[best_format]

    # Patterns
    detected_patterns = _detect_patterns(full_text)

    # Hook / CTA / Visuals
    hook = _extract_hook(title or description)
    cta = _extract_cta(full_text)
    visual_tags = _extract_visual_tags(meta)

    # Reasoning string
    reasoning = (
        f"Format '{best_format}' scored {best_score:.2f} based on keyword overlap. "
        f"Detected {len(detected_patterns)} patterns. "
        f"Hook: {'yes' if hook else 'no'}. CTA: {'yes' if cta else 'no'}."
    )

    return ClassificationResult(
        format_name=best_format,
        format_confidence=round(best_score, 2),
        detected_patterns=detected_patterns,
        hook_text=hook,
        cta_text=cta,
        visual_tags=visual_tags,
        reasoning=reasoning,
    )


# ---------------------------------------------------------------------------
# Batch classification
# ---------------------------------------------------------------------------

def batch_classify(scraped_results: List[Dict]) -> List[ClassificationResult]:
    """Classify a batch of scraped results."""
    out = []
    for res in scraped_results:
        result = classify_content(
            title=res.get("title"),
            description=res.get("description"),
            transcript=res.get("transcript"),
            metadata=res.get("raw_metadata"),
        )
        out.append(result)
    return out
