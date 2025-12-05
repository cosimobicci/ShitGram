import pandas as pd
import json
import warnings
from config import PASTEL_HEX_MAP, USER_CONFIG, sanitize_class_name
from data_loader import load_chat_data
from geo_engine import GeoEngine
from map_builder import create_map

warnings.filterwarnings("ignore")

def main():
    # 1. Caricamento Dati
    try:
        df = load_chat_data('_chat.txt')
    except Exception as e:
        print(e)
        return

    unique_users = sorted(df['User'].unique())

    # 2. Setup Motore Geografico
    geo_engine = GeoEngine()
    
    print("📍 Assegnazione Stati ai Punti...")
    df['Country'] = df.apply(lambda row: geo_engine.get_country(row['Latitude'], row['Longitude']), axis=1)

    # 3. Elaborazione Temporale (Core Logic)
    print("⏳ Calcolo Dominio e Timeline...")
    df = df.sort_values(by='Timestamp')
    timeline_dates = df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M').unique().tolist()

    data_by_time = {}
    dominance_by_time = {}
    user_totals_by_time = {}
    geo_dominance_accum = {}
    user_counts_accum = {u: 0 for u in unique_users}

    for time_val in timeline_dates:
        current_slice = df[df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M') == time_val]
        
        # Aggiorna statistiche
        for _, row in current_slice.iterrows():
            u = row['User']
            c = row['Country']
            user_counts_accum[u] += 1
            
            if c != "Unknown":
                if c not in geo_dominance_accum: geo_dominance_accum[c] = {}
                geo_dominance_accum[c][u] = geo_dominance_accum[c].get(u, 0) + 1
        
        # Calcolo vincitori stati
        current_map_colors = {}
        for country, contenders in geo_dominance_accum.items():
            winner = max(contenders, key=contenders.get)
            winner_color = PASTEL_HEX_MAP.get(USER_CONFIG.get(winner, {}).get('color'), '#333')
            current_map_colors[country] = winner_color
            
        dominance_by_time[time_val] = current_map_colors
        user_totals_by_time[time_val] = user_counts_accum.copy()
        
        # Preparazione Markers
        features_slice = []
        for _, row in current_slice.iterrows():
            user = row['User']
            color = PASTEL_HEX_MAP.get(USER_CONFIG.get(user, {}).get('color', 'gray'), 'gray')
            popup = f"<b>{user}</b><br>{row['Country']}<br>{row['Timestamp'].strftime('%H:%M')}"
            features_slice.append({
                "lat": row['Latitude'], "lon": row['Longitude'],
                "user": user, "hex_color": color, 
                "safe_class": sanitize_class_name(user),
                "popup": popup
            })
        data_by_time[time_val] = features_slice

    # 4. Generazione Mappa
    # Preparazione dati JSON per il frontend
    js_data = (
        json.dumps(timeline_dates),
        json.dumps(data_by_time),
        json.dumps(dominance_by_time),
        json.dumps(user_totals_by_time),
        json.dumps({u: PASTEL_HEX_MAP.get(USER_CONFIG.get(u, {}).get('color'), 'gray') for u in unique_users}),
        unique_users
    )

    create_map(geo_engine.geo_data, js_data)

if __name__ == "__main__":
    main()
