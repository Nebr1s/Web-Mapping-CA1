from django.contrib.gis import admin

from .models import Neighbourhood, Place, Route

admin.site.register(Neighbourhood, admin.GISModelAdmin)
admin.site.register(Route, admin.GISModelAdmin)
admin.site.register(Place, admin.GISModelAdmin)
