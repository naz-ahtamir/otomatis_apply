import re
from config import CV_PATH

CANDIDATE_PROFILE = {
    "first_name": "Nasaruddin",
    "last_name": "ST",
    "full_name": "Nasaruddin, ST",
    "email": "nasaruddin.ahtamir@gmail.com",
    "phone": "+6282220715073",
    "phone_national": "082220715073",
    "city": "Morowali",
    "state": "Central Sulawesi",
    "country": "Indonesia",
    "postal_code": "94973",
    "address": "Morowali, Central Sulawesi, Indonesia",
    "revou_cv_name": "Nasaruddin,ST2",
    "resume_path": str(CV_PATH),
    "linkedin_url": "https://www.linkedin.com/in/nasaruddin-ahtamir",
    "github_url": "https://github.com/nasaruddin-ahtamir",
    "portfolio_url": "https://nasaruddin.dev",
    "headline": "Junior Software Engineer - Backend Developer (TypeScript, NestJS, PostgreSQL)",
    "skills": [
        "TypeScript", "JavaScript", "NestJS", "Node.js", "PostgreSQL",
        "Prisma ORM", "Next.js", "React", "REST API", "MongoDB",
        "Git", "Docker", "Supabase"
    ]
}

# Screening questions default answers
ANSWERS_MAPPING = {
    # Experience years
    r"years.*experience.*typescript": "1",
    r"years.*experience.*javascript": "2",
    r"years.*experience.*node": "1",
    r"years.*experience.*nest": "1",
    r"years.*experience.*react": "1",
    r"years.*experience.*next": "1",
    r"years.*experience.*sql|postgres": "1",
    r"years.*experience.*backend": "1",
    r"years.*experience.*software": "1",
    r"years.*experience.*web": "1",
    r"how many years": "1",

    # Work authorization & Sponsorship
    r"legally authorized.*work in": "Yes",
    r"authorized to work": "Yes",
    r"require.*sponsorship": "No",  # For remote positions, generally select No/Yes based on employer preference
    r"visa.*sponsorship": "No",
    r"willing.*relocate": "Yes",
    r"remote": "Yes",
    
    # Notice & Availability
    r"notice period": "Immediately",
    r"start date|when can you start": "Immediately",
    r"how soon": "Immediately",
    
    # English proficiency
    r"english.*proficiency|level of english": "Professional",
    r"fluent in english": "Yes",

    # Salary expectations
    r"salary expectation|desired salary": "Negotiable",
    r"expected.*rate": "Negotiable",
}

def generate_recruiter_note(recruiter_name: str, job_title: str, company_name: str) -> str:
    """
    Generate concise personalized connection note (LinkedIn character limit is 200 or 300 chars for free tier).
    Free tier limit is usually 200 chars. Keep it sharp and under 200 characters.
    """
    clean_name = recruiter_name.split()[0] if recruiter_name else "there"
    # Target under 190 characters
    note = f"Hi {clean_name}, I recently applied for the {job_title} role at {company_name}. With my background in backend dev (TypeScript, NestJS), I'd love to connect and follow your team's work!"
    if len(note) > 200:
        note = f"Hi {clean_name}, applied for the {job_title} position at {company_name}. Excited about your team's work and would love to connect!"
    if len(note) > 200:
        note = f"Hi {clean_name}, I applied for the {job_title} role at {company_name}. Would love to connect!"
    return note[:200]
