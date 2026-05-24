#!/usr/bin/env python3
"""
Script to clone repositories and organize source JSON files by type.
Also fetches modules from the Sora Module Library API for repos that
only contain .js files (no JSON metadata).

Output structure:
  anymex/
    50n50/
      anime.json
      manga.json
      novels.json
      audiobooks.json
      other.json
    ibro/
      anime.json
      manga.json
      novels.json
      ...
"""

import os
import json
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Configuration - Repository URLs
REPOSITORIES = {
    "ibro": "https://git.luna-app.eu/ibro/services.git",
    "50n50": "https://git.luna-app.eu/50n50/sources.git",
    "cufiy": "https://git.luna-app.eu/Cufiy/sora-modules.git",
    "emp0ry": "https://git.luna-app.eu/emp0ry/sources.git",
    "mxfia19": "https://gitlab.com/mxfia19-group/module-sora.git",
    "cprmichel": "https://github.com/CPRmichel/sora-movie2k-module.git",
    "ylruhc": "https://github.com/Ylruhc/AllAnime.git",
    "xdfkenny": "https://github.com/xdfkenny/xdfkenny-sora-modules.git",
    "soony5": "https://github.com/Soony5/MangaWorld.git",
    "justbbcr": "https://github.com/justbbcr/streamex.git",
    "mxfia19-twitch": "https://github.com/MXFia19/Twitchnosub-Sora.git",
}

# Sora Module Library API - used as fallback for repos without JSON metadata
SORA_API_URL = "https://library.cufiy.net/api/modules.json"

OUTPUT_DIR = Path("anymex")

# Consolidation map: raw normalized type → canonical output file (without .json)
# Anything streaming-related collapses into "anime"
TYPE_CONSOLIDATION: Dict[str, str] = {
    # Anime / streaming
    "anime":               "anime",
    "animes":              "anime",
    "anime_movies_shows":  "anime",
    "anime_shows_movies":  "anime",
    "movies_shows":        "anime",
    "shows_movies":        "anime",
    "shows_movies_anime":  "anime",
    "movies":              "anime",
    "shows":               "anime",
    # Manga
    "manga":               "manga",
    "mangas":              "manga",
    # Novels
    "novel":               "novels",
    "novels":              "novels",
    # Audiobooks
    "audiobooks":          "audiobooks",
    "audiobook":           "audiobooks",
    # Other (catch-all)
    "other":               "other",
}


def normalize_type(type_str: str) -> str:
    """Normalize the raw type string to a consistent format."""
    if not type_str:
        return "other"
    type_clean = type_str.lower().strip()
    type_clean = type_clean.replace("/", "_").replace(" ", "_").replace("-", "_")
    while "__" in type_clean:
        type_clean = type_clean.replace("__", "_")
    return type_clean


def canonical_type(type_str: str) -> str:
    """Map a normalized type string to its canonical output file name."""
    normalized = normalize_type(type_str)
    return TYPE_CONSOLIDATION.get(normalized, "other")


def get_repo_key_from_url(url: str) -> Optional[str]:
    """Map a scriptUrl from the Sora API to a repo key matching REPOSITORIES dict."""
    if not url:
        return None

    # raw.githubusercontent.com/OWNER/REPO/...
    import re
    raw_gh = re.match(r"https://raw\.githubusercontent\.com/([^/]+)/", url)
    if raw_gh:
        owner = raw_gh.group(1)
        owner_map = {
            "50n50": "50n50",
            "CPRmichel": "cprmichel",
            "Ylruhc": "ylruhc",
            "xdfkenny": "xdfkenny",
            "Soony5": "soony5",
            "justbbcr": "justbbcr",
            "MXFia19": "mxfia19-twitch",
        }
        return owner_map.get(owner, owner)

    # git.luna-app.eu/OWNER/REPO/...
    luna = re.match(r"https://git\.luna-app\.eu/([^/]+)/", url)
    if luna:
        owner = luna.group(1)
        owner_map = {
            "ibro": "ibro",
            "50n50": "50n50",
            "Cufiy": "cufiy",
            "emp0ry": "emp0ry",
        }
        return owner_map.get(owner, owner)

    # gitlab.com/GROUP/REPO/...
    gl = re.match(r"https://gitlab\.com/([^/]+)/", url)
    if gl:
        owner = gl.group(1)
        owner_map = {
            "mxfia19-group": "mxfia19",
            "50n50": "50n50",
        }
        return owner_map.get(owner, owner)

    # codeberg.org/OWNER/REPO/...
    cb = re.match(r"https://codeberg\.org/([^/]+)/", url)
    if cb:
        owner = cb.group(1)
        owner_map = {"50n50": "50n50"}
        return owner_map.get(owner, owner)

    return None


def find_json_files(directory: Path) -> List[Path]:
    """Recursively find all JSON files in subdirectories (depth > 1)."""
    json_files = []
    if not directory.exists():
        return json_files
    for item in directory.rglob("*.json"):
        if item.is_file():
            if not any(part.startswith('.') for part in item.parts):
                relative_path = item.relative_to(directory)
                if len(relative_path.parts) > 1:
                    json_files.append(item)
    return json_files


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON decode error in {file_path}: {e}")
    except Exception as e:
        print(f"  ⚠️  Error reading {file_path}: {e}")
    return None


def fetch_sora_api() -> List[Dict[str, Any]]:
    """Fetch module list from the Sora Module Library API."""
    print("\n🌐 Fetching Sora Module Library API...")
    try:
        req = urllib.request.Request(
            SORA_API_URL,
            headers={"User-Agent": "sources-dart-bot/1.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                print(f"  ✅ Fetched {len(data)} modules from API")
                return data
            else:
                print(f"  ⚠️  Unexpected API response format")
                return []
    except urllib.error.URLError as e:
        print(f"  ❌ Failed to fetch Sora API: {e}")
        return []
    except Exception as e:
        print(f"  ❌ Error fetching Sora API: {e}")
        return []


def clone_repositories() -> List[str]:
    """Clone all configured repositories."""
    print("=" * 60)
    print("Cloning Repositories")
    print("=" * 60)

    cloned_repos = []

    for repo_name, repo_url in REPOSITORIES.items():
        print(f"\n📥 Cloning {repo_name}...")

        repo_dir = Path(repo_name)
        if repo_dir.exists():
            print(f"  🗑️  Removing existing {repo_name}/ directory")
            subprocess.run(["rm", "-rf", str(repo_dir)], check=True)

        try:
            subprocess.run(
                ["git", "clone", repo_url, repo_name],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"  ✅ Successfully cloned {repo_name}")
            cloned_repos.append(repo_name)

            json_files = list(repo_dir.rglob("*.json"))
            print(f"  📄 Found {len(json_files)} JSON files")

        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to clone {repo_name}")
            print(f"     Possible reasons: authentication, Cloudflare, repo missing, network")
            if e.stderr:
                print(f"     Error: {e.stderr.strip()}")
            print(f"     ⚠️  Continuing with other repositories...")

    print(f"\n📊 Successfully cloned {len(cloned_repos)} repositories")
    return cloned_repos


def find_repositories() -> List[str]:
    """Find git repositories in the current directory."""
    return [
        item.name
        for item in Path(".").iterdir()
        if item.is_dir() and not item.name.startswith('.') and (item / ".git").exists()
    ]


def organize_sources():
    """Main function to clone repositories and organize source files."""
    print("=" * 60)
    print("Starting Source Organization")
    print("=" * 60)

    # Step 1: Clone
    cloned_repos = clone_repositories()
    if not cloned_repos:
        print("❌ No repositories were successfully cloned")
        return

    # Step 2: Discover cloned repos
    repositories = find_repositories()
    print(f"\n📋 Processing {len(repositories)} repositories: {', '.join(repositories)}")

    # Output root
    OUTPUT_DIR.mkdir(exist_ok=True)

    # {repo_name: {canonical_type: [sources]}}
    organized_data: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: defaultdict(list))

    # Track which sourceNames we already have per repo+type (to avoid API duplicates)
    existing_names: Dict[str, set] = defaultdict(set)

    total_found = total_processed = total_failed = 0

    # Step 3: Process cloned repos for JSON files
    for repo_name in repositories:
        print(f"\n{'='*60}")
        print(f"Processing repository: {repo_name}")
        print(f"{'='*60}")

        repo_dir = Path(repo_name)
        json_files = find_json_files(repo_dir)
        total_found += len(json_files)
        print(f"📁 Found {len(json_files)} JSON files in subdirectories")

        for json_file in json_files:
            relative_path = json_file.relative_to(repo_dir)
            print(f"\n  📄 Processing: {relative_path}")

            data = load_json_file(json_file)
            if data is None:
                total_failed += 1
                continue

            raw_type = data.get("type", "other")
            canon = canonical_type(raw_type)
            source_name = data.get("sourceName", "Unknown")

            organized_data[repo_name][canon].append(data)
            existing_names[f"{repo_name}/{canon}"].add(source_name)
            total_processed += 1

            print(f"    ✅ '{source_name}' → {repo_name}/{canon}  (raw type: '{raw_type}')")

    # Step 4: Fetch from Sora API and fill in missing modules
    #         (for repos that only have .js files, no JSON metadata)
    print(f"\n{'='*60}")
    print("Fetching from Sora Module Library API (fallback)")
    print(f"{'='*60}")

    api_modules = fetch_sora_api()
    api_added = 0

    for module in api_modules:
        script_url = module.get("scriptUrl", "")
        repo_key = get_repo_key_from_url(script_url)

        if not repo_key:
            continue

        # Only add if this repo is in our REPOSITORIES config
        if repo_key not in REPOSITORIES:
            continue

        raw_type = module.get("type", "other")
        canon = canonical_type(raw_type)
        source_name = module.get("sourceName", "Unknown")
        names_key = f"{repo_key}/{canon}"

        # Skip if already found via cloned repo JSON files
        if source_name in existing_names.get(names_key, set()):
            continue

        organized_data[repo_key][canon].append(module)
        existing_names[names_key].add(source_name)
        api_added += 1

        print(f"  ✅ API: '{source_name}' → {repo_key}/{canon}")

    print(f"\n📊 Added {api_added} modules from API that weren't in cloned repo JSONs")

    # Step 5: Write output files under anymex/<repo>/
    print(f"\n{'='*60}")
    print("Writing Organized Files  →  anymex/<repo>/")
    print(f"{'='*60}")

    all_canon_types: set = set()

    for repo_name, types_dict in organized_data.items():
        repo_out_dir = OUTPUT_DIR / repo_name
        repo_out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n📂 anymex/{repo_name}/")

        for canon, sources in sorted(types_dict.items()):
            all_canon_types.add(canon)
            sources.sort(key=lambda x: x.get("sourceName", "").lower())
            output_file = repo_out_dir / f"{canon}.json"

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sources, f, indent=2, ensure_ascii=False)

            print(f"  ✅ {canon}.json  ({len(sources)} sources)")

    # Step 6: Summary
    summary = {
        "output_root": str(OUTPUT_DIR.absolute()),
        "total_repositories": len(organized_data),
        "canonical_types": sorted(list(all_canon_types)),
        "statistics": {
            "files_found": total_found,
            "files_processed": total_processed + api_added,
            "files_failed": total_failed,
            "api_added": api_added,
        },
        "repositories": {
            repo_name: {
                "types": sorted(types_dict.keys()),
                "total_sources": sum(len(s) for s in types_dict.values()),
                "sources_by_type": {
                    canon: {
                        "count": len(sources),
                        "sources": [s.get("sourceName", "Unknown") for s in sources]
                    }
                    for canon, sources in sorted(types_dict.items())
                }
            }
            for repo_name, types_dict in organized_data.items()
        }
    }

    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Summary → {summary_file}")

    # Step 7: Final stats
    print(f"\n{'='*60}")
    print("Organization Complete!")
    print(f"{'='*60}")
    print(f"📊 Statistics:")
    print(f"  • JSON files found:  {total_found}")
    print(f"  • From cloned repos: {total_processed}")
    print(f"  • From API fallback: {api_added}")
    print(f"  • Failed:            {total_failed}")
    print(f"  • Repositories:      {len(organized_data)}")
    print(f"  • Canonical types:   {', '.join(sorted(all_canon_types))}")
    print(f"\n📂 Output root: {OUTPUT_DIR.absolute()}")
    for repo_name, types_dict in organized_data.items():
        total = sum(len(s) for s in types_dict.values())
        print(f"  • anymex/{repo_name}/  →  {total} sources across {len(types_dict)} files")

    # Step 8: Cleanup cloned repos
    print(f"\n{'='*60}")
    print("Cleaning Up Cloned Repos")
    print(f"{'='*60}")
    for repo_name in repositories:
        repo_dir = Path(repo_name)
        if repo_dir.exists():
            print(f"  🗑️  Removing {repo_name}/")
            subprocess.run(["rm", "-rf", str(repo_dir)], check=True)
    print("✅ Cleanup complete!")


if __name__ == "__main__":
    organize_sources()
