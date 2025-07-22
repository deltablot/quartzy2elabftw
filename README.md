# Sync Data - Quartzy2eLabFTW

This script is used to fetch inventory data from a user's Quartzy's **Inventory** and send it to eLabFTW as readonly **Resources**.
It creates the **Resource Categories** from the "**Type**" column of your Inventory, and places the rest of the data as extra fields.

## Requirements

This project uses `uv` as a dependency manager. See installation instructions: https://github.com/astral-sh/uv?tab=readme-ov-file#installation

## Install dependencies

~~~bash
# Clone this repository
git clone git@github.com:deltablot/quartzy2elabftw.git

# Get into the folder
cd quartzy2elabftw

# Install dependencies with uv
uv sync --frozen
~~~

## Env configuration

These variables are needed for the correct execution of the script:

~~~bash
# your Quartzy access token created from https://app.quartzy.com/profile/access-tokens
QUARTZY_TOKEN=thisIsAnExampleKeyNotReal
# make sure to have /api/v2/ at the end!
ELABFTW_HOST_URL=https://lab.example.fr/api/v2/
ELABFTW_API_KEY=3-C5EF0776BCE0A85
# define here the list of categories you'd like to be synchronized
CATEGORIES=["Antibody", "Plasmid", "-80 boxes"]
~~~

You can use a `.env` file to store them permanently, see the [.env.dist](./.env.dist) file for reference.

~~~bash
cp .env.dist .env
chmod 600 .env
$EDITOR .env
~~~

## Run

This script retrieves inventory data from Quartzy and uploads it to eLabFTW. It creates resource categories based on the "Type" column of the inventory and adds the remaining data as extra fields.

The categories defined in `CATEGORIES` env will be processed.

These categories are created in eLabFTW to store the incoming inventory data, and the resources are then locked.

After the initial run, subsequent executions will check for any necessary updates to existing data, only patching those that require changes.

~~~bash
# Run the script
uv run main.py
# Run in dev mode: add the --verbose flag for logging
uv run main.py --verbose
# you can also add --insecure flag in dev mode to disable SSL warnings
~~~

## Caveats

No support for archived or deleted entries from Quartzy.
