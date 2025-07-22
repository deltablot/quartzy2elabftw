# utils.py

import logging

# using local imports since each utils are reused elsewhere

def compute_reminder_date(expiration_date_str, auto_reminder):
    # convert the "auto_reminder" from Quartzy API to a date.
    # e.g expiration_date = 2025-06-28, auto_reminder = "2 WEEK" > converted to "2025-06-13"
    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    if not auto_reminder or auto_reminder.lower() == "none":
        return ""
    try:
        expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d")
    except Exception:
        logging.error(f"Invalid expiration date format: {expiration_date_str}")
        return ""

    if auto_reminder == "1WEEK":
        reminder_date = expiration_date - relativedelta(weeks=1)
    elif auto_reminder == "2WEEK":
        reminder_date = expiration_date - relativedelta(weeks=2)
    elif auto_reminder == "1MONTH":
        reminder_date = expiration_date - relativedelta(months=1)
    else:
        logging.warning(f"Unknown reminder format: {auto_reminder}")
        return ""

    return reminder_date.strftime("%Y-%m-%d")

# fetch all quartzy items, while taking into account the pagination
def fetch_all_quartzy_items(api_url, headers, per_page=25, max_pages=60, verbose=False):
    # currently, there are like 45 pages. Can be updated accordingly in the future
    # api doesn't allow fetching only the pages to see how much there are
    from tqdm import tqdm
    import requests
    all_items = []
    page = 1

    if verbose:
        pbar = tqdm(total=max_pages, desc="Fetching inventory", unit="page")
    else:
        pbar = None

    while page <= max_pages:
        if verbose:
            pbar.set_description(f"Fetching page {page}")

        response = requests.get(api_url, headers=headers, params={"page": page, "per_page": per_page})
        if response.status_code != 200:
            if verbose:
                pbar.write(f"\nQuartzy API failed on page {page}: {response.status_code}")
            logging.error(f"Failed to fetch page {page}: {response.status_code}")
            break

        page_items = response.json()
        if not isinstance(page_items, list):
            if verbose:
                pbar.write("\nUnexpected response format")
            logging.error(f"Unexpected response format on page {page}")
            break

        if not page_items:
            if verbose:
                pbar.write("\nNo more items to fetch.")
            logging.info(f"No more items to fetch (Page {page}).")
            break

        all_items.extend(page_items)
        page += 1
        if verbose:
            pbar.update(1)

        # Avoid rate limiting or getting blocked for 429: too many requests.
        import time
        time.sleep(0.2)

    if verbose:
        pbar.close()

    if not verbose:
        logging.info(f"Total fetched: {len(all_items)} items.")

    return all_items
