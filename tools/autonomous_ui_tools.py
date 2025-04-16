# tools/autonomous_ui_tools.py
import json
import os
import shutil

from langchain.tools import tool


@tool
def scan_codebase_for_ui_components(repo_dir: str) -> str:
    """
    Scan a repository to identify UI components that could be enhanced.

    Args:
        repo_dir (str): The root directory of the repository.

    Returns:
        str: JSON string containing identified UI component files and their paths.
    """
    if not os.path.exists(repo_dir):
        return json.dumps({"error": f"Repository directory {repo_dir} does not exist"})

    ui_extensions = ['.jsx', '.tsx', '.js', '.tsx', '.vue', '.svelte']
    ui_directories = ['components', 'pages', 'views', 'ui', 'src']
    ui_files = []

    for root, dirs, files in os.walk(repo_dir):
        # Prioritize important UI directories
        if any(ui_dir in root.lower() for ui_dir in ui_directories):
            for file in files:
                # Check if file has UI extension
                if any(file.endswith(ext) for ext in ui_extensions):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, repo_dir)

                    # Read file content to check if it contains UI elements
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Simple heuristic: check for UI-related keywords
                            ui_keywords = ['render', 'component', 'className', 'style', 'div', 'button', 'input']
                            has_ui = any(keyword in content for keyword in ui_keywords)

                            if has_ui:
                                ui_files.append({
                                    "path": relative_path,
                                    "size": len(content),
                                    "type": os.path.splitext(file)[1][1:]  # Extension without dot
                                })
                    except Exception as e:
                        print(f"Error reading {relative_path}: {e}")

    # Sort by file type and then by path
    ui_files.sort(key=lambda x: (x["type"], x["path"]))

    return json.dumps({
        "ui_components": ui_files,
        "total_count": len(ui_files)
    }, indent=2)


@tool
def analyze_ui_component(repo_dir: str, file_path: str) -> str:
    """
    Perform deep analysis of a UI component to understand its structure, styling, and purpose.

    Args:
        repo_dir (str): The root directory of the repository.
        file_path (str): Path to the component file relative to repo_dir.

    Returns:
        str: JSON string containing detailed analysis of the component.
    """
    full_path = os.path.join(repo_dir, file_path)
    if not os.path.exists(full_path):
        return json.dumps({"error": f"File {file_path} does not exist"})

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get file extension
        ext = os.path.splitext(file_path)[1].lower()

        # Detect framework (React, Vue, etc.)
        framework = "Unknown"
        if ext in ['.jsx', '.tsx']:
            framework = "React"
        elif ext == '.vue':
            framework = "Vue"
        elif ext == '.svelte':
            framework = "Svelte"
        elif 'React' in content or 'react' in content:
            framework = "React"
        elif 'Vue' in content:
            framework = "Vue"
        elif 'angular' in content.lower():
            framework = "Angular"

        # Detect styling approach
        styling_approach = []
        if 'className' in content:
            styling_approach.append("CSS Classes")
        if 'style=' in content:
            styling_approach.append("Inline Styles")
        if 'styled' in content:
            styling_approach.append("Styled Components")
        if 'import' in content and '.css' in content:
            styling_approach.append("CSS Imports")
        if 'tailwind' in content.lower() or 'tw-' in content:
            styling_approach.append("Tailwind CSS")

        # Check for color usage
        colors = []
        color_patterns = [
            r'#[0-9a-fA-F]{3,6}',  # Hex colors
            r'rgba?\([^)]+\)',  # RGB/RGBA colors
            r'hsla?\([^)]+\)'  # HSL/HSLA colors
        ]

        # Add color names that might be in variables
        color_names = ['white', 'black', 'gray', 'red', 'blue', 'green', 'yellow',
                       'purple', 'pink', 'indigo', 'teal', 'orange', 'brown']

        # Extract the content of the file
        extracted_content = content

        # Return analysis results
        return json.dumps({
            "file_path": file_path,
            "framework": framework,
            "styling_approaches": styling_approach,
            "component_size": len(content),
            "ui_elements": {
                "has_buttons": "button" in content.lower(),
                "has_forms": "form" in content.lower() or "input" in content.lower(),
                "has_navigation": "nav" in content.lower() or "menu" in content.lower(),
                "has_layout_components": any(x in content.lower() for x in ["grid", "flex", "layout", "container"]),
            },
            "content_sample": content[:500] + ("..." if len(content) > 500 else ""),
            "full_content": content  # Include full content for AI analysis
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Error analyzing {file_path}: {str(e)}"})


@tool
def regenerate_ui_component(repo_dir: str, file_path: str, new_content: str, backup: bool = True) -> str:
    """
    Completely regenerate a UI component file with enhanced content.

    Args:
        repo_dir (str): The root directory of the repository.
        file_path (str): Path to the component file relative to repo_dir.
        new_content (str): The new content to write to the file.
        backup (bool): Whether to create a backup of the original file.

    Returns:
        str: Result of the regeneration operation.
    """
    full_path = os.path.join(repo_dir, file_path)

    if not os.path.exists(full_path):
        return json.dumps({"error": f"File {file_path} does not exist"})

    try:
        # Create backup if requested
        if backup:
            backup_path = f"{full_path}.bak"
            shutil.copy2(full_path, backup_path)

        # Write new content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        result = {
            "success": True,
            "file_path": file_path,
            "message": f"Successfully regenerated {file_path}",
            "backup_created": backup
        }

        if backup:
            result["backup_path"] = f"{file_path}.bak"

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error regenerating {file_path}: {str(e)}"
        })


@tool
def revert_ui_changes(repo_dir: str, file_path: str) -> str:
    """
    Revert changes to a UI component by restoring from backup.

    Args:
        repo_dir (str): The root directory of the repository.
        file_path (str): Path to the component file relative to repo_dir.

    Returns:
        str: Result of the revert operation.
    """
    full_path = os.path.join(repo_dir, file_path)
    backup_path = f"{full_path}.bak"

    if not os.path.exists(backup_path):
        return json.dumps({
            "success": False,
            "error": f"No backup found for {file_path}"
        })

    try:
        shutil.copy2(backup_path, full_path)
        os.remove(backup_path)

        return json.dumps({
            "success": True,
            "message": f"Successfully reverted changes to {file_path}"
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error reverting {file_path}: {str(e)}"
        })


@tool
def determine_optimal_ui_changes(ui_analysis: str) -> str:
    """
    Determine optimal UI improvements based on analysis. This is a reasoning tool
    that doesn't actually perform filesystem operations but rather helps the AI
    decide what changes would be best.

    Args:
        ui_analysis (str): JSON string containing UI component analysis.

    Returns:
        str: JSON string containing suggested UI improvements.
    """
    # This function is mainly a placeholder for the AI to use its reasoning
    # capabilities. The actual reasoning happens in the LLM, not in this function.

    try:
        analysis = json.loads(ui_analysis)

        # This is just a simple framework to help the AI organize its thoughts
        improvements = {
            "visual_enhancements": [],
            "structural_improvements": [],
            "recommended_changes": {},
            "justification": ""
        }

        # The LLM will actually fill in the details based on its analysis
        return json.dumps(improvements, indent=2)

    except Exception as e:
        return json.dumps({
            "error": f"Error processing UI analysis: {str(e)}"
        })
