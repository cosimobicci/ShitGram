import pandas as pd
import re
import numpy as np
import folium
import os
import webbrowser
import json
import requests
from shapely.geometry import shape, Point
from shapely.prepared import prep
import warnings

# ==========================================
# 🛠️ 1. CONFIGURAZIONE E SETUP
# ==========================================

warnings.filterwarnings("ignore")

# URL GeoJSON Alta Risoluzione
GEOJSON_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries.geojson"

PASTEL_HEX_MAP = {
    'beige':     '#FFF0B5', 'magenta':   '#FF66FF', 'purple':    '#DA70D6',
    'green':     '#76E076', 'red':       '#FF6B6B', 'pink':      '#FFB6C1',
    'orange':    '#FFB347', 'brown':     '#E0A96D', 'yellow':    '#FFF176',
    'cyan':      '#4DD0E1', 'blue':      '#6495ED', 'darkred':   '#EF5350',
    'cadetblue': '#80DEEA', 'darkgreen': '#66BB6A', 'darkblue':  '#5C6BC0',
    'gray':      '#BDBDBD', 'black':     '#757575', 'lightgray': '#E0E0E0'
}

USER_CONFIG = {
    'Cosimo': {'color': 'cadetblue'}, 'Riccardo': {'color': 'magenta'},
    'Mariam': {'color': 'purple'}, 'Tommaso': {'color': 'green'},
    'Armando': {'color': 'red'}, 'Stefano': {'color': 'pink'},
    'Leo': {'color': 'orange'}, 'Francesca': {'color': 'yellow'},
    'Cava': {'color': 'cyan'}, 'Luca': {'color': 'blue'},
    'Asia': {'color': 'darkred'},
    'DEFAULT': {'color': 'gray'}
}

AWARDS_CONFIG = {
    'gold': ('Caca-Master', '🥇', 1000), 'silver': ('Argento', '🥈', 500),
    'bronze': ('Bronzo', '🥉', 250), 'wood': ('Lega Legno', '🪵', 50),
    'globetrotter': ('Globe Trotter', '✈️', 400), 'north': ('Re del Nord', '❄️', 300),
    'south': ('Re del Sud', '🐧', 300), 'east': ('Re dell\'Est', '🌅', 300),
    'west': ('Re del West', '🤠', 300), 'base_poop': ('Attività Base', '💩', 20)
}

def sanitize_class_name(name): return re.sub(r'[^a-zA-Z0-9]', '_', name)

# ==========================================
# 📥 2. CARICAMENTO DATI
# ==========================================

FILE_NAME = '_chat.txt'
if not os.path.exists(FILE_NAME):
    print(f"⚠️ ERRORE: '{FILE_NAME}' mancante!")
    exit()

print("1. Lettura chat...")
with open(FILE_NAME, 'r', encoding='utf-8') as f: chat_content = f.read()

matches = re.findall(r"^\[(\d{2}\/\d{2}\/\d{2}),\s(\d{2}:\d{2}:\d{2})\]\s([^:]+):\s(.*)$", chat_content, re.MULTILINE)
data = [{'Date_Str': m[0], 'Time_Str': m[1], 'User': m[2].strip(), 'Message_Content': m[3].strip()} for m in matches]
df = pd.DataFrame(data)
df['Timestamp'] = pd.to_datetime(df['Date_Str'] + ' ' + df['Time_Str'], format='%d/%m/%y %H:%M:%S', errors='coerce')
df['Is_Poop'] = df['Message_Content'].str.contains('💩', regex=False)

# Logica Estrazione Posizione
df['Location'] = np.where(
    (df['Message_Content'].str.contains(r'Posizione:|maps', regex=True).shift(-1) == True) & 
    (df['User'].shift(-1) == df['User']), 
    df['Message_Content'].shift(-1), None
)
df = df[df['Is_Poop'] == True].copy()

def get_coords(text):
    match = re.search(r'(-?\d+\.\d+),\s*(-?\d+\.\d+)', str(text))
    return (float(match.group(1)), float(match.group(2))) if match else (np.nan, np.nan)

df[['Latitude', 'Longitude']] = df['Location'].apply(get_coords).apply(pd.Series)
df = df.dropna(subset=['Latitude', 'Longitude'])

# Mapping Utenti
user_mapping = {
    'cosimobicci': 'Cosimo', 'riki nata': 'Riccardo', 'Federation non è rotto qualcosa Yonghong': 'Armando',
    'Maurizio dalla sezione Marketing': 'Tommaso', 'Asia Mariani': 'Asia', 'Stefano Panichi': 'Stefano',
    'Leo Chelsea': 'Leo', 'Luca Viezzoli': 'Luca', 'mariam': 'Mariam', 'Francesca Piersigilli': 'Francesca'
}
for k, v in user_mapping.items(): df['User'] = df['User'].str.replace(k, v, regex=False)
unique_users = sorted(df['User'].unique())

# ==========================================
# 🌍 3. GEOMETRIA & LOGICA DOMINIO
# ==========================================
print("2. Setup GeoJSON e Poligoni...")
try:
    if not os.path.exists("world_hires.json"):
        r = requests.get(GEOJSON_URL)
        geo_data = r.json()
        with open("world_hires.json", "w") as f: json.dump(geo_data, f)
    else:
        with open("world_hires.json", "r") as f: geo_data = json.load(f)
except Exception as e:
    geo_data = requests.get(GEOJSON_URL).json()

# Prepara poligoni per ricerca veloce
countries_polys = []
for feature in geo_data['features']:
    geom = shape(feature['geometry'])
    name = feature['properties'].get('ADMIN', feature['properties'].get('NAME', 'Unknown'))
    countries_polys.append({'name': name, 'poly': prep(geom)}) 

def get_country(lat, lon):
    p = Point(lon, lat)
    for c in countries_polys:
        if c['poly'].contains(p): return c['name']
    return "Unknown"

print("3. Assegnazione Stati ai Punti...")
df['Country'] = df.apply(lambda row: get_country(row['Latitude'], row['Longitude']), axis=1)

# ==========================================
# 📊 4. ELABORAZIONE DATI TEMPORALI
# ==========================================
print("4. Calcolo Dominio e Timeline...")

df = df.sort_values(by='Timestamp')
timeline_dates = df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M').unique().tolist()

data_by_time = {}      # I marker
dominance_by_time = {} # Chi comanda quale stato
user_totals_by_time = {} # Totali per classifica utenti

# Struttura accumulo: { 'Italy': { 'Cosimo': 5, 'Leo': 2 }, ... }
geo_dominance_accum = {}
user_counts_accum = {u: 0 for u in unique_users}

for time_val in timeline_dates:
    current_slice = df[df['Timestamp'].dt.strftime('%Y-%m-%d %H:%M') == time_val]
    
    # Aggiorna statistiche dominio
    for _, row in current_slice.iterrows():
        u = row['User']
        c = row['Country']
        user_counts_accum[u] += 1
        
        if c != "Unknown":
            if c not in geo_dominance_accum: geo_dominance_accum[c] = {}
            geo_dominance_accum[c][u] = geo_dominance_accum[c].get(u, 0) + 1
    
    # Calcola chi vince in ogni stato IN QUESTO MOMENTO
    current_map_colors = {}
    for country, contenders in geo_dominance_accum.items():
        # Trova utente con max cagate
        winner = max(contenders, key=contenders.get)
        winner_color = PASTEL_HEX_MAP.get(USER_CONFIG.get(winner, {}).get('color'), '#333')
        current_map_colors[country] = winner_color
        
    dominance_by_time[time_val] = current_map_colors
    user_totals_by_time[time_val] = user_counts_accum.copy()
    
    # Marker
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

# JSON Dumps
js_timeline = json.dumps(timeline_dates)
js_point_data = json.dumps(data_by_time)
js_dominance = json.dumps(dominance_by_time)
js_user_totals = json.dumps(user_totals_by_time)
js_user_colors = json.dumps({u: PASTEL_HEX_MAP.get(USER_CONFIG.get(u, {}).get('color'), 'gray') for u in unique_users})

# ==========================================
# 🗺️ 5. UI COMPLETA (Tutte le finestre)
# ==========================================

m = folium.Map(location=[45.0, 10.0], zoom_start=4, tiles="CartoDB dark_matter", zoom_control=False, world_copy_jump=True, min_zoom=2)

# GeoJSON Layer (Inizialmente vuoto/nero)
folium.GeoJson(
    geo_data,
    name="Stati",
    style_function=lambda x: {'fillColor': '#222', 'color': '#444', 'weight': 0.5, 'fillOpacity': 0.1},
    tooltip=folium.GeoJsonTooltip(fields=['ADMIN'], aliases=['Stato:'])
).add_to(m)

map_id = m.get_name()

# 1. Pannello Membri (Filtri)
legend_items = "".join([f"""
    <div style="display:flex; align-items:center; margin-bottom:5px;">
        <input type="checkbox" id="chk_{sanitize_class_name(u)}" checked onclick="toggleUser('{sanitize_class_name(u)}')" style="margin-right:8px; accent-color:{PASTEL_HEX_MAP.get(USER_CONFIG.get(u,{}).get('color'),'#888')};">
        <span style="width:10px; height:10px; background:{PASTEL_HEX_MAP.get(USER_CONFIG.get(u,{}).get('color'),'#888')}; border-radius:50%; margin-right:8px;"></span>
        <label for="chk_{sanitize_class_name(u)}" style="font-size:12px; cursor:pointer;">{u}</label>
    </div>""" for u in unique_users])

right_panel = f"""
<div id="filter-legend" class="glass-panel" style="position:fixed; top:20px; right:20px; z-index:1000; max-height:80vh; overflow-y:auto; min-width:150px;">
    <div class="draggable-header">👥 Membri</div>
    {legend_items}
</div>
"""

# 2. Pannello Premi (Awards)
awards_items = "".join([f"""
    <div style="margin-bottom:6px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:4px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:14px; margin-right:5px;">{icon}</span>
            <strong style="font-size:11px; flex-grow:1;">{title}</strong>
            <span style="background:rgba(255,255,255,0.1); padding:1px 4px; border-radius:4px; font-size:9px;">+{xp}</span>
        </div>
    </div>""" for _, (title, icon, xp) in sorted(AWARDS_CONFIG.items(), key=lambda x: x[1][2], reverse=True)])

left_panel = f"""
<div id="awards-legend" class="glass-panel" style="position:fixed; top:20px; left:20px; z-index:1000; max-height:60vh; overflow-y:auto; width:220px;">
    <div class="draggable-header">🏆 Guida XP</div>
    {awards_items}
</div>
"""

# 3. Pannello Classifica Utenti (Chart)
chart_panel = f"""
<div id="chart-panel" class="glass-panel" style="position:fixed; bottom:120px; right:20px; z-index:1000; width:240px;">
    <div class="draggable-header">📊 Classifica Live</div>
    <div id="chart-container" style="padding-top:5px;"></div>
</div>
<style id="dynamic-user-styles"></style>
"""

# 4. Slider
slider_html = f"""
<div id="custom-slider-container" class="glass-panel">
    <div class="slider-controls">
        <button id="play-pause-btn" onclick="togglePlay()"><i class="fa fa-play"></i></button>
        <div class="slider-wrapper">
            <input type="range" min="0" max="{len(timeline_dates)-1}" value="0" class="neon-slider" id="time-slider" oninput="updateMapFromSlider(this.value)">
        </div>
        <div id="date-display">--:--</div>
    </div>
</div>
"""

script_js = f"""
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
<style>
    body {{ font-family: 'Poppins', sans-serif; }}
    .glass-panel {{
        background: rgba(20, 20, 25, 0.9); backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.15); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        color: #e0e0e0; border-radius: 16px; padding: 15px; transition: all 0.3s ease;
    }}
    #custom-slider-container {{
        position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
        width: 60%; max-width: 700px; min-width: 320px; z-index: 9999;
        display: flex; flex-direction: column; align-items: center; padding: 10px 20px;
    }}
    .slider-controls {{ display: flex; align-items: center; width: 100%; gap: 15px; }}
    #play-pause-btn {{
        background: #00e5ff; border: none; border-radius: 50%; width: 40px; height: 40px;
        cursor: pointer; color: #1a1a1a; display: flex; align-items: center; justify-content: center;
        transition: transform 0.2s;
    }}
    #play-pause-btn:hover {{ transform: scale(1.1); background: #fff; }}
    #date-display {{ min-width: 130px; font-family: monospace; font-weight: bold; color: #00e5ff; text-align: right; }}
    .neon-slider {{ -webkit-appearance: none; width: 100%; background: transparent; }}
    .neon-slider:focus {{ outline: none; }}
    .neon-slider::-webkit-slider-runnable-track {{ width: 100%; height: 6px; cursor: pointer; background: rgba(255,255,255,0.2); border-radius: 3px; }}
    .neon-slider::-webkit-slider-thumb {{ height: 18px; width: 18px; border-radius: 50%; background: #00e5ff; cursor: pointer; -webkit-appearance: none; margin-top: -6px; box-shadow: 0 0 10px #00e5ff; }}
    .draggable-header {{ cursor: move; border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 10px; font-weight: 600; text-transform: uppercase; color: #fff; font-size:12px; }}
</style>

<script>
    var timelineDates = {js_timeline};
    var pointData = {js_point_data};
    var dominanceData = {js_dominance};
    var userTotals = {js_user_totals};
    var userColors = {js_user_colors};
    
    var currentStep = 0;
    var lastRenderedStep = -1; 
    var isPlaying = false;
    var playInterval;
    var mapInstance;
    var markersGroup = L.layerGroup();
    var currentCounts = {{}};
    var userVisibility = {{}};
    
    function updateMap(idx) {{
        var stepIndex = parseInt(idx);
        var dateStr = timelineDates[stepIndex];
        
        document.getElementById('date-display').innerText = dateStr;
        document.getElementById('time-slider').value = stepIndex;
        
        if (stepIndex == lastRenderedStep + 1) {{
            addPointsForStep(stepIndex);
        }} else {{
            markersGroup.clearLayers();
            currentCounts = {{}};
            for(var i=0; i<=stepIndex; i++) {{
                addPointsForStep(i);
            }}
        }}
        lastRenderedStep = stepIndex;
        
        var currentDom = dominanceData[dateStr] || {{}};
        mapInstance.eachLayer(function(layer) {{
            if (layer.feature && layer.feature.properties) {{
                var name = layer.feature.properties.ADMIN || layer.feature.properties.NAME;
                var domColor = currentDom[name];
                
                if(domColor) {{
                    layer.setStyle({{
                        fillColor: domColor,
                        fillOpacity: 0.6,
                        weight: 1,
                        color: '#fff'
                    }});
                }} else {{
                    layer.setStyle({{ fillColor: '#222', fillOpacity: 0.1, weight: 0.5, color: '#444' }});
                }}
            }}
        }});

        updateUserChart(userTotals[dateStr]);
    }}

    function addPointsForStep(idx) {{
        var d = timelineDates[idx];
        if (pointData[d]) {{
            pointData[d].forEach(p => {{
                if (userVisibility[p.safe_class] === false) return;

                var m = L.circleMarker([p.lat, p.lon], {{
                    radius: 6,
                    fillColor: p.hex_color,
                    color: "#fff",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 1,
                    className: p.safe_class
                }});

                m.bindPopup(p.popup);
                markersGroup.addLayer(m);

                if (!currentCounts[p.user]) currentCounts[p.user] = 0;
                currentCounts[p.user]++;
            }});
        }}
    }}

    function updateUserChart(totals) {{
        var container = document.getElementById('chart-container');
        if(!totals) return;
        
        var visibleTotals = {{}};
        for(var user in totals) {{
            if(userVisibility[user] !== false) {{
                visibleTotals[user] = totals[user];
            }}
        }}
        
        var sorted = Object.keys(visibleTotals).map(u => ({{user:u, count:visibleTotals[u]}})).sort((a,b)=>b.count-a.count);
        var maxVal = sorted[0] && sorted[0].count > 0 ? sorted[0].count : 1;
        
        var html = "";
        sorted.forEach((u, idx) => {{
            if(u.count > 0) {{
                var pct = (u.count / maxVal) * 100;
                var medal = idx === 0 ? '🥇' : idx === 1 ? '🥈' : idx === 2 ? '🥉' : '🔹';
                html += `<div style="margin-bottom:6px; font-size:11px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; color:#eee;">
                        <span>${{medal}} ${{u.user}}</span>
                        <span style="color:${{userColors[u.user]}}; font-weight:bold;">${{u.count}}</span>
                    </div>
                    <div style="background:rgba(255,255,255,0.1); height:4px; border-radius:2px; margin-top:2px;">
                        <div style="width:${{pct}}%; background:${{userColors[u.user]}}; height:100%; border-radius:2px;"></div>
                    </div>
                </div>`;
            }}
        }});
        container.innerHTML = html || "<i style='color:#777; font-size:10px'>Nessun dato</i>";
    }}
    
    function updateMapFromSlider(val) {{
        currentStep = parseInt(val);
        updateMap(currentStep);
    }}

    function togglePlay() {{
        isPlaying = !isPlaying;
        var btn = document.querySelector('#play-btn i');
        if(isPlaying) {{
            btn.classList.remove('fa-play'); btn.classList.add('fa-pause');
            playInterval = setInterval(() => {{
                if(currentStep < timelineDates.length - 1) {{
                    currentStep++;
                    updateMap(currentStep);
                }} else {{ togglePlay(); }}
            }}, 200);
        }} else {{
            btn.classList.remove('fa-pause'); btn.classList.add('fa-play');
            clearInterval(playInterval);
        }}
    }}
    
    function toggleUser(uClass) {{
        var chk = document.getElementById('chk_' + uClass);
        userVisibility[uClass] = chk.checked;
        var styleTag = document.getElementById('dynamic-user-styles');
        var rules = "";
        for(var u in userVisibility) {{
            if(!userVisibility[u]) rules += "." + u + " {{ display: none !important; }} ";
        }}
        styleTag.innerHTML = rules;
        updateMap(currentStep);
    }}

    window.onload = function() {{
        mapInstance = {map_id};
        mapInstance.addLayer(markersGroup);
        
        for(var user in userColors) {{
            userVisibility[user] = true;
        }}
        
        function makeDrag(elm) {{
            var pos1=0,pos2=0,pos3=0,pos4=0;
            var head = elm.querySelector(".draggable-header");
            if(head) head.onmousedown = dragMouseDown;
            function dragMouseDown(e) {{ e.preventDefault(); pos3=e.clientX; pos4=e.clientY; document.onmouseup=closeDrag; document.onmousemove=elDrag; }}
            function elDrag(e) {{ e.preventDefault(); pos1=pos3-e.clientX; pos2=pos4-e.clientY; pos3=e.clientX; pos4=e.clientY; elm.style.top=(elm.offsetTop-pos2)+"px"; elm.style.left=(elm.offsetLeft-pos1)+"px"; }}
            function closeDrag() {{ document.onmouseup=null; document.onmousemove=null; }}
        }}
        
        makeDrag(document.getElementById("filter-legend"));
        makeDrag(document.getElementById("awards-legend"));
        makeDrag(document.getElementById("chart-panel"));
        
        updateMap(0);
        
        document.addEventListener('keydown', function(e) {{
            if(e.code === 'Space') {{ e.preventDefault(); togglePlay(); }}
            if(e.code === 'ArrowRight') {{ updateMap(Math.min(currentStep+1, timelineDates.length-1)); }}
            if(e.code === 'ArrowLeft') {{ updateMap(Math.max(currentStep-1, 0)); }}
        }});
    }};
</script>
"""

m.get_root().html.add_child(folium.Element(right_panel))
m.get_root().html.add_child(folium.Element(left_panel))
m.get_root().html.add_child(folium.Element(chart_panel))
m.get_root().html.add_child(folium.Element(slider_html))
m.get_root().html.add_child(folium.Element(script_js))

output_file = "Mappa_Dominio_Finale.html"
m.save(output_file)
print(f"✅ Mappa creata: {output_file}")
try: webbrowser.open('file://' + os.path.realpath(output_file))
except: pass
