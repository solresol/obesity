#!/usr/bin/env python3
"""
Citation Network Analysis Tool

Extracts and analyzes citation networks for medical papers.
"""

import argparse
import json
import sys
from typing import Dict, List, Any, Set
from pathlib import Path

# Import our modules
sys.path.insert(0, str(Path(__file__).parent))
from pubmed_search import get_citations, get_references, fetch_paper_details
from classify_citations import classify_citation_context, aggregate_consensus


def build_citation_network(pmid: str, depth: int = 1, max_per_level: int = 20) -> Dict[str, Any]:
    """
    Build a citation network starting from a seed paper.

    Args:
        pmid: Starting PMID
        depth: How many levels deep to traverse
        max_per_level: Maximum papers to analyze per level

    Returns:
        Network dictionary with nodes and edges
    """
    network = {
        'seed_pmid': pmid,
        'nodes': {},  # PMID -> paper metadata
        'edges': [],  # Citation relationships
        'depth': depth
    }

    visited = set()
    to_process = [(pmid, 0)]  # (PMID, current_depth)

    while to_process:
        current_pmid, current_depth = to_process.pop(0)

        if current_pmid in visited:
            continue

        visited.add(current_pmid)

        # Fetch paper details
        print(f"Fetching PMID:{current_pmid} (depth {current_depth})...", file=sys.stderr)
        paper = fetch_paper_details(current_pmid)

        if not paper:
            continue

        network['nodes'][current_pmid] = {
            **paper,
            'depth': current_depth
        }

        # If not at max depth, get citing papers
        if current_depth < depth:
            citing_pmids = get_citations(current_pmid)
            print(f"  Found {len(citing_pmids)} citing papers", file=sys.stderr)

            # Limit to max_per_level
            for citing_pmid in citing_pmids[:max_per_level]:
                if citing_pmid not in visited:
                    # Add edge
                    network['edges'].append({
                        'citing': citing_pmid,
                        'cited': current_pmid,
                        'depth': current_depth + 1
                    })
                    # Queue for processing
                    to_process.append((citing_pmid, current_depth + 1))

    return network


def analyze_citation_network(network: Dict[str, Any], classify: bool = False) -> Dict[str, Any]:
    """
    Analyze a citation network to extract statistics and patterns.

    Args:
        network: Network dictionary from build_citation_network
        classify: Whether to classify citation relationships (slow)

    Returns:
        Analysis results
    """
    analysis = {
        'total_papers': len(network['nodes']),
        'total_citations': len(network['edges']),
        'papers_by_depth': {},
        'papers_by_year': {},
        'papers_by_type': {},
        'most_cited': [],
        'classification_summary': None
    }

    # Papers by depth
    for pmid, node in network['nodes'].items():
        depth = node['depth']
        analysis['papers_by_depth'][depth] = analysis['papers_by_depth'].get(depth, 0) + 1

    # Papers by year
    for pmid, node in network['nodes'].items():
        year = node.get('year', 'Unknown')
        if year:
            analysis['papers_by_year'][year] = analysis['papers_by_year'].get(year, 0) + 1

    # Papers by publication type
    for pmid, node in network['nodes'].items():
        pub_types = node.get('publication_types', [])
        for pt in pub_types:
            analysis['papers_by_type'][pt] = analysis['papers_by_type'].get(pt, 0) + 1

    # Most cited papers (in this network)
    citation_counts = {}
    for edge in network['edges']:
        cited = edge['cited']
        citation_counts[cited] = citation_counts.get(cited, 0) + 1

    most_cited = sorted(citation_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    analysis['most_cited'] = [
        {
            'pmid': pmid,
            'count': count,
            'title': network['nodes'][pmid]['title'],
            'year': network['nodes'][pmid].get('year')
        }
        for pmid, count in most_cited
    ]

    # Classification analysis (if requested)
    if classify:
        print("Classifying citations (this may take a while)...", file=sys.stderr)
        classifications = []

        for edge in network['edges']:
            citing_pmid = edge['citing']
            cited_pmid = edge['cited']

            citing_paper = network['nodes'].get(citing_pmid)
            cited_paper = network['nodes'].get(cited_pmid)

            if not citing_paper or not cited_paper:
                continue

            # Use citing paper's abstract as context
            context = citing_paper.get('abstract', citing_paper.get('title', ''))
            pub_types = citing_paper.get('publication_types', [])

            result = classify_citation_context(context, pub_types)
            classifications.append(result)

            edge['classification'] = result.classification
            edge['confidence'] = result.confidence
            edge['study_weight'] = result.study_weight

        # Aggregate consensus
        if classifications:
            analysis['classification_summary'] = aggregate_consensus(classifications)

    return analysis


def format_network_summary(network: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """Format network analysis as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append("CITATION NETWORK ANALYSIS")
    lines.append("=" * 80)
    lines.append(f"\nSeed Paper: PMID:{network['seed_pmid']}")

    seed_paper = network['nodes'][network['seed_pmid']]
    lines.append(f"Title: {seed_paper['title']}")
    lines.append(f"Year: {seed_paper.get('year', 'Unknown')}")

    lines.append(f"\n--- Network Statistics ---")
    lines.append(f"Total papers: {analysis['total_papers']}")
    lines.append(f"Total citations: {analysis['total_citations']}")

    lines.append(f"\nPapers by depth:")
    for depth in sorted(analysis['papers_by_depth'].keys()):
        count = analysis['papers_by_depth'][depth]
        lines.append(f"  Depth {depth}: {count} papers")

    if analysis['papers_by_year']:
        lines.append(f"\nPapers by year (top 10):")
        sorted_years = sorted(analysis['papers_by_year'].items(), key=lambda x: str(x[0]), reverse=True)
        for year, count in sorted_years[:10]:
            lines.append(f"  {year}: {count} papers")

    if analysis['papers_by_type']:
        lines.append(f"\nPublication types:")
        sorted_types = sorted(analysis['papers_by_type'].items(), key=lambda x: x[1], reverse=True)
        for pub_type, count in sorted_types[:10]:
            lines.append(f"  {pub_type}: {count} papers")

    lines.append(f"\n--- Most Cited Papers (in network) ---")
    for i, paper in enumerate(analysis['most_cited'][:5], 1):
        lines.append(f"\n{i}. PMID:{paper['pmid']} ({paper['count']} citations in network)")
        lines.append(f"   {paper['title']}")
        lines.append(f"   Year: {paper['year']}")

    if analysis['classification_summary']:
        cs = analysis['classification_summary']
        lines.append(f"\n--- Classification Summary ---")
        lines.append(f"Consensus Score: {cs['consensus_score']:.3f}")
        lines.append(f"Interpretation: {cs['interpretation']}")
        lines.append(f"Total citations analyzed: {cs['total_citations']}")
        lines.append(f"\nBreakdown:")
        for classification, stats in cs['breakdown'].items():
            if stats['count'] > 0:
                lines.append(f"  {classification}: {stats['count']} "
                           f"(weight: {stats['weight']:.2f})")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Analyze citation networks for medical papers'
    )

    parser.add_argument('pmid', help='Seed PMID to start analysis')
    parser.add_argument('--depth', type=int, default=1,
                       help='Citation depth to traverse (default: 1)')
    parser.add_argument('--max-per-level', type=int, default=20,
                       help='Max papers per level (default: 20)')
    parser.add_argument('--classify', action='store_true',
                       help='Classify citation relationships (slower)')
    parser.add_argument('--format', choices=['json', 'summary'], default='summary',
                       help='Output format')
    parser.add_argument('--output', help='Output file (default: stdout)')

    args = parser.parse_args()

    # Build network
    print(f"Building citation network for PMID:{args.pmid}...", file=sys.stderr)
    network = build_citation_network(args.pmid, args.depth, args.max_per_level)

    print(f"\nAnalyzing network...", file=sys.stderr)
    analysis = analyze_citation_network(network, classify=args.classify)

    # Format output
    if args.format == 'json':
        output = json.dumps({
            'network': network,
            'analysis': analysis
        }, indent=2)
    else:
        output = format_network_summary(network, analysis)

    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"\nWrote output to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == '__main__':
    main()
