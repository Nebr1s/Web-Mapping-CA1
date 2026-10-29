from django.contrib.gis.db import models

# GeoDjango creates a GiST spatial index on every geometry field (spatial_index=True by default).


class Neighbourhood(models.Model):
    """Polygon: an area of Dublin."""

    name = models.CharField(max_length=100, unique=True)
    boundary = models.PolygonField(srid=4326)

    def __str__(self):
        return self.name


class Route(models.Model):
    """LineString: a walking or cycling route."""

    KINDS = [("walk", "Walking"), ("cycle", "Cycling")]

    name = models.CharField(max_length=100)
    kind = models.CharField(max_length=10, choices=KINDS)
    path = models.LineStringField(srid=4326)

    def __str__(self):
        return self.name


class Place(models.Model):
    """Point: a spot worth visiting."""

    CATEGORIES = [
        ("cafe", "Café"),
        ("park", "Park"),
        ("museum", "Museum"),
        ("library", "Library"),
        ("transport", "Transport"),
        ("landmark", "Landmark"),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    description = models.TextField(blank=True)
    location = models.PointField(srid=4326)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
