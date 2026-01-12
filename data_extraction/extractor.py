import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

DATA_FOLDER = "data/"
INPUT_FILE = "tdf_stages.csv"
OUTPUT_FILE = "tdf_stages_enriched_wiki_final.csv"

def clean_distance(dist_str):
    if pd.isna(dist_str): return 0
    match = re.search(r"(\d+(\.\d+)?)", str(dist_str))
    return float(match.group(1)) if match else 0

def split_course(course_str):
    if pd.isna(course_str): return "Unknown", "Unknown"
    parts = re.split(r" to | - ", str(course_str))
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return parts[0].strip(), "Unknown"

def dbpedia_format(name):
    if not name: return ""
    return name.strip().replace(" ", "_").replace("’", "'")

def format_complex_city_uri(name):
    if pd.isna(name) or not name: return ""
    
    match = re.match(r"^(.*?)\s*\((.*?)\)$", str(name).strip())
    
    if match:
        main_part = dbpedia_format(match.group(1))
        detail_part = dbpedia_format(match.group(2))
        return f"{main_part},{detail_part}"
    else:
        return dbpedia_format(name)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_wiki_url(year, stage):
    if str(stage) == "1":
        stage_str = "1re"
    else:
        stage_str = f"{stage}e"
    base_name = f"{stage_str}_étape_du_Tour_de_France_{year}"
    encoded_name = urllib.parse.quote(base_name)
    return f"https://fr.wikipedia.org/wiki/{encoded_name}"

def scrape_stage_data(year, stage, is_mountain_stage=False):
    url = get_wiki_url(year, stage)
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None, []

        soup = BeautifulSoup(response.content, 'html.parser')
        
        elevation = 0
        
        for row in soup.find_all('tr'):
            row_text = row.get_text().strip()
            
            if 'dénivelé' in row_text.lower():
                clean_text = row_text.replace('\xa0', '').replace(' ', '').replace(',', '')
                
                match = re.search(r'(\d{3,5})', clean_text)
                if match:
                    elevation = int(match.group(1))
                    break

        if not is_mountain_stage:
            return elevation, []

        mountains = []
        content_text = soup.get_text()
        mountain_pattern = re.compile(r'((?:Col |Côte |Montée |Alpe |Port ).+?)\s?\(km')
        found = mountain_pattern.findall(content_text)
        seen = set()
        for m in found:
            m_clean = m.strip().replace("d'", "d'").replace("’", "'")
            if len(m_clean) < 50 and m_clean not in seen:
                mountains.append(m_clean)
                seen.add(m_clean)

        return elevation, mountains
    except Exception as e:
        print(f"Error scraping {year} stage {stage}: {e}")
        return None, []

print("1. Reading CSV...")
df = pd.read_csv(DATA_FOLDER + INPUT_FILE)

print("2. Cleaning Data (Splitting Cities)...")
df[['Start_City', 'End_City']] = df['Course'].apply(lambda x: pd.Series(split_course(x)))
df['Distance_Value'] = df['Distance'].apply(clean_distance)

df['Elevation_Gain'] = 0
df['Mountain_Name'] = ""

i=0
total_rows = len(df)

print("3. Scraping Wikipedia for enrichment...")

for index, row in df.iterrows():
    type_str = str(row['Type']).lower()

    i += 1
    if i % 100 == 0 or i == total_rows:
        print(f"   Processing row {i}/{total_rows} - Year: {row['Year']}, Stage: {row['Stage']}")

    ele, mts = scrape_stage_data(row['Year'], row['Stage'], "mountain" in type_str)
    
    if ele: 
        df.at[index, 'Elevation_Gain'] = ele
    else:
        if "high" in type_str: df.at[index, 'Elevation_Gain'] = 4000
        elif "mountain" in type_str: df.at[index, 'Elevation_Gain'] = 2500
        
    if mts: 
        df.at[index, 'Mountain_Name'] = ", ".join(mts)

def clean_mountains_for_uri(mt_string):
    if not mt_string: return ""
    names = str(mt_string).split(", ")
    uris = [dbpedia_format(n) for n in names]
    return ",".join(uris)

print("4. Formatting URIs...")

df['Start_City_URI'] = df['Start_City'].apply(format_complex_city_uri)
df['End_City_URI'] = df['End_City'].apply(format_complex_city_uri)
df['Mountain_URI'] = df['Mountain_Name'].apply(clean_mountains_for_uri)

output_columns = [
    'Year', 'Stage', 'Start_City', 'End_City', 
    'Distance_Value', 'Elevation_Gain', 
    'Mountain_Name', 'Start_City_URI', 'End_City_URI', 'Mountain_URI'
]

df.to_csv(DATA_FOLDER + OUTPUT_FILE, columns=output_columns, index=False)
print(f"\nSaved to '{DATA_FOLDER + OUTPUT_FILE}'.")
