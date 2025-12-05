import requests
import json
import os
from shapely.geometry import shape, Point
from shapely.prepared import prep
from config import GEOJSON_URL

class GeoEngine:
    def __init__(self):
        self.geo_data = None
        self.countries_polys = []
        self._load_geojson()
        self._prepare_polygons()

    def _load_geojson(self):
        print("🌍 Setup GeoJSON...")
        try:
            if not os.path.exists("world_hires.json"):
                r = requests.get(GEOJSON_URL)
                self.geo_data = r.json()
                with open("world_hires.json", "w") as f:
                    json.dump(self.geo_data, f)
            else:
                with open("world_hires.json", "r") as f:
                    self.geo_data = json.load(f)
        except Exception:
            self.geo_data = requests.get(GEOJSON_URL).json()

    def _prepare_polygons(self):
        print("🗺️ Preparazione poligoni...")
        for feature in self.geo_data['features']:
            geom = shape(feature['geometry'])
            name = feature['properties'].get('ADMIN', feature['properties'].get('NAME', 'Unknown'))
            self.countries_polys.append({'name': name, 'poly': prep(geom)})

    def get_country(self, lat, lon):
        p = Point(lon, lat)
        for c in self.countries_polys:
            if c['poly'].contains(p):
                return c['name']
        return "Unknown"
