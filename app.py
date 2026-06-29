import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import time
import random
import re
from datetime import datetime
import os
import io

# ==========================================
# Settings & Globals
# ==========================================

CATEGORIES_POOL = {
    "توسعه‌دهنده (Developer)": "https://jobvision.ir/jobs/category/developer",
    "علوم داده (Data Science)": "https://jobvision.ir/jobs/category/data-science",
    "دیجیتال مارکتینگ (Digital Marketing)": "https://jobvision.ir/jobs/category/digital-marketing",
    "تولید محتوا (Content)": "https://jobvision.ir/jobs/category/content",
    "تست نرم‌افزار (Software QA)": "https://jobvision.ir/jobs/category/software-qa",
    "شبکه و زیرساخت (Network)": "https://jobvision.ir/jobs/category/network",
    "بازی‌سازی (Game Development)": "https://jobvision.ir/jobs/category/game",
    "طراحی گرافیک (Graphics)": "https://jobvision.ir/jobs/category/graphics",
    "طراحی UI/UX": "https://jobvision.ir/jobs/category/ui-ux",
    "مدیریت محصول (Product Manager)": "https://jobvision.ir/jobs/category/product-manager",
    "توسعه کسب‌وکار (Business Development)": "https://jobvision.ir/jobs/category/business-development",
    "معامله‌گر / تریدر (Trader)": "https://jobvision.ir/jobs/category/trader"
}

KEYWORDS_POOL = {
    'Python': r'\bpython\b|پایتون',
    'C# (.NET)': r'\bc#\b|\b\.net\b|دات‌نت Core',
    'Java': r'\bjava\b|جاوا(?!اسکریپت)',
    'Go / Golang': r'\bgo\b|\bgolang\b|گولنگ',
    'PHP / Laravel': r'\bphp\b|پی‌اچ‌پ|laravel|لاراول',
    'JavaScript': r'\bjavascript\b|جاوااسکریپت|\bjs\b',
    'TypeScript': r'\btypescript\b|تایپ‌اسکریپت|\bts\b',
    'LLM / AI / GPT': r'\bllm\b|\bai\b|هوش مصنوعی|openai|chatgpt|gemini',
    'Claude / Anthropic': r'\bclaude\b|کلود',
    'Vibe Coding / Prompt Engineering': r'vibe\s?coder|وایب کدینگ|prompt\s?engineering|مهندسی پرامپت',
    'AI Coding Tools': r'cursor|copilot|claudecode|v0\.dev|lovable|bolt\.new',
    'LangChain / LangGraph': r'langchain|langgraph|crewai|ایجنت',
    'RAG / Vector Databases': r'\brag\b|vector\s?database|qdrant|chromadb',
    'Machine / Deep Learning': r'machine\s?learning|deep\s?learning|یادگیری ماشین|pytorch|tensorflow|scikit',
    'Computer Vision': r'computer\s?vision|opencv|بینایی ماشین|پردازش تصویر',
    'React / Next.js': r'react|ری‌اکت|next\.js|نکست',
    'Angular': r'angular|انگولار',
    'Vue.js': r'vue\.js|ویو جی اس',
    'Flutter / Dart': r'flutter|فلاتر|\bdart\b',
    'WordPress': r'wordpress|وردپرس',
    'SQL Server / T-SQL': r'sql\s?server|t-sql|اس‌کیو‌ال سرور',
    'PostgreSQL / MySQL': r'postgresql|postgres|mysql|پستگرس',
    'NoSQL (MongoDB/Redis)': r'mongodb|redis|مونگو|ردیس',
    'Big Data (Spark/Kafka)': r'spark|kafka|hadoop|کافکا|اسپارک',
    'Docker / Kubernetes': r'docker|kubernetes|داکر|کوبرنتیز',
    'Microservices / MQ': r'microservice|میکروسرویس|rabbitmq|message\s?queue|صف پیام',
    'Clean Code / SOLID': r'clean\s?code|solid|ddd|کد تمیز|معماری تمیز',
    'Power BI / BI': r'power\s?bi|هوش تجاری|\bbi\b|dashboards',
    'BPMS / BPMN': r'bpms|bpmn|مدل‌سازی فرآیند',
    'FinTech / Blockchain / ERP': r'fintech|فین‌تک|blockchain|بلاکچین|رمز\s?ارز|crypto|erp|ای‌آرپی',
    'Git / GitLab / GitHub': r'\bgit\b|gitlab|github|گیت',
    'Jira / Scrum / Agile': r'\bjira\b|جیرا|scrum|اسکرام|agile|اجایل',
    'HTML / CSS': r'\bhtml\b|\bcss\b',
    'RESTful API': r'\brest\b|\bapi\b|restful',
    'Node.js': r'node\.js|node js|نود جی اس',
    'Django': r'django|جانگو|جنگو',
    'ASP.NET / Entity Framework': r'asp\.net|entity framework|ef core',
    'C++': r'\bc\+\+\b|سی پلاس پلاس',
    'Linux': r'\blinux\b|لینوکس',
    'DevOps / CI/CD': r'devops|دوآپس|ci/cd|azure|tfs',
    'Elasticsearch': r'elastic\s?search|الاستیک',
    'Oracle': r'oracle|اوراکل',
    'Figma / Adobe': r'figma|فیگما|adobe|فتوشاپ|photoshop',
    'Microsoft Office (Excel/Word)': r'excel|اکسل|word|پاورپوینت|powerpoint'
}

MAX_PAGES = 10
MAX_RETRIES = 3

# ==========================================
# Scraper Logic
# ==========================================

def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument("--headless") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument('--blink-settings=imagesEnabled=false')
    options.page_load_strategy = 'eager'
    
    driver_path = r"E:\random project\jab vision scraper\chromedriver.exe"
    
    try:
        driver = uc.Chrome(options=options, driver_executable_path=driver_path, version_main=149)
    except:
        driver = uc.Chrome(options=options)
    return driver

def clean_persian_text(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def is_recent_job(card_text, max_days):
    if not card_text: return True
    text = card_text.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')).lower()
    
    job_age_days = 999
    if any(k in text for k in ["امروز", "لحظه", "ساعت", "دقیقه", "today", "hour", "minute", "just now"]):
        job_age_days = 0
    elif any(k in text for k in ["دیروز", "yesterday"]):
        job_age_days = 1
    else:
        day_match = re.search(r'(\d+)\s*(?:روز\s*پیش|days?\s*ago)', text)
        if day_match: job_age_days = int(day_match.group(1))
        week_match = re.search(r'(\d+)\s*(?:هفته\s*پیش|weeks?\s*ago)', text)
        if week_match: job_age_days = int(week_match.group(1)) * 7
        month_match = re.search(r'(\d+)\s*(?:ماه\s*پیش|months?\s*ago)', text)
        if month_match: job_age_days = int(month_match.group(1)) * 30

    return job_age_days <= max_days

def safe_get(driver, url):
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(random.uniform(1.0, 2.0))
            driver.get(url)
            time.sleep(1.5)
            return BeautifulSoup(driver.page_source, 'html.parser')
        except:
            time.sleep(2)
    return None

def extract_job_details(driver, job_url):
    soup = safe_get(driver, job_url)
    if not soup: return None
    try:
        title_element = soup.find('h1')
        title = clean_persian_text(title_element.get_text()) if title_element else "N/A"
        city = "N/A"
        city_element = soup.find('span', class_=re.compile(r'yn_category'))
        if not city_element:
            city_element = soup.find(lambda tag: tag.name == "span" and any(k in tag.text for k in ["استخدام در", "Hiring in"]))
        if city_element:
            city_text = city_element.get_text().replace("استخدام در", "").replace("Hiring in", "")
            city = clean_persian_text(re.sub(r'\s*[،,]\s*', '، ', city_text))
        description = "N/A"
        desc_header = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and any(k in tag.text.lower() for k in ["شرح شغل", "وظایف", "job description"]))
        if desc_header:
            content_div = desc_header.find_next_sibling('div')
            if content_div:
                for br in content_div.find_all("br"): br.replace_with(" | ") 
                description = clean_persian_text(content_div.get_text())
        key_indicators = "N/A"
        key_header = soup.find(lambda tag: tag.name in ["h2", "h3", "h4"] and any(k in tag.text.lower() for k in ["شاخص های کلیدی", "key indicators"]))
        if key_header and key_header.parent:
            content_container = key_header.parent.find_next_sibling('div')
            if content_container:
                texts = [clean_persian_text(text) for text in content_container.stripped_strings if text]
                key_indicators = " | ".join(texts)
        return {'title': title, 'city': city, 'description_and_responsibilities': description, 'key_indicators': key_indicators, 'url': job_url}
    except:
        return None

# ==========================================
# Analyzer Logic
# ==========================================

def extract_experience(text):
    match = re.search(r'(\d+)\s*سال\s*(?:سابقه|تجربه)|experience\s*:?\s*(\d+)', text, re.IGNORECASE)
    if match:
        nums = [int(s) for s in match.groups() if s is not None]
        return nums[0] if nums else None
    return None

def analyze_data(df, selected_skills=None):
    text_cols = ['title', 'description_and_responsibilities', 'key_indicators']
    df['combined_text'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)
    df['combined_text_lower'] = df['combined_text'].str.lower()
    
    if selected_skills:
        pattern_list = [KEYWORDS_POOL[skill] for skill in selected_skills]
        combined_pattern = "|".join(pattern_list)
        df = df[df['combined_text_lower'].str.contains(combined_pattern, regex=True)]
    
    total_jobs = len(df)
    if total_jobs == 0:
        return None, None, None, 0, df
    
    skills_to_check = selected_skills if selected_skills else KEYWORDS_POOL.keys()
    skills_results = {}
    for skill in skills_to_check:
        pattern = KEYWORDS_POOL[skill]
        skills_results[skill] = df['combined_text_lower'].apply(lambda x: bool(re.search(pattern, x))).sum()
        
    remote_count = df['combined_text_lower'].apply(lambda x: bool(re.search(r'دورکاری|ریموت|remote|دورکار', x))).sum()
    hybrid_count = df['combined_text_lower'].apply(lambda x: bool(re.search(r'هیبرید|hybrid|نیمه‌حضوری', x))).sum()
    onsite_count = total_jobs - (remote_count + hybrid_count)
    
    df['extracted_exp'] = df['combined_text_lower'].apply(extract_experience)
    avg_exp = df['extracted_exp'].mean()
    
    modes = {"Remote": remote_count, "Hybrid": hybrid_count, "Onsite/Other": onsite_count}
    return skills_results, modes, avg_exp, total_jobs, df

# ==========================================
# Streamlit UI
# ==========================================

st.set_page_config(page_title="Smart Job Market Dashboard", layout="wide", page_icon="📊")

if 'scraped_data' not in st.session_state:
    st.session_state['scraped_data'] = None

st.title("📊 Integrated Job Posting Scraper & Analyzer")
st.markdown("This system scrapes JobVision postings in real-time and analyzes them using AI.")

st.sidebar.header("⚙️ Settings & Filters Panel")

selected_category_names = st.sidebar.multiselect(
    "1. Select Job Category (Required):",
    options=list(CATEGORIES_POOL.keys()),
    default=["توسعه‌دهنده (Developer)"]
)

time_options = {"Today": 0, "Last 2 Days": 2, "Last Week": 7, "Last Month": 30}
selected_time_name = st.sidebar.radio(
    "2. Job Posting Timeframe:",
    options=list(time_options.keys()),
    index=2 
)
max_days = time_options[selected_time_name]

selected_skills = st.sidebar.multiselect(
    "3. Filter by Specific Skills (Optional):",
    options=list(KEYWORDS_POOL.keys()),
    help="If left empty, all ads will be extracted and all skills analyzed."
)

start_btn = st.sidebar.button("🚀 Start Scraping & Analysis", use_container_width=True, type="primary")

# --- App Logic ---
if start_btn:
    if not selected_category_names:
        st.error("Error: Please select at least one job category.")
    else:
        scraped_data = []
        progress_text = st.empty()
        
        with st.spinner('Initializing the scraper bot (Please wait)...'):
            driver = setup_driver()
            try:
                all_job_links = set()
                for cat_name in selected_category_names:
                    cat_url = CATEGORIES_POOL[cat_name]
                    progress_text.info(f"Searching in category: {cat_name} ...")
                    for page in range(1, MAX_PAGES + 1):
                        page_url = f"{cat_url}?page={page}"
                        soup = safe_get(driver, page_url)
                        if not soup: break
                        found_links_on_page = 0
                        for a_tag in soup.find_all('a', href=True):
                            href = a_tag['href']
                            if '/jobs/' in href and '/category/' not in href and '/keyword/' not in href:
                                parent = a_tag
                                for _ in range(5):
                                    if parent.parent: parent = parent.parent
                                card_text = parent.get_text()
                                if is_recent_job(card_text, max_days):
                                    full_url = f"https://jobvision.ir{href}" if not href.startswith('http') else href
                                    all_job_links.add(full_url)
                                    found_links_on_page += 1
                        if found_links_on_page == 0:
                            break 
                
                total_links = len(all_job_links)
                if total_links == 0:
                    st.warning("No new jobs found in these categories for the selected timeframe.")
                else:
                    progress_bar = st.progress(0)
                    for idx, url in enumerate(all_job_links):
                        progress_text.text(f"Extracting job {idx+1} of {total_links}...")
                        job_data = extract_job_details(driver, url)
                        if job_data and job_data['title'] != "N/A":
                            scraped_data.append(job_data)
                        progress_bar.progress((idx + 1) / total_links)
                    
                    progress_text.success(f"Scraping completed successfully. Found {len(scraped_data)} valid jobs.")
                    st.session_state['scraped_data'] = scraped_data
            finally:
                driver.quit()

# --- نمایش داشبورد ---
if st.session_state['scraped_data']:
    df = pd.DataFrame(st.session_state['scraped_data'])
    
    with st.spinner('Processing and analyzing data...'):
        skills_res, modes_res, avg_exp, total_ads, filtered_df = analyze_data(df, selected_skills)
    
    # ---------------------------------------------------------
    # 🎯 تولید نام فایل پویا بر اساس تنظیمات کاربر
    # ---------------------------------------------------------
    
    # ۱. استخراج نام‌های انگلیسی دسته‌بندی‌ها
    eng_cats = []
    for cat in selected_category_names:
        match = re.search(r'\((.*?)\)', cat)
        if match:
            eng_cats.append(match.group(1).strip())
        else:
            eng_cats.append(cat)
    cats_str = "(" + " - ".join(eng_cats) + ")"
    
    # ۲. نگاشت نام بازه زمانی به مخفف‌ها
    time_abbr_map = {"Today": "1D", "Last 2 Days": "2D", "Last Week": "W", "Last Month": "M"}
    time_str = time_abbr_map.get(selected_time_name, "Unknown")
    
    # ۳. فیلتر مهارت‌ها (حذف کاراکترهای غیرمجاز در ویندوز)
    if selected_skills:
        safe_skills = [re.sub(r'[\\/*?:"<>|]', '', s).strip() for s in selected_skills]
        skills_str = "_".join(safe_skills)
        if len(skills_str) > 80: # جلوگیری از ارور طولانی شدن اسم فایل
            skills_str = skills_str[:80] + "..."
    else:
        skills_str = "AllSkills"
        
    # ۴. تاریخ امروز
    date_str = datetime.now().strftime('%Y-%m-%d')
    
    # ۵. نام نهایی پایه برای هر دو فایل
    dynamic_filename_base = f"{cats_str}_{time_str}_{skills_str}_{date_str}"
    # ---------------------------------------------------------

    if total_ads == 0:
        st.warning("The found job postings did not contain your selected skills.")
    else:
        st.markdown("---")
        st.subheader(f"📈 Job Market Analysis Results (Matched Ads: {total_ads})")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Analyzed Ads", total_ads)
        col2.metric("Avg Required Experience", f"{avg_exp:.1f} years" if pd.notnull(avg_exp) else "Unknown")
        col3.metric("Remote Positions", modes_res.get("Remote", 0))
        col4.metric("Hybrid Positions", modes_res.get("Hybrid", 0))

        st.markdown("---")
        col_chart, col_data = st.columns([2, 1])

        with col_chart:
            st.write("**Skills Demand Chart**")
            skills_df = pd.DataFrame(list(skills_res.items()), columns=['Skill', 'Count']).sort_values(by='Count', ascending=False)
            skills_df = skills_df[skills_df['Count'] > 0] 
            skills_df['Percentage'] = (skills_df['Count'] / total_ads) * 100
            
            if not skills_df.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.barplot(x="Percentage", y="Skill", data=skills_df, palette="plasma", ax=ax)
                ax.set_xlabel("Percentage of Ads (%)")
                ax.set_ylabel("Technology / Skill")
                for p in ax.patches:
                    width = p.get_width()
                    ax.text(width + 0.5, p.get_y() + p.get_height()/2 + 0.1, f'{width:.1f}%', ha="left", va="center", fontsize=9)
                
                st.pyplot(fig)
                
                img_buffer = io.BytesIO()
                fig.savefig(img_buffer, format="png", bbox_inches="tight", dpi=300)
                img_buffer.seek(0)
                st.download_button(
                    label="🖼️ Download Chart Image (PNG)",
                    data=img_buffer,
                    file_name=f"{dynamic_filename_base}.png",
                    mime="image/png",
                    use_container_width=True
                )
            else:
                st.info("None of the listed skills were found in these ads.")

        with col_data:
            st.write("**Collaboration Type Details**")
            modes_df = pd.DataFrame(list(modes_res.items()), columns=["Collaboration Type", "Count"])
            st.dataframe(modes_df, use_container_width=True)
            
            st.write("**Extracted Data (Raw)**")
            st.dataframe(filtered_df[['title', 'city', 'url']].head(10), use_container_width=True)

        excel_buffer = io.BytesIO()
        export_df = filtered_df.drop(columns=['combined_text', 'combined_text_lower', 'extracted_exp'], errors='ignore')

        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            export_df.to_excel(writer, sheet_name="Scraped Jobs", index=False)
            modes_df.to_excel(writer, sheet_name="Collaboration Modes", index=False)
            
        excel_buffer.seek(0)

        st.download_button(
            label="📥 Download Data (Excel - Multiple Sheets)",
            data=excel_buffer,
            file_name=f"{dynamic_filename_base}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )