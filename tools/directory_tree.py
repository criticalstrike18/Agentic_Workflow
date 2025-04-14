import os

from langchain.tools import tool


@tool
def get_directory_tree(root_dir: str) -> str:
    """Generate a directory tree starting from the specified root directory.

    Args:
        root_dir (str): The path to the root directory.

    Returns:
        str: A string representing the directory tree.
    """
    tree = ""
    for root, dirs, files in os.walk(root_dir):
        level = root.replace(root_dir, "").count(os.sep)
        indent = " " * 4 * level
        tree += f"{indent}{os.path.basename(root)}/\n"
        sub_indent = " " * 4 * (level + 1)
        for f in files:
            tree += f"{sub_indent}{f}\n"
    return tree
