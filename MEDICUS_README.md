# Medicus - Medical Literature Analysis System

A comprehensive tool for analyzing medical literature citation networks using PubMed, with recursive subagent architecture for determining scientific consensus on clinical questions.

## Overview

Medicus helps answer questions like:
- **"Is there consensus that aspirin reduces cardiovascular events?"**
- **"What evidence supports vitamin D supplementation?"**
- **"Has hormone replacement therapy been ruled out for cardioprotection?"**

By analyzing citation networks, classifying relationships (SUPPORTING, REFUTING, etc.), and weighting by study quality (meta-analyses > RCTs > observational studies), Medicus calculates a **consensus score** from -1 (strong negative) to +1 (strong positive).

## Features

✅ **PubMed Integration**: Search and retrieve medical literature via NCBI Entrez APIs
✅ **Citation Network Analysis**: Map how papers cite each other
✅ **Intelligent Classification**: Pattern-based classification (SUPPORTING, REFUTING, CONTRASTING, etc.)
✅ **Study Quality Weighting**: Evidence hierarchy (meta-analysis=3.0x, RCT=2.0x, observational=1.0x)
✅ **Hypothesis Tracking**: Identify ruled-out medical theories
✅ **Clinical Trials Integration**: Link to ClinicalTrials.gov data
✅ **Session Management**: Organize research into database-backed sessions
✅ **Recursive Subagents**: Depth-limited citation tree traversal

## Architecture

```
medicus/
├── .claude/skills/med-literature/
│   ├── scripts/
│   │   ├── pubmed_search.py       # PubMed API interface
│   │   ├── litdb.py               # Database management CLI
│   │   ├── classify_citations.py  # Citation classifier
│   │   ├── citation_analysis.py   # Network analysis
│   │   └── trial_lookup.py        # ClinicalTrials.gov API
│   ├── subagent-instructions.md   # Recursive analysis workflow
│   ├── examples.md                # Usage examples
│   └── SKILL.md                   # Claude Code skill metadata
├── pyproject.toml                 # Dependencies (uv)
├── CLAUDE.md                      # Project instructions
└── README.md                      # This file
```

Database: `~/.med-literature/citations.db` (SQLite)

## Installation

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone <repo-url> medicus
cd medicus

# Install dependencies (uv handles this automatically)
uv sync
```

## Quick Start

### 1. Search PubMed

```bash
uv run .claude/skills/med-literature/scripts/pubmed_search.py search \
  --query "aspirin cardiovascular primary prevention" \
  --max-results 10 \
  --format summary
```

### 2. Classify a Citation

```bash
uv run .claude/skills/med-literature/scripts/classify_citations.py \
  --context "Smith et al. demonstrated significant efficacy in reducing mortality" \
  --publication-types "Randomized Controlled Trial"
```

### 3. Create a Research Session

```bash
# Create session
SESSION_ID=$(uv run .claude/skills/med-literature/scripts/litdb.py session create \
  --question "Does aspirin reduce cardiovascular events?" \
  --seed-pmid 12345678 \
  --depth-limit 2)

# Add papers and citations (see examples.md)
```

### 4. Analyze Citation Network

```bash
uv run .claude/skills/med-literature/scripts/citation_analysis.py 12345678 \
  --depth 2 \
  --classify \
  --format summary
```

### 5. View Database Statistics

```bash
uv run .claude/skills/med-literature/scripts/litdb.py stats
```

## Database Schema

### Papers
- PMID (primary key)
- Title, authors, journal, year
- Abstract, DOI, PMCID
- MeSH terms, publication types
- Study design (RCT, observational, etc.)

### Citations
- Citing PMID → Cited PMID
- Classification (SUPPORTING, REFUTING, etc.)
- Confidence (0-1)
- Study weight (based on design)
- Context and reasoning

### Sessions
- Research question
- Seed papers
- Depth limit
- Consensus score
- Status (active, completed)

### Hypotheses
- Name and description
- Status (ACTIVE, RULED_OUT, SUPPORTED)
- Ruling evidence
- Confidence

### Clinical Trials
- NCT ID
- Status, phase, enrollment
- Conditions, interventions
- Primary outcome
- Linked PMIDs

### Outcomes
- Paper PMID
- Outcome type (mortality, morbidity, etc.)
- Measure and results
- Statistical significance

## Citation Classifications

| Type | Description | Example |
|------|-------------|---------|
| **SUPPORTING** | Confirms findings, shows benefit | "demonstrated efficacy", "reduced mortality" |
| **CONTRASTING** | Alternative interpretations | "however, our results differ", "inconsistent with" |
| **REFUTING** | Contradicts, shows no benefit | "failed to demonstrate", "no significant difference" |
| **METHODOLOGICAL** | References methods/protocols | "using method described in", "protocol from" |
| **CONTEXTUAL** | Background, history | "first described by", "pioneered by" |
| **META_ANALYSIS** | Systematic review/meta-analysis | "meta-analysis including", "pooled analysis" |

## Consensus Scoring

Formula: `(SUPPORTING + META_ANALYSIS - CONTRASTING - 2×REFUTING) / total_weight`

Interpretation:
- **+0.7 to +1.0**: Strong positive consensus
- **+0.4 to +0.7**: Moderate positive consensus
- **+0.1 to +0.4**: Weak positive consensus
- **-0.1 to +0.1**: No clear consensus (mixed evidence)
- **-0.4 to -0.1**: Weak negative consensus
- **-0.7 to -0.4**: Moderate negative consensus
- **-1.0 to -0.7**: Strong negative consensus (likely refuted)

## Study Quality Weights

- **Meta-analysis / Systematic review**: 3.0x
- **Randomized Controlled Trial (RCT)**: 2.0x
- **Observational study**: 1.0x
- **Case report / case series**: 0.5x

## Usage Examples

See [examples.md](.claude/skills/med-literature/examples.md) for comprehensive examples including:
1. Treatment efficacy analysis
2. Ruled-out hypothesis tracking
3. Active debate / mixed evidence
4. Citation network visualization
5. Clinical trial integration
6. Database queries and exports

## Subagent Workflow

For recursive citation analysis, see [subagent-instructions.md](.claude/skills/med-literature/subagent-instructions.md).

Basic workflow:
1. Fetch seed paper metadata
2. Get citing papers (up to 50)
3. Classify each citation based on context
4. Weight by study design
5. Calculate local consensus
6. Recurse on high-quality citations (if depth < limit)
7. Track ruled-out hypotheses
8. Return summary with consensus score

## CLI Tools

### `pubmed_search.py`
- `search`: Search PubMed
- `fetch`: Get paper details
- `citations`: Get citing papers
- `references`: Get referenced papers

### `litdb.py`
- `papers`: add, get, list
- `citations`: add, summary
- `session`: create, add-paper, complete, list, get
- `hypothesis`: add, list, ruled-out
- `outcome`: add, list
- `export`: Export database
- `stats`: Show statistics

### `classify_citations.py`
- Classify citation context with confidence and study weight

### `citation_analysis.py`
- Build and analyze citation networks

### `trial_lookup.py`
- `search`: Find trials by condition/intervention
- `fetch`: Get trial details

## Development

### Adding New Classification Patterns

Edit `scripts/classify_citations.py` and add patterns to:
- `SUPPORTING_PATTERNS`
- `CONTRASTING_PATTERNS`
- `REFUTING_PATTERNS`
- etc.

### Extending Database Schema

Edit `scripts/litdb.py` and add tables/fields in the `create_schema()` method.

### Testing

```bash
# Test PubMed search
uv run .claude/skills/med-literature/scripts/pubmed_search.py search --query "diabetes" --max-results 5

# Test classification
uv run .claude/skills/med-literature/scripts/classify_citations.py \
  --context "demonstrated efficacy" \
  --format summary

# Test database
uv run .claude/skills/med-literature/scripts/litdb.py stats
```

## Known Limitations

- **API Rate Limits**: NCBI limits to 3 requests/second (no API key)
- **Context Extraction**: Currently uses full abstracts; sentence-level context would be more accurate
- **Pattern-Based Classification**: May miss nuanced relationships
- **English Only**: PubMed is multilingual, but patterns are English-only
- **No Full Text**: Only abstracts available (full text requires additional APIs)

## Future Enhancements

- [ ] Full-text parsing (via PubMed Central)
- [ ] Machine learning classification (beyond regex patterns)
- [ ] Interactive visualization of citation networks
- [ ] Integration with additional databases (Cochrane, Embase)
- [ ] Automated hypothesis generation
- [ ] Conflict of interest detection
- [ ] Retraction tracking

## License

[Specify license]

## Contributing

Contributions welcome! Areas of interest:
- Improved classification patterns
- Additional medical databases
- Visualization tools
- Machine learning models

## Citation

If you use Medicus in research, please cite:
[Citation info]

## Contact

[Contact information]

---

**Medicus**: Mapping medical literature to find scientific consensus.
