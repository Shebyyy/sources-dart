#!/usr/bin/env python3
"""
Script to organize source JSON files from cloned repositories by type.
Works with locally cloned git repositories.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Configuration
SOURCE_REPOS = {
    "50n50": "temp_sources/50n50",
    "ibro": "temp_sources/ibro"
}

OUTPUT_DIR = Path("organized_sources")

def normalize_type(type_str: str) -> str:
    """Normalize the type string to a consistent format."""
    if not type_str:
        return "other"
    
    type_lower = type_str.lower()
    
    # Handle compound types like "shows/movies/anime"
    types_found = []
    
    if "anime" in type_lower:
        types_found.append("anime")
    if "manga" in type_lower:
        types_found.append("manga")
    if "novel" in type_lower:
        types_found.append("novels")
    if "movie" in type_lower or "show" in type_lower:
        # Only add movies_shows if anime wasn't already found
        if "anime" not in types_found:
            types_found.append("movies_shows")
    
    # If we found specific types, return the first one (prioritize anime > manga > novels)
    if types_found:
        return types_found[0]
    
    # Otherwise, sanitize and return as-is
    return type_lower.replace("/", "_").replace(" ", "_").replace("-", "_")

def find_json_files(directory: Path) -> List[Path]:
    """Recursively find all JSON files in a directory."""
    json_files = []
    
    if not directory.exists():
        print(f"Warning: Directory {directory} does not exist")
        return json_files
    
    for item in directory.rglob("*.json"):
        if item.is_file():
            # Skip hidden files and common non-source files
            if not any(part.startswith('.') for part in item.parts):
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

def organize_sources():
    """Main function to organize source files."""
    print("=" * 60)
    print("Starting Source Organization")
    print("=" * 60)
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Structure: {repo_name: {type: [sources]}}
    organized_data = defaultdict(lambda: defaultdict(list))
    
    # Statistics
    total_files_found = 0
    total_files_processed = 0
    total_files_failed = 0
    
    for repo_name, repo_path in SOURCE_REPOS.items():
        print(f"\n{'='*60}")
        print(f"Processing repository: {repo_name}")
        print(f"Path: {repo_path}")
        print(f"{'='*60}")
        
        repo_dir = Path(repo_path)
        
        if not repo_dir.exists():
            print(f"❌ Repository path not found: {repo_path}")
            continue
        
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
        "repositories": {}
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
    
    for repo_name, types_dict in organized_data.items():
        total = sum(len(sources) for sources in types_dict.values())
        print(f"  • {repo_name}: {total} sources across {len(types_dict)} types")

if __name__ == "__main__":
    organize_sources()
