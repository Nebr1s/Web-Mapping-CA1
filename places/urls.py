from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("places", views.PlaceViewSet, basename="place")
router.register("neighbourhoods", views.NeighbourhoodViewSet)
router.register("routes", views.RouteViewSet)

urlpatterns = [
    path("", views.index, name="index"),
    path("api/", include(router.urls)),
]
