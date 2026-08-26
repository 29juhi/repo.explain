"""Print the directory structure of a GitHub repository."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


API_ROOT = "https://api.github.com"


@dataclass(frozen=True)
class Repository:
    owner: str
    name: str


def parse_repository_url(repository_url: str) -> Repository:
    """Extract the owner and repository name from a GitHub URL."""
    parsed = urlparse(repository_url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        raise ValueError("URL must point to github.com, for example https://github.com/owner/repo")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0].lower() in {"search", "explore", "topics"}:
        raise ValueError("URL must include an owner and repository name")

    repository_name = parts[1]
    if repository_name.endswith(".git"):
        repository_name = repository_name[:-4]
    if not repository_name:
        raise ValueError("Repository name cannot be empty")

    return Repository(owner=parts[0], name=repository_name)


def fetch_contents(repository: Repository, path: str = "") -> list[dict[str, str]]:
    """Fetch one directory listing from GitHub's Contents API."""
    encoded_path = f"/{path}" if path else ""
    endpoint = f"{API_ROOT}/repos/{repository.owner}/{repository.name}/contents{encoded_path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "github-structure-script",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(endpoint, headers=headers)
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if not isinstance(payload, list):
        raise ValueError("The repository root is a file or could not be read as a directory")
    return payload


def print_files(repository: Repository) -> None:
    """Recursively print only file paths in the repository."""
    def visit(path: str) -> None:
        entries = fetch_contents(repository, path)
        entries.sort(key=lambda entry: entry.get("path", "").lower())

        for entry in entries:
            entry_type = entry.get("type")
            if entry_type == "dir":
                visit(entry.get("path", ""))
            elif entry_type == "file":
                print(entry.get("path", ""))

    visit("")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print file paths in a GitHub repository.")
    parser.add_argument("url", nargs="?", help="GitHub repository URL")
    args = parser.parse_args()
    repository_url = args.url or input("Enter a GitHub repository URL: ").strip()

    try:
        repository = parse_repository_url(repository_url)
        print_files(repository)
    except (HTTPError, URLError) as error:
        print(f"GitHub request failed: {error}", file=sys.stderr)
        return 1
    except (ValueError, TimeoutError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())