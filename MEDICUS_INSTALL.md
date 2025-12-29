# Medicus Installation Guide

## Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended) or pip
- Internet access for PubMed API

## Installation Steps

### 1. Install uv (Recommended)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or on macOS with Homebrew:

```bash
brew install uv
```

### 2. Clone the Repository

```bash
git clone <repository-url> medicus
cd medicus
```

### 3. Install Dependencies

Using uv (recommended):

```bash
uv sync
```

Using pip (alternative):

```bash
pip install -e .
```

### 4. Verify Installation

```bash
# Test the classifier
uv run .claude/skills/med-literature/scripts/classify_citations.py \
  --context "demonstrated efficacy in randomized trial" \
  --format summary

# Test the database
uv run .claude/skills/med-literature/scripts/litdb.py stats

# Test PubMed search (requires internet)
uv run .claude/skills/med-literature/scripts/pubmed_search.py search \
  --query "diabetes" \
  --max-results 3 \
  --format pmids
```

## Database Location

The SQLite database is automatically created at:
```
~/.med-literature/citations.db
```

This location is outside the repository to keep research data separate from code.

## Running Scripts

All scripts are in `.claude/skills/med-literature/scripts/`:

```bash
# Prefix all script paths with this
uv run .claude/skills/med-literature/scripts/

# Examples:
uv run .claude/skills/med-literature/scripts/pubmed_search.py search --query "aspirin"
uv run .claude/skills/med-literature/scripts/litdb.py papers list
uv run .claude/skills/med-literature/scripts/classify_citations.py --context "..."
```

## Environment Variables (Optional)

You can customize the database location:

```bash
export MEDICUS_DB_PATH=/path/to/custom/location.db
```

## Troubleshooting

### PubMed API Access

If you get API errors:
- Check your internet connection
- Verify you're not behind a restrictive firewall
- NCBI rate limits to 3 requests/second without an API key
- For higher rates, register for an NCBI API key

### Import Errors

If you get import errors:
```bash
# Reinstall dependencies
uv sync --reinstall
```

### Database Locked

If database is locked:
```bash
# Close all connections to the database
# Or delete and recreate:
rm ~/.med-literature/citations.db
uv run .claude/skills/med-literature/scripts/litdb.py stats  # Recreates DB
```

## Next Steps

See [README.md](README.md) for usage instructions and [examples.md](.claude/skills/med-literature/examples.md) for comprehensive examples.

## Support

For issues and questions:
- Check [examples.md](.claude/skills/med-literature/examples.md)
- Review [subagent-instructions.md](.claude/skills/med-literature/subagent-instructions.md)
- Open an issue on GitHub

## Development Setup

For contributing:

```bash
# Install dev dependencies (when added)
uv sync --all-extras

# Run tests (when added)
pytest

# Format code
black .

# Type check
mypy .
```
