# med-literature

Search medical literature using PubMed, analyze citation networks with recursive subagents, and determine clinical consensus on research questions.

## When to Use This Skill

Use this skill when the user asks about:
- Medical research questions (efficacy, safety, mechanisms)
- Clinical consensus on treatments or interventions
- Evidence quality for medical claims
- Citation analysis of medical papers
- Ruled-out hypotheses or debunked theories in medicine

## What This Skill Does

1. **Searches PubMed**: Queries medical literature using NCBI Entrez APIs
2. **Analyzes Citations**: Maps citation networks to understand how papers reference each other
3. **Classifies Relationships**: Determines if citations are SUPPORTING, REFUTING, CONTRASTING, etc.
4. **Weights Evidence**: Applies study quality weights (meta-analyses > RCTs > observational > case reports)
5. **Calculates Consensus**: Computes weighted consensus scores (-1 to 1) for research questions
6. **Tracks Hypotheses**: Identifies ruled-out theories based on refuting evidence
7. **Manages Sessions**: Organizes research into database-backed sessions

## Examples

- "Is there consensus that metformin reduces cardiovascular mortality?"
- "What evidence supports vitamin D supplementation?"
- "Has hormone replacement therapy for cardiovascular protection been ruled out?"
- "Analyze the citation network for PMID:12345678"

## Tools Provided

- `pubmed_search.py`: Search and retrieve from PubMed
- `litdb.py`: Database management (papers, citations, sessions, hypotheses)
- `classify_citations.py`: Citation relationship classification
- `citation_analysis.py`: Network analysis
- `trial_lookup.py`: ClinicalTrials.gov integration

## Architecture

Uses recursive subagents to traverse citation networks depth-first, classifying each citation relationship based on context patterns and study quality.

See `subagent-instructions.md` for detailed workflow.
