from django.urls import path
from . import views

urlpatterns = [
    path("in-network-files/", views.get_in_network_files),
    path("plans/<str:plan_key>/", views.get_plan),
    path("plans/<str:plan_key>/data/", views.get_plan_records, name="get_plan_records"),
    path(
        "plans/<str:plan_key>/search/", views.search_plan_data, name="search_plan_data"
    ),
]
