#!/usr/bin/env python3
"""
Medical Literature Database Manager (litdb.py)

Database schema and CLI for managing medical literature analysis sessions.
Stores papers, citations, hypotheses, clinical trials, and outcomes.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Database location
DB_PATH = Path.home() / ".med-literature" / "citations.db"


class MedicalLiteratureDB:
    """Database manager for medical literature analysis."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self.connect()
        self.create_schema()

    def connect(self):
        """Connect to the SQLite database."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        # Enable foreign keys
        self.conn.execute("PRAGMA foreign_keys = ON")

    def create_schema(self):
        """Create all database tables."""
        cursor = self.conn.cursor()

        # Papers table - stores medical literature metadata
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                pmid TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT,  -- JSON list of authors
                journal TEXT,
                year INTEGER,
                volume TEXT,
                issue TEXT,
                pages TEXT,
                abstract TEXT,
                doi TEXT,
                pmcid TEXT,
                mesh_terms TEXT,  -- JSON list of MeSH terms
                publication_types TEXT,  -- JSON list like ["Clinical Trial", "RCT"]
                patient_population TEXT,
                study_design TEXT,  -- RCT, observational, case report, review, etc.
                added_date TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Citations table - tracks citation relationships and classifications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citing_pmid TEXT NOT NULL,  -- Paper that contains the citation
                cited_pmid TEXT NOT NULL,   -- Paper being cited
                classification TEXT NOT NULL,  -- SUPPORTING, CONTRASTING, REFUTING, etc.
                confidence REAL DEFAULT 0.5,  -- 0-1 confidence in classification
                study_weight REAL DEFAULT 1.0,  -- Weight based on study design
                context TEXT,  -- The sentence/paragraph containing the citation
                reasoning TEXT,  -- Why this classification was chosen
                matched_patterns TEXT,  -- JSON list of regex patterns matched
                session_id INTEGER,
                added_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (citing_pmid) REFERENCES papers(pmid),
                FOREIGN KEY (cited_pmid) REFERENCES papers(pmid),
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                UNIQUE(citing_pmid, cited_pmid)
            )
        """)

        # Sessions table - research question analysis sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                research_question TEXT NOT NULL,
                seed_pmid TEXT,  -- Initial paper that started the analysis
                depth_limit INTEGER DEFAULT 2,
                status TEXT DEFAULT 'active',  -- active, completed, archived
                consensus_score REAL,  -- Final weighted consensus (-1 to 1)
                summary TEXT,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_date TEXT,
                FOREIGN KEY (seed_pmid) REFERENCES papers(pmid)
            )
        """)

        # Session papers - tracks which papers were analyzed in each session
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                pmid TEXT NOT NULL,
                depth INTEGER DEFAULT 0,  -- Depth in citation tree
                is_seed BOOLEAN DEFAULT 0,  -- Whether this was a seed paper
                added_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                FOREIGN KEY (pmid) REFERENCES papers(pmid),
                UNIQUE(session_id, pmid)
            )
        """)

        # Hypotheses table - track medical theories/claims
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hypotheses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                status TEXT DEFAULT 'ACTIVE',  -- ACTIVE, RULED_OUT, SUPPORTED, UNCERTAIN
                ruling_evidence TEXT,  -- PMIDs or summary of evidence
                confidence REAL,  -- 0-1 confidence in status
                category TEXT,  -- treatment, mechanism, safety, guideline
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_date TEXT
            )
        """)

        # Clinical trials table - track trial registry data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clinical_trials (
                nct_id TEXT PRIMARY KEY,
                title TEXT,
                status TEXT,  -- Recruiting, Completed, Terminated, etc.
                phase TEXT,  -- Phase 1, Phase 2, Phase 3, Phase 4
                enrollment INTEGER,
                conditions TEXT,  -- JSON list of conditions
                interventions TEXT,  -- JSON list of interventions
                primary_outcome TEXT,
                results_available BOOLEAN DEFAULT 0,
                linked_pmid TEXT,  -- If published, link to paper
                start_date TEXT,
                completion_date TEXT,
                added_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (linked_pmid) REFERENCES papers(pmid)
            )
        """)

        # Outcomes table - clinical endpoints from studies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_pmid TEXT NOT NULL,
                outcome_type TEXT,  -- mortality, morbidity, quality_of_life, surrogate
                outcome_measure TEXT,  -- Specific measure (e.g., "all-cause mortality")
                result_summary TEXT,  -- E.g., "HR 0.85, 95% CI 0.75-0.96"
                statistical_significance REAL,  -- p-value
                effect_direction TEXT,  -- positive, negative, neutral
                added_date TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (paper_pmid) REFERENCES papers(pmid)
            )
        """)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_cited ON citations(cited_pmid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_pmid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_papers_session ON session_papers(session_id)")

        self.conn.commit()

    # ==================== Papers ====================

    def add_paper(self, pmid: str, title: str, **kwargs) -> bool:
        """Add a paper to the database."""
        cursor = self.conn.cursor()

        # Convert lists to JSON
        for field in ['authors', 'mesh_terms', 'publication_types']:
            if field in kwargs and isinstance(kwargs[field], list):
                kwargs[field] = json.dumps(kwargs[field])

        # Build INSERT query dynamically
        fields = ['pmid', 'title'] + list(kwargs.keys())
        placeholders = ['?' for _ in fields]
        values = [pmid, title] + list(kwargs.values())

        try:
            cursor.execute(f"""
                INSERT OR REPLACE INTO papers ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            """, values)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding paper: {e}", file=sys.stderr)
            return False

    def get_paper(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Get paper details by PMID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE pmid = ?", (pmid,))
        row = cursor.fetchone()

        if row:
            paper = dict(row)
            # Parse JSON fields
            for field in ['authors', 'mesh_terms', 'publication_types']:
                if paper.get(field):
                    try:
                        paper[field] = json.loads(paper[field])
                    except json.JSONDecodeError:
                        pass
            return paper
        return None

    def list_papers(self, year: Optional[int] = None, study_design: Optional[str] = None,
                   limit: int = 20) -> List[Dict[str, Any]]:
        """List papers with optional filters."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM papers WHERE 1=1"
        params = []

        if year:
            query += " AND year = ?"
            params.append(year)

        if study_design:
            query += " AND study_design = ?"
            params.append(study_design)

        query += f" ORDER BY added_date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        papers = []
        for row in cursor.fetchall():
            paper = dict(row)
            # Parse JSON fields
            for field in ['authors', 'mesh_terms', 'publication_types']:
                if paper.get(field):
                    try:
                        paper[field] = json.loads(paper[field])
                    except json.JSONDecodeError:
                        pass
            papers.append(paper)

        return papers

    # ==================== Citations ====================

    def add_citation(self, citing_pmid: str, cited_pmid: str, classification: str,
                    **kwargs) -> bool:
        """Add a citation relationship."""
        cursor = self.conn.cursor()

        # Convert lists to JSON
        if 'matched_patterns' in kwargs and isinstance(kwargs['matched_patterns'], list):
            kwargs['matched_patterns'] = json.dumps(kwargs['matched_patterns'])

        fields = ['citing_pmid', 'cited_pmid', 'classification'] + list(kwargs.keys())
        placeholders = ['?' for _ in fields]
        values = [citing_pmid, cited_pmid, classification] + list(kwargs.values())

        try:
            cursor.execute(f"""
                INSERT OR REPLACE INTO citations ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            """, values)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding citation: {e}", file=sys.stderr)
            return False

    def get_citation_summary(self, pmid: Optional[str] = None, session_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get weighted consensus summary for a paper or session.
        Returns classification counts, weighted scores, and consensus.
        """
        cursor = self.conn.cursor()

        query = """
            SELECT
                classification,
                COUNT(*) as count,
                AVG(confidence) as avg_confidence,
                AVG(study_weight) as avg_weight,
                SUM(study_weight) as total_weight
            FROM citations
            WHERE 1=1
        """
        params = []

        if pmid:
            query += " AND cited_pmid = ?"
            params.append(pmid)

        if session_id:
            query += " AND session_id = ?"
            params.append(session_id)

        query += " GROUP BY classification"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Calculate weighted consensus score
        supporting = 0.0
        contrasting = 0.0
        refuting = 0.0
        meta_analysis = 0.0
        total_weight = 0.0

        summary = {}
        for row in rows:
            classification = row['classification']
            weight = row['total_weight']
            summary[classification] = {
                'count': row['count'],
                'avg_confidence': row['avg_confidence'],
                'avg_weight': row['avg_weight'],
                'total_weight': weight
            }

            if classification == 'SUPPORTING':
                supporting = weight
            elif classification == 'CONTRASTING':
                contrasting = weight
            elif classification == 'REFUTING':
                refuting = weight
            elif classification == 'META_ANALYSIS':
                meta_analysis = weight

            total_weight += weight

        # Consensus formula: (SUPPORTING + META - CONTRASTING - 2*REFUTING) / total
        if total_weight > 0:
            consensus = (supporting + meta_analysis - contrasting - 2 * refuting) / total_weight
        else:
            consensus = 0.0

        return {
            'summary': summary,
            'consensus_score': consensus,
            'total_citations': sum(s['count'] for s in summary.values()),
            'total_weight': total_weight
        }

    # ==================== Sessions ====================

    def create_session(self, research_question: str, **kwargs) -> int:
        """Create a new research session."""
        cursor = self.conn.cursor()

        fields = ['research_question'] + list(kwargs.keys())
        placeholders = ['?' for _ in fields]
        values = [research_question] + list(kwargs.values())

        cursor.execute(f"""
            INSERT INTO sessions ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
        """, values)
        self.conn.commit()
        return cursor.lastrowid

    def add_session_paper(self, session_id: int, pmid: str, depth: int = 0,
                         is_seed: bool = False) -> bool:
        """Add a paper to a session."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO session_papers (session_id, pmid, depth, is_seed)
                VALUES (?, ?, ?, ?)
            """, (session_id, pmid, depth, is_seed))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding session paper: {e}", file=sys.stderr)
            return False

    def complete_session(self, session_id: int, summary: str, consensus_score: float) -> bool:
        """Mark a session as completed."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                UPDATE sessions
                SET status = 'completed',
                    summary = ?,
                    consensus_score = ?,
                    completed_date = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (summary, consensus_score, session_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error completing session: {e}", file=sys.stderr)
            return False

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session details."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def list_sessions(self, status: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """List sessions."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM sessions WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_date DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ==================== Hypotheses ====================

    def add_hypothesis(self, name: str, **kwargs) -> bool:
        """Add or update a hypothesis."""
        cursor = self.conn.cursor()

        fields = ['name'] + list(kwargs.keys()) + ['updated_date']
        placeholders = ['?' for _ in fields]
        values = [name] + list(kwargs.values()) + [datetime.now().isoformat()]

        # Handle UPSERT
        update_fields = ', '.join([f"{f} = excluded.{f}" for f in fields if f != 'name'])

        try:
            cursor.execute(f"""
                INSERT INTO hypotheses ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
                ON CONFLICT(name) DO UPDATE SET {update_fields}
            """, values)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding hypothesis: {e}", file=sys.stderr)
            return False

    def list_hypotheses(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List hypotheses, optionally filtered by status."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM hypotheses WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY updated_date DESC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ==================== Outcomes ====================

    def add_outcome(self, paper_pmid: str, outcome_type: str, **kwargs) -> bool:
        """Add an outcome measure from a paper."""
        cursor = self.conn.cursor()

        fields = ['paper_pmid', 'outcome_type'] + list(kwargs.keys())
        placeholders = ['?' for _ in fields]
        values = [paper_pmid, outcome_type] + list(kwargs.values())

        try:
            cursor.execute(f"""
                INSERT INTO outcomes ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            """, values)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding outcome: {e}", file=sys.stderr)
            return False

    def list_outcomes(self, pmid: Optional[str] = None) -> List[Dict[str, Any]]:
        """List outcomes, optionally for a specific paper."""
        cursor = self.conn.cursor()

        query = "SELECT * FROM outcomes WHERE 1=1"
        params = []

        if pmid:
            query += " AND paper_pmid = ?"
            params.append(pmid)

        query += " ORDER BY added_date DESC"

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ==================== Export & Stats ====================

    def export_database(self, format: str = 'json') -> str:
        """Export entire database."""
        cursor = self.conn.cursor()

        data = {
            'papers': [dict(row) for row in cursor.execute("SELECT * FROM papers").fetchall()],
            'citations': [dict(row) for row in cursor.execute("SELECT * FROM citations").fetchall()],
            'sessions': [dict(row) for row in cursor.execute("SELECT * FROM sessions").fetchall()],
            'hypotheses': [dict(row) for row in cursor.execute("SELECT * FROM hypotheses").fetchall()],
            'outcomes': [dict(row) for row in cursor.execute("SELECT * FROM outcomes").fetchall()],
        }

        if format == 'json':
            return json.dumps(data, indent=2)
        # Could add CSV export here
        return json.dumps(data, indent=2)

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.cursor()

        stats = {}
        for table in ['papers', 'citations', 'sessions', 'hypotheses', 'clinical_trials', 'outcomes']:
            cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = cursor.fetchone()['count']

        # Additional stats
        cursor.execute("SELECT COUNT(DISTINCT pmid) as seed_papers FROM session_papers WHERE is_seed = 1")
        stats['seed_papers'] = cursor.fetchone()['seed_papers']

        cursor.execute("SELECT COUNT(*) as completed_sessions FROM sessions WHERE status = 'completed'")
        stats['completed_sessions'] = cursor.fetchone()['completed_sessions']

        cursor.execute("SELECT COUNT(*) as ruled_out_hypotheses FROM hypotheses WHERE status = 'RULED_OUT'")
        stats['ruled_out_hypotheses'] = cursor.fetchone()['ruled_out_hypotheses']

        return stats

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# ==================== CLI ====================

def main():
    parser = argparse.ArgumentParser(description='Medical Literature Database Manager')
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Papers commands
    papers = subparsers.add_parser('papers', help='Manage papers')
    papers_sub = papers.add_subparsers(dest='subcommand')

    papers_add = papers_sub.add_parser('add', help='Add a paper')
    papers_add.add_argument('--pmid', required=True)
    papers_add.add_argument('--title', required=True)
    papers_add.add_argument('--study-design')
    papers_add.add_argument('--year', type=int)

    papers_get = papers_sub.add_parser('get', help='Get a paper')
    papers_get.add_argument('--pmid', required=True)

    papers_list = papers_sub.add_parser('list', help='List papers')
    papers_list.add_argument('--year', type=int)
    papers_list.add_argument('--study-design')
    papers_list.add_argument('--limit', type=int, default=20)

    # Citations commands
    citations = subparsers.add_parser('citations', help='Manage citations')
    citations_sub = citations.add_subparsers(dest='subcommand')

    citations_add = citations_sub.add_parser('add', help='Add a citation')
    citations_add.add_argument('--citing', required=True, help='Citing PMID')
    citations_add.add_argument('--cited', required=True, help='Cited PMID')
    citations_add.add_argument('--classification', required=True,
                              choices=['SUPPORTING', 'CONTRASTING', 'REFUTING',
                                      'METHODOLOGICAL', 'CONTEXTUAL', 'META_ANALYSIS'])
    citations_add.add_argument('--study-weight', type=float, default=1.0)
    citations_add.add_argument('--confidence', type=float, default=0.5)

    citations_summary = citations_sub.add_parser('summary', help='Get citation summary')
    citations_summary.add_argument('--pmid')
    citations_summary.add_argument('--session-id', type=int)

    # Sessions commands
    session = subparsers.add_parser('session', help='Manage research sessions')
    session_sub = session.add_subparsers(dest='subcommand')

    session_create = session_sub.add_parser('create', help='Create a session')
    session_create.add_argument('--question', required=True)
    session_create.add_argument('--seed-pmid')
    session_create.add_argument('--depth-limit', type=int, default=2)

    session_add_paper = session_sub.add_parser('add-paper', help='Add paper to session')
    session_add_paper.add_argument('--session-id', type=int, required=True)
    session_add_paper.add_argument('--pmid', required=True)
    session_add_paper.add_argument('--depth', type=int, default=0)
    session_add_paper.add_argument('--seed', action='store_true')

    session_complete = session_sub.add_parser('complete', help='Complete a session')
    session_complete.add_argument('--id', type=int, required=True)
    session_complete.add_argument('--summary', required=True)
    session_complete.add_argument('--consensus-score', type=float, required=True)

    session_list = session_sub.add_parser('list', help='List sessions')
    session_list.add_argument('--status')

    session_get = session_sub.add_parser('get', help='Get session details')
    session_get.add_argument('--id', type=int, required=True)

    # Hypotheses commands
    hypothesis = subparsers.add_parser('hypothesis', help='Manage hypotheses')
    hypothesis_sub = hypothesis.add_subparsers(dest='subcommand')

    hypothesis_add = hypothesis_sub.add_parser('add', help='Add a hypothesis')
    hypothesis_add.add_argument('--name', required=True)
    hypothesis_add.add_argument('--description')
    hypothesis_add.add_argument('--status', choices=['ACTIVE', 'RULED_OUT', 'SUPPORTED', 'UNCERTAIN'])
    hypothesis_add.add_argument('--ruling', help='Ruling evidence (PMIDs or summary)')

    hypothesis_list = hypothesis_sub.add_parser('list', help='List hypotheses')
    hypothesis_list.add_argument('--status')

    hypothesis_ruled_out = hypothesis_sub.add_parser('ruled-out', help='Show ruled out hypotheses')

    # Outcomes commands
    outcome = subparsers.add_parser('outcome', help='Manage outcomes')
    outcome_sub = outcome.add_subparsers(dest='subcommand')

    outcome_add = outcome_sub.add_parser('add', help='Add an outcome')
    outcome_add.add_argument('--pmid', required=True)
    outcome_add.add_argument('--type', required=True,
                            choices=['mortality', 'morbidity', 'quality_of_life', 'surrogate'])
    outcome_add.add_argument('--measure')
    outcome_add.add_argument('--result')
    outcome_add.add_argument('--p-value', type=float)

    outcome_list = outcome_sub.add_parser('list', help='List outcomes')
    outcome_list.add_argument('--pmid')

    # Export & Stats
    export = subparsers.add_parser('export', help='Export database')
    export.add_argument('--format', choices=['json', 'csv'], default='json')

    stats = subparsers.add_parser('stats', help='Show database statistics')

    args = parser.parse_args()

    # Initialize database
    db = MedicalLiteratureDB()

    try:
        # Papers
        if args.command == 'papers':
            if args.subcommand == 'add':
                kwargs = {}
                if args.study_design:
                    kwargs['study_design'] = args.study_design
                if args.year:
                    kwargs['year'] = args.year
                if db.add_paper(args.pmid, args.title, **kwargs):
                    print(f"Added paper PMID:{args.pmid}")
                else:
                    sys.exit(1)

            elif args.subcommand == 'get':
                paper = db.get_paper(args.pmid)
                if paper:
                    print(json.dumps(paper, indent=2))
                else:
                    print(f"Paper PMID:{args.pmid} not found", file=sys.stderr)
                    sys.exit(1)

            elif args.subcommand == 'list':
                papers = db.list_papers(year=args.year, study_design=args.study_design,
                                       limit=args.limit)
                for paper in papers:
                    print(f"PMID:{paper['pmid']} | {paper['year']} | {paper['title']}")

        # Citations
        elif args.command == 'citations':
            if args.subcommand == 'add':
                if db.add_citation(args.citing, args.cited, args.classification,
                                  study_weight=args.study_weight, confidence=args.confidence):
                    print(f"Added citation: {args.citing} -> {args.cited} [{args.classification}]")
                else:
                    sys.exit(1)

            elif args.subcommand == 'summary':
                summary = db.get_citation_summary(pmid=args.pmid, session_id=args.session_id)
                print(json.dumps(summary, indent=2))

        # Sessions
        elif args.command == 'session':
            if args.subcommand == 'create':
                kwargs = {}
                if args.seed_pmid:
                    kwargs['seed_pmid'] = args.seed_pmid
                if args.depth_limit:
                    kwargs['depth_limit'] = args.depth_limit
                session_id = db.create_session(args.question, **kwargs)
                print(f"Created session ID: {session_id}")

            elif args.subcommand == 'add-paper':
                if db.add_session_paper(args.session_id, args.pmid, args.depth, args.seed):
                    print(f"Added paper {args.pmid} to session {args.session_id}")
                else:
                    sys.exit(1)

            elif args.subcommand == 'complete':
                if db.complete_session(args.id, args.summary, args.consensus_score):
                    print(f"Completed session {args.id}")
                else:
                    sys.exit(1)

            elif args.subcommand == 'list':
                sessions = db.list_sessions(status=args.status)
                for s in sessions:
                    print(f"[{s['id']}] {s['research_question']} | {s['status']} | "
                          f"Score: {s['consensus_score'] if s['consensus_score'] else 'N/A'}")

            elif args.subcommand == 'get':
                session = db.get_session(args.id)
                if session:
                    print(json.dumps(session, indent=2))
                else:
                    print(f"Session {args.id} not found", file=sys.stderr)
                    sys.exit(1)

        # Hypotheses
        elif args.command == 'hypothesis':
            if args.subcommand == 'add':
                kwargs = {}
                if args.description:
                    kwargs['description'] = args.description
                if args.status:
                    kwargs['status'] = args.status
                if args.ruling:
                    kwargs['ruling_evidence'] = args.ruling
                if db.add_hypothesis(args.name, **kwargs):
                    print(f"Added/updated hypothesis: {args.name}")
                else:
                    sys.exit(1)

            elif args.subcommand == 'list':
                hypotheses = db.list_hypotheses(status=args.status)
                for h in hypotheses:
                    print(f"[{h['status']}] {h['name']}")
                    if h['description']:
                        print(f"  {h['description']}")

            elif args.subcommand == 'ruled-out':
                hypotheses = db.list_hypotheses(status='RULED_OUT')
                print(f"\nRuled Out Hypotheses ({len(hypotheses)}):")
                print("=" * 80)
                for h in hypotheses:
                    print(f"\n{h['name']}")
                    if h['description']:
                        print(f"Description: {h['description']}")
                    if h['ruling_evidence']:
                        print(f"Evidence: {h['ruling_evidence']}")

        # Outcomes
        elif args.command == 'outcome':
            if args.subcommand == 'add':
                kwargs = {}
                if args.measure:
                    kwargs['outcome_measure'] = args.measure
                if args.result:
                    kwargs['result_summary'] = args.result
                if args.p_value:
                    kwargs['statistical_significance'] = args.p_value
                if db.add_outcome(args.pmid, args.type, **kwargs):
                    print(f"Added outcome to PMID:{args.pmid}")
                else:
                    sys.exit(1)

            elif args.subcommand == 'list':
                outcomes = db.list_outcomes(pmid=args.pmid)
                for o in outcomes:
                    print(f"[{o['outcome_type']}] {o['outcome_measure']} - {o['result_summary']}")

        # Export
        elif args.command == 'export':
            output = db.export_database(format=args.format)
            print(output)

        # Stats
        elif args.command == 'stats':
            stats = db.get_stats()
            print("\nDatabase Statistics:")
            print("=" * 40)
            for key, value in stats.items():
                print(f"{key.replace('_', ' ').title()}: {value}")

        else:
            parser.print_help()

    finally:
        db.close()


if __name__ == '__main__':
    main()
