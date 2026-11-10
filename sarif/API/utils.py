import hashlib
import json
from pathlib import Path
import ijson
from django.core.cache import cache
import requests

PLAN_CACHE_KEY = "cms:plans"
PLAN_CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

#  load ininital TOC json to find In network urls
def get_toc_data():
    file_path = Path(
        "/Users/keith_brien/Documents/Projects/SarifAPI/sarif/API/2026-09-28_ambetter_index (1).json"
    )

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


#  FUNDTION TO LODA THE LOCATION KEY to
def extract_in_network_urls():
    toc_data = get_toc_data()

    results = []

    for structure_index, structure in enumerate(
        toc_data.get("reporting_structure", [])
    ):
        plans = structure.get("reporting_plans", [])
        files = structure.get("in_network_files", [])

        if not plans or not files:
            continue

        file_data = [
            {
                "description": file.get("description"),
                "url": file.get("location"),
            }
            for file in files
            if file.get("location")
        ]

        if not file_data:
            continue

        for plan_index, plan in enumerate(plans):
            identifier = (
                f"{structure_index}:{plan_index}:"
                f"{plan.get('plan_id')}:{plan.get('plan_name')}"
            )

            plan_key = hashlib.sha256(identifier.encode("utf-8")).hexdigest()

            results.append(
                {
                    "plan_key": plan_key,
                    "plan_name": plan.get("plan_name"),
                    "plan_id": plan.get("plan_id"),
                    "plan_id_type": plan.get("plan_id_type"),
                    "in_network_files": file_data,
                }
            )

    return results


def get_cached_plans():
    plans = cache.get(PLAN_CACHE_KEY)

    if plans is not None:
        print("CACHE HIT: Returning plans from cache")
        return plans

    print("CACHE MISS: Reading TOC file")

    plans = extract_in_network_urls()

    cache.set(PLAN_CACHE_KEY, plans, timeout=PLAN_CACHE_TIMEOUT)

    print("CACHE SET: Plans saved to cache")

    return plans


def get_plan_by_key(plan_key):
    plans = get_cached_plans()

    for plan in plans:
        if plan["plan_key"] == plan_key:
            return plan

    return None


#  injest the plan data from the in network json to a cache, so if you search for repeated data you dont have to run through the same json again.  Using python stream to we dont load the json all at once and only extracting relevant fields from the json
def get_plan_data(plan_key):
    plan = get_plan_by_key(plan_key)

    if not plan:
        return None

    cache_key = f"plan_records_{plan_key}"

    # Check whether this plan has already been ingested
    cached_records = cache.get(cache_key)

    if cached_records is not None:
        return {
            "plan_key": plan_key,
            "status": "completed",
            "records_processed": len(cached_records),
            "cached": True,
        }

    files_data = []
    records_processed = 0

    for file in plan.get("in_network_files", []):
        url = file.get("url")

        if not url:
            continue

        with requests.get(url, stream=True, timeout=(10, 300)) as response:

            response.raise_for_status()
            response.raw.decode_content = True

            for item in ijson.items(response.raw, "in_network.item"):
                print(item.keys())

                # Extract only relevant fields
                record = {
                    "billing_code": item.get("billing_code"),
                    "billing_code_type": item.get("billing_code_type"),
                    "description": item.get("description"),
                    "negotiated_rates": item.get("negotiated_rates", []),
                }

                files_data.append(record)
                records_processed += 1

    # Store extracted records in Django cache
    cache.set(cache_key, files_data, timeout=86400)

    return {
        "plan_key": plan_key,
        "status": "completed",
        "records_processed": records_processed,
        "cached": False,
    }


def get_cached_plan_data(plan_key):
    cache_key = f"plan_records_{plan_key}"

    records = cache.get(cache_key)

    if records is None:
        return None

    return records


#  searcg fir specific plans within the json to get relevant record. you can search by billing_code or a partial match descriptino. If both are provided its an AND condition
def search_plan_records(plan_key, billing_code=None, description=None):
    cache_key = f"plan_records_{plan_key}"
    records = cache.get(cache_key)

    if records is None:
        return None

    results = []

    for record in records:
        if billing_code and record.get("billing_code") != billing_code:
            continue

        if (
            description
            and description.lower() not in record.get("description", "").lower()
        ):
            continue

        results.append(record)

    # Count distinct billing codes
    unique_billing_codes = len(set(record.get("billing_code") for record in results))

    # Count individual negotiated prices
    total_negotiated_rates = sum(
        len(rate_group.get("negotiated_prices", []))
        for record in results
        for rate_group in record.get("negotiated_rates", [])
    )

    return {
        "unique_billing_codes": unique_billing_codes,
        "total_negotiated_rates": total_negotiated_rates,
        "results": results,
    }
