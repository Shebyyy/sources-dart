# Sources Organization by Type

This project automatically organizes source JSON files from multiple repositories by their type (anime, manga, novel, movies_shows).

## What it does

1. **Clones** multiple services repositories from `https://git.luna-app.eu/`
2. **Finds** all JSON files in all repositories
3. **Categorizes** each JSON file by its `type` field
4. **Creates organized output**:
   - Individual repository folders with JSON files grouped by type
   - Combined JSON files for each type across all repositories
   - Summary statistics

## Key Features

- **Multiple Repository Support**: Process repositories from different owners (50n50, ibro, etc.)
- **No Local Storage Needed**: Repositories are cloned temporarily during GitHub Action run
- **Automatic Type Detection**: Intelligently categorizes JSON files
- **Combined Output**: Merges all sources of the same type across repositories

## Current Repositories

- **ibro**: `https://git.luna-app.eu/ibro/services.git`
- **50n50**: `https://git.luna-app.eu/50n50/services.git`

## Output Structure

```
organized_sources/
├── ibro/                    # Individual repo organization
│   ├── anime.json          # All anime from ibro
│   ├── manga.json          # All manga from ibro  
│   ├── novels.json         # All novels from ibro
│   └── movies_shows.json   # All movies/shows from ibro
├── 50n50/                   # Individual repo organization
│   ├── anime.json          # All anime from 50n50
│   ├── manga.json          # All manga from 50n0
│   └── ...                 # Other types
├── combined/               # Combined across all repos
│   ├── anime.json          # All anime from all repos
│   ├── manga.json          # All manga from all repos
│   ├── novels.json         # All novels from all repos
│   └── movies_shows.json   # All movies/shows from all repos
└── summary.json            # Complete statistics
```

## Type Categories

- **anime**: Sources with "anime" in their type field
- **manga**: Sources with "manga" or "mangas" in their type field  
- **novel**: Sources with "novel" or "novels" in their type field
- **movies_shows**: Sources with "movie", "show", "tv", or "series" in their type field
- **other**: All other types

## GitHub Actions

The workflow runs automatically:
- **On push** to main/master branches
- **Daily** at 2 AM UTC
- **Manual dispatch** via GitHub Actions UI

### Workflow Steps

1. **Checkout** the repository
2. **Set up Python** environment
3. **Run organization script** - handles cloning, processing, and cleanup
4. **Upload** organized sources as artifacts
5. **Commit** changes back to repository (if run on push)

## Adding More Repositories

To add more repositories, update the `REPOSITORIES` dictionary in `organize_sources.py`:

```python
REPOSITORIES = {
    "ibro": "https://git.luna-app.eu/ibro/services.git",
    "50n50": "https://git.luna-app.eu/50n50/services.git",
    "new_user": "https://git.luna-app.eu/new_user/services.git"  # Add new repository
}
```

## JSON File Format

Each source JSON file should have at least:

```json
{
  "sourceName": "Source Name",
  "type": "anime|manga|novel|movies_shows|other",
  "url": "https://example.com",
  "description": "Source description"
}
```

## Local Development

To run locally:

```bash
# Clone this repository
git clone <this-repo-url>
cd sources-dart

# Run the organization script
python3 organize_sources.py
```

Note: Some repositories may require authentication and might not clone successfully in local environments.