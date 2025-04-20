import json
import os
import shutil

from langchain.tools import tool


@tool
def introduce_new_ui_feature(repo_dir: str, feature_spec: str, target_directory: str) -> str:
    """
    Introduce a completely new UI feature by creating new files.

    Args:
        repo_dir (str): The root directory of the repository.
        feature_spec (str): JSON specification of the new feature.
        target_directory (str): Directory where the feature should be created.

    Returns:
        str: JSON string with result of the feature creation.
    """
    target_path = os.path.join(repo_dir, target_directory)

    # Ensure target directory exists
    try:
        os.makedirs(target_path, exist_ok=True)
    except Exception as e:
        return json.dumps({"error": f"Failed to create target directory: {str(e)}"})

    try:
        # Parse feature specification
        feature = json.loads(feature_spec)
        created_files = []

        # For each file in the feature spec, create it
        for file_spec in feature.get("files", []):
            file_name = file_spec.get("name", "")
            file_content = file_spec.get("content", "")
            file_path = os.path.join(target_path, file_name)

            # Check if file already exists
            if os.path.exists(file_path):
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)

            # Write the new file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)

            created_files.append({
                "path": os.path.join(target_directory, file_name),
                "type": os.path.splitext(file_name)[1][1:]
            })

        return json.dumps({
            "success": True,
            "feature_name": feature.get("name", "New Feature"),
            "created_files": created_files,
            "target_directory": target_directory
        })
    except Exception as e:
        return json.dumps({
            "error": f"Error creating new feature: {str(e)}"
        })
