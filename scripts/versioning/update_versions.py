# scripts/update_versions.py
import os
import sys
import yaml
import requests

# --- Configuration ---
VERSIONS_FILE = "versions.yml"
GITHUB_API_BASE = "https://api.github.com"
PYPI_API_BASE = "https://pypi.org/pypi"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") # For authenticated requests to avoid rate limits

# --- Helper Functions ---
def set_output(name, value):
    """Sets an output for the GitHub Actions workflow."""
    with open(os.getenv('GITHUB_ENV'), 'a') as env_file:
        env_file.write(f"{name}={value}\n")
    print(f"==> Set output {name}={value}")

# --- Fetcher Functions ---

def fetch_github_release(identifier, options):
    """Fetches the latest release version from GitHub."""
    allow_prerelease = options.get("allow_prerelease", False)
    strip_prefix_v = options.get("strip_prefix_v", True)

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    if allow_prerelease:
        # Get all releases and pick the first one (most recent)
        url = f"{GITHUB_API_BASE}/repos/{identifier}/releases"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        if not response.json():
            print(f"Warning: No releases found for {identifier}.")
            return None
        version = response.json()[0]["tag_name"]
    else:
        # Get the 'latest' stable release
        url = f"{GITHUB_API_BASE}/repos/{identifier}/releases/latest"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        version = response.json()["tag_name"]

    if strip_prefix_v and version.startswith('v'):
        return version[1:]
    return version

def fetch_pypi_version(identifier, options):
    """Fetches the latest version from PyPI."""
    url = f"{PYPI_API_BASE}/{identifier}/json"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["info"]["version"]

# --- Main Logic ---

def main():
    try:
        with open(VERSIONS_FILE, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {VERSIONS_FILE} not found!")
        sys.exit(1)

    fetchers = {
        "github_release": fetch_github_release,
        "pypi": fetch_pypi_version,
    }

    changes_made = False
    for item in data.get("software", []):
        name = item["name"]
        source = item["source"]
        identifier = item["identifier"]
        current_version = item["current_version"]
        options = item.get("options", {})

        print(f"Checking {name}...")

        if source not in fetchers:
            print(f"Warning: Unknown source '{source}' for {name}. Skipping.")
            continue

        try:
            fetcher_func = fetchers[source]
            latest_version = fetcher_func(identifier, options)

            if latest_version and latest_version != str(current_version):
                print(f"  Found new version: {latest_version} (was {current_version})")
                item["current_version"] = latest_version
                changes_made = True
            else:
                print(f"  No new version found. Current: {current_version}")

        except requests.exceptions.RequestException as e:
            print(f"Error fetching version for {name}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {name}: {e}")

    if changes_made:
        print("\nChanges were made. Updating versions.yml...")
        try:
            with open(VERSIONS_FILE, 'w') as f:
                # Use sort_keys=False to preserve the order from the original file
                yaml.dump(data, f, sort_keys=False, indent=2)
            set_output("CHANGES_MADE", "true")
        except Exception as e:
            print(f"Error writing to {VERSIONS_FILE}: {e}")
            sys.exit(1)
    else:
        print("\nNo changes detected.")
        set_output("CHANGES_MADE", "false")

if __name__ == "__main__":
    main()
