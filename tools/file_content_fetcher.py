import os

from langchain.tools import tool


@tool
def get_file_content(repo_dir: str, relative_path: str) -> str:
    """Fetch the content of a file within the repository.

    Args:
        repo_dir (str): The root directory of the repository.
        relative_path (str): The path to the file relative to repo_dir.

    Returns:
        str: The file content or an error message.
    """
    full_path = os.path.join(repo_dir, relative_path)
    if not full_path.startswith(repo_dir):
        return "Error: Attempt to access file outside the repository."
    try:
        with open(full_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except Exception as e:
        return f"Error reading file {relative_path}: {e}"
