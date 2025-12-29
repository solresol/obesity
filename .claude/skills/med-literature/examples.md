# Medicus Usage Examples

Comprehensive examples of how to use the medical literature analysis system.

---

## Example 1: Treatment Efficacy Analysis

**Question**: "Is there consensus that aspirin reduces cardiovascular events in primary prevention?"

### Workflow

```bash
# 1. Search for seed papers
uv run scripts/pubmed_search.py search \
  --query "aspirin primary prevention cardiovascular" \
  --max-results 10 \
  --format summary

# Pick a relevant PMID (e.g., 28459234)

# 2. Create a research session
SESSION_ID=$(uv run scripts/litdb.py session create \
  --question "Does aspirin reduce cardiovascular events in primary prevention?" \
  --seed-pmid 28459234 \
  --depth-limit 2)

echo "Created session: $SESSION_ID"

# 3. Fetch and store the seed paper
uv run scripts/pubmed_search.py fetch 28459234 --format json | \
  jq -r '. | "uv run scripts/litdb.py papers add --pmid \(.pmid) --title \"\(.title)\" --year \(.year) --study-design RCT"' | \
  bash

# Add to session
uv run scripts/litdb.py session add-paper \
  --session-id $SESSION_ID \
  --pmid 28459234 \
  --depth 0 \
  --seed

# 4. Get citing papers
uv run scripts/pubmed_search.py citations 28459234 \
  --format pmids \
  --max-results 50 > citing_pmids.txt

# 5. Classify each citation (loop through)
while read citing_pmid; do
  # Fetch citing paper abstract
  uv run scripts/pubmed_search.py fetch $citing_pmid --format json > temp.json

  # Extract context and classify
  CONTEXT=$(jq -r '.abstract' temp.json)
  PUB_TYPES=$(jq -r '.publication_types | join(" ")' temp.json)

  # Classify
  uv run scripts/classify_citations.py \
    --context "$CONTEXT" \
    --publication-types $PUB_TYPES \
    --format json > classification.json

  # Store citation
  CLASSIFICATION=$(jq -r '.classification' classification.json)
  CONFIDENCE=$(jq -r '.confidence' classification.json)
  WEIGHT=$(jq -r '.study_weight' classification.json)

  uv run scripts/litdb.py citations add \
    --citing $citing_pmid \
    --cited 28459234 \
    --classification $CLASSIFICATION \
    --study-weight $WEIGHT \
    --confidence $CONFIDENCE
done < citing_pmids.txt

# 6. Calculate consensus
uv run scripts/litdb.py citations summary --pmid 28459234

# 7. Complete session
uv run scripts/litdb.py session complete \
  --id $SESSION_ID \
  --summary "Analysis of aspirin in primary prevention shows..." \
  --consensus-score 0.65
```

### Expected Output

Moderate positive consensus (0.5-0.7) with some REFUTING citations from recent trials showing limited benefit in modern populations.

---

## Example 2: Ruled-Out Hypothesis

**Question**: "Is hormone replacement therapy cardioprotective in postmenopausal women?"

### Workflow

```bash
# 1. Search for the key trial that refuted this
uv run scripts/pubmed_search.py search \
  --query "Women's Health Initiative hormone replacement cardiovascular" \
  --format summary

# 2. Analyze the WHI trial (hypothetical PMID: 12117397)
uv run scripts/citation_analysis.py 12117397 \
  --depth 2 \
  --classify \
  --format summary

# 3. Add ruled-out hypothesis
uv run scripts/litdb.py hypothesis add \
  --name "Hormone replacement therapy is cardioprotective" \
  --description "Previously believed HRT would reduce cardiovascular events" \
  --status RULED_OUT \
  --ruling "PMID:12117397 (WHI trial - increased cardiovascular risk)"

# 4. List all ruled-out hypotheses
uv run scripts/litdb.py hypothesis ruled-out
```

### Expected Output

```
Ruled Out Hypotheses (1):
================================================================================

Hormone replacement therapy is cardioprotective
Description: Previously believed HRT would reduce cardiovascular events
Evidence: PMID:12117397 (WHI trial - increased cardiovascular risk)
```

---

## Example 3: Active Debate / Mixed Evidence

**Question**: "Should vitamin D supplementation be routine for adults?"

### Workflow

```bash
# 1. Search recent meta-analyses
uv run scripts/pubmed_search.py search \
  --query "vitamin D supplementation meta-analysis" \
  --year-from 2018 \
  --max-results 5 \
  --format summary

# 2. Create session for mixed evidence
SESSION_ID=$(uv run scripts/litdb.py session create \
  --question "Should vitamin D supplementation be routine?" \
  --depth-limit 1)

# 3. Add multiple seed papers (both positive and negative findings)
for pmid in 29719996 31573634 31486311; do
  uv run scripts/litdb.py session add-paper \
    --session-id $SESSION_ID \
    --pmid $pmid \
    --depth 0 \
    --seed
done

# 4. Analyze citations for all seeds
# (similar classification loop as Example 1)

# 5. Get session summary
uv run scripts/litdb.py session get --id $SESSION_ID
uv run scripts/litdb.py citations summary --session-id $SESSION_ID
```

### Expected Output

Consensus score near 0 (-0.2 to 0.2) indicating "No clear consensus (mixed evidence)".

---

## Example 4: Quick Citation Network Visualization

**Question**: "Show me the citation network for this paper on SGLT2 inhibitors"

### Workflow

```bash
# Analyze citation network with classification
uv run scripts/citation_analysis.py 28459234 \
  --depth 2 \
  --max-per-level 15 \
  --classify \
  --format summary \
  --output sglt2_network.txt

# View results
cat sglt2_network.txt
```

### Expected Output

```
================================================================================
CITATION NETWORK ANALYSIS
================================================================================

Seed Paper: PMID:28459234
Title: SGLT2 inhibitors and cardiovascular outcomes...
Year: 2017

--- Network Statistics ---
Total papers: 127
Total citations: 126

Papers by depth:
  Depth 0: 1 papers
  Depth 1: 15 papers
  Depth 2: 111 papers

--- Classification Summary ---
Consensus Score: 0.721
Interpretation: Strong positive consensus
Total citations analyzed: 126

Breakdown:
  SUPPORTING: 89 (weight: 156.20)
  CONTRASTING: 12 (weight: 15.30)
  REFUTING: 3 (weight: 4.50)
  META_ANALYSIS: 15 (weight: 45.00)
  METHODOLOGICAL: 5 (weight: 5.00)
  CONTEXTUAL: 2 (weight: 2.00)
```

---

## Example 5: Clinical Trial Integration

**Question**: "Find trials on metformin for diabetes and link to publications"

### Workflow

```bash
# 1. Search ClinicalTrials.gov
uv run scripts/trial_lookup.py search \
  --condition "Type 2 Diabetes" \
  --intervention "Metformin" \
  --max-results 10 \
  --format json > metformin_trials.json

# 2. Fetch details for specific trial
uv run scripts/trial_lookup.py fetch NCT00375388 --format summary

# 3. Extract linked PMIDs
jq -r '.[].linked_pmids[]' metformin_trials.json | while read pmid; do
  echo "Analyzing publication PMID:$pmid"
  uv run scripts/pubmed_search.py fetch $pmid --format summary
done
```

---

## Example 6: Database Statistics and Export

### View Database Stats

```bash
uv run scripts/litdb.py stats
```

### Expected Output

```
Database Statistics:
========================================
Papers: 342
Citations: 1,247
Sessions: 8
Hypotheses: 5
Clinical Trials: 12
Outcomes: 89
Seed Papers: 8
Completed Sessions: 6
Ruled Out Hypotheses: 2
```

### Export Everything

```bash
# Export as JSON
uv run scripts/litdb.py export --format json > medicus_db_export.json

# Query specific data
uv run scripts/litdb.py papers list --year 2023 --limit 50
uv run scripts/litdb.py session list --status completed
uv run scripts/litdb.py outcome list --pmid 28459234
```

---

## Example 7: Pattern Testing

Test classification patterns on sample contexts:

```bash
# Supporting
uv run scripts/classify_citations.py \
  --context "Smith et al. demonstrated significant efficacy of aspirin in reducing cardiovascular events" \
  --publication-types "Randomized Controlled Trial"

# Refuting
uv run scripts/classify_citations.py \
  --context "Our trial failed to demonstrate any significant benefit of vitamin E supplementation" \
  --publication-types "Randomized Controlled Trial"

# Meta-analysis
uv run scripts/classify_citations.py \
  --context "This meta-analysis included 15 randomized controlled trials evaluating statin efficacy" \
  --publication-types "Meta-Analysis" "Systematic Review"
```

---

## Tips for Effective Analysis

1. **Start with high-quality seed papers**: RCTs, meta-analyses, landmark studies
2. **Limit depth to 2-3**: Deeper networks become noisy
3. **Use study design filters**: Focus on RCTs for efficacy questions
4. **Check for conflicts of interest**: Industry-funded studies may bias results
5. **Consider publication date**: Recent evidence may supersede older studies
6. **Track ruled-out hypotheses**: Medical knowledge evolves; what was believed is now refuted
7. **Export sessions**: Save your analysis for future reference

---

## Common Research Questions

### Efficacy Questions
- "Does [drug] improve [outcome]?"
- "Is [treatment] effective for [condition]?"
- **Focus on**: SUPPORTING vs REFUTING citations, RCTs, meta-analyses

### Safety Questions
- "Is [drug] safe in [population]?"
- "What are the risks of [intervention]?"
- **Focus on**: Adverse events, REFUTING patterns, observational studies

### Mechanism Questions
- "How does [drug] work?"
- "What is the pathophysiology of [condition]?"
- **Focus on**: CONTEXTUAL, METHODOLOGICAL citations, basic science papers

### Guideline Questions
- "What do guidelines recommend for [condition]?"
- "Is there consensus on [practice]?"
- **Focus on**: Practice guidelines, meta-analyses, consensus statements

---

## Subagent Usage (Advanced)

For automated recursive analysis, spawn subagents following `subagent-instructions.md`:

```python
# Pseudocode for subagent
def analyze_paper(pmid, session_id, depth, depth_limit):
    if depth >= depth_limit:
        return

    # Fetch paper
    paper = fetch_paper_details(pmid)
    store_paper(paper)

    # Get citing papers
    citing_pmids = get_citations(pmid)

    # Classify each citation
    for citing_pmid in citing_pmids[:50]:
        citing_paper = fetch_paper_details(citing_pmid)
        result = classify_citation_context(
            citing_paper['abstract'],
            citing_paper['publication_types']
        )
        store_citation(citing_pmid, pmid, result, session_id)

        # Recurse for high-quality, substantive citations
        if result.classification in ['SUPPORTING', 'REFUTING', 'CONTRASTING']:
            if result.study_weight >= 2.0:  # RCT or better
                analyze_paper(citing_pmid, session_id, depth + 1, depth_limit)

    return calculate_consensus(pmid, session_id)
```

This recursive approach builds a comprehensive citation network automatically.
