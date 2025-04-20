import json
import os

from langchain.tools import tool


@tool
def scan_for_ui_files(repo_dir: str) -> str:
    """
    Scan a repository to identify all UI-related files of any type.

    Args:
        repo_dir (str): The root directory of the repository.

    Returns:
        str: JSON string containing identified UI files categorized by type.
    """
    if not os.path.exists(repo_dir):
        return json.dumps({"error": f"Repository directory {repo_dir} does not exist"})

    # File extensions to scan for
    ui_extensions = {
        'markup': ['.html', '.jsx', '.tsx', '.vue', '.svelte', '.astro', '.ejs'],
        'style': ['.css', '.scss', '.sass', '.less', '.styled.js', '.style.js'],
        'script': ['.js', '.ts', '.mjs', '.cjs'],
        'animation': ['.js', '.ts', '.css', '.scss'],
        'asset': ['.svg', '.jpg', '.png', '.webp']
    }

    # Collect all files in the repository first
    all_files = []
    for root, _, files in os.walk(repo_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, repo_dir)
            file_ext = os.path.splitext(file)[1].lower()

            all_files.append({
                "path": rel_path,
                "extension": file_ext,
                "size": os.path.getsize(full_path)
            })

    # Debug output of repository structure
    print(f"\nRepository structure ({len(all_files)} total files):")
    dirs_seen = set()
    for file_info in sorted(all_files, key=lambda x: x["path"]):
        dir_path = os.path.dirname(file_info["path"])
        if dir_path and dir_path not in dirs_seen:
            print(f"  Directory: {dir_path}/")
            dirs_seen.add(dir_path)
        print(f"    {file_info['path']} ({file_info['size']} bytes)")

    # Keywords that indicate different UI aspects
    ui_keywords = {
        'theme': ['theme', 'color', 'palette', 'dark', 'light', 'style', 'brand'],
        'animation': ['animation', 'transition', 'motion', 'gsap', 'animate', 'keyframe'],
        'layout': ['layout', 'grid', 'flex', 'container', 'responsive', 'mobile'],
        'component': ['component', 'button', 'input', 'form', 'card', 'modal', 'dialog'],
        'navigation': ['nav', 'menu', 'link', 'route', 'path', 'drawer', 'sidebar'],
        'performance': ['performance', 'loading', 'lazy', 'optimize', 'cache']
    }

    # Results categorized by UI aspect
    ui_files = {
        'theme': [],
        'animation': [],
        'layout': [],
        'component': [],
        'navigation': [],
        'performance': [],
        'other': []
    }

    # Filter for UI-related files
    for file_info in all_files:
        path = file_info["path"]
        extension = file_info["extension"]
        size = file_info["size"]

        # Skip very large files or files that are likely not UI-related
        if size > 1000000 or size == 0:
            continue

        full_path = os.path.join(repo_dir, path)

        # Determine file category based on extension
        file_category = None
        for category, extensions in ui_extensions.items():
            if extension in extensions:
                file_category = category
                break

        # Skip if not a UI-related file extension
        if not file_category:
            continue

        # Try to read and analyze file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Determine UI aspect based on file content and path
            aspect_match = None
            max_matches = 0

            for aspect, keywords in ui_keywords.items():
                # Count matches in path and content
                path_matches = sum(1 for kw in keywords if kw.lower() in path.lower())
                content_matches = sum(1 for kw in keywords if kw.lower() in content.lower())
                total_matches = path_matches * 3 + content_matches  # Path matches weighted higher

                if total_matches > max_matches:
                    max_matches = total_matches
                    aspect_match = aspect

            # Add to the appropriate category
            file_entry = {
                "path": path,
                "extension": extension,
                "category": file_category,
                "size": size
            }

            if aspect_match and max_matches > 0:
                file_entry["aspect"] = aspect_match
                ui_files[aspect_match].append(file_entry)
            else:
                file_entry["aspect"] = "other"
                ui_files["other"].append(file_entry)

        except Exception as e:
            print(f"Error reading {path}: {e}")
            # Skip files we can't read

    # Sort each category by path
    for category in ui_files:
        ui_files[category].sort(key=lambda x: x["path"])

    # Compile summary statistics
    summary = {
        "total_files": sum(len(files) for files in ui_files.values()),
        "files_by_aspect": {aspect: len(files) for aspect, files in ui_files.items()},
        "files_by_extension": {},
        "repository_structure": {
            "total_files": len(all_files),
            "directories": sorted(list(dirs_seen))
        }
    }

    # Count files by extension
    all_ui_files = [file for files in ui_files.values() for file in files]
    for file in all_ui_files:
        ext = file["extension"]
        summary["files_by_extension"][ext] = summary["files_by_extension"].get(ext, 0) + 1

    return json.dumps({
        "ui_files": ui_files,
        "summary": summary
    }, indent=2)
