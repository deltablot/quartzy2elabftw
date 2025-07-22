#!/usr/bin/env python
# © Deltablot 2025
# License: MIT

# dev file: only used for fetching the inventory during dev phase, paste the json in an inventory.json and use that in JSON Editor to check data edits
import os
import sys
import requests
import elabapi_python
import json
import subprocess

import urllib3
urllib3.disable_warnings(category=urllib3.exceptions.InsecureRequestWarning)

QUARTZY_TOKEN = os.getenv('QUARTZY_TOKEN') or sys.exit('QUARTZY_TOKEN environment variable not set')
QUARTZY_API_INVENTORY_URL = 'https://api.quartzy.com/inventory-items'
ELABFTW_HOST_URL = os.getenv('ELABFTW_HOST_URL') or sys.exit('ELABFTW_HOST_URL environment variable not set')
ELABFTW_API_KEY = os.getenv('ELABFTW_API_KEY') or sys.exit('ELABFTW_API_KEY environment variable not set')

# Configure the api client
configuration = elabapi_python.Configuration()
configuration.api_key["api_key"] = ELABFTW_API_KEY
configuration.api_key_prefix["api_key"] = "Authorization"
configuration.host = ELABFTW_HOST_URL
configuration.debug = False
configuration.verify_ssl = False

api_client = elabapi_python.ApiClient(configuration)
api_client.set_default_header(header_name="Authorization", header_value=ELABFTW_API_KEY)

headers = {
    "Access-Token": QUARTZY_TOKEN,
    "Accept": "application/json"
}

# # Uncomment and try: to confirm how many items per page
# # output: 25 items in one page
# params = {"page": 49} # figured there are 49 pages (24 items on last page)
# response = requests.get(QUARTZY_API_INVENTORY_URL, headers=headers, params=params)
# if response.status_code == 200:
#     items = response.json()
#     print(f"Page contains {len(items)} items")
# sys.exit(1)

all_items = []
page = 1
per_page = 25

while True: # stops after around 48 pages so it's normal
    print(f"Fetching page {page}...")
    params = {"page": page, "per_page": per_page}
    response = requests.get(QUARTZY_API_INVENTORY_URL, headers=headers, params=params)

    if response.status_code != 200:
        print("Quartzy API failed:", response.status_code, response.text)
        sys.exit(1)

    page_items = response.json()

    if not isinstance(page_items, list):
        print("❌ Unexpected format — expected list of items.")
        sys.exit(1)

    if not page_items:
        break  # stop the loop

    all_items.extend(page_items)
    page += 1

print(f"\nSuccessfully fetched {len(all_items)} items from Quartzy!")

# Write to file
with open("inventory.json", "w") as f:
    json.dump(all_items, f, indent=2)

# Open in default system viewer for dev inspection
subprocess.run(["xdg-open", os.path.abspath("inventory.json")])
