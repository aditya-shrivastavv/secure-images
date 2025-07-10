# scripts/versioning/update_versions.py
import os
import sys
import re
import yaml
import requests
from bs4 import BeautifulSoup
from packaging.version import Version, InvalidVersion

# --- Configuration ---
VERSIONS_FILE = "versions.yaml" # Renamed to match your file
APACHE_ARCHIVE_BASE = "https://archive.apache.org/dist"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# --- Helper Functions ---
def set_output(name, value):
    """Sets an output for the GitHub Actions workflow."""
    with open(os.getenv('GITHUB_ENV'), 'a') as env_file:
        env_file.write(f"{name}={value}\n")
    print(f"==> Set output {name}={value}")

# --- Fetcher Functions ---

# NEW: Custom fetcher for Apache Archive HTML pages
def fetch_apache_archive_version(identifier, options):
    """
    Fetches the latest version by parsing an Apache Archive directory listing.
    """
    url = f"{APACHE_ARCHIVE_BASE}/{identifier}/"
    print(f"  Fetching from Apache Archive: {url}")
    response = requests.get(url)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'lxml')
    versions = []
    # Regular expression to match version-like directory names (e.g., 3.7.0/)
    version_pattern = re.compile(r'^\d+\.\d+\.\d+/$')

    for link in soup.find_all('a'):
        href = link.get('href')
        if href and version_pattern.match(href):
            try:
                # Strip the trailing slash and create a Version object
                version_str = href[:-1]
                versions.append(Version(version_str))
            except InvalidVersion:
                # Ignore entries that look like versions but aren't (e.g., weird tags)
                continue

    if not versions:
        print(f"Warning: No valid versions found for {identifier} at {url}")
        return None

    # The max() of a list of Version objects will be the latest version
    latest_version = max(versions)
    return str(latest_version)

def fetch_github_release(identifier, options):
    """Fetches the latest release version from GitHub."""
    allow_prerelease = options.get("allow_prerelease", False)
    strip_prefix_v = options.get("strip_prefix_v", True)

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    if allow_prerelease:
        url = f"{GITHUB_API_BASE}/repos/{identifier}/releases"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        if not response.json():
            print(f"Warning: No releases found for {identifier}.")
            return None
        version = response.json()[0]["tag_name"]
    else:
        url = f"{GITHUB_API_BASE}/repos/{identifier}/releases/latest"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        version = response.json()["tag_name"]

    if strip_prefix_v and version.startswith('v'):
        return version[1:]
    return version

# --- Main Logic ---
def main():
    try:
        with open(VERSIONS_FILE, 'r') as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {VERSIONS_FILE} not found!")
        sys.exit(1)

    # NEW: Register the custom fetcher
    fetchers = {
        "github_release": fetch_github_release,
        "apache_archive": fetch_apache_archive_version,
    }

    changes_made = False
    # FIX: Changed 'softwares' to 'software' to match your YAML file structure
    for item in data.get("software", []):
        name = item["name"]
        source = item["source"]
        # Identifier can be optional for some sources, handle gracefully
        identifier = item.get("identifier")
        current_version = item["current_version"]
        options = item.get("options", {})

        print(f"Checking {name}...")

        if source not in fetchers:
            print(f"Warning: Unknown source '{source}' for {name}. Skipping.")
            continue
        
        # Some fetchers might not need an identifier
        if source in ["apache_archive", "github_release"] and not identifier:
             print(f"Warning: Source '{source}' for {name} requires an 'identifier'. Skipping.")
             continue

        try:
            fetcher_func = fetchers[source]
            latest_version = fetcher_func(identifier, options)

            if latest_version and latest_version != str(current_version):
                print(f"  Found new version: {latest_version} (was {current_version})")
                item["current_version"] = latest_version
                changes_made = True
            elif latest_version:
                print(f"  No new version found. Current: {current_version}")
            # If latest_version is None, a warning was already printed by the fetcher

        except requests.exceptions.RequestException as e:
            print(f"Error fetching version for {name}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {name}: {e}")

    if changes_made:
        print(f"\nChanges were made. Updating {VERSIONS_FILE}...")
        try:
            with open(VERSIONS_FILE, 'w') as f:
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
