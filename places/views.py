from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Neighbourhood, Place, Route
from .serializers import NeighbourhoodSerializer, PlaceSerializer, RouteSerializer

IRISH_GRID = 2157  # Irish Transverse Mercator (metres), used for buffering


def index(request):
    return render(request, "places/index.html", {"categories": Place.CATEGORIES})


def _float_param(request, name, lo, hi, default=None):
    """Read a numeric query param, raising a 400 if it is missing, invalid or out of range."""
    raw = request.query_params.get(name, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValidationError({name: "Must be a number."})
    if not lo <= value <= hi:
        raise ValidationError({name: f"Must be between {lo} and {hi}."})
    return value


class PlaceViewSet(viewsets.ModelViewSet):
    """CRUD for places. Optional ?category= filter."""

    serializer_class = PlaceSerializer

    def get_queryset(self):
        qs = Place.objects.all()
        category = self.request.query_params.get("category")
        return qs.filter(category=category) if category else qs

    @action(detail=False)
    def nearest(self, request):
        """Spatial query 1 (proximity): the N places closest to ?lat=&lng=."""
        lat = _float_param(request, "lat", -90, 90)
        lng = _float_param(request, "lng", -180, 180)
        limit = int(_float_param(request, "limit", 1, 50, default=5))
        point = Point(lng, lat, srid=4326)
        qs = self.get_queryset().annotate(distance=Distance("location", point)).order_by("distance")[:limit]
        return Response(self.get_serializer(qs, many=True).data)


class NeighbourhoodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Neighbourhood.objects.all()
    serializer_class = NeighbourhoodSerializer

    @action(detail=True)
    def contents(self, request, pk=None):
        """Spatial query 2 (containment + intersection): places inside the area and routes crossing it."""
        area = self.get_object()
        return Response({
            "places": PlaceSerializer(Place.objects.filter(location__within=area.boundary), many=True).data,
            "routes": RouteSerializer(Route.objects.filter(path__intersects=area.boundary), many=True).data,
        })


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Route.objects.all()
    serializer_class = RouteSerializer

    @action(detail=True)
    def nearby(self, request, pk=None):
        """Spatial query 3 (buffer): places within ?distance= metres (default 250) of the route."""
        distance = _float_param(request, "distance", 10, 2000, default=250)
        route = self.get_object()
        # Buffer in a metric CRS, then back to WGS84 to compare with the stored points
        corridor = route.path.transform(IRISH_GRID, clone=True).buffer(distance)
        corridor.transform(4326)
        places = Place.objects.filter(location__within=corridor)
        return Response({
            "corridor": corridor.json,
            "places": PlaceSerializer(places, many=True).data,
        })
