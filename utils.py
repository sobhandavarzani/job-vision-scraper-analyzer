"""
Shared utilities for the Job Vision Scraper & Analyzer project.
Contains common functions and keyword definitions used across all modules.
"""
import os
import re
import logging
from datetime import datetime, timedelta

# ─── Logging Setup ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─── ChromeDriver Path (auto-detect) ────────────────────────────────────────
def get_chromedriver_path():
    """
    Auto-detect chromedriver.exe location.
    Priority: 1) Environment variable  2) Project root  3) System PATH
    """
    # 1. Check environment variable
    env_path = os.environ.get("CHROMEDRIVER_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2. Check project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(project_root, "chromedriver.exe")
    if os.path.isfile(local_path):
        return local_path

    # 3. Fallback: let undetected-chromedriver handle it automatically
    return None

# ─── Comprehensive Keywords Pool ─────────────────────────────────────────────
KEYWORDS_POOL = {
    # Main Languages & Stacks
    'Python': r'\bpython\b|پایتون',
    'C# (.NET)': r'\bc#\b|\b\.net\b|دات‌نت Core',
    'Java': r'\bjava\b|جاوا(?!اسکریپت)',
    'Go / Golang': r'\bgolang\b|گولنگ|\bgo(?:lang)?\b(?=.*(?:programming|language|زبان|برنامه‌نویسی))',
    'PHP / Laravel': r'\bphp\b|پی‌اچ‌پ|laravel|لاراول',
    'JavaScript': r'\bjavascript\b|جاوااسکریپت',
    'TypeScript': r'\btypescript\b|تایپ‌اسکریپت',

    # AI & Modern Coding
    'LLM / AI / GPT': r'\bllm\b|هوش مصنوعی|openai|chatgpt|gemini|\bartificial\s?intelligence\b|\bai\b(?=.*(?:model|agent|tool|engine|system|platform|assistant|chatbot|copilot|coding))',
    'Claude / Anthropic': r'\bclaude\b|کلود',
    'Vibe Coding / Prompt Engineering': r'vibe\s?coder|وایب کدینگ|prompt\s?engineering|مهندسی پرامپت',
    'AI Coding Tools (Cursor/Copilot)': r'cursor|copilot|claudecode|v0\.dev|lovable|bolt\.new',
    'LangChain / LangGraph': r'langchain|langgraph|crewai|ایجنت',
    'RAG / Vector Databases': r'\brag\b|vector\s?database|qdrant|chromadb',
    'Machine / Deep Learning': r'machine\s?learning|deep\s?learning|یادگیری ماشین|pytorch|tensorflow|scikit',
    'Computer Vision / OpenCV': r'computer\s?vision|opencv|بینایی ماشین|پردازش تصویر',

    # Frontend & Mobile
    'React / Next.js': r'react|ری‌اکت|next\.js|نکست',
    'Angular': r'angular|انگولار',
    'Vue.js': r'vue\.js|ویو جی اس',
    'Flutter / Dart': r'flutter|فلاتر|\bdart\b',
    'WordPress': r'wordpress|وردپرس',

    # Database & Big Data
    'SQL Server / T-SQL': r'sql\s?server|t-sql|اس‌کیو‌ال سرور',
    'PostgreSQL / MySQL': r'postgresql|postgres|mysql|پستگرس',
    'NoSQL (MongoDB/Redis)': r'mongodb|redis|مونگو|ردیس',
    'Big Data (Spark/Kafka)': r'spark|kafka|hadoop|کافکا|اسپارک',

    # Architecture & DevOps
    'Docker / Kubernetes': r'docker|kubernetes|داکر|کوبرنتیز',
    'Microservices / MQ': r'microservice|میکروسرویس|rabbitmq|message\s?queue|صف پیام',
    'Clean Code / SOLID / DDD': r'clean\s?code|solid|ddd|کد تمیز|معماری تمیز',

    # Data & Process Tools
    'Power BI / BI': r'power\s?bi|هوش تجاری|\bbi\b(?=.*(?:tool|dashboard|report|platform|ابزار|داشبورد))',
    'BPMS / BPMN': r'bpms|bpmn|مدل‌سازی فرآیند',

    # Special Domains
    'FinTech / Blockchain / ERP': r'fintech|فین‌تک|blockchain|بلاکچین|رمز\s?ارز|crypto|erp|ای‌آرپی',
}

# ─── Text Cleaning ───────────────────────────────────────────────────────────
def clean_persian_text(text):
    """Normalize Persian/Arabic text for consistent matching."""
    if not isinstance(text, str):
        return ""
    text = text.replace('\u200c', ' ')  # Zero-width non-joiner → space
    text = text.replace('\u200d', ' ')  # Zero-width joiner → space
    text = text.replace('\xa0', ' ')    # Non-breaking space → space
    text = re.sub(r'\s+', ' ', text)    # Collapse multiple spaces
    return text.strip()

# ─── Safe Element Getter ─────────────────────────────────────────────────────
def safe_get(element, by, value, default=""):
    """Safely get text from a Selenium element, returning default on failure."""
    try:
        return element.find_element(by, value).text.strip()
    except Exception:
        return default

# ─── Experience Extraction ───────────────────────────────────────────────────
def extract_experience(text):
    """Extract years of experience from Persian/English text."""
    if not isinstance(text, str):
        return None
    match = re.search(
        r'(\d+)\s*سال\s*(?:سابقه|تجربه)|experience\s*:?\s*(\d+)',
        text, re.IGNORECASE
    )
    if match:
        nums = [int(s) for s in match.groups() if s is not None]
        return nums[0] if nums else None
    return None

# ─── Job Detail Extraction ───────────────────────────────────────────────────
def extract_job_details(text):
    """Extract salary, cooperation type, and work hours from job description text."""
    if not isinstance(text, str):
        return {"salary": "نامشخص", "cooperation_type": "نامشخص", "work_hours": "نامشخص"}

    # Salary
    salary = "نامشخص"
    salary_patterns = [
        r'حقوق\s*:\s*([^\n,]+)',
        r'حقوق\s*ماهیانه\s*:\s*([^\n,]+)',
        r'درآمد\s*:\s*([^\n,]+)',
        r'salary\s*:\s*([^\n,]+)',
        r'(?:بین|از)\s*([\d,]+)\s*(?:تا|الی)\s*([\d,]+)\s*(?:تومان|ریال)',
    ]
    for pattern in salary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            salary = match.group(0).replace("حقوق :", "").replace("حقوق:", "").strip()
            break

    # Cooperation type
    cooperation_type = "نامشخص"
    if re.search(r'دورکاری|ریموت|remote|دورکار', text, re.IGNORECASE):
        cooperation_type = "دورکاری"
    elif re.search(r'هیبرید|hybrid|نیمه‌حضوری', text, re.IGNORECASE):
        cooperation_type = "هیبرید"
    elif re.search(r'حضوری|on-site|onsite|full-time', text, re.IGNORECASE):
        cooperation_type = "حضوری"

    # Work hours
    work_hours = "نامشخص"
    hours_match = re.search(r'ساعت\s*کاری\s*:\s*([^\n]+)', text)
    if hours_match:
        work_hours = hours_match.group(1).strip()

    return {"salary": salary, "cooperation_type": cooperation_type, "work_hours": work_hours}

# ─── Recent Job Check ────────────────────────────────────────────────────────
def is_recent_job(date_str, days=7):
    """Check if a job posting is from the last N days."""
    try:
        job_date = datetime.strptime(date_str, "%Y-%m-%d")
        return job_date >= datetime.now() - timedelta(days=days)
    except (ValueError, TypeError):
        return True  # If date can't be parsed, include the job