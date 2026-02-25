# Sync Data - Quartzy2eLabFTW

This script is used to fetch inventory data from a user's Quartzy's **Inventory** and send it to eLabFTW as readonly **Resources**.
It creates the **Resource Categories** from the "**Type**" column of your Inventory, and places the rest of the data as extra fields.

## Requirements

This project uses `uv` as a dependency manager. See installation instructions: https://github.com/astral-sh/uv?tab=readme-ov-file#installation

This project can also be run with Docker, see [Run with Docker](#run-with-docker) section.

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

> [!WARNING]
> Items will be imported into the team associated with the API key specified in the configuration!
>
> Ensure the API key is generated from an account logged into the correct receiving team.
>
> For instructions, see: https://doc.elabftw.net/api.html#generating-a-key

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

## Run with Docker

```bash
# Create and edit the .env file (not included in the image)
cp .env.dist .env
chmod 600 .env
$EDITOR .env
```

If you're running the sync with a local instance of eLabFTW, refer to this section: [Networking](#Networking).

Otherwise, just run with the command:

```bash
# Run the sync (once)
docker run --rm --env-file .env ghcr.io/deltablot/quartzy2elabftw
```

### With docker-compose

A sample config is provided in `docker-compose.yml.dist`. Copy it and edit to your needs:

```bash
cp docker-compose.yml.dist docker-compose.yml
$EDITOR docker-compose.yml

# Repeat steps for setting .env file
cp .env.dist .env
chmod 600 .env
$EDITOR .env
```

Then run the sync script:

```bash
docker compose run --rm quartzy2elabftw
```

### Networking

When running locally, with eLabFTW on the same host (linux):

- Make sure you previously set the host url in .env file: `ELABFTW_HOST_URL=https://your-domain.local:3148/api/v2/`
- Use `--add-host=elab.local:host-gateway` (replace with your host name)
- If your cert is self-signed, add `--insecure` flag (dev only)

```bash
docker run --rm --env-file .env --add-host=elab.local:host-gateway quartzy2elabftw --insecure
# with mitmproxy setup
# docker run --rm --env-file .env --add-host=host.docker.internal:host-gateway --add-host=elab.local:host-gateway -e HTTP_PROXY=http://host.docker.internal:8080 -e HTTPS_PROXY=http://host.docker.internal:8080 -e NO_PROXY= -e REQUESTS_CA_BUNDLE=/mitmproxy/mitmproxy-ca.pem -v /path/to/your/.mitmproxy:/mitmproxy:ro,Z ghcr.io/deltablot/quartzy2elabftw --insecure
```

## Automation

You can automate the sync with a cron job. Edit your user crontab:

```bash
crontab -e
```

Run every day at 07:30:

```cron
# Every day at 07:30 - edit the path to point to the script's directory
30 07 * * * /usr/bin/docker run --rm --env-file /path/to/quartzy2elabftw/.env --add-host=host.docker.internal:host-gateway --add-host=elab.local:host-gateway ghcr.io/deltablot/quartzy2elabftw
```

## Caveats

No support for archived or deleted entries from Quartzy.
