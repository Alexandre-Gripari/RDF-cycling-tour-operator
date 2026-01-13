import pandas as pd
import re

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
    return str(val).strip().replace(" ", "_").replace("'", "").replace(",", "_")

def is_higher_than_column(df):
    altitudes_numeric = pd.to_numeric(df['Altitude'], errors='coerce')
    
    temp_ref = pd.DataFrame({'alt': altitudes_numeric, 'uri': df['URI_Suffix']})
    temp_ref = temp_ref.dropna(subset=['alt']).sort_values('alt').drop_duplicates('alt')
    altitude_to_uri = pd.Series(temp_ref['uri'].values, index=temp_ref['alt']).to_dict()
    
    unique_alts = sorted(altitudes_numeric.dropna().unique())
    prev_alt_map = {unique_alts[i]: unique_alts[i-1] for i in range(1, len(unique_alts))}
    
    df['Higher_Than'] = altitudes_numeric.map(prev_alt_map).map(altitude_to_uri)

df_m = pd.read_csv('data/mountains_details_final.csv')

df_m['lat'] = df_m['Coordonnées'].apply(lambda x: dms_to_decimal(x.split(',')[0]))
df_m['long'] = df_m['Coordonnées'].apply(lambda x: dms_to_decimal(x.split(',')[1]))
df_m[['Mountain_Range', 'Specific_Mountain_Range']] = df_m['Massif'].apply(lambda x: pd.Series(parse_massif(x)))

df_m['URI_Suffix'] = df_m['Nom'].apply(make_safe_uri)

df_m['Altitude'] = df_m['Altitude'].astype(str).str.replace(r'\D', '', regex=True)

is_higher_than_column(df_m)

df_m.to_csv('mountains_ready.csv', index=False)

df_s = pd.read_csv('data/stages_clean.csv')

df_s['Path_ID'] = df_s.apply(lambda row: f"{make_safe_uri(row['Start_City'])}_{make_safe_uri(row['End_City'])}_Path", axis=1)

df_s.to_csv('stages_ready.csv', index=False)
