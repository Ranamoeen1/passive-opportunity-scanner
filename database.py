import sqlite3
from typing import List, Optional
import json
from models import UserProfile, Opportunity, OpportunityEvaluation, ApplicationDraft

DB_PATH = "scanner.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY DEFAULT 1,
        skills TEXT,
        interests TEXT,
        goals TEXT,
        experience_level TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS opportunities (
        id TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        url TEXT,
        source TEXT,
        published_date TEXT,
        relevance_score INTEGER DEFAULT 0,
        reasoning TEXT,
        difficulty_level TEXT,
        is_urgent BOOLEAN DEFAULT FALSE,
        status TEXT DEFAULT 'new'
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS drafts (
        opportunity_id TEXT PRIMARY KEY,
        draft_content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
    )
    ''')

    conn.commit()
    conn.close()

def save_user_profile(profile: UserProfile):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO user_profile (id, skills, interests, goals, experience_level)
    VALUES (1, ?, ?, ?, ?)
    ''', (
        json.dumps(profile.skills),
        json.dumps(profile.interests),
        profile.goals,
        profile.experience_level
    ))
    conn.commit()
    conn.close()

def get_user_profile() -> Optional[UserProfile]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT skills, interests, goals, experience_level FROM user_profile WHERE id = 1')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return UserProfile(
            skills=json.loads(row[0]),
            interests=json.loads(row[1]),
            goals=row[2],
            experience_level=row[3]
        )
    return None

def save_opportunity(opp: Opportunity):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO opportunities (
        id, title, description, url, source, published_date, 
        relevance_score, reasoning, difficulty_level, is_urgent, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        opp.id, opp.title, opp.description, opp.url, opp.source, opp.published_date,
        opp.relevance_score, opp.reasoning, opp.difficulty_level, opp.is_urgent, "new"
    ))
    conn.commit()
    conn.close()

def update_opportunity_scores(opp_id: str, relevance_score: int, reasoning: str, difficulty_level: str, is_urgent: bool):
    """Updates only the AI evaluation fields for an existing opportunity."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE opportunities
    SET relevance_score = ?, reasoning = ?, difficulty_level = ?, is_urgent = ?
    WHERE id = ?
    ''', (relevance_score, reasoning, difficulty_level, is_urgent, opp_id))
    conn.commit()
    conn.close()

def get_all_opportunities() -> List[Opportunity]:
    """Returns every opportunity in the DB regardless of score (used for re-evaluation)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM opportunities')
    rows = cursor.fetchall()
    conn.close()
    return [Opportunity(**dict(row)) for row in rows]

def get_opportunities(min_score: int = 50) -> List[Opportunity]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
    SELECT * FROM opportunities 
    WHERE relevance_score >= ? 
    ORDER BY is_urgent DESC, relevance_score DESC
    ''', (min_score,))
    rows = cursor.fetchall()
    conn.close()
    
    opps = []
    for row in rows:
        opps.append(Opportunity(**dict(row)))
    return opps

def update_opportunity_status(opp_id: str, new_status: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE opportunities SET status = ? WHERE id = ?', (new_status, opp_id))
    conn.commit()
    conn.close()

def save_draft(opportunity_id: str, draft_content: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR REPLACE INTO drafts (opportunity_id, draft_content)
    VALUES (?, ?)
    ''', (opportunity_id, draft_content))
    conn.commit()
    conn.close()

def get_draft(opportunity_id: str) -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT draft_content FROM drafts WHERE opportunity_id = ?', (opportunity_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None
