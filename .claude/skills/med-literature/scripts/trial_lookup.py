#!/usr/bin/env python3
"""
Clinical Trials Lookup Tool

Query ClinicalTrials.gov for trial information and link to PubMed publications.
"""

import argparse
import json
import sys
import requests
from typing import Dict, List, Any, Optional
from xml.etree import ElementTree as ET


CLINICALTRIALS_API = "https://clinicaltrials.gov/api/query/full_studies"
CLINICALTRIALS_SEARCH_API = "https://clinicaltrials.gov/api/query/study_fields"


def search_trials(condition: Optional[str] = None,
                 intervention: Optional[str] = None,
                 max_results: int = 20) -> List[str]:
    """
    Search ClinicalTrials.gov and return NCT IDs.

    Args:
        condition: Medical condition (e.g., "diabetes")
        intervention: Intervention/treatment (e.g., "metformin")
        max_results: Maximum number of results

    Returns:
        List of NCT IDs
    """
    params = {
        'expr': '',
        'max_rnk': max_results,
        'fmt': 'json'
    }

    # Build search expression
    terms = []
    if condition:
        terms.append(f"AREA[Condition]{condition}")
    if intervention:
        terms.append(f"AREA[Intervention]{intervention}")

    if terms:
        params['expr'] = ' AND '.join(terms)
    else:
        print("Error: Must specify condition or intervention", file=sys.stderr)
        return []

    try:
        response = requests.get(CLINICALTRIALS_SEARCH_API, params=params)
        response.raise_for_status()

        data = response.json()

        nct_ids = []
        if 'StudyFieldsResponse' in data and 'StudyFields' in data['StudyFieldsResponse']:
            for study in data['StudyFieldsResponse']['StudyFields']:
                if 'NCTId' in study:
                    nct_ids.extend(study['NCTId'])

        return nct_ids

    except Exception as e:
        print(f"Error searching ClinicalTrials.gov: {e}", file=sys.stderr)
        return []


def fetch_trial_details(nct_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed information for a clinical trial.

    Args:
        nct_id: NCT ID (e.g., "NCT12345678")

    Returns:
        Dictionary with trial details or None
    """
    params = {
        'expr': nct_id,
        'fmt': 'json'
    }

    try:
        response = requests.get(CLINICALTRIALS_API, params=params)
        response.raise_for_status()

        data = response.json()

        if 'FullStudiesResponse' not in data or 'FullStudies' not in data['FullStudiesResponse']:
            return None

        studies = data['FullStudiesResponse']['FullStudies']
        if not studies:
            return None

        study = studies[0]['Study']

        # Extract protocol section
        protocol = study.get('ProtocolSection', {})
        id_module = protocol.get('IdentificationModule', {})
        status_module = protocol.get('StatusModule', {})
        design_module = protocol.get('DesignModule', {})
        arms_module = protocol.get('ArmsInterventionsModule', {})
        outcomes_module = protocol.get('OutcomesModule', {})
        conditions_module = protocol.get('ConditionsModule', {})
        enrollment_module = protocol.get('DesignModule', {}).get('EnrollmentInfo', {})

        # Extract results section (if available)
        results_section = study.get('ResultsSection', {})
        has_results = bool(results_section)

        # Build trial details
        trial = {
            'nct_id': nct_id,
            'title': id_module.get('OfficialTitle', id_module.get('BriefTitle', '')),
            'status': status_module.get('OverallStatus', ''),
            'phase': design_module.get('PhaseList', {}).get('Phase', [''])[0] if design_module.get('PhaseList') else '',
            'enrollment': enrollment_module.get('EnrollmentCount', 0),
            'conditions': conditions_module.get('ConditionList', {}).get('Condition', []),
            'interventions': [],
            'primary_outcome': '',
            'results_available': has_results,
            'start_date': status_module.get('StartDateStruct', {}).get('StartDate', ''),
            'completion_date': status_module.get('CompletionDateStruct', {}).get('CompletionDate', ''),
            'linked_pmids': []
        }

        # Interventions
        if 'InterventionList' in arms_module:
            for intervention in arms_module['InterventionList'].get('Intervention', []):
                trial['interventions'].append({
                    'type': intervention.get('InterventionType', ''),
                    'name': intervention.get('InterventionName', ''),
                    'description': intervention.get('InterventionDescription', '')
                })

        # Primary outcome
        if 'PrimaryOutcomeList' in outcomes_module:
            primary_outcomes = outcomes_module['PrimaryOutcomeList'].get('PrimaryOutcome', [])
            if primary_outcomes:
                trial['primary_outcome'] = primary_outcomes[0].get('PrimaryOutcomeMeasure', '')

        # Linked publications (PMIDs)
        references_module = protocol.get('ReferencesModule', {})
        if 'ReferenceList' in references_module:
            for ref in references_module['ReferenceList'].get('Reference', []):
                pmid = ref.get('ReferencePMID')
                if pmid:
                    trial['linked_pmids'].append(pmid)

        return trial

    except Exception as e:
        print(f"Error fetching NCT:{nct_id}: {e}", file=sys.stderr)
        return None


def format_trial_summary(trial: Dict[str, Any]) -> str:
    """Format trial details as human-readable summary."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"Clinical Trial: {trial['nct_id']}")
    lines.append("=" * 80)
    lines.append(f"\nTitle: {trial['title']}")
    lines.append(f"Status: {trial['status']}")

    if trial['phase']:
        lines.append(f"Phase: {trial['phase']}")

    if trial['enrollment']:
        lines.append(f"Enrollment: {trial['enrollment']} participants")

    if trial['start_date']:
        lines.append(f"Start Date: {trial['start_date']}")

    if trial['completion_date']:
        lines.append(f"Completion Date: {trial['completion_date']}")

    if trial['conditions']:
        lines.append(f"\nConditions:")
        for condition in trial['conditions']:
            lines.append(f"  - {condition}")

    if trial['interventions']:
        lines.append(f"\nInterventions:")
        for intervention in trial['interventions']:
            lines.append(f"  - {intervention['type']}: {intervention['name']}")
            if intervention.get('description'):
                lines.append(f"    {intervention['description'][:100]}...")

    if trial['primary_outcome']:
        lines.append(f"\nPrimary Outcome:")
        lines.append(f"  {trial['primary_outcome']}")

    if trial['linked_pmids']:
        lines.append(f"\nLinked Publications:")
        for pmid in trial['linked_pmids']:
            lines.append(f"  - PMID: {pmid}")

    lines.append(f"\nResults Available: {'Yes' if trial['results_available'] else 'No'}")

    lines.append("\n" + "=" * 80)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Lookup clinical trials from ClinicalTrials.gov'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for trials')
    search_parser.add_argument('--condition', help='Medical condition')
    search_parser.add_argument('--intervention', help='Intervention/treatment')
    search_parser.add_argument('--max-results', type=int, default=20,
                              help='Maximum results (default: 20)')
    search_parser.add_argument('--format', choices=['json', 'nct_ids'], default='nct_ids')

    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch trial details')
    fetch_parser.add_argument('nct_id', help='NCT ID (e.g., NCT12345678)')
    fetch_parser.add_argument('--format', choices=['json', 'summary'], default='summary')

    args = parser.parse_args()

    if args.command == 'search':
        if not args.condition and not args.intervention:
            print("Error: Must specify --condition or --intervention", file=sys.stderr)
            sys.exit(1)

        nct_ids = search_trials(
            condition=args.condition,
            intervention=args.intervention,
            max_results=args.max_results
        )

        if args.format == 'nct_ids':
            for nct_id in nct_ids:
                print(nct_id)
        else:  # json
            trials = []
            for nct_id in nct_ids:
                trial = fetch_trial_details(nct_id)
                if trial:
                    trials.append(trial)
            print(json.dumps(trials, indent=2))

    elif args.command == 'fetch':
        trial = fetch_trial_details(args.nct_id)
        if trial:
            if args.format == 'json':
                print(json.dumps(trial, indent=2))
            else:  # summary
                print(format_trial_summary(trial))
        else:
            print(f"Could not fetch NCT:{args.nct_id}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
