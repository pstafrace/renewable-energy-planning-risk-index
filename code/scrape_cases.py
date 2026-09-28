import requests
import random
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
import re
import time
import concurrent.futures

BASE_URL = "https://www.austlii.edu.au"
VCAT_INDEX = "https://www.austlii.edu.au/au/cases/vic/VCAT/"
VSC_INDEX = "https://www.austlii.edu.au/au/cases/vic/VSC/"

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(connect=5, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

KEYWORDS = ["wind farm", "solar farm", "renewable energy"]
# Set to None to scrape all years, or a specific int like 3 to only scrape the last 3 years of cases
YEARS_TO_SCRAPE_PER_COURT = 10 

def get_years_from_index(index_url):
    response = session.get(index_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    years = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if re.match(r"^\d{4}/?$", href):
            years.append(index_url + href if href.endswith('/') else index_url + href + '/')
    return sorted(list(set(years)), reverse=True)

def get_cases_from_year(year_url):
    response = session.get(year_url, headers=HEADERS, timeout=10)
    soup = BeautifulSoup(response.text, "html.parser")
    cases = []
    for a in soup.find_all("a"):
        href = a.get("href", "")
        if "/viewdoc/" in href and href.endswith(".html"):
            text = a.text.strip()
            if text:
                cases.append((text, BASE_URL + href))
    return cases

print("Fetching year indices...")
vcat_years = get_years_from_index(VCAT_INDEX)
vsc_years = get_years_from_index(VSC_INDEX)

if YEARS_TO_SCRAPE_PER_COURT:
    vcat_years = vcat_years[:YEARS_TO_SCRAPE_PER_COURT]
    vsc_years = vsc_years[:YEARS_TO_SCRAPE_PER_COURT]

all_years = vcat_years + vsc_years
print(f"Found {len(all_years)} year pages to scan across VCAT and VSC.")

all_case_links = []
print("Queueing all case links from year pages...")
for year_url in tqdm(all_years): 
    all_case_links.extend(get_cases_from_year(year_url))
    time.sleep(0.1)

all_case_links = list(set(all_case_links))
random.shuffle(all_case_links)
print(f"Total cases queued to filter: {len(all_case_links)}")

results = []

def fetch_and_check(case):
    title, url = case
    try:
        r = session.get(url, headers=HEADERS, timeout=10)
        lower_text = r.text.lower()
        if not any(kw.lower() in lower_text for kw in KEYWORDS):
            return None

        s = BeautifulSoup(r.text, "html.parser")
        paragraphs = s.find_all("p")
        text = " ".join(p.text for p in paragraphs[:20])

        return {
            "case_name": title,
            "url": url,
            "summary_text": text
        }
    except Exception:
        return None

try:
    print(f"Scanning cases for keywords concurrently...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(fetch_and_check, case) for case in all_case_links]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            res = future.result()
            if res:
                results.append(res)
except KeyboardInterrupt:
    print("\nInterrupted by user. Saving whatever was collected so far...")

print("Classifying cases...")
def classify_case(text):
    tech = None
    if "wind" in text.lower():
        tech = "Wind"
    elif "solar" in text.lower():
        tech = "Solar"
    elif "battery" in text.lower():
        tech = "Battery"

    outcome = None
    if "refuse" in text.lower():
        outcome = "Refused"
    elif "permit granted" in text.lower():
        outcome = "Approved"

    clause = None
    if "52.32" in text:
        clause = "Clause 52.32"

    return tech, outcome, clause

def extract_year(text):
    match = re.search(r"\b(20\d{2})\b", text)
    if match:
        return match.group()
    return None

df = pd.DataFrame(results)
if not df.empty:
    df["technology"], df["outcome"], df["planning_clause"] = zip(
        *df["summary_text"].apply(classify_case)
    )
    df["year"] = df["summary_text"].apply(extract_year)

    def friction_score(row):
        score = 0
        if row["outcome"] == "Refused":
            score += 2
        if row["planning_clause"] == "Clause 52.32":
            score += 1
        return score

    df["friction_score"] = df.apply(friction_score, axis=1)

    df.to_csv("renewable_energy_cases_victoria.csv", columns=['case_name', 'url', 'summary_text'], index=False)
    print(f"Dataset created with {len(df)} structured cases.")
else:
    print("Dataset not created. 0 cases found matching keywords.")





