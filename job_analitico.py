import os
import glob
import re
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from datetime import datetime

# ۱. تنظیمات پوشه ورودی
SOURCE_DIR = "data_files"

# ۲. بانک کلمات کلیدی فوق‌العاده جامع (تکنولوژی‌ها، ابزارها و مفاهیم نوین)
KEYWORDS_POOL = {
    # زبان‌ها و استک‌های اصلی
    'Python': r'\bpython\b|پایتون',
    'C# (.NET)': r'\bc#\b|\b\.net\b|دات‌نت Core',
    'Java': r'\bjava\b|جاوا(?!اسکریپت)',
    'Go / Golang': r'\bgo\b|\bgolang\b|گولنگ',
    'PHP / Laravel': r'\bphp\b|پی‌اچ‌پ|laravel|لاراول',
    'JavaScript': r'\bjavascript\b|جاوااسکریپت|\bjs\b',
    'TypeScript': r'\btypescript\b|تایپ‌اسکریپت|\bts\b',
    
    # هوش مصنوعی و کدنویسی مدرن (AI & AI-First Dev)
    'LLM / AI / GPT': r'\bllm\b|\bai\b|هوش مصنوعی|openai|chatgpt|gemini',
    'Claude / Anthropic': r'\bclaude\b|کلود',
    'Vibe Coding / Prompt Engineering': r'vibe\s?coder|وایب کدینگ|prompt\s?engineering|مهندسی پرامپت',
    'AI Coding Tools (Cursor/Copilot)': r'cursor|copilot|claudecode|v0\.dev|lovable|bolt\.new',
    'LangChain / LangGraph': r'langchain|langgraph|crewai|ایجنت',
    'RAG / Vector Databases': r'\brag\b|vector\s?database|qdrant|chromadb',
    'Machine / Deep Learning': r'machine\s?learning|deep\s?learning|یادگیری ماشین|pytorch|tensorflow|scikit',
    'Computer Vision / OpenCV': r'computer\s?vision|opencv|بینایی ماشین|پردازش تصویر',
    
    # فرانت‌اند و موبایل
    'React / Next.js': r'react|ری‌اکت|next\.js|نکست',
    'Angular': r'angular|انگولار',
    'Vue.js': r'vue\.js|ویو جی اس',
    'Flutter / Dart': r'flutter|فلاتر|\bdart\b',
    'WordPress': r'wordpress|وردپرس',
    
    # دیتابیس و پردازش کلان‌داده
    'SQL Server / T-SQL': r'sql\s?server|t-sql|اس‌کیو‌ال سرور',
    'PostgreSQL / MySQL': r'postgresql|postgres|mysql|پستگرس',
    'NoSQL (MongoDB/Redis)': r'mongodb|redis|مونگو|ردیس',
    'Big Data (Spark/Kafka)': r'spark|kafka|hadoop|کافکا|اسپارک',
    
    # معماری و دوآپس
    'Docker / Kubernetes': r'docker|kubernetes|داکر|کوبرنتیز',
    'Microservices / MQ': r'microservice|میکروسرویس|rabbitmq|message\s?queue|صف پیام',
    'Clean Code / SOLID / DDD': r'clean\s?code|solid|ddd|کد تمیز|معماری تمیز',
    
    # ابزارهای داده و فرآیند
    'Power BI / BI': r'power\s?bi|هوش تجاری|\bbi\b|dashboards',
    'BPMS / BPMN': r'bpms|bpmn|مدل‌سازی فرآیند',
    
    # حوزه‌های خاص
    'FinTech / Blockchain / ERP': r'fintech|فین‌تک|blockchain|بلاکچین|رمز\s?ارز|crypto|erp|ای‌آرپی'
}

def load_all_files(directory):
    """Load all Excel and CSV files simultaneously"""
    all_files = glob.glob(os.path.join(directory, "*.csv")) + \
                glob.glob(os.path.join(directory, "*.xlsx")) + \
                glob.glob(os.path.join(directory, "*.xls"))
    
    combined_df = pd.DataFrame()
    for file in all_files:
        try:
            print(f"🔄 Loading: {os.path.basename(file)}")
            if file.endswith('.csv'):
                df = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip')
            else:
                df = pd.read_excel(file)
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        except Exception as e:
            print(f"❌ Error reading {os.path.basename(file)}: {e}")
    return combined_df

def extract_experience(text):
    """استخراج سال سابقه کار با الگوهای عددی فارسی و انگلیسی"""
    # جستجوی الگوهایی مثل "5 سال سابقه" یا "حداقل 3 سال" یا "experience: 4 years"
    match = re.search(r'(\d+)\s*سال\s*(?:سابقه|تجربه)|experience\s*:?\s*(\d+)', text, re.IGNORECASE)
    if match:
        # برگشت دادن اولین عددی که پیدا شده
        nums = [int(s) for s in match.groups() if s is not None]
        return nums[0] if nums else None
    return None

def analyze_data(df):
    """آنالیز جامع کلمات کلیدی، نوع همکاری (دورکاری) و سابقه کار"""
    text_cols = [col for col in df.columns if col in ['description_and_responsibilities', 'key_indicators', 'title', 'description']]
    if not text_cols:
        text_cols = df.select_dtypes(include=['object']).columns.tolist()
        
    df['combined_text'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)
    df['combined_text_lower'] = df['combined_text'].str.lower()
    
    total_jobs = len(df)
    
    # الف) آنالیز کلمات کلیدی مهارت‌ها
    skills_results = {}
    for skill, pattern in KEYWORDS_POOL.items():
        match_count = df['combined_text_lower'].apply(lambda x: bool(re.search(pattern, x))).sum()
        skills_results[skill] = match_count
        
    # ب) آنالیز نوع همکاری (دورکاری / حضوری)
    remote_count = df['combined_text_lower'].apply(lambda x: bool(re.search(r'دورکاری|ریموت|remote|دورکار', x))).sum()
    hybrid_count = df['combined_text_lower'].apply(lambda x: bool(re.search(r'هیبرید|hybrid|نیمه‌حضوری', x))).sum()
    # اگر کلمه حضوری باشد یا عبارات دورکاری نباشد، حضوری فرض می‌شود (برای سادگی تحلیل)
    onsite_count = total_jobs - remote_count
    
    # ج) آنالیز سابقه کار
    df['extracted_exp'] = df['combined_text_lower'].apply(extract_experience)
    valid_exp_df = df['extracted_exp'].dropna()
    avg_exp = valid_exp_df.mean() if not valid_exp_df.empty else None
    
    return skills_results, {"Remote": remote_count, "Hybrid": hybrid_count, "Onsite/Other": onsite_count}, avg_exp, total_jobs

def generate_reports(skills, job_types, avg_exp, total_jobs):
    """Print text reports and save to Excel and Image"""
    print("\n" + "="*50)
    print(f"📊 Final Tech Job Market Analysis Report (Total Ads: {total_jobs})")
    print("="*50)
    
    if avg_exp:
        print(f"⏱️ Average Required Experience: {avg_exp:.1f} years")
    else:
        print("⏱️ No specific experience required found in the ads.")
        
    print("-"*50)
    print("🏢 Job Collaboration Models (Market Status):")
    for mode, count in job_types.items():
        pct = (count / total_jobs) * 100
        print(f"   🔹 {mode}: {count} ads ({pct:.1f}%)")
        
    print("-"*50)
    print("🛠️ Skills Demand (Sorted by highest):")
    skills_df = pd.DataFrame(skills.items(), columns=['Skill', 'Count']).sort_values(by='Count', ascending=False)
    skills_df['Percentage'] = (skills_df['Count'] / total_jobs) * 100
    
    for _, row in skills_df.iterrows():
        print(f"   🔹 {row['Skill']}: {row['Count']} occurrences ({row['Percentage']:.1f}%)")
        
    # --- ساخت پوشه خروجی بر اساس تاریخ ---
    today_date = datetime.now().strftime("%Y-%m-%d")
    output_dir = os.path.join("analysis", today_date)
    os.makedirs(output_dir, exist_ok=True)
    
    excel_path = os.path.join(output_dir, "advanced_market_analysis.xlsx")
    image_path = os.path.join(output_dir, "comprehensive_skills_chart.png")

    # --- ۱. ذخیره در اکسل (اضافه شدن شیت خلاصه وضعیت) ---
    summary_data = {
        "Metric": ["Total Ads", "Average Experience (Years)", "Remote Jobs", "Hybrid Jobs", "Onsite/Other Jobs"],
        "Value": [
            total_jobs, 
            round(avg_exp, 1) if avg_exp else "N/A",
            f"{job_types.get('Remote', 0)} ({job_types.get('Remote', 0)/total_jobs*100:.1f}%)",
            f"{job_types.get('Hybrid', 0)} ({job_types.get('Hybrid', 0)/total_jobs*100:.1f}%)",
            f"{job_types.get('Onsite/Other', 0)} ({job_types.get('Onsite/Other', 0)/total_jobs*100:.1f}%)"
        ]
    }
    summary_df = pd.DataFrame(summary_data)

    with pd.ExcelWriter(excel_path) as writer:
        summary_df.to_excel(writer, sheet_name="General Summary", index=False) # شیت جدید اضافه شد
        skills_df.to_excel(writer, sheet_name="Skills Demand", index=False)
        pd.DataFrame(job_types.items(), columns=["Job Mode", "Count"]).to_excel(writer, sheet_name="Job Modes", index=False)
            
    print(f"\n💾 Structured reports saved to '{excel_path}'.")
    
    # --- ۲. رسم نمودار و اضافه کردن اطلاعات به عکس ---
    # عرض تصویر را کمی بیشتر کردیم (16) تا جا برای باکس متن باز شود
    plt.figure(figsize=(16, 10)) 
    sns.set_theme(style="whitegrid")
    
    ax = sns.barplot(x="Percentage", y="Skill", data=skills_df, palette="plasma")
    plt.title(f"Comprehensive Tech Skills Demand Analysis (Based on {total_jobs} Ads)", fontsize=16, fontweight='bold')
    plt.xlabel("Percentage (%) of Job Openings", fontsize=12)
    plt.ylabel("Core Skills & Paradigms", fontsize=12)
    
    for p in ax.patches:
        width = p.get_width()
        ax.text(width + 0.3, p.get_y() + p.get_height()/2 + 0.1, f'{width:.1f}%', ha="left", va="center", fontsize=9)
        
    # --- ساخت باکس اطلاعات روی عکس ---
    exp_text = f"{avg_exp:.1f} years" if avg_exp else "N/A"
    box_text = (
        f"📌 MARKET SUMMARY\n"
        f"-----------------------\n"
        f"Total Ads: {total_jobs}\n"
        f"Avg Exp: {exp_text}\n\n"
        f"🏢 JOB MODES:\n"
        f"Remote: {job_types.get('Remote', 0)} ({job_types.get('Remote', 0)/total_jobs*100:.1f}%)\n"
        f"Hybrid: {job_types.get('Hybrid', 0)} ({job_types.get('Hybrid', 0)/total_jobs*100:.1f}%)\n"
        f"Onsite: {job_types.get('Onsite/Other', 0)} ({job_types.get('Onsite/Other', 0)/total_jobs*100:.1f}%)"
    )
    
    # تنظیم کادر پلات برای باز شدن فضا در سمت راست (اختصاص 25 درصد فضا به متن)
    plt.subplots_adjust(right=0.75) 
    # قرار دادن متن در فضای ایجاد شده
    plt.figtext(0.77, 0.5, box_text, fontsize=12, va='center', family='monospace',
                bbox=dict(facecolor='#f0f4f8', alpha=0.9, edgecolor='black', boxstyle='round,pad=1'))
                
    plt.savefig(image_path, dpi=300)
    plt.show()

if __name__ == "__main__":
    if not os.path.exists(SOURCE_DIR):
        os.makedirs(SOURCE_DIR)
        print(f"📁 Folder '{SOURCE_DIR}' created. Please place your Excel/CSV files in it and run again.")
    else:
        df_all = load_all_files(SOURCE_DIR)
        if df_all.empty:
            print("⚠️ Folder is empty or no data found.")
        else:
            skills_res, modes_res, avg_experience, total_ads = analyze_data(df_all)
            generate_reports(skills_res, modes_res, avg_experience, total_ads)