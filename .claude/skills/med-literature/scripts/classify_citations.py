#!/usr/bin/env python3
"""
Citation Classifier for Medical Literature

Classifies citation relationships based on context and patterns.
Uses regex patterns to identify: SUPPORTING, CONTRASTING, REFUTING,
METHODOLOGICAL, CONTEXTUAL, and META_ANALYSIS citations.
"""

import re
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass

@dataclass
class ClassificationResult:
    """Result of citation classification."""
    classification: str
    confidence: float
    study_weight: float
    matched_patterns: List[str]
    reasoning: str


# ==================== Medical Citation Patterns ====================

# SUPPORTING - Confirms efficacy, safety, mechanism
SUPPORTING_PATTERNS = [
    r"demonstrated\s+(efficacy|effectiveness|benefit)",
    r"showed?\s+(significant\s+)?improvement",
    r"(reduced|decreased|lowered)\s+(mortality|morbidity|risk)",
    r"statistically\s+significant\s+(benefit|improvement)",
    r"superior\s+to\s+(placebo|control|standard)",
    r"confirmed\s+(safety|tolerability|efficacy)",
    r"validates?\s+(the|our)",
    r"consistent\s+with\s+(previous|prior|earlier)",
    r"supports?\s+(the\s+)?(hypothesis|finding|conclusion)",
    r"in\s+agreement\s+with",
    r"corroborates?",
    r"(establishes?|established)\s+(that|the)",
    r"proven\s+(effective|safe|beneficial)",
    r"successfully\s+(treated|prevented|reduced)",
]

# CONTRASTING - Alternative interpretations, conflicting data
CONTRASTING_PATTERNS = [
    r"however,?\s+(the|this|our)",
    r"in\s+contrast",
    r"on\s+the\s+other\s+hand",
    r"conflicting\s+(results|data|evidence|findings)",
    r"inconsistent\s+with",
    r"(differs?|different)\s+from",
    r"alternative\s+(explanation|interpretation|mechanism)",
    r"(whereas|while)\s+(we|our|the)",
    r"conversely",
    r"mixed\s+(results|evidence|findings)",
    r"uncertain(ty)?\s+(regarding|about)",
    r"debate\s+(continues|remains)",
    r"discrepan(cy|t)",
    r"(varies?|variable|variation)\s+(across|between)",
]

# REFUTING - Rules out efficacy/safety, contradicts definitively
REFUTING_PATTERNS = [
    r"failed\s+to\s+(demonstrate|show|find)",
    r"no\s+significant\s+(difference|benefit|effect|improvement)",
    r"(not|no)\s+statistically\s+significant",
    r"ruled?\s+out",
    r"contraindicated",
    r"harmful",
    r"(adverse|serious)\s+(event|effect|reaction)",
    r"(withdrawn|recalled)\s+(from|due\s+to)",
    r"inferior\s+to",
    r"(refutes?|refuted|disproven)",
    r"contradicts?",
    r"(absence|lack)\s+of\s+(efficacy|benefit|effect)",
    r"negative\s+(trial|study|result)",
    r"did\s+not\s+(improve|reduce|prevent)",
    r"ineffective",
    r"(increased|higher)\s+(mortality|risk|harm)",
    r"safety\s+(concerns?|issues?|signals?)",
]

# METHODOLOGICAL - Cites methods, protocols, statistical tools
METHODOLOGICAL_PATTERNS = [
    r"using\s+(the\s+)?(method|approach|technique|protocol)\s+(of|described|from)",
    r"(method|protocol|procedure)\s+(described|outlined|detailed)\s+(in|by)",
    r"statistical\s+(analysis|method|approach)\s+(from|of|described)",
    r"according\s+to\s+(the\s+)?(protocol|method|guideline)",
    r"(adapted|modified)\s+from",
    r"(measured|assessed|evaluated)\s+(as\s+described|using)",
    r"(calculated|computed)\s+(using|according\s+to)",
    r"(randomized|blinded)\s+(as\s+described|per)",
    r"statistical\s+power\s+(calculated|determined)",
    r"sample\s+size\s+(determined|calculated)",
]

# CONTEXTUAL - Background, epidemiology, history
CONTEXTUAL_PATTERNS = [
    r"(first|initially)\s+(described|reported|identified)\s+by",
    r"historically",
    r"traditionally",
    r"originally\s+(described|reported|discovered)",
    r"pioneered\s+by",
    r"(prevalence|incidence|epidemiology)\s+(of|reported)",
    r"(introduction|discovery)\s+of",
    r"(classic|seminal)\s+(study|work|paper)",
    r"(reviewed?|overview)\s+(in|by)",
    r"background\s+on",
    r"(well|previously)\s+established",
    r"(known|recognized)\s+(that|to|as)",
]

# META_ANALYSIS - Systematic reviews citing primary studies
META_ANALYSIS_PATTERNS = [
    r"meta-analysis\s+(of|including|combining)",
    r"systematic\s+review\s+(of|including)",
    r"pooled\s+(analysis|data|results?)",
    r"cochrane\s+review",
    r"(combined|aggregated)\s+(results?|data|studies)",
    r"(synthesized?|synthesis)\s+(of|from)",
    r"included\s+in\s+(the\s+)?meta-analysis",
    r"forest\s+plot",
    r"(heterogeneity|I2)\s+(analysis|statistic)",
]

# Study design patterns for weighting
STUDY_DESIGN_PATTERNS = {
    'meta_analysis': (3.0, [
        r"meta-analysis",
        r"systematic\s+review",
        r"cochrane\s+review",
    ]),
    'rct': (2.0, [
        r"randomized\s+controlled\s+trial",
        r"randomized\s+trial",
        r"double.?blind",
        r"placebo.?controlled",
        r"RCT",
    ]),
    'observational': (1.0, [
        r"cohort\s+study",
        r"case.?control",
        r"observational\s+study",
        r"prospective\s+study",
        r"retrospective\s+study",
    ]),
    'case_report': (0.5, [
        r"case\s+report",
        r"case\s+series",
        r"single\s+case",
    ]),
}


def detect_study_design(text: str) -> Tuple[str, float]:
    """
    Detect study design from text and return design type and weight.

    Args:
        text: Text to analyze (typically publication types or abstract)

    Returns:
        Tuple of (design_type, weight)
    """
    text_lower = text.lower()

    for design_type, (weight, patterns) in STUDY_DESIGN_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return design_type, weight

    # Default: unknown/other study type
    return 'other', 1.0


def classify_citation_context(context: str, publication_types: List[str] = None) -> ClassificationResult:
    """
    Classify a citation based on its context.

    Args:
        context: The text surrounding the citation (sentence or paragraph)
        publication_types: List of publication types from PubMed metadata

    Returns:
        ClassificationResult with classification, confidence, weight, and reasoning
    """
    context_lower = context.lower()
    matched_patterns = []
    scores = {
        'SUPPORTING': 0,
        'CONTRASTING': 0,
        'REFUTING': 0,
        'METHODOLOGICAL': 0,
        'CONTEXTUAL': 0,
        'META_ANALYSIS': 0,
    }

    # Check each pattern type
    pattern_groups = [
        ('SUPPORTING', SUPPORTING_PATTERNS),
        ('CONTRASTING', CONTRASTING_PATTERNS),
        ('REFUTING', REFUTING_PATTERNS),
        ('METHODOLOGICAL', METHODOLOGICAL_PATTERNS),
        ('CONTEXTUAL', CONTEXTUAL_PATTERNS),
        ('META_ANALYSIS', META_ANALYSIS_PATTERNS),
    ]

    for classification, patterns in pattern_groups:
        for pattern in patterns:
            matches = re.findall(pattern, context_lower, re.IGNORECASE)
            if matches:
                scores[classification] += len(matches)
                matched_patterns.append(f"{classification}:{pattern}")

    # Determine study weight from publication types
    study_weight = 1.0
    study_design = 'other'
    if publication_types:
        pub_types_str = ' '.join(publication_types)
        study_design, study_weight = detect_study_design(pub_types_str)

    # Also check context for study design mentions
    context_design, context_weight = detect_study_design(context)
    if context_weight > study_weight:
        study_weight = context_weight
        study_design = context_design

    # Determine classification based on scores
    if all(score == 0 for score in scores.values()):
        # No patterns matched - default to CONTEXTUAL with low confidence
        return ClassificationResult(
            classification='CONTEXTUAL',
            confidence=0.3,
            study_weight=study_weight,
            matched_patterns=[],
            reasoning=f"No clear citation pattern detected. Default to CONTEXTUAL. "
                     f"Study design: {study_design} (weight: {study_weight})"
        )

    # Find top scoring classification
    max_score = max(scores.values())
    top_classifications = [c for c, s in scores.items() if s == max_score]

    # If tie, use priority order: REFUTING > META_ANALYSIS > SUPPORTING > CONTRASTING > METHODOLOGICAL > CONTEXTUAL
    priority = ['REFUTING', 'META_ANALYSIS', 'SUPPORTING', 'CONTRASTING', 'METHODOLOGICAL', 'CONTEXTUAL']
    classification = next((c for c in priority if c in top_classifications), top_classifications[0])

    # Calculate confidence based on pattern strength
    total_matches = sum(scores.values())
    classification_matches = scores[classification]

    # Confidence = (matches for this class / total matches) * strength factor
    base_confidence = classification_matches / total_matches if total_matches > 0 else 0.5

    # Boost confidence if multiple patterns matched for same classification
    if classification_matches >= 3:
        base_confidence = min(0.95, base_confidence + 0.2)
    elif classification_matches >= 2:
        base_confidence = min(0.85, base_confidence + 0.1)

    # Lower confidence if competing classifications also scored high
    competing_scores = [s for c, s in scores.items() if c != classification and s > 0]
    if competing_scores:
        max_competing = max(competing_scores)
        if max_competing >= classification_matches:
            base_confidence *= 0.7

    confidence = min(0.99, max(0.3, base_confidence))

    # Build reasoning
    reasoning = f"Classified as {classification} based on {classification_matches} pattern match(es). "
    if study_design != 'other':
        reasoning += f"Study design: {study_design} (weight: {study_weight}). "
    if competing_scores:
        reasoning += f"Note: Competing classifications also detected."

    return ClassificationResult(
        classification=classification,
        confidence=confidence,
        study_weight=study_weight,
        matched_patterns=matched_patterns,
        reasoning=reasoning
    )


def aggregate_consensus(classifications: List[ClassificationResult]) -> Dict[str, Any]:
    """
    Aggregate multiple citation classifications to determine consensus.

    Args:
        classifications: List of classification results

    Returns:
        Dictionary with consensus score and statistics
    """
    if not classifications:
        return {
            'consensus_score': 0.0,
            'total_citations': 0,
            'total_weight': 0.0,
            'breakdown': {}
        }

    # Calculate weighted scores
    supporting = 0.0
    contrasting = 0.0
    refuting = 0.0
    meta_analysis = 0.0
    total_weight = 0.0

    breakdown = {
        'SUPPORTING': {'count': 0, 'weight': 0.0},
        'CONTRASTING': {'count': 0, 'weight': 0.0},
        'REFUTING': {'count': 0, 'weight': 0.0},
        'METHODOLOGICAL': {'count': 0, 'weight': 0.0},
        'CONTEXTUAL': {'count': 0, 'weight': 0.0},
        'META_ANALYSIS': {'count': 0, 'weight': 0.0},
    }

    for result in classifications:
        weight = result.study_weight * result.confidence
        breakdown[result.classification]['count'] += 1
        breakdown[result.classification]['weight'] += weight
        total_weight += weight

        if result.classification == 'SUPPORTING':
            supporting += weight
        elif result.classification == 'CONTRASTING':
            contrasting += weight
        elif result.classification == 'REFUTING':
            refuting += weight
        elif result.classification == 'META_ANALYSIS':
            meta_analysis += weight

    # Consensus formula: (SUPPORTING + META - CONTRASTING - 2*REFUTING) / total
    if total_weight > 0:
        consensus = (supporting + meta_analysis - contrasting - 2 * refuting) / total_weight
    else:
        consensus = 0.0

    # Clamp to [-1, 1]
    consensus = max(-1.0, min(1.0, consensus))

    return {
        'consensus_score': consensus,
        'total_citations': len(classifications),
        'total_weight': total_weight,
        'breakdown': breakdown,
        'interpretation': interpret_consensus(consensus)
    }


def interpret_consensus(score: float) -> str:
    """
    Interpret consensus score into human-readable categories.

    Args:
        score: Consensus score from -1 to 1

    Returns:
        String interpretation
    """
    if score >= 0.7:
        return "Strong positive consensus"
    elif score >= 0.4:
        return "Moderate positive consensus"
    elif score >= 0.1:
        return "Weak positive consensus"
    elif score >= -0.1:
        return "No clear consensus (mixed evidence)"
    elif score >= -0.4:
        return "Weak negative consensus"
    elif score >= -0.7:
        return "Moderate negative consensus"
    else:
        return "Strong negative consensus (likely refuted)"


# ==================== CLI for Testing ====================

def main():
    """Test the classifier with example contexts."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Classify medical citation contexts')
    parser.add_argument('--context', required=True, help='Citation context text')
    parser.add_argument('--publication-types', nargs='*', help='Publication types')
    parser.add_argument('--format', choices=['json', 'summary'], default='summary')

    args = parser.parse_args()

    result = classify_citation_context(args.context, args.publication_types or [])

    if args.format == 'json':
        print(json.dumps({
            'classification': result.classification,
            'confidence': result.confidence,
            'study_weight': result.study_weight,
            'matched_patterns': result.matched_patterns,
            'reasoning': result.reasoning
        }, indent=2))
    else:
        print(f"Classification: {result.classification}")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Study Weight: {result.study_weight:.2f}")
        print(f"Matched Patterns: {len(result.matched_patterns)}")
        print(f"Reasoning: {result.reasoning}")


if __name__ == '__main__':
    main()
