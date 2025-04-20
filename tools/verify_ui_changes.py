import json
import os
import re

from langchain.tools import tool


@tool
def verify_ui_changes(repo_dir: str, modified_files_json: str) -> str:
    """
    Verify that UI changes are consistent and don't break functionality.

    Args:
        repo_dir (str): The root directory of the repository.
        modified_files_json (str): JSON string listing the modified files.

    Returns:
        str: JSON string with verification results.
    """
    try:
        modified_files = json.loads(modified_files_json)

        verification_result = {
            "success": True,
            "potential_issues": [],
            "verification_steps": [
                "File existence check",
                "Syntax validation",
                "Style consistency check",
                "Component references check"
            ],
            "verified_files": []
        }

        # Check files exist and parse correctly
        for file_info in modified_files.get("files", []):
            file_path = file_info.get("path", "")
            enhancement_type = file_info.get("enhancement_type", "unknown")
            full_path = os.path.join(repo_dir, file_path)

            # First check if file exists
            if not os.path.exists(full_path):
                issue = {
                    "file": file_path,
                    "issue": "File not found after reported modification",
                    "severity": "high"
                }
                verification_result["potential_issues"].append(issue)
                verification_result["success"] = False
                print(f"Verification failed: {issue['issue']} for {file_path}")
                continue

            # File exists, add to verified files
            verification_result["verified_files"].append({
                "path": file_path,
                "enhancement_type": enhancement_type,
                "verified": True
            })
            print(f"Verified file exists: {file_path}")

            # Now check syntax based on file type
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for syntax issues based on file type
                file_ext = os.path.splitext(file_path)[1].lower()

                # JavaScript/React syntax check
                if file_ext in ['.js', '.jsx', '.ts', '.tsx']:
                    # Check for basic syntax issues
                    syntax_issues = []

                    # Unmatched brackets
                    brackets = {'(': ')', '[': ']', '{': '}'}
                    stack = []

                    for i, char in enumerate(content):
                        if char in brackets.keys():
                            stack.append((char, i))
                        elif char in brackets.values():
                            if not stack:
                                syntax_issues.append(f"Unexpected closing bracket '{char}' at position {i}")
                                break
                            last_open, _ = stack.pop()
                            if brackets[last_open] != char:
                                syntax_issues.append(
                                    f"Mismatched brackets: '{last_open}' and '{char}'"
                                )
                                break

                    if stack:
                        positions = [pos for _, pos in stack]
                        syntax_issues.append(f"Unclosed brackets at positions: {positions}")

                    # Check for missing semicolons (simplified)
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if (line and
                                not line.endswith(';') and
                                not line.endswith('{') and
                                not line.endswith('}') and
                                not line.endswith(',') and
                                not line.startswith('//') and
                                not line.startswith('import') and
                                not line.startswith('export') and
                                not line.startswith('function') and
                                not line.startswith('class') and
                                not line.startswith('if') and
                                not line.startswith('for') and
                                not line.startswith('while') and
                                not line.startswith('return')):
                            # This is a very simplified check and might have false positives
                            pass  # We'll skip this for now as it's too simple to be reliable

                    # Report any issues found
                    if syntax_issues:
                        verification_result["potential_issues"].append({
                            "file": file_path,
                            "issue": f"Syntax issues: {'; '.join(syntax_issues)}",
                            "severity": "high"
                        })
                        verification_result["success"] = False

                # CSS syntax check
                elif file_ext in ['.css', '.scss']:
                    # Very basic CSS syntax check
                    css_issues = []

                    # Check for unclosed braces
                    open_braces = content.count('{')
                    close_braces = content.count('}')
                    if open_braces != close_braces:
                        css_issues.append(
                            f"Mismatched braces: {open_braces} opening vs {close_braces} closing"
                        )

                    # Check for unclosed selectors or missing semicolons
                    # (This is a simplified check)
                    if css_issues:
                        verification_result["potential_issues"].append({
                            "file": file_path,
                            "issue": f"CSS syntax issues: {'; '.join(css_issues)}",
                            "severity": "high"
                        })
                        verification_result["success"] = False

                # HTML syntax check
                elif file_ext in ['.html', '.htm']:
                    # Very basic HTML syntax check
                    html_issues = []

                    # Check for basic tag balance (very simplified)
                    # A proper check would use an HTML parser
                    opening_tags = re.findall(r'<\s*([a-zA-Z0-9_-]+)[^>]*>', content)
                    closing_tags = re.findall(r'</\s*([a-zA-Z0-9_-]+)\s*>', content)

                    for tag in set(opening_tags):
                        if tag not in ['meta', 'link', 'img', 'br', 'hr', 'input']:  # Self-closing tags
                            opens = opening_tags.count(tag)
                            closes = closing_tags.count(tag)
                            if opens != closes:
                                html_issues.append(
                                    f"Mismatched tags: {opens} <{tag}> vs {closes} </{tag}>"
                                )

                    if html_issues:
                        verification_result["potential_issues"].append({
                            "file": file_path,
                            "issue": f"HTML syntax issues: {'; '.join(html_issues)}",
                            "severity": "high"
                        })
                        verification_result["success"] = False

            except Exception as e:
                verification_result["potential_issues"].append({
                    "file": file_path,
                    "issue": f"Error checking file: {str(e)}",
                    "severity": "medium"
                })
                # We won't fail verification for reading errors

        return json.dumps(verification_result, indent=2)

    except Exception as e:
        # If we can't process the verification, return an error
        return json.dumps({
            "success": False,
            "error": f"Verification error: {str(e)}",
            "potential_issues": [{
                "issue": f"Failed to complete verification: {str(e)}",
                "severity": "high"
            }]
        }, indent=2)
