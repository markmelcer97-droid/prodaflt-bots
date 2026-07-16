"""
PRODAFLT Content Researcher Pipeline — Scorer
Calculates Virality Score (0-10) × 0.6 + Adaptation Potential (0-10) × 0.4 = Final Score.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Virality Score components
# ---------------------------------------------------------------------------

VIRALITY_WEIGHTS = {
    "hook_strength": 0.25,      # First 3s grab attention
    "emotional_trigger": 0.20,  # Shock, FOMO, curiosity
    "shareability": 0.15,       # Easy to share, relatable
    "pattern_strength": 0.20,   # Uses known viral patterns
    "platform_fit": 0.20,       # Optimized for target platform
}

ADAPTATION_WEIGHTS = {
    "creative_flexibility": 0.25,   # Easy to re-skin / localize
    "cost_to_produce": 0.20,        # Lower cost = higher score
    "compliance_risk": 0.20,        # Lower risk = higher score
    "audience_breadth": 0.15,       # Works across GEOs/demos
    "cta_clarity": 0.20,            # Clear conversion path
}


# ---------------------------------------------------------------------------
# Helper: normalize any metric to 0-10
# ---------------------------------------------------------------------------

def _clamp(val: float, lo: float = 0.0, hi: float = 10.0) -> float:
    return max(lo, min(hi, val))


def _sigmoid(x: float, midpoint: float = 5.0, steepness: float = 1.0) -> float:
    """Sigmoid mapping for smoother scoring."""
    return 10.0 / (1.0 + math.exp(-steepness * (x - midpoint)))


# ---------------------------------------------------------------------------
# Virality Score calculator
# ---------------------------------------------------------------------------

@dataclass
class ViralityInputs:
    has_strong_hook: bool = False           # Detected hook in first 3s
    emotional_tags: List[str] = None        # shock, curiosity, fomo, joy, anger
    estimated_share_rate: float = 0.0       # 0-1 proxy
    pattern_count: int = 0                  # Number of viral patterns detected
    platform_match_score: float = 0.0       # 0-1 how well it fits target platform
    view_velocity_proxy: float = 0.0        # Engagement proxy (likes/views ratio etc)

    def __post_init__(self):
        if self.emotional_tags is None:
            self.emotional_tags = []


def calculate_virality_score(inputs: ViralityInputs) -> float:
    """
    Calculate Virality Score on 0-10 scale.
    """
    # Hook strength
    hook_score = 8.5 if inputs.has_strong_hook else 4.0

    # Emotional trigger
    emotional_map = {"shock": 9, "fomo": 8.5, "curiosity": 8, "joy": 7, "anger": 6.5, "sadness": 4}
    emotional_score = 5.0
    if inputs.emotional_tags:
        scores = [emotional_map.get(t.lower(), 5.0) for t in inputs.emotional_tags]
        emotional_score = sum(scores) / len(scores)

    # Shareability
    share_score = _sigmoid(inputs.estimated_share_rate * 10, midpoint=5, steepness=0.8)

    # Pattern strength
    pattern_score = min(5.0 + inputs.pattern_count * 1.5, 10.0)

    # Platform fit
    platform_score = inputs.platform_match_score * 10

    # Weighted sum
    score = (
        hook_score * VIRALITY_WEIGHTS["hook_strength"]
        + emotional_score * VIRALITY_WEIGHTS["emotional_trigger"]
        + share_score * VIRALITY_WEIGHTS["shareability"]
        + pattern_score * VIRALITY_WEIGHTS["pattern_strength"]
        + platform_score * VIRALITY_WEIGHTS["platform_fit"]
    )
    return round(_clamp(score), 1)


# ---------------------------------------------------------------------------
# Adaptation Potential calculator
# ---------------------------------------------------------------------------

@dataclass
class AdaptationInputs:
    format_flexibility: float = 5.0     # 0-10 how easy to modify
    production_cost_estimate: float = 5.0  # 0-10 (10 = very cheap)
    compliance_risk_score: float = 5.0   # 0-10 (10 = no risk)
    geo_applicability: List[str] = None  # List of GEOs it works for
    cta_clarity_score: float = 5.0       # 0-10 clear CTA
    asset_reusability: float = 5.0       # 0-10 can reuse assets

    def __post_init__(self):
        if self.geo_applicability is None:
            self.geo_applicability = []


def calculate_adaptation_potential(inputs: AdaptationInputs) -> float:
    """
    Calculate Adaptation Potential on 0-10 scale.
    """
    # Creative flexibility
    flexibility_score = inputs.format_flexibility

    # Cost (invert: cheaper = higher score)
    cost_score = inputs.production_cost_estimate

    # Compliance (lower risk = higher score)
    compliance_score = inputs.compliance_risk_score

    # Audience breadth
    geo_count = len(inputs.geo_applicability)
    audience_score = min(5.0 + geo_count * 1.0, 10.0)

    # CTA clarity
    cta_score = inputs.cta_clarity_score

    # Asset reusability
    reuse_score = inputs.asset_reusability

    score = (
        flexibility_score * ADAPTATION_WEIGHTS["creative_flexibility"]
        + cost_score * ADAPTATION_WEIGHTS["cost_to_produce"]
        + compliance_score * ADAPTATION_WEIGHTS["compliance_risk"]
        + audience_score * ADAPTATION_WEIGHTS["audience_breadth"]
        + cta_score * ADAPTATION_WEIGHTS["cta_clarity"]
    )
    return round(_clamp(score), 1)


# ---------------------------------------------------------------------------
# Final Score
# ---------------------------------------------------------------------------

def calculate_final_score(virality: float, adaptation: float) -> float:
    """
    Final Score = Virality × 0.6 + Adaptation × 0.4
    """
    final = virality * 0.6 + adaptation * 0.4
    return round(_clamp(final), 1)


# ---------------------------------------------------------------------------
# Convenience: score from classification + metadata
# ---------------------------------------------------------------------------

def score_from_classification(
    classification: Dict,
    platform: Optional[str] = None,
    duration_sec: Optional[int] = None,
    has_transcript: bool = False,
    geo_targets: Optional[List[str]] = None,
) -> Dict:
    """
    High-level convenience that takes classifier output + metadata
    and returns full scoring dict.
    """
    geo_targets = geo_targets or ["US", "CA", "AU", "GB", "DE"]

    # Build virality inputs
    v_inputs = ViralityInputs(
        has_strong_hook=bool(classification.get("hook_text")),
        emotional_tags=classification.get("detected_patterns", []),
        estimated_share_rate=0.5,  # Default until we have real data
        pattern_count=len(classification.get("detected_patterns", [])),
        platform_match_score=0.7 if platform in {"tiktok", "instagram", "youtube"} else 0.5,
        view_velocity_proxy=0.0,
    )

    # Build adaptation inputs
    a_inputs = AdaptationInputs(
        format_flexibility=7.0,
        production_cost_estimate=6.0,
        compliance_risk_score=7.0,
        geo_applicability=geo_targets,
        cta_clarity_score=8.0 if classification.get("cta_text") else 4.0,
        asset_reusability=6.0,
    )

    virality = calculate_virality_score(v_inputs)
    adaptation = calculate_adaptation_potential(a_inputs)
    final = calculate_final_score(virality, adaptation)

    return {
        "virality_score": virality,
        "adaptation_potential": adaptation,
        "final_score": final,
        "virality_breakdown": {
            "hook_strength": 8.5 if v_inputs.has_strong_hook else 4.0,
            "emotional_trigger": v_inputs.emotional_tags,
            "pattern_count": v_inputs.pattern_count,
            "platform_match": v_inputs.platform_match_score * 10,
        },
        "adaptation_breakdown": {
            "flexibility": a_inputs.format_flexibility,
            "cost_estimate": a_inputs.production_cost_estimate,
            "compliance": a_inputs.compliance_risk_score,
            "geo_count": len(a_inputs.geo_applicability),
            "cta_clarity": a_inputs.cta_clarity_score,
        },
    }
