from django.contrib.auth.models import User
from django.core.management import call_command
from rest_framework.test import APITestCase

from .models import Neighbourhood, Place, Route


class SpatialApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed", verbosity=0)

    def test_nearest_is_sorted_by_distance(self):
        # Right beside the Spire
        res = self.client.get("/api/places/nearest/", {"lat": 53.3499, "lng": -6.2602, "limit": 3})
        feats = res.json()["features"]
        self.assertEqual(feats[0]["properties"]["name"], "The Spire")
        dists = [f["properties"]["distance_m"] for f in feats]
        self.assertEqual(dists, sorted(dists))

    def test_nearest_rejects_bad_coords(self):
        self.assertEqual(self.client.get("/api/places/nearest/", {"lat": "abc", "lng": 0}).status_code, 400)
        self.assertEqual(self.client.get("/api/places/nearest/", {"lat": 200, "lng": 0}).status_code, 400)

    def test_neighbourhood_contents(self):
        area = Neighbourhood.objects.get(name="Rathmines")
        data = self.client.get(f"/api/neighbourhoods/{area.id}/contents/").json()
        names = {f["properties"]["name"] for f in data["places"]["features"]}
        self.assertIn("Rathmines Library", names)
        self.assertNotIn("The Spire", names)
        routes = {f["properties"]["name"] for f in data["routes"]["features"]}
        self.assertEqual(routes, {"Grand Canal Way"})

    def test_route_buffer(self):
        route = Route.objects.get(name="Liffey Quays")
        data = self.client.get(f"/api/routes/{route.id}/nearby/", {"distance": 200}).json()
        names = {f["properties"]["name"] for f in data["places"]["features"]}
        self.assertIn("Ha'penny Bridge", names)
        self.assertNotIn("Rathmines Library", names)

    def test_writes_need_login_and_valid_location(self):
        body = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [-6.26, 53.34]},
                "properties": {"name": "Test spot", "category": "cafe"}}
        self.assertEqual(self.client.post("/api/places/", body, format="json").status_code, 403)

        self.client.force_login(User.objects.create_user("tester", password="pw"))
        self.assertEqual(self.client.post("/api/places/", body, format="json").status_code, 201)

        body["geometry"]["coordinates"] = [0, 0]  # not in Dublin
        self.assertEqual(self.client.post("/api/places/", body, format="json").status_code, 400)
        self.assertTrue(Place.objects.filter(name="Test spot").exists())
