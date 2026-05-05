import PyPDF2
from models import UserProfile
from intelligence import call_gemini
import json

def parse_resume_file(file_obj) -> UserProfile:
    """Reads a PDF resume from a file-like object and uses LLM to generate a UserProfile."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

    prompt = f"""
    You are an expert recruiter AI. I am providing you with the extracted raw text of a candidate's resume.
    Please analyze it and extract their core skills, likely professional interests, career goals based on their trajectory, and their overall experience level.
    
    Resume Text (Limit to first 5000 chars for safety):
    {text[:5000]}
    
    Return STRICTLY a JSON object matching this schema:
    {{
        "skills": ["skill1", "skill2", ...],
        "interests": ["interest 1", "interest 2", ...],
        "goals": "A 1-sentence summary of what kind of gigs/jobs they are likely looking for.",
        "experience_level": "beginner" | "intermediate" | "advanced"
    }}
    """
    
    try:
        content = call_gemini(prompt, json_mode=True)
        data = json.loads(content)
        
        # Guardrails for expected arrays
        if not isinstance(data.get("skills"), list): data["skills"] = ["General Software Engineering"]
        if not isinstance(data.get("interests"), list): data["interests"] = ["Tech"]
        
        return UserProfile(**data)
    except Exception as e:
        print(f"Error parsing resume via Gemini: {e}")
        return None
