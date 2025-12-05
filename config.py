import re

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

def sanitize_class_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)
