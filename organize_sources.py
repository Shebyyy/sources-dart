#!/usr/bin/env python3
"""
Script to clone repositories and organize source JSON files by type.
Handles everything: cloning, processing, and organizing.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Configuration - Repository URLs
REPOSITORIES = {
    "ibro": "https://git.luna-app.eu/ibro/services.git",
    "50n50": "https://git.luna-app.eu/50n50/sources.git"
}

OUTPUT_DIR = Path("organized_sources")

def normalize_type(type_str: str) -> str:
    """Normalize the type string to a consistent format."""
    if not type_str:
        return "other"
    
    # Clean up the type string
    type_clean = type_str.lower().strip()
    # Replace common separators with underscores
    type_clean = type_clean.replace("/", "_").replace(" ", "_").replace("-", "_")
    # Remove multiple underscores
    while "__" in type_clean:
        type_clean = type_clean.replace("__", "_")
    
    return type_clean

def find_json_files(directory: Path) -> List[Path]:
    """Recursively find all JSON files in a directory, ignoring root-level files."""
    json_files = []
    
    if not directory.exists():
        return json_files
    
    for item in directory.rglob("*.json"):
        if item.is_file():
            # Skip hidden files and common non-source files
            if not any(part.startswith('.') for part in item.parts):
                # Only include files that are in subdirectories (depth > 1)
                # This ignores files like: repository/file.json
                # But includes: repository/subfolder/file.json
                relative_path = item.relative_to(directory)
                if len(relative_path.parts) > 1:
                    json_files.append(item)
    
    return json_files

def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load a JSON file and return its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {file_path}: {e}")
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return None

def clone_repositories() -> List[str]:
    """Clone all configured repositories."""
    print("=" * 60)
    print("Cloning Repositories")
    print("=" * 60)
    
    cloned_repos = []
    
    for repo_name, repo_url in REPOSITORIES.items():
        print(f"\n📥 Cloning {repo_name}...")
        
        # Remove existing directory if it exists
        repo_dir = Path(repo_name)
        if repo_dir.exists():
            print(f"  🗑️  Removing existing {repo_name}/ directory")
            subprocess.run(["rm", "-rf", str(repo_dir)], check=True)
        
        # Clone the repository
        try:
            result = subprocess.run(
                ["git", "clone", repo_url, repo_name],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"  ✅ Successfully cloned {repo_name}")
            cloned_repos.append(repo_name)
            
            # Show some info about what we got
            json_files = list(repo_dir.rglob("*.json"))
            print(f"  📄 Found {len(json_files)} JSON files")
            
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to clone {repo_name}")
            print(f"     This might be due to:")
            print(f"     • Authentication required")
            print(f"     • Cloudflare protection")
            print(f"     • Repository doesn't exist")
            print(f"     • Network issues")
            if e.stderr:
                print(f"     Error details: {e.stderr.strip()}")
            print(f"     ⚠️  Will continue with other repositories...")
    
    print(f"\n📊 Successfully cloned {len(cloned_repos)} repositories")
    return cloned_repos

def find_repositories() -> List[str]:
    """Find repositories that were successfully cloned."""
    repositories = []
    current_dir = Path(".")
    
    for item in current_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Check if it looks like a git repository
            if (item / ".git").exists():
                repositories.append(item.name)
    
    return repositories

def organize_sources():
    """Main function to clone repositories and organize source files."""
    print("=" * 60)
    print("Starting Source Organization")
    print("=" * 60)
    
    # Step 1: Clone repositories
    cloned_repos = clone_repositories()
    
    if not cloned_repos:
        print("❌ No repositories were successfully cloned")
        return
    
    # Step 2: Find repositories that were cloned
    repositories = find_repositories()
    
    print(f"\n📋 Processing {len(repositories)} repositories: {', '.join(repositories)}")
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Structure: {repo_name: {type: [sources]}}
    organized_data = defaultdict(lambda: defaultdict(list))
    
    # Statistics
    total_files_found = 0
    total_files_processed = 0
    total_files_failed = 0
    
    for repo_name in repositories:
        print(f"\n{'='*60}")
        print(f"Processing repository: {repo_name}")
        print(f"{'='*60}")
        
        repo_dir = Path(repo_name)
        
        # Find all JSON files
        json_files = find_json_files(repo_dir)
        total_files_found += len(json_files)
        
        print(f"📁 Found {len(json_files)} JSON files")
        
        for json_file in json_files:
            relative_path = json_file.relative_to(repo_dir)
            print(f"\n  📄 Processing: {relative_path}")
            
            json_data = load_json_file(json_file)
            
            if json_data is None:
                print(f"    ⚠️  Failed to load JSON")
                total_files_failed += 1
                continue
            
            # Get the type from JSON
            source_type = json_data.get("type", "other")
            normalized_type = normalize_type(source_type)
            
            # Add metadata about file location
            json_data["_metadata"] = {
                "original_file": str(relative_path),
                "repository": repo_name,
                "original_type": source_type
            }
            
            # Add to organized structure
            organized_data[repo_name][normalized_type].append(json_data)
            total_files_processed += 1
            
            source_name = json_data.get("sourceName", "Unknown")
            print(f"    ✅ Added '{source_name}' to {repo_name}/{normalized_type}")
    
    # Create directory structure and write files
    print(f"\n{'='*60}")
    print("Writing Organized Files")
    print(f"{'='*60}")
    
    all_types = set()
    
    # Group all sources by type across all repositories for combined files
    combined_by_type = defaultdict(list)
    
    for repo_name, types_dict in organized_data.items():
        repo_dir = OUTPUT_DIR / repo_name
        repo_dir.mkdir(exist_ok=True)
        
        print(f"\n📂 Repository: {repo_name}")
        
        for source_type, sources in sorted(types_dict.items()):
            all_types.add(source_type)
            output_file = repo_dir / f"{source_type}.json"
            
            # Sort sources by sourceName for consistency
            sources.sort(key=lambda x: x.get("sourceName", "").lower())
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sources, f, indent=2, ensure_ascii=False)
            
            print(f"  ✅ {source_type}.json ({len(sources)} sources)")
            
            # Add to combined structure
            for source in sources:
                # Add repository info to each source
                source["repository"] = repo_name
                combined_by_type[source_type].append(source)
    
    # Create combined files by type across all repositories
    print(f"\n{'='*60}")
    print("Creating Combined Type Files")
    print(f"{'='*60}")
    
    combined_dir = OUTPUT_DIR / "combined"
    combined_dir.mkdir(exist_ok=True)
    
    for source_type, sources in sorted(combined_by_type.items()):
        output_file = combined_dir / f"{source_type}.json"
        
        # Sort by repository then by sourceName
        sources.sort(key=lambda x: (x.get("repository", ""), x.get("sourceName", x.get("name", "")).lower()))
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sources, f, indent=2, ensure_ascii=False)
        
        repos = set(s.get("repository", "Unknown") for s in sources)
        print(f"  ✅ combined/{source_type}.json ({len(sources)} sources from {len(repos)} repos)")
    
    # Create a summary file
    print(f"\n{'='*60}")
    print("Creating Summary")
    print(f"{'='*60}")
    
    summary = {
        "generated_at": str(Path.cwd()),
        "total_repositories": len(organized_data),
        "total_types": len(all_types),
        "all_types": sorted(list(all_types)),
        "statistics": {
            "files_found": total_files_found,
            "files_processed": total_files_processed,
            "files_failed": total_files_failed
        },
        "repositories": {},
        "combined_summary": {}
    }
    
    for repo_name, types_dict in organized_data.items():
        repo_summary = {
            "types": sorted(list(types_dict.keys())),
            "total_sources": sum(len(sources) for sources in types_dict.values()),
            "sources_by_type": {}
        }
        
        for source_type, sources in sorted(types_dict.items()):
            repo_summary["sources_by_type"][source_type] = {
                "count": len(sources),
                "sources": [s.get("sourceName", "Unknown") for s in sources]
            }
        
        summary["repositories"][repo_name] = repo_summary
    
    # Add combined summary
    for source_type, sources in combined_by_type.items():
        repos = set(s.get("repository", "Unknown") for s in sources)
        summary["combined_summary"][source_type] = {
            "total_sources": len(sources),
            "repositories": sorted(list(repos)),
            "repository_count": len(repos)
        }
    
    summary_file = OUTPUT_DIR / "summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Summary written to: {summary_file}")
    
    # Print final statistics
    print(f"\n{'='*60}")
    print("Organization Complete!")
    print(f"{'='*60}")
    print(f"📊 Statistics:")
    print(f"  • Total files found: {total_files_found}")
    print(f"  • Successfully processed: {total_files_processed}")
    print(f"  • Failed: {total_files_failed}")
    print(f"  • Repositories: {len(organized_data)}")
    print(f"  • Unique types: {len(all_types)}")
    print(f"  • Types: {', '.join(sorted(all_types))}")
    
    print(f"\n📂 Output directory: {OUTPUT_DIR.absolute()}")
    print(f"📂 Individual repo files: {OUTPUT_DIR}/<repo_name>/")
    print(f"📂 Combined type files: {OUTPUT_DIR}/combined/")
    
    # Print repository summary
    for repo_name, types_dict in organized_data.items():
        total = sum(len(sources) for sources in types_dict.values())
        print(f"  • {repo_name}: {total} sources across {len(types_dict)} types")
    
    # Print combined summary
    print(f"\n🔗 Combined files:")
    for source_type, sources in combined_by_type.items():
        repos = set(s.get("repository", "Unknown") for s in sources)
        print(f"  • {source_type}.json: {len(sources)} sources from {len(repos)} repositories")
    
    # Step 3: Clean up cloned repositories
    print(f"\n{'='*60}")
    print("Cleaning Up")
    print(f"{'='*60}")
    
    for repo_name in repositories:
        repo_dir = Path(repo_name)
        if repo_dir.exists():
            print(f"  🗑️  Removing {repo_name}/")
            subprocess.run(["rm", "-rf", str(repo_dir)], check=True)
    
    print(f"✅ Cleanup complete!")

if __name__ == "__main__":
    organize_sources()