import json
import os
import shutil

from langchain.tools import tool


def validate_syntax(file_path: str, content: str) -> tuple[bool, str, str]:
    """Validate file content for basic syntax errors."""
    # error_message = ""

    # Check for balanced brackets
    brackets = {'(': ')', '[': ']', '{': '}'}
    stack = []
    line_num = 1
    col_num = 1

    for i, char in enumerate(content):
        if char == '\n':
            line_num += 1
            col_num = 1
        else:
            col_num += 1

        if char in brackets.keys():
            stack.append((char, line_num, col_num))
        elif char in brackets.values():
            if not stack:
                error_message = f"Syntax error: Unexpected closing bracket '{char}' at line {line_num}, column {col_num}"
                return False, content, error_message

            last_open, _, _ = stack.pop()
            if brackets[last_open] != char:
                error_message = f"Syntax error: Mismatched brackets at line {line_num}, column {col_num}"
                return False, content, error_message

    if stack:
        last_open, err_line, err_col = stack[-1]
        error_message = f"Syntax error: Unclosed bracket '{last_open}' at line {err_line}, column {err_col}"
        return False, content, error_message

    # Additional file-specific checks
    if file_path.endswith('.js') or file_path.endswith('.jsx'):
        # Check for missing parentheses in if statements (common issue)
        import re
        if_stmt_pattern = r'if\s*\([^)]*\s*\{'
        if_stmts = re.findall(if_stmt_pattern, content)
        for if_stmt in if_stmts:
            if '(' in if_stmt and ')' not in if_stmt:
                # Attempt to fix
                fixed = content.replace(if_stmt, if_stmt.replace('{', ') {'))
                error_message = "Fixed missing parenthesis in if statement"
                return False, fixed, error_message

    # Astro-specific checks
    if file_path.endswith('.astro'):
        # Check for client directives
        if "client:" in content and any(directive in content for directive in
                                        ["client:load", "client:visible", "client:only",
                                         "client:media", "client:idle"]):
            # Remove the problematic directives
            import re
            fixed_content = re.sub(r'client:(load|visible|only|media|idle)="[^"]*"', '', content)
            fixed_content = re.sub(r'client:(load|visible|only|media|idle)', '', fixed_content)
            error_message = "Removed invalid Astro client directives"
            return False, fixed_content, error_message

    return True, content, ""


def validate_astro_file(content: str) -> tuple[bool, str]:
    """Validate Astro file content before applying changes."""
    # Check for invalid client directives
    if "client:" in content and any(directive in content for directive in
                                    ["client:load", "client:visible", "client:only",
                                     "client:media", "client:idle"]):
        # Remove the problematic directives
        import re
        fixed_content = re.sub(r'client:(load|visible|only|media|idle)="[^"]*"', '', content)
        fixed_content = re.sub(r'client:(load|visible|only|media|idle)', '', fixed_content)
        return False, fixed_content

    return True, content


@tool
def modify_ui_file(repo_dir: str, file_path: str, enhancement_type: str, enhanced_content: str = None) -> str:
    """
    Modify a UI file to implement a specific enhancement.
    """
    full_path = os.path.join(repo_dir, file_path)
    if not os.path.exists(full_path):
        print(f"ERROR: File does not exist: {full_path}")
        return json.dumps({"success": False, "error": f"File {file_path} does not exist"})

    # Create backup of original file
    backup_path = f"{full_path}.bak"
    try:
        print(f"Creating backup: {backup_path}")
        shutil.copy2(full_path, backup_path)
    except Exception as e:
        print(f"ERROR: Failed to create backup: {str(e)}")
        return json.dumps({"success": False, "error": f"Failed to create backup: {str(e)}"})

    try:
        # Read the file content
        with open(full_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
            print(f"Successfully read original content ({len(original_content)} bytes)")

        # Determine what content to use - FIXED LOGIC HERE
        if enhanced_content is None or enhanced_content == "":
            print("WARNING: No enhanced content provided, using original content")
            transformed_content = original_content
        else:
            print(f"Using provided enhanced content ({len(enhanced_content)} bytes)")
            transformed_content = enhanced_content

            # DEBUG: Print a sample to verify content is different
            if original_content == transformed_content:
                print("WARNING: Enhanced content is identical to original content!")
            else:
                print(f"PREVIEW - Original starts with: {original_content[:50]}...")
                print(f"PREVIEW - Enhanced starts with: {transformed_content[:50]}...")

        # Special handling for Astro files to fix client directives
        if file_path.endswith(".astro"):
            is_valid, transformed_content = validate_astro_file(transformed_content)
            if not is_valid:
                print("WARNING: Fixed invalid Astro client directives")

        # Validate syntax and fix issues
        is_valid, validated_content, error_msg = validate_syntax(file_path, transformed_content)
        if not is_valid:
            print(f"WARNING: {error_msg}")
            transformed_content = validated_content

            # If we still have errors after attempted fixes, revert to original
            is_valid_after_fix, _, _ = validate_syntax(file_path, transformed_content)
            if not is_valid_after_fix:
                print("ERROR: Cannot fix syntax issues automatically, reverting to original content")
                transformed_content = original_content

        # Write back the transformed content
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(transformed_content)
            print(f"Successfully wrote transformed content to {file_path}")

        return json.dumps({
            "success": True,
            "file_path": file_path,
            "enhancement_type": enhancement_type,
            "message": f"Successfully enhanced {file_path}",
            "backup_created": True,
            "backup_path": f"{file_path}.bak"
        })
    except Exception as e:
        error_msg = f"Error enhancing {file_path}: {str(e)}"
        print(f"ERROR: {error_msg}")

        # Restore from backup if there was an error
        try:
            print(f"Attempting to restore from backup")
            shutil.copy2(backup_path, full_path)
            print(f"Successfully restored from backup")
        except Exception as restore_error:
            print(f"ERROR: Failed to restore from backup: {str(restore_error)}")

        return json.dumps({"success": False, "error": error_msg})
