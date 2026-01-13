import pandas as pd
import requests
import time
from urllib.parse import quote

FOLDER = "data/"
INPUT_CSV = "tdf_stages_enriched_wiki_final.csv" 
OUTPUT_CSV = "stages_clean.csv"
LOG_FILE = "removed_uris.txt"
MIN_YEAR = 2009
SPARQL_ENDPOINT = "https://dbpedia.org/sparql"
BATCH_SIZE = 50

def get_full_url(uri_fragment):
    s = uri_fragment.strip()
    if not s: return None
    return f"http://dbpedia.org/resource/{s}"

def check_uris_via_sparql(uri_list):
    if not uri_list:
        return set()

    values_clause = " ".join([f"<{u}>" for u in uri_list])
    
    query = f"""
    SELECT DISTINCT ?s WHERE {{
      VALUES ?s {{ {values_clause} }}
      ?s ?p ?o .
    }}
    """

    try:
        params = {'query': query, 'format': 'json'}
        headers = {'User-Agent': 'TDF-Data-Cleaner/1.0 (Student Lab)'}
        
        r = requests.get(SPARQL_ENDPOINT, params=params, headers=headers, timeout=10)
        
        if r.status_code != 200:
            print(f"  [!] SPARQL Error {r.status_code}: {r.text[:100]}")
            return set()
            
        data = r.json()
        valid_uris = set()
        for binding in data['results']['bindings']:
            valid_uris.add(binding['s']['value'])
            
        return valid_uris
        
    except Exception as e:
        print(f"  [!] Connection exception: {e}")
        return set()

def process_csv():
    print(f"Reading {FOLDER + INPUT_CSV}...")
    try:
        df = pd.read_csv(FOLDER + INPUT_CSV)
    except FileNotFoundError:
        print("Error: Input CSV file not found.")
        return

    print(f"Filtering rows before {MIN_YEAR}...")
    df = df[df['Year'] >= MIN_YEAR].copy()

    print("Extracting unique URIs for batch checking...")
    uri_columns = ['Start_City_URI', 'End_City_URI', 'Mountain_URI']
    
    all_raw_uris = set()
    
    for col in uri_columns:
        if col not in df.columns: continue
        for val in df[col].dropna().astype(str):
            if not val.strip(): continue
            parts = val.split(',')
            for p in parts:
                full_url = get_full_url(p)
                if full_url:
                    all_raw_uris.add(full_url)
    
    print(f"Found {len(all_raw_uris)} unique URIs to validate.")

    valid_map = set()
    uri_list = list(all_raw_uris)
    
    for i in range(0, len(uri_list), BATCH_SIZE):
        batch = uri_list[i : i + BATCH_SIZE]
        print(f"  > Checking batch {i}-{i+len(batch)} via SPARQL...")
        
        valid_batch = check_uris_via_sparql(batch)
        valid_map.update(valid_batch)
        
        time.sleep(0.1)

    print(f"Validation complete. {len(valid_map)} URIs confirmed valid.")

    print("Cleaning CSV entries...")
    removed_log = []
    
    for index, row in df.iterrows():
        for col in uri_columns:
            if col not in df.columns or pd.isna(row[col]): continue
            
            original_val = str(row[col])
            if not original_val.strip(): continue
            
            parts = [p.strip() for p in original_val.split(',')]
            valid_parts = []
            
            for p in parts:
                full_url = get_full_url(p)
                if full_url in valid_map:
                    valid_parts.append(p)
                else:
                    removed_log.append(f"Row {index} [{col}]: Removed '{p}' (Not found in DBpedia)")
            
            new_val = ",".join(valid_parts)
            df.at[index, col] = new_val

    print(f"Saving cleaned data to {OUTPUT_CSV}...")
    df.to_csv(OUTPUT_CSV, index=False)
    
    print(f"Saving removed URI log to {LOG_FILE}...")
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Total URIs removed: {len(removed_log)}\n")
        f.write("\n".join(removed_log))

    print("Done!")

if __name__ == "__main__":
    process_csv()
