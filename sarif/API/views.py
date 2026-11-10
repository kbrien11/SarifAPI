from django.shortcuts import render

# Create your views here.

import requests
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .utils import (
    get_cached_plans,
    get_plan_by_key,
    get_plan_data,
    get_cached_plan_data,
    search_plan_records,
)

#  find in network url/json
@api_view(["GET"])
def get_in_network_files(request):
    try:
        plans = get_cached_plans()

        return Response({"count": len(plans), "results": plans})

    except requests.RequestException as error:
        return Response({"error": str(error)}, status=status.HTTP_502_BAD_GATEWAY)


#  injest plans
@api_view(["GET"])
def get_plan(request, plan_key):
    data = get_plan_data(plan_key)

    if data is None:
        return Response({"error": "Plan not found"}, status=404)

    return Response({"result": data})


@api_view(["GET"])
def get_plan_records(request, plan_key):
    records = get_cached_plan_data(plan_key)

    if records is None:
        return Response({"error": "Plan has not been ingested yet"}, status=404)

    return Response(
        {
            "plan_key": plan_key,
            "status": "completed",
            "total_records": len(records),
            "records": records,
        }
    )


# search endpoint
@api_view(["GET"])
def search_plan_data(request, plan_key):
    billing_code = request.GET.get("billing_code")
    description = request.GET.get("description")
    results = search_plan_records(plan_key, billing_code, description)
    if results is None:
        return Response({"error": "Plan has not been ingested yet"}, status=404)

    return Response(
        {
            "plan_key": plan_key,
            "billing_code": billing_code,
            "unique_billing_codes": results["unique_billing_codes"],
            "total_negotiated_rates": results["total_negotiated_rates"],
            "results": results["results"],
        }
    )
