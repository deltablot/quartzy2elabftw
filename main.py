#!/usr/bin/env python
# © Deltablot 2025
# License: MIT

# This script is used to fetch inventory data from Quartzy and send it to eLabFTW.
# It creates the resource categories from the "Type" column of your Inventory, and places the rest of the data as extra fields.
import os
import sys
import elabapi_python
import random
import html
import json
import logging
from tqdm import tqdm  # as we import 1000+ items, display a progress bar
import argparse
import urllib3
from dotenv import load_dotenv

load_dotenv()

# convert auto_reminder date from string to date (e.g. "1WEEK" -> date - 1 week)
# fetch_all_quartzy_items needed as there's pagination logic not inherited from the Public API
from utils import compute_reminder_date, fetch_all_quartzy_items

#########################
#      API CONFIG       #
#########################

# see https://docs.quartzy.com/api/#tag/Inventory-Item
QUARTZY_API_INVENTORY_URL = 'https://api.quartzy.com/inventory-items'
QUARTZY_TOKEN = os.getenv('QUARTZY_TOKEN') or sys.exit('QUARTZY_TOKEN environment variable not set')

# Read CATEGORIES from environment variable
CATEGORIES_ENV = os.getenv('CATEGORIES')
if CATEGORIES_ENV is None:
    sys.exit("CATEGORIES environment variable not set")
try:
    ALLOWED_CATEGORIES = json.loads(CATEGORIES_ENV)
    if not ALLOWED_CATEGORIES:
        sys.exit("CATEGORIES cannot be an empty array.")
except json.JSONDecodeError as e:
    sys.exit(f"Failed to decode CATEGORIES environment variable: {e}")

#########################
#      ELAB CONFIG      #
#########################

ELABFTW_HOST_URL = os.getenv('ELABFTW_HOST_URL') or sys.exit('ELABFTW_HOST_URL environment variable not set')
ELABFTW_API_KEY = os.getenv('ELABFTW_API_KEY') or sys.exit('ELABFTW_API_KEY environment variable not set')

#########################
#     ArgumentParser    #
#########################

def parse_args():
    parser = argparse.ArgumentParser(description="Sync Quartzy Inventory to eLabFTW")
    parser.add_argument('--verbose', action='store_true', help="Enable verbose output for debugging")
    parser.add_argument('--insecure', action='store_true', help="Disable SSL verification and suppress SSL warnings")
    return parser.parse_args()

# parse command-line arguments
args = parse_args()

def handle_insecure_flag(insecure):
    if insecure:
        urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

# Handle the --insecure flag
handle_insecure_flag(args.insecure)

# Configure the api client
configuration = elabapi_python.Configuration()
configuration.api_key["api_key"] = ELABFTW_API_KEY
configuration.api_key_prefix["api_key"] = "Authorization"
configuration.host = ELABFTW_HOST_URL
configuration.debug = False
# set verify_ssl based on flag Before creating ApiClient
configuration.verify_ssl = not args.insecure

# setup proxy to elabapi client's config
proxy_url = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
if proxy_url:
    configuration.proxy = proxy_url

# set CA for both requests and the elabapi-client
ca_path = os.getenv("CA_PATH") or os.getenv("REQUESTS_CA_BUNDLE")
if ca_path:
    configuration.ssl_ca_cert = ca_path
    if not os.getenv("REQUESTS_CA_BUNDLE"):
        os.environ["REQUESTS_CA_BUNDLE"] = ca_path

# create an instance of the API class
api_client = elabapi_python.ApiClient(configuration)
# fix issue with Authorization header not being properly set by the generated lib
api_client.set_default_header(header_name="Authorization", header_value=ELABFTW_API_KEY)
# filter eLabFTW traffic in mitmproxy
api_client.set_default_header(header_name="X-Proxy-Trace", header_value="quartzy2elabftw")

itemsApi = elabapi_python.ItemsApi(api_client)
itemsTypesApi = elabapi_python.ItemsTypesApi(api_client)
infoApi = elabapi_python.InfoApi(api_client)

#########################
#     Logging Setup     #
#########################

# Set up logging
def setup_logging(verbose):
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Set up logging with the verbose flag
setup_logging(args.verbose)

#################################
#     Version Compatibility     #
#################################

# compatible up to version 5.3 due to major changes on items templates & categories. See blogpost about eLabFTW 5.3
info_response = infoApi.get_info()
info = info_response.to_dict()
version_int = info.get("elabftw_version_int", 0)
version = info.get("elabftw_version", "unknown")

# if version_int >= 50300:
#     sys.exit(
#         "ERROR: This script is not compatible with eLabFTW versions after 5.3.\n"
#         f"You are currently using version {version}, which introduced breaking changes in resources categories & templates.\n"
#         "A working version is on the way."
#     )

#########################
#     Load Categories   #
#########################

# Check ALLOWED_CATEGORIES loaded from the environment
logging.debug(f"Categories allowed : {ALLOWED_CATEGORIES}")

#########################
#   QUARTZY INVENTORY   #
#########################

# compare existing metadata & incoming metadata
def metadata_changed(existing_metadata_raw, new_metadata_dict):
    existing_metadata = json.loads(existing_metadata_raw) if isinstance(existing_metadata_raw, str) else existing_metadata_raw
    existing_metadata_json = json.dumps(existing_metadata, sort_keys=True)
    new_metadata_json = json.dumps(new_metadata_dict, sort_keys=True)

    return existing_metadata_json != new_metadata_json

# Quartzy public API authorizations (AccessToken)
headers = {"Access-Token": QUARTZY_TOKEN, "Accept": "application/json"}
# Fetch Quartzy inventory and filter
quartzy_raw_items = fetch_all_quartzy_items(QUARTZY_API_INVENTORY_URL, headers, verbose=args.verbose)
quartzy_items = [
    item for item in quartzy_raw_items
    if item.get("type", {}).get("name") in ALLOWED_CATEGORIES
]

logging.debug(f"Total filtered Quartzy items: {len(quartzy_items)}")

#########################
#      eLabFTW SYNC     #
#########################

# Category Sync
existing_types = itemsTypesApi.read_items_types()
category_id_map = {cat.title: cat.id for cat in existing_types}
new_categories = sorted(set(item["type"]["name"] for item in quartzy_items))

logging.debug("Syncing resources categories...")

for category in new_categories:
    if category in category_id_map:
        logging.debug(f"Category already exists: {category}")
        continue
    # generate random color for category
    color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    _, status, headers = itemsTypesApi.post_items_types_with_http_info(
        body={"title": category, "color": color}
    )
    if status == 201:
        location = headers.get("Location", "")
        try:
            new_id = int(location.rstrip("/").split("/")[-1])
            category_id_map[category] = new_id
            logging.debug(f"Created category: {category} (ID: {new_id})")
        except Exception:
            logging.error(f"Couldn't parse ID from Location header: {location}")
    else:
        logging.error(f"Failed to create category '{category}', status: {status}")

def build_metadata(item):
    qid = item.get("id")
    if not qid:
        raise ValueError(f"[ERROR] Missing Quartzy ID for item: {item.get('name')}")

    extra_fields = {
        # keep unique identifier from quartzy to patch existing in eLabFTW
        "Quartzy ID": {"type": "text", "value": qid},
        "Name": {"type": "text", "value": item.get("name", "")},
        "Vendor": {"type": "text", "value": item.get("vendor", "")},
        "Catalog Number": {"type": "text", "value": item.get("catalog_number", "")},
        # the quantity unit is not available via Quartzy API, neither are MIN/MAX to stock
        "Quantity": {
            "type": "number",
            "units": [item.get("unit_size", "")],
            "unit": item.get("unit_size", ""),
            "value": item.get("quantity", "")
        },
        # the price unit is not available via Quartzy API
        "Price": {
            "type": "number",
            "units": ["€", "$"],
            "unit": "€",
            "value": item.get("price", "")
        },
        "Open in Quartzy": {"type": "url", "value": item.get("app_url", "")},
        "Public URL": {
            "type": "url",
            "description": "Origin URL of the item",
            "value": item.get("url", "")
        },
        "Owner": {
            "type": "text",
            "value": f'{(item.get("added_by") or {}).get("first_name", "")} {(item.get("added_by") or {}).get("last_name", "")}'.strip()
        },
        "Owner Contact": {
            "type": "email",
            "value": (item.get("added_by") or {}).get("email", "")
        },
        "Cas Number": {"type": "text", "value": item.get("cas_number", "")},
        "Lot Number": {"type": "text", "value": item.get("lot_number", "")},
        "Serial Number": {"type": "text", "value": item.get("serial_number", "")},
        "Location": {
            "type": "text",
            "value": (item.get("location") or {}).get("name", "")
        },
        "Sub-location": {
            "type": "text",
            "value": (item.get("sublocation") or {}).get("name", "")
        },
        "Technical details": {"type": "text", "value": item.get("technical_details", "")},
        "Expiration Date": {"type": "text", "value": item.get("expiration_date", "")},
        "Reminder Date": {
            "type": "date",
            "value": compute_reminder_date(item.get("expiration_date", ""), item.get("auto_reminder", ""))
        }
    }

    # remove fields with no values
    cleaned = {k: v for k, v in extra_fields.items() if v.get("value")}

    if not cleaned:
        raise ValueError(f"[ERROR] Empty metadata for item: {item.get('name')}")

    return {"extra_fields": cleaned}


#########################
#   eLabFTW resources   #
#########################
logging.debug("Pushing Quartzy Inventory to eLabFTW...")
existing_qid_map = {}

response = itemsApi.read_items(_preload_content=False, limit=1500)  # quartzy data has proven to be more than 1300
items = json.loads(response.data.decode("utf-8"))

for elab_item in items:
    metadata_raw = elab_item.get("metadata")
    if not metadata_raw:
        continue

    try:
        # normalize to dict to use metadata
        if isinstance(metadata_raw, str):
            metadata = json.loads(metadata_raw)
        else:
            metadata = metadata_raw

        qid = metadata.get("extra_fields", {}).get("Quartzy ID", {}).get("value")
        if qid:
            existing_qid_map[qid] = elab_item["id"]
        else:
            continue
    except Exception as e:
        logging.error(f"Failed to parse metadata for item ID {elab_item.get('id')}: {e}")

logging.debug(f"Found {len(existing_qid_map)} existing items with Quartzy ID.")

# Loop
created, updated = 0, 0

pbar = tqdm(quartzy_items, desc="Syncing Quartzy items", unit="item", disable=not args.verbose)

for item in pbar:
    try:
        name = item.get("name", "Unnamed")
        if args.verbose:
            pbar.write(f"Handling item: {name}")

        cat_name = item["type"]["name"]
        cat_id = category_id_map.get(cat_name)

        if not cat_id:
            continue

        qid = item.get("id")
        if not qid:
            logging.warning(f"Skipping item '{item['name']}' (missing Quartzy ID)")
            continue

        body = ""
        tech_details = item.get("technical_details")
        if tech_details:
            escaped = html.escape(tech_details).replace("\n", "<br>")
            body = f"<h1>Technical details</h1>\n<p>{escaped}</p>"

        if qid in existing_qid_map:
            # PATCH existing item
            item_id = existing_qid_map[qid]

            # before sending a patch request, check if the data has changed. If not, do not send useless request
            response = itemsApi.get_item(item_id, _preload_content=False)
            existing_item = json.loads(response.data.decode("utf-8"))

            # Get and parse existing metadata
            existing_metadata_raw = existing_item.get("metadata")
            existing_metadata = (
                json.loads(existing_metadata_raw)
                if isinstance(existing_metadata_raw, str)
                else existing_metadata_raw
            )

            # Build new metadata dict to compare with existing
            new_metadata_dict = {
                "extra_fields": build_metadata(item).get("extra_fields", {})
            }

            # use metadata_changed function to compare
            if not metadata_changed(existing_metadata_raw, new_metadata_dict):
                continue  # Skip patching, no change in metadata

            patch_payload = {
                "title": item["name"],
                "body": body,
                "metadata": json.dumps(new_metadata_dict)
            }
            itemsApi.patch_item(item_id, body=patch_payload)
            logging.debug(f"Updated item '{item['name']}' (ID: {item_id})")
            updated += 1
            itemsApi.patch_item(item_id, body={"action": "forcelock"})
        else:
            # POST new item (only with category_id)
            _, status_code, headers = itemsApi.post_item_with_http_info(body={
                "category_id": cat_id
            })
            location = headers.get("Location", "")
            item_id = int(location.rstrip("/").split("/")[-1])

            # PATCH with metadata, title, and body
            patch_payload = {
                "title": item["name"],
                "body": body,
                "metadata": json.dumps(build_metadata(item))
            }
            itemsApi.patch_item(item_id, body=patch_payload)
            logging.debug(f"Created item '{item['name']}' (ID: {item_id})")
            created += 1
            itemsApi.patch_item(item_id, body={"action": "forcelock"})

            pbar.set_postfix(created=created, updated=updated, refresh=False)
    except Exception as e:
        logging.error(f"Exception on item '{name}': {e}")

total = len(quartzy_items)

if created == 0:
    logging.debug(f"Done: {created}/{total} item{'s' if total != 1 else ''} needed import.")
else:
    logging.debug(f"Done: {created}/{total} item{'s' if created != 1 else ''} successfully imported.")
if updated == 0:
    logging.debug(f"Done: {updated}/{total} item{'s' if total != 1 else ''} needed update.")
else:
    logging.debug(f"Done: {updated}/{total} item{'s' if updated != 1 else ''} successfully updated.")
