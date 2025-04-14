import subprocess

from langchain.tools import tool


@tool
def git_clone(repo_url: str, target_dir: str) -> str:
    """Clone a Git repository to a local directory.

    Args:
        repo_url (str): The URL of the Git repository to clone.
        target_dir (str): The local directory where the repo will be cloned.

    Returns:
        str: A message indicating success or failure.
    """
    try:
        subprocess.run(["git", "clone", repo_url, target_dir], check=True)
        return f"Successfully cloned {repo_url} to {target_dir}"
    except subprocess.CalledProcessError as e:
        return f"Failed to clone {repo_url}: {e}"
