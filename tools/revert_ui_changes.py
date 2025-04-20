import json
import os
import shutil
from typing import List

from langchain.tools import tool


@tool
def revert_ui_changes(repo_dir: str, files_to_revert: List[str]) -> str:
    """
    Revert UI changes for specified files by restoring from backups.

    Args:
        repo_dir (str): The root directory of the repository.
        files_to_revert (List[str]): List of file paths to revert.

    Returns:
        str: JSON string with revert results.
    """
    results = {
        "successful_reverts": [],
        "failed_reverts": []
    }

    for file_path in files_to_revert:
        full_path = os.path.join(repo_dir, file_path)
        backup_path = f"{full_path}.bak"

        if os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, full_path)
                os.remove(backup_path)
                results["successful_reverts"].append(file_path)
            except Exception as e:
                results["failed_reverts"].append({
                    "file": file_path,
                    "error": str(e)
                })
        else:
            results["failed_reverts"].append({
                "file": file_path,
                "error": "Backup file not found"
            })

    return json.dumps(results)
