from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from .models import Neighbourhood, Place, Route

# Rough bounding box of County Dublin (lng/lat)
DUBLIN_BBOX = (-6.55, 53.15, -6.00, 53.65)


class NeighbourhoodSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Neighbourhood
        geo_field = "boundary"
        fields = ["id", "name"]


class RouteSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Route
        geo_field = "path"
        fields = ["id", "name", "kind"]


class PlaceSerializer(GeoFeatureModelSerializer):
    # Only filled in on results of the "nearest" query
    distance_m = serializers.SerializerMethodField()

    class Meta:
        model = Place
        geo_field = "location"
        fields = ["id", "name", "category", "description", "created_at", "distance_m"]
        read_only_fields = ["created_at"]

    def get_distance_m(self, obj):
        d = getattr(obj, "distance", None)
        return round(d.m) if d is not None else None

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be blank.")
        return value.strip()

    def validate_location(self, point):
        min_x, min_y, max_x, max_y = DUBLIN_BBOX
        if not (min_x <= point.x <= max_x and min_y <= point.y <= max_y):
            raise serializers.ValidationError("Location must be inside County Dublin.")
        return point
