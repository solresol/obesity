#!/usr/bin/env python3
"""
PubMed search and retrieval tool.
Searches medical literature using PubMed/NCBI Entrez APIs.
"""

import argparse
import json
import sys
from typing import Dict, List, Optional, Any
from Bio import Entrez
import xml.etree.ElementTree as ET

# Set your email for NCBI (required by their terms of service)
Entrez.email = "medicus@example.com"
Entrez.tool = "medicus"

def search_pubmed(query: str, max_results: int = 20, year_from: Optional[int] = None,
                 year_to: Optional[int] = None) -> List[str]:
    """
    Search PubMed and return list of PMIDs.

    Args:
        query: Search query (can include MeSH terms, author names, etc.)
        max_results: Maximum number of results to return
        year_from: Filter results from this year onwards
        year_to: Filter results up to this year

    Returns:
        List of PMIDs as strings
    """
    # Build date filter if years specified
    date_filter = ""
    if year_from or year_to:
        from_year = year_from or 1800
        to_year = year_to or 2100
        date_filter = f" AND {from_year}:{to_year}[PDAT]"

    full_query = query + date_filter

    try:
        handle = Entrez.esearch(
            db='pubmed',
            term=full_query,
            retmax=max_results,
            sort='relevance'
        )
        record = Entrez.read(handle)
        handle.close()
        return record['IdList']
    except Exception as e:
        print(f"Error searching PubMed: {e}", file=sys.stderr)
        return []


def fetch_paper_details(pmid: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed metadata for a single paper.

    Args:
        pmid: PubMed ID

    Returns:
        Dictionary with paper metadata or None if error
    """
    try:
        handle = Entrez.efetch(
            db='pubmed',
            id=pmid,
            retmode='xml'
        )
        xml_data = handle.read()
        handle.close()

        # Parse XML
        root = ET.fromstring(xml_data)
        article = root.find('.//PubmedArticle')

        if article is None:
            return None

        # Extract basic metadata
        medline_citation = article.find('.//MedlineCitation')
        article_elem = medline_citation.find('.//Article')

        # Title
        title_elem = article_elem.find('.//ArticleTitle')
        title = ''.join(title_elem.itertext()) if title_elem is not None else ""

        # Authors
        authors = []
        author_list = article_elem.find('.//AuthorList')
        if author_list is not None:
            for author in author_list.findall('.//Author'):
                last_name = author.find('.//LastName')
                fore_name = author.find('.//ForeName')
                if last_name is not None:
                    name = last_name.text
                    if fore_name is not None:
                        name = f"{fore_name.text} {name}"
                    authors.append(name)

        # Journal info
        journal = article_elem.find('.//Journal')
        journal_title = ""
        year = ""
        volume = ""
        issue = ""

        if journal is not None:
            journal_title_elem = journal.find('.//Title')
            journal_title = journal_title_elem.text if journal_title_elem is not None else ""

            pub_date = journal.find('.//PubDate')
            if pub_date is not None:
                year_elem = pub_date.find('.//Year')
                year = year_elem.text if year_elem is not None else ""

            issue_elem = journal.find('.//JournalIssue')
            if issue_elem is not None:
                volume_elem = issue_elem.find('.//Volume')
                volume = volume_elem.text if volume_elem is not None else ""
                issue_num = issue_elem.find('.//Issue')
                issue = issue_num.text if issue_num is not None else ""

        # Pages
        pagination = article_elem.find('.//Pagination/MedlinePgn')
        pages = pagination.text if pagination is not None else ""

        # Abstract
        abstract_elem = article_elem.find('.//Abstract/AbstractText')
        abstract = ''.join(abstract_elem.itertext()) if abstract_elem is not None else ""

        # MeSH terms
        mesh_terms = []
        mesh_list = medline_citation.find('.//MeshHeadingList')
        if mesh_list is not None:
            for mesh in mesh_list.findall('.//MeshHeading'):
                descriptor = mesh.find('.//DescriptorName')
                if descriptor is not None:
                    mesh_terms.append(descriptor.text)

        # Publication types
        pub_types = []
        pub_type_list = article_elem.find('.//PublicationTypeList')
        if pub_type_list is not None:
            for pub_type in pub_type_list.findall('.//PublicationType'):
                if pub_type.text:
                    pub_types.append(pub_type.text)

        # DOI and PMCID
        doi = ""
        pmcid = ""
        article_id_list = article.find('.//PubmedData/ArticleIdList')
        if article_id_list is not None:
            for article_id in article_id_list.findall('.//ArticleId'):
                id_type = article_id.get('IdType')
                if id_type == 'doi':
                    doi = article_id.text or ""
                elif id_type == 'pmc':
                    pmcid = article_id.text or ""

        return {
            'pmid': pmid,
            'title': title,
            'authors': authors,
            'journal': journal_title,
            'year': year,
            'volume': volume,
            'issue': issue,
            'pages': pages,
            'abstract': abstract,
            'mesh_terms': mesh_terms,
            'publication_types': pub_types,
            'doi': doi,
            'pmcid': pmcid
        }

    except Exception as e:
        print(f"Error fetching PMID {pmid}: {e}", file=sys.stderr)
        return None


def get_citations(pmid: str) -> List[str]:
    """
    Get PMIDs of papers that cite this paper.

    Args:
        pmid: PubMed ID

    Returns:
        List of PMIDs that cite this paper
    """
    try:
        handle = Entrez.elink(
            dbfrom='pubmed',
            id=pmid,
            linkname='pubmed_pubmed_citedin'
        )
        record = Entrez.read(handle)
        handle.close()

        citing_pmids = []
        if record and len(record) > 0:
            link_set = record[0]
            if 'LinkSetDb' in link_set and len(link_set['LinkSetDb']) > 0:
                links = link_set['LinkSetDb'][0]
                if 'Link' in links:
                    citing_pmids = [link['Id'] for link in links['Link']]

        return citing_pmids

    except Exception as e:
        print(f"Error getting citations for PMID {pmid}: {e}", file=sys.stderr)
        return []


def get_references(pmid: str) -> List[str]:
    """
    Get PMIDs of papers referenced by this paper.

    Args:
        pmid: PubMed ID

    Returns:
        List of PMIDs referenced by this paper
    """
    try:
        handle = Entrez.elink(
            dbfrom='pubmed',
            id=pmid,
            linkname='pubmed_pubmed_refs'
        )
        record = Entrez.read(handle)
        handle.close()

        ref_pmids = []
        if record and len(record) > 0:
            link_set = record[0]
            if 'LinkSetDb' in link_set and len(link_set['LinkSetDb']) > 0:
                links = link_set['LinkSetDb'][0]
                if 'Link' in links:
                    ref_pmids = [link['Id'] for link in links['Link']]

        return ref_pmids

    except Exception as e:
        print(f"Error getting references for PMID {pmid}: {e}", file=sys.stderr)
        return []


def format_summary(paper: Dict[str, Any]) -> str:
    """Format paper metadata as human-readable summary."""
    authors_str = ", ".join(paper['authors'][:3])
    if len(paper['authors']) > 3:
        authors_str += f" et al. ({len(paper['authors'])} authors)"

    citation = f"{authors_str}\n"
    citation += f"{paper['title']}\n"
    citation += f"{paper['journal']}"

    if paper['year']:
        citation += f" ({paper['year']})"
    if paper['volume']:
        citation += f" {paper['volume']}"
    if paper['issue']:
        citation += f"({paper['issue']})"
    if paper['pages']:
        citation += f": {paper['pages']}"

    citation += f"\nPMID: {paper['pmid']}"

    if paper['doi']:
        citation += f" | DOI: {paper['doi']}"
    if paper['pmcid']:
        citation += f" | PMCID: {paper['pmcid']}"

    if paper['publication_types']:
        citation += f"\nPublication types: {', '.join(paper['publication_types'])}"

    if paper['mesh_terms']:
        citation += f"\nMeSH terms: {', '.join(paper['mesh_terms'][:10])}"
        if len(paper['mesh_terms']) > 10:
            citation += f" ... ({len(paper['mesh_terms'])} total)"

    if paper['abstract']:
        abstract_preview = paper['abstract'][:300]
        if len(paper['abstract']) > 300:
            abstract_preview += "..."
        citation += f"\n\nAbstract: {abstract_preview}"

    return citation


def main():
    parser = argparse.ArgumentParser(
        description='Search and retrieve medical literature from PubMed'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search PubMed')
    search_parser.add_argument('--query', required=True, help='Search query')
    search_parser.add_argument('--max-results', type=int, default=20,
                              help='Maximum number of results (default: 20)')
    search_parser.add_argument('--year-from', type=int, help='Filter from this year')
    search_parser.add_argument('--year-to', type=int, help='Filter to this year')
    search_parser.add_argument('--format', choices=['json', 'summary', 'pmids'],
                              default='summary', help='Output format')

    # Citations command
    cite_parser = subparsers.add_parser('citations', help='Get papers citing a given PMID')
    cite_parser.add_argument('pmid', help='PubMed ID')
    cite_parser.add_argument('--format', choices=['json', 'summary', 'pmids'],
                            default='pmids', help='Output format')
    cite_parser.add_argument('--max-results', type=int, default=50,
                            help='Maximum number of citations to return')

    # References command
    ref_parser = subparsers.add_parser('references', help='Get papers referenced by a given PMID')
    ref_parser.add_argument('pmid', help='PubMed ID')
    ref_parser.add_argument('--format', choices=['json', 'summary', 'pmids'],
                           default='pmids', help='Output format')

    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch details for a specific PMID')
    fetch_parser.add_argument('pmid', help='PubMed ID')
    fetch_parser.add_argument('--format', choices=['json', 'summary'],
                             default='summary', help='Output format')

    args = parser.parse_args()

    if args.command == 'search':
        pmids = search_pubmed(
            args.query,
            max_results=args.max_results,
            year_from=args.year_from,
            year_to=args.year_to
        )

        if args.format == 'pmids':
            for pmid in pmids:
                print(pmid)
        elif args.format == 'json':
            papers = []
            for pmid in pmids:
                paper = fetch_paper_details(pmid)
                if paper:
                    papers.append(paper)
            print(json.dumps(papers, indent=2))
        else:  # summary
            for i, pmid in enumerate(pmids, 1):
                paper = fetch_paper_details(pmid)
                if paper:
                    print(f"\n{'='*80}")
                    print(f"Result {i}/{len(pmids)}")
                    print('='*80)
                    print(format_summary(paper))

    elif args.command == 'citations':
        pmids = get_citations(args.pmid)[:args.max_results]

        if args.format == 'pmids':
            for pmid in pmids:
                print(pmid)
        elif args.format == 'json':
            papers = []
            for pmid in pmids:
                paper = fetch_paper_details(pmid)
                if paper:
                    papers.append(paper)
            print(json.dumps(papers, indent=2))
        else:  # summary
            print(f"Papers citing PMID {args.pmid}: {len(pmids)} found")
            for i, pmid in enumerate(pmids[:10], 1):
                paper = fetch_paper_details(pmid)
                if paper:
                    print(f"\n{i}. {paper['title']}")
                    print(f"   PMID: {pmid} | {paper['year']}")

    elif args.command == 'references':
        pmids = get_references(args.pmid)

        if args.format == 'pmids':
            for pmid in pmids:
                print(pmid)
        elif args.format == 'json':
            papers = []
            for pmid in pmids:
                paper = fetch_paper_details(pmid)
                if paper:
                    papers.append(paper)
            print(json.dumps(papers, indent=2))
        else:  # summary
            print(f"Papers referenced by PMID {args.pmid}: {len(pmids)} found")
            for i, pmid in enumerate(pmids[:10], 1):
                paper = fetch_paper_details(pmid)
                if paper:
                    print(f"\n{i}. {paper['title']}")
                    print(f"   PMID: {pmid} | {paper['year']}")

    elif args.command == 'fetch':
        paper = fetch_paper_details(args.pmid)
        if paper:
            if args.format == 'json':
                print(json.dumps(paper, indent=2))
            else:  # summary
                print(format_summary(paper))
        else:
            print(f"Could not fetch PMID {args.pmid}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
