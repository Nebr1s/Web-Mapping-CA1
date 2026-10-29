from django.contrib.gis.geos import GEOSGeometry
from django.core.management.base import BaseCommand

from places.models import Neighbourhood, Place, Route

NEIGHBOURHOODS = {
    "City Centre": "POLYGON((-6.275 53.338, -6.245 53.338, -6.245 53.352, -6.275 53.352, -6.275 53.338))",
    "Docklands": "POLYGON((-6.245 53.336, -6.220 53.336, -6.220 53.350, -6.245 53.350, -6.245 53.336))",
    "Rathmines": "POLYGON((-6.278 53.315, -6.250 53.315, -6.250 53.334, -6.278 53.334, -6.278 53.315))",
    "Phibsborough": "POLYGON((-6.285 53.354, -6.258 53.354, -6.258 53.368, -6.285 53.368, -6.285 53.354))",
}

ROUTES = [
    ("Grand Canal Way", "walk", "LINESTRING(-6.293 53.333, -6.270 53.332, -6.256 53.333, -6.239 53.3395)"),
    ("Liffey Quays", "cycle", "LINESTRING(-6.295 53.346, -6.275 53.3455, -6.259 53.347, -6.240 53.348, -6.225 53.347)"),
    ("Royal Canal Greenway", "cycle", "LINESTRING(-6.282 53.361, -6.265 53.359, -6.245 53.354, -6.234 53.350)"),
]

PLACES = [
    ("St Stephen's Green", "park", -6.2592, 53.3382, "Victorian park in the city centre."),
    ("Merrion Square", "park", -6.2490, 53.3398, "Georgian square with the Oscar Wilde statue."),
    ("Mountjoy Square", "park", -6.2551, 53.3567, "Quiet Georgian square on the north side."),
    ("Herbert Park", "park", -6.2340, 53.3265, "Park with a duck pond in Ballsbridge."),
    ("National Gallery", "museum", -6.2526, 53.3409, "Irish and European art, free entry."),
    ("EPIC Museum", "museum", -6.2394, 53.3485, "Museum of Irish emigration."),
    ("Kilmainham Gaol", "museum", -6.3096, 53.3419, "Historic prison, now a museum."),
    ("Guinness Storehouse", "landmark", -6.2867, 53.3419, "Brewery visitor experience."),
    ("The Spire", "landmark", -6.2603, 53.3498, "120 m steel monument on O'Connell Street."),
    ("Ha'penny Bridge", "landmark", -6.2631, 53.3463, "Cast-iron pedestrian bridge over the Liffey."),
    ("Connolly Station", "transport", -6.2496, 53.3509, "Rail and DART station."),
    ("Heuston Station", "transport", -6.2925, 53.3464, "Main line rail to the south and west."),
    ("Grand Canal Dock DART", "transport", -6.2377, 53.3396, "DART station in the Docklands."),
    ("Pearse Street Library", "library", -6.2470, 53.3433, "Public library and city archives."),
    ("Rathmines Library", "library", -6.2652, 53.3227, "Carnegie library on Rathmines Road."),
    ("Phibsborough Library", "library", -6.2734, 53.3600, "Local library near the Royal Canal."),
    ("Grafton Street Café", "cafe", -6.2600, 53.3417, "Classic café on Grafton Street."),
    ("Canal Side Coffee", "cafe", -6.2650, 53.3318, "Coffee by the Grand Canal at Portobello."),
]


class Command(BaseCommand):
    help = "Load sample Dublin data (only if the tables are empty)."

    def handle(self, *args, **options):
        if Place.objects.exists() or Neighbourhood.objects.exists():
            self.stdout.write("Data already present, skipping seed.")
            return
        for name, wkt in NEIGHBOURHOODS.items():
            Neighbourhood.objects.create(name=name, boundary=GEOSGeometry(wkt, srid=4326))
        for name, kind, wkt in ROUTES:
            Route.objects.create(name=name, kind=kind, path=GEOSGeometry(wkt, srid=4326))
        for name, category, lng, lat, description in PLACES:
            Place.objects.create(
                name=name, category=category, description=description,
                location=GEOSGeometry(f"POINT({lng} {lat})", srid=4326),
            )
        self.stdout.write(self.style.SUCCESS("Seeded sample data."))
