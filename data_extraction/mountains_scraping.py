import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import quote

FOLDER = "data/"

INPUT_CSV = "stages_clean.csv"       
OUTPUT_CSV = "mountains_details.csv"
WIKI_BASE_URL = "https://fr.wikipedia.org/wiki/"

HEADERS = {
    "User-Agent": "Mountain-Scraper/1.0 (Educational Project)"
}

def get_mountain_details(mountain_name):
    safe_name = mountain_name.replace(" ", "_")
    url = WIKI_BASE_URL + quote(safe_name)

    data = {
        "Nom": mountain_name,
        "Altitude": None,
        "Massif": None,
        "Coordonnées": None,
        "Pays": None,
        "Région": None,
        "Département": None,
    }

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        
        if response.status_code != 200:
            print(f"Not found {url}")
            return data

        soup = BeautifulSoup(response.text, 'html.parser')

        infobox = soup.find('div', class_='infobox_v3') or soup.find('table', class_='infobox')
        
        if not infobox:
            print(f"No infobox for {mountain_name}")
            return data

        rows = infobox.find_all('tr')
        for row in rows:
            th = row.find('th')
            td = row.find('td')

            if th and td:
                header_text = th.get_text(strip=True).lower()
                value_text = td.get_text(" ", strip=True)

                value_text = re.sub(r'\[.*?\]', '', value_text).strip()

                if "altitude" in header_text:
                    data["Altitude"] = value_text
                elif "massif" in header_text:
                    data["Massif"] = value_text
                elif "coordonnées" in header_text:
                    data["Coordonnées"] = value_text
                elif "pays" in header_text:
                    data["Pays"] = value_text

    except Exception as e:
        print(f"Error {mountain_name}: {e}")

    return data

def main():
    df = pd.read_csv(FOLDER + INPUT_CSV)

    unique_mountains = set()
    
    target_col = 'Mountain_Name'
    
    for item in df[target_col].dropna().astype(str):
        parts = item.split(',')
        for p in parts:
            name = p.strip().replace("_", " ")
            if name:
                unique_mountains.add(name)

    print(f"{len(unique_mountains)} mountains")

    results = []
    total = len(unique_mountains)
    
    for i, mountain in enumerate(unique_mountains, 1):
        print(f"[{i}/{total}] Scraping : {mountain}")
        details = get_mountain_details(mountain)
        results.append(details)
        time.sleep(0.1)

    df_results = pd.DataFrame(results)
    
    cols_order = ["Nom", "Altitude", "Massif", "Coordonnées", "Pays"]
    df_results = df_results[cols_order]
    
    df_results.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

if __name__ == "__main__":
    main()
    