import os
import json
import hashlib
import time
import requests
import vcr
from pathlib import Path
from models import UserProfile, Opportunity, OpportunityEvaluation

# Directory that stores cassette YAML files
CASSETTES_DIR = Path(__file__).parent / "cassettes"
CASSETTES_DIR.mkdir(exist_ok=True)

# VCR: replays cached cassettes, records only new prompts. API key is stripped from files.
gemini_vcr = vcr.VCR(
    cassette_library_dir=str(CASSETTES_DIR),
    record_mode="new_episodes",
    match_on=["method", "scheme", "host", "port", "path"],
    filter_query_parameters=["key"],
)

# Gemini free tier: 15 RPM max → 1 request per 4 seconds is safe
_RATE_LIMIT_DELAY = 4.0

def _cassette_name(prompt: str, json_mode: bool) -> str:
    """Unique filename keyed by prompt hash — same prompt = instant replay, no API call."""
    digest = hashlib.md5((prompt + str(json_mode)).encode()).hexdigest()
    return f"gemini_{digest}.yaml"

def _cassette_exists(name: str) -> bool:
    return (CASSETTES_DIR / name).exists()

def call_gemini(prompt: str, json_mode: bool = False) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    if json_mode:
        payload["generationConfig"] = {"responseMimeType": "application/json"}
    headers = {"Content-Type": "application/json"}
    cassette = _cassette_name(prompt, json_mode)

    # Only throttle when we're actually going to hit the real API (no cassette yet)
    if not _cassette_exists(cassette):
        time.sleep(_RATE_LIMIT_DELAY)

    max_retries = 3
    for attempt in range(max_retries):
        with gemini_vcr.use_cassette(cassette):
            response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 429 and attempt < max_retries - 1:
            wait = _RATE_LIMIT_DELAY * (2 ** attempt)   # 4s, 8s, 16s
            print(f"Rate limited (429). Waiting {wait}s before retry {attempt + 2}/{max_retries}...")
            time.sleep(wait)
            # Delete partial cassette so it records fresh on retry
            cassette_path = CASSETTES_DIR / cassette
            if cassette_path.exists():
                cassette_path.unlink()
            continue

        response.raise_for_status()
        data = response.json()
        break

    try:
        return data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        raise ValueError(f"Unexpected response from Gemini: {data}")


def evaluate_opportunity(profile: UserProfile, opportunity: Opportunity) -> OpportunityEvaluation:
    """Evaluates an opportunity against the user's profile and scores it."""
    prompt = f"""
    You are an AI career and opportunity scout. Evaluate the following opportunity against the user's profile.
    
    USER PROFILE:
    Skills: {', '.join(profile.skills)}
    Interests: {', '.join(profile.interests)}
    Goals: {profile.goals}
    Experience Level: {profile.experience_level}
    
    OPPORTUNITY:
    Title: {opportunity.title}
    Source: {opportunity.source}
    Description: {opportunity.description[:2000]}
    Date: {opportunity.published_date}
    
    Analyze how well this opportunity matches the user profile. Pay attention to keywords.
    Important: If the deadline is near, or it's a fast-moving freelance gig or hackathon, flag it as urgent.
    
    Respond STRICTLY with a valid JSON object matching this schema:
    {{
        "relevance_score": (int, 0-100),
        "reasoning": (string, 1-2 sentence explanation),
        "difficulty_level": (string, "beginner", "intermediate", "advanced", or "unknown"),
        "is_urgent": (boolean, true if deadline soon or time-sensitive)
    }}
    """
    
    try:
        content = call_gemini(prompt, json_mode=True)
        data = json.loads(content)
        # Ensure default values if LLM misses something
        data.setdefault("relevance_score", 50)
        data.setdefault("reasoning", "Parsed safely.")
        data.setdefault("difficulty_level", "unknown")
        data.setdefault("is_urgent", False)
        return OpportunityEvaluation(**data)
    except Exception as e:
        print(f"Error evaluating opportunity {opportunity.id}: {str(e)}")
        return OpportunityEvaluation(
            relevance_score=0,
            reasoning=f"Error during AI evaluation.",
            difficulty_level="unknown",
            is_urgent=False
        )

def generate_application_draft(profile: UserProfile, opportunity: Opportunity) -> str:
    """Generates a customized application, proposal, or cover letter."""
    prompt = f"""
    You are an expert career assistant. Write a professional application/proposal draft for the user based on their profile and the opportunity description.
    
    USER PROFILE:
    Skills: {', '.join(profile.skills)}
    Interests: {', '.join(profile.interests)}
    Goals: {profile.goals}
    Experience Level: {profile.experience_level}
    
    OPPORTUNITY:
    Title: {opportunity.title}
    Description: {opportunity.description[:2000]}
    Source: {opportunity.source}
    
    Draft an impressive, concise cover letter, proposal, or statement of interest. Ensure it's tailored to the opportunity. Do not use placeholders like [Your Name] if possible, just leave the sign-off generic. Keep it under 250 words.
    """
    
    try:
        content = call_gemini(prompt, json_mode=False)
        return content.strip()
    except Exception as e:
        return f"Error generating draft."
