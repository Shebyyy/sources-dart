#!/usr/bin/env python3
"""
Script to organize source JSON files from multiple repositories by type.
Fetches JSON files from git.luna-app.eu repositories and organizes them.
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Configuration
REPOS = {
    "50n50": "https://git.luna-app.eu/50n50/sources",
    "ibro": "https://git.luna-app.eu/ibro/services"
}

# Output directory structure
OUTPUT_DIR = Path("organized_sources")

def get_api_url(repo_url: str) -> str:
    """Convert git repo URL to API URL."""
    # git.luna-app.eu uses Gitea, API format: /api/v1/repos/{owner}/{repo}
    parts = repo_url.replace("https://git.luna-app.eu/", "").split("/")
    owner, repo = parts[0], parts[1]
    return f"https://git.luna-app.eu/api/v1/repos/{owner}/{repo}"

def get_repo_tree(api_url: str, branch: str = "main") -> List[Dict]:
    """Get the file tree of a repository."""
    tree_url = f"{api_url}/git/trees/{branch}?recursive=1"
    response = requests.get(tree_url)
    
    if response.status_code != 200:
        print(f"Failed to fetch tree from {tree_url}: {response.status_code}")
        return []
    
    data = response.json()
    return data.get("tree", [])

def fetch_json_file(repo_owner: str, repo_name: str, file_path: str) -> Dict[str, Any]:
    """Fetch a JSON file content from the repository."""
    raw_url = f"https://git.luna-app.eu/{repo_owner}/{repo_name}/raw/branch/main/{file_path}"
    
    try:
        response = requests.get(raw_url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching {file_path}: {e}")
    
    return None

def normalize_type(type_str: str) -> str:
    """Normalize the type string to a consistent format."""
    if not type_str:
        return "other"
    
    type_lower = type_str.lower()
    
    # Map various type strings to standard categories
    if "anime" in type_lower:
        return "anime"
    elif "manga" in type_lower:
        return "manga"
    elif "novel" in type_lower:
        return "novels"
    elif "movie" in type_lower or "show" in type_lower:
        if "anime" in type_lower:
            return "anime"
        return "movies_shows"
    else:
        return type_lower.replace("/", "_").replace(" ", "_")

def organize_sources():
    """Main function to organize source files."""
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Structure: {repo_name: {type: [sources]}}
    organized_data = defaultdict(lambda: defaultdict(list))
    
    for repo_name, repo_url in REPOS.items():
        print(f"\nProcessing repository: {repo_name}")
        
        api_url = get_api_url(repo_url)
        tree = get_repo_tree(api_url)
        
        if not tree:
            print(f"Could not fetch tree for {repo_name}")
            continue
        
        # Find all JSON files
        json_files = [item for item in tree if item["path"].endswith(".json") and item["type"] == "blob"]
        
        print(f"Found {len(json_files)} JSON files in {repo_name}")
        
        for file_item in json_files:
            file_path = file_item["path"]
            print(f"  Fetching: {file_path}")
            
            json_data = fetch_json_file(repo_name, 
                                       "sources" if repo_name == "50n50" else "services", 
                                       file_path)
            
            if json_data:
                # Get the type from JSON
                source_type = json_data.get("type", "other")
                normalized_type = normalize_type(source_type)
                
                # Add to organized structure
                organized_data[repo_name][normalized_type].append(json_data)
                print(f"    Added to {repo_name}/{normalized_type}")
    
    # Create directory structure and write files
    for repo_name, types_dict in organized_data.items():
        repo_dir = OUTPUT_DIR / repo_name
        repo_dir.mkdir(exist_ok=True)
        
        print(f"\nWriting files for {repo_name}:")
        
        for source_type, sources in types_dict.items():
            output_file = repo_dir / f"{source_type}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sources, f, indent=2, ensure_ascii=False)
            
            print(f"  Created: {output_file} ({len(sources)} sources)")
    
    # Create a summary file
    summary = {
        "total_repositories": len(organized_data),
        "repositories": {}
    }
    
    for repo_name, types_dict in organized_data.items():
        summary["repositories"][repo_name] = {
            "types": list(types_dict.keys()),
            "total_sources": sum(len(sources) for sources in types_dict.values()),
            "sources_by_type": {t: len(s) for t, s in types_dict.items()}
        }
    
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\nSummary written to: {summary_file}")
    print("\nOrganization complete!")
    print(f"Total repositories processed: {len(organized_data)}")
    for repo_name, types_dict in organized_data.items():
        total = sum(len(sources) for sources in types_dict.values())
        print(f"  {repo_name}: {total} sources across {len(types_dict)} types")

if __name__ == "__main__":
    organize_sources()
