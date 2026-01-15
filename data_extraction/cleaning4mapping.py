import pandas as pd
import re
import unicodedata

def dms_to_decimal(dms_str):
    regex = r"(\d+)°\s*(\d+)′\s*(\d+)″\s*([nord|sud|est|ouest|N|S|E|W]+)"
    match = re.search(regex, str(dms_str), re.IGNORECASE)
    if not match: return None
    deg, minutes, seconds, direction = match.groups()
    decimal = float(deg) + float(minutes)/60 + float(seconds)/3600
    if direction.lower() in ['sud', 's', 'ouest', 'w']: decimal = -decimal
    return decimal

def parse_massif(val):
    val = str(val).strip()
    match = re.search(r'^(.*)\s*\((.*)\)\s*$', val)
    if match: return match.group(2).strip(), match.group(1).strip()
    return val, None

def make_safe_uri(val):
    if pd.isna(val): return None
    val = str(val).strip().replace(" ", "_").replace("'", "").replace(",", "_")
    return unicodedata.normalize('NFD', val).encode('ascii', 'ignore').decode("utf-8")

def is_higher_than_column(df):
    altitudes_numeric = pd.to_numeric(df['Altitude'], errors='coerce')
    
    temp_ref = pd.DataFrame({'alt': altitudes_numeric, 'id': df['Nom'].apply(make_safe_uri)})
    
    temp_ref = temp_ref.dropna(subset=['alt']).sort_values('alt').drop_duplicates('alt')
    
    altitude_to_id = pd.Series(temp_ref['id'].values, index=temp_ref['alt']).to_dict()
    
    unique_alts = sorted(altitudes_numeric.dropna().unique())
    prev_alt_map = {unique_alts[i]: unique_alts[i-1] for i in range(1, len(unique_alts))}
    
    df['Higher_Than'] = altitudes_numeric.map(prev_alt_map).map(altitude_to_id)

def normalize_key(text):
    if pd.isna(text) or text == "":
        return None
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')
    return re.sub(r'[^a-z0-9]', '', text.lower())

def check_uri(df_m, df_s):
    valid_uris = set()
    for uri_entry in df_s['Mountain_URI'].dropna():
        for uri in str(uri_entry).split(','):
            clean_uri = uri.strip()
            if clean_uri:
                valid_uris.add(clean_uri)

    uri_map = {}
    for uri in valid_uris:
        key = normalize_key(uri)
        if key:
            uri_map[key] = uri

    df_m['URI_Suffix'] = df_m['Nom'].apply(lambda x: uri_map.get(normalize_key(x), None))

def calculate_difficulties(elevation_gain):
    if elevation_gain < 1000:
        return 'Easy'
    elif 1000 <= elevation_gain < 2000:
        return 'Moderate'
    elif 2000 <= elevation_gain < 3000:
        return 'Hard'
    else:
        return 'VeryHard'

df_m = pd.read_csv('data/mountains_details_final.csv')
df_s = pd.read_csv('data/stages_clean.csv')

df_m['lat'] = df_m['Coordonnées'].apply(lambda x: dms_to_decimal(x.split(',')[0]))
df_m['long'] = df_m['Coordonnées'].apply(lambda x: dms_to_decimal(x.split(',')[1]))
df_m[['Mountain_Range', 'Specific_Mountain_Range']] = df_m['Massif'].apply(lambda x: pd.Series(parse_massif(x)))
df_m['Altitude'] = df_m['Altitude'].astype(str).str.replace(r'\D', '', regex=True)

is_higher_than_column(df_m)
check_uri(df_m, df_s)

df_m.to_csv('mountains_ready.csv', index=False)

df_s['Path_ID'] = df_s.apply(lambda row: f"{make_safe_uri(row['Start_City'])}_{make_safe_uri(row['End_City'])}_Path", axis=1)

df_s['Mountain_Name'] = df_s['Mountain_Name'].apply(lambda x: ','.join([str(name).strip().replace(" ", "_") for name in str(x).split(',')]))

df_s['Difficulty'] = df_s['Elevation_Gain'].apply(lambda x: calculate_difficulties(float(x)) if pd.notna(x) else None)

df_s = df_s.dropna(subset=['Start_City_URI', 'End_City_URI'])
invalid_values = ['unknown', '', 'nan']
mask_end = df_s['End_City_URI'].astype(str).str.strip().str.lower().isin(invalid_values)
mask_start = df_s['Start_City_URI'].astype(str).str.strip().str.lower().isin(invalid_values)
df_s = df_s[~mask_end & ~mask_start]

df_s.to_csv('stages_ready.csv', index=False)
