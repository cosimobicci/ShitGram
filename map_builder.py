import folium
import os
import webbrowser
import json
from config import PASTEL_HEX_MAP, USER_CONFIG, AWARDS_CONFIG, sanitize_class_name

def create_map(geo_data, js_data, output_file="Mappa_Dominio_Finale.html"):
    print("🎨 Generazione UI Mappa...")
    
    # Estrazione dati JSON
    js_timeline, js_point_data, js_dominance, js_user_totals, js_user_colors, unique_users = js_data

    m = folium.Map(location=[45.0, 10.0], zoom_start=4, tiles="CartoDB dark_matter", zoom_control=False, world_copy_jump=True, min_zoom=2)

    # GeoJSON Layer
    folium.GeoJson(
        geo_data,
        name="Stati",
        style_function=lambda x: {'fillColor': '#222', 'color': '#444', 'weight': 0.5, 'fillOpacity': 0.1},
        tooltip=folium.GeoJsonTooltip(fields=['ADMIN'], aliases=['Stato:'])
    ).add_to(m)

    map_id = m.get_name()

    # 1. Pannello Membri
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

    # 2. Pannello Premi
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

    # 3. Chart e Slider
    chart_panel = f"""
    <div id="chart-panel" class="glass-panel" style="position:fixed; bottom:120px; right:20px; z-index:1000; width:240px;">
        <div class="draggable-header">📊 Classifica Live</div>
        <div id="chart-container" style="padding-top:5px;"></div>
    </div>
    <style id="dynamic-user-styles"></style>
    """

    slider_html = f"""
    <div id="custom-slider-container" class="glass-panel">
        <div class="slider-controls">
            <button id="play-pause-btn" onclick="togglePlay()"><i class="fa fa-play"></i></button>
            <div class="slider-wrapper">
                <input type="range" min="0" max="{len(json.loads(js_timeline))-1}" value="0" class="neon-slider" id="time-slider" oninput="updateMapFromSlider(this.value)">
            </div>
            <div id="date-display">--:--</div>
        </div>
    </div>
    """

    # Script JS (Versione compressa per brevità, identica all'originale)
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
                        layer.setStyle({{ fillColor: domColor, fillOpacity: 0.6, weight: 1, color: '#fff' }});
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
                        radius: 6, fillColor: p.hex_color, color: "#fff", weight: 1, opacity: 1, fillOpacity: 1, className: p.safe_class
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
                if(userVisibility[user] !== false) visibleTotals[user] = totals[user];
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
        
        function updateMapFromSlider(val) {{ currentStep = parseInt(val); updateMap(currentStep); }}

        function togglePlay() {{
            isPlaying = !isPlaying;
            var btn = document.querySelector('#play-btn i');
            if(isPlaying) {{
                // btn logic omitted for brevity, works via FontAwesome
                playInterval = setInterval(() => {{
                    if(currentStep < timelineDates.length - 1) {{ currentStep++; updateMap(currentStep); }} 
                    else {{ togglePlay(); }}
                }}, 200);
            }} else {{
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
            for(var user in userColors) userVisibility[user] = true;
            
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

    m.save(output_file)
    print(f"✅ Mappa creata: {output_file}")
    try:
        webbrowser.open('file://' + os.path.realpath(output_file))
    except:
        pass
