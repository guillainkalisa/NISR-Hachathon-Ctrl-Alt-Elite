from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.map_view, name="map"),
    path("districts.geojson", views.districts_geojson, name="geojson"),
    path("district/<slug:slug>/", views.district_detail, name="district"),
    path("checker/", views.checker, name="checker"),
    path("simulator/", views.simulator_view, name="simulator"),
    path("about/", views.about, name="about"),
]
