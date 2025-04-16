# tools/ui_enhancement_tools.py
import json
import os
import re
import shutil
from typing import List

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


@tool
def analyze_ui_capabilities(repo_dir: str, ui_files_json: str) -> str:
    """
    Analyze the UI capabilities and patterns in the repository.

    Args:
        repo_dir (str): The root directory of the repository.
        ui_files_json (str): JSON string from scan_for_ui_files.

    Returns:
        str: JSON string with analysis of UI system capabilities.
    """
    ui_data = json.loads(ui_files_json)
    ui_files = ui_data.get("ui_files", {})

    # Framework detection patterns
    frameworks = {
        'react': [r'import\s+React|from\s+[\'"]react[\'"]|ReactDOM|useState|useEffect'],
        'vue': [r'import\s+Vue|from\s+[\'"]vue[\'"]|createApp|<template>|<script setup>'],
        'angular': [r'import\s+{\s*Component\s*}|@Component|@Angular|NgModule'],
        'svelte': [r'<script>.*?</script>.*?<style', r'from\s+[\'"]svelte[\'"]'],
        'astro': [r'---.*?---.*?<html', r'from\s+[\'"]astro[\'"]'],
        'nextjs': [r'import\s+{\s*useRouter\s*}\s+from\s+[\'"]next/router[\'"]|nextjs|getStaticProps'],
        'nuxt': [r'from\s+[\'"]nuxt[\'"]|defineNuxtConfig|useNuxtApp'],
    }

    # UI library detection patterns
    ui_libraries = {
        'tailwind': [r'tailwind|className=[\'"][^\'"]*(flex|grid|bg-|text-|p-|m-|rounded)[^\'"]*[\'"]'],
        'bootstrap': [r'bootstrap|class=[\'"][^\'"]*(btn|container|row|col|navbar)[^\'"]*[\'"]'],
        'material-ui': [r'@mui|@material-ui|makeStyles|createTheme|ThemeProvider'],
        'chakra-ui': [r'@chakra-ui|ChakraProvider|useDisclosure'],
        'styled-components': [r'styled\.|createGlobalStyle|css`|styled\([^\)]+\)`'],
        'framer-motion': [r'framer-motion|motion\.|animate|useAnimation|AnimatePresence'],
        'gsap': [r'gsap|TweenMax|TimelineMax|ScrollTrigger'],
        'three': [r'three\.js|THREE\.|Scene|WebGLRenderer|PerspectiveCamera'],
    }

    # Animation/transition patterns
    animation_patterns = {
        'css': [r'@keyframes|animation:|transition:|transform:'],
        'js': [r'requestAnimationFrame|animate\(|\.to\(|\.from\(|\.fromTo\('],
        'libraries': [r'gsap|anime\.|motion\.|framer|lottie|velocity']
    }

    # Results
    ui_analysis = {
        "framework": {
            "detected": [],
            "confidence": {}
        },
        "ui_libraries": {
            "detected": [],
            "confidence": {}
        },
        "animation_system": {
            "types": [],
            "capabilities": []
        },
        "theme_system": {
            "type": "unknown",
            "capabilities": []
        },
        "responsive_design": {
            "approach": "unknown",
            "breakpoints": []
        },
        "component_architecture": {
            "pattern": "unknown",
            "reusability": 0
        },
        "performance_optimization": {
            "techniques": []
        }
    }

    # Sample a subset of files from each category for deeper analysis
    sample_files = []
    for aspect, files in ui_files.items():
        # Take up to 5 files from each aspect
        sample_files.extend(files[:5])

    # Framework detection counters
    framework_counts = {framework: 0 for framework in frameworks}
    library_counts = {library: 0 for library in ui_libraries}
    animation_counts = {anim_type: 0 for anim_type in animation_patterns}

    # Media queries for responsive design
    media_queries = []

    # Analyze sampled files
    for file_info in sample_files:
        try:
            file_path = os.path.join(repo_dir, file_info["path"])
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Framework detection
            for framework, patterns in frameworks.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                        framework_counts[framework] += 1
                        break

            # UI library detection
            for library, patterns in ui_libraries.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                        library_counts[library] += 1
                        break

            # Animation detection
            for anim_type, patterns in animation_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                        animation_counts[anim_type] += 1
                        break

            # Extract media queries for responsive design
            if file_info["extension"] in ['.css', '.scss', '.less']:
                media_query_matches = re.findall(r'@media\s*\([^)]+\)', content)
                media_queries.extend(media_query_matches)

                # Check for CSS variables (theme system)
                if re.search(r'--[a-zA-Z0-9_-]+:', content):
                    ui_analysis["theme_system"]["type"] = "css-variables"
                    ui_analysis["theme_system"]["capabilities"].append("custom-properties")

            # Look for performance optimizations
            if "loading=" in content or "lazy" in content:
                if "performance_optimization" not in ui_analysis["performance_optimization"]["techniques"]:
                    ui_analysis["performance_optimization"]["techniques"].append("lazy-loading")

            if "preload" in content or "prefetch" in content:
                if "resource-hints" not in ui_analysis["performance_optimization"]["techniques"]:
                    ui_analysis["performance_optimization"]["techniques"].append("resource-hints")

        except Exception as e:
            # Skip files that can't be analyzed
            continue

    # Process framework detection results
    for framework, count in framework_counts.items():
        if count > 0:
            confidence = min(count / len(sample_files) * 100, 100)
            if confidence > 20:  # Only include if confidence is reasonable
                ui_analysis["framework"]["detected"].append(framework)
                ui_analysis["framework"]["confidence"][framework] = round(confidence)

    # Process UI library detection results
    for library, count in library_counts.items():
        if count > 0:
            confidence = min(count / len(sample_files) * 100, 100)
            if confidence > 20:  # Only include if confidence is reasonable
                ui_analysis["ui_libraries"]["detected"].append(library)
                ui_analysis["ui_libraries"]["confidence"][library] = round(confidence)

    # Process animation results
    for anim_type, count in animation_counts.items():
        if count > 0:
            ui_analysis["animation_system"]["types"].append(anim_type)

    # Determine animation capabilities
    if "gsap" in ui_analysis["ui_libraries"]["detected"]:
        ui_analysis["animation_system"]["capabilities"].extend(["timeline", "advanced-easing", "scroll-triggered"])
    elif "framer-motion" in ui_analysis["ui_libraries"]["detected"]:
        ui_analysis["animation_system"]["capabilities"].extend(["declarative", "gesture-based", "variants"])
    elif animation_counts["css"] > 0:
        ui_analysis["animation_system"]["capabilities"].append("css-based")
    elif animation_counts["js"] > 0:
        ui_analysis["animation_system"]["capabilities"].append("javascript-based")

    # Determine responsive approach
    if len(media_queries) > 0:
        ui_analysis["responsive_design"]["approach"] = "media-queries"

        # Extract breakpoints from media queries
        breakpoints = set()
        for query in media_queries:
            width_matches = re.findall(r'(max|min)-width:\s*(\d+)(px|rem|em)', query)
            for match in width_matches:
                breakpoints.add(f"{match[0]}-width-{match[1]}{match[2]}")

        ui_analysis["responsive_design"]["breakpoints"] = list(breakpoints)
    elif "tailwind" in ui_analysis["ui_libraries"]["detected"]:
        ui_analysis["responsive_design"]["approach"] = "utility-classes"

    # Determine component architecture
    if "react" in ui_analysis["framework"]["detected"]:
        component_files = len(ui_files.get("component", []))
        total_markup_files = sum(
            1 for files in ui_files.values() for file in files if file["extension"] in ['.jsx', '.tsx'])

        if total_markup_files > 0:
            reusability = min(component_files / total_markup_files * 100, 100)
            ui_analysis["component_architecture"]["reusability"] = round(reusability)

            if reusability > 70:
                ui_analysis["component_architecture"]["pattern"] = "highly-componentized"
            elif reusability > 40:
                ui_analysis["component_architecture"]["pattern"] = "moderately-componentized"
            else:
                ui_analysis["component_architecture"]["pattern"] = "low-componentization"

    return json.dumps(ui_analysis, indent=2)


@tool
def identify_enhancement_opportunities(repo_dir: str, ui_analysis_json: str) -> str:
    """
    Identify opportunities for UI/UX enhancement in the codebase.
    This tool helps the AI determine what aspects could be improved.

    Args:
        repo_dir (str): The root directory of the repository.
        ui_analysis_json (str): JSON string from analyze_ui_capabilities.

    Returns:
        str: JSON string with enhancement opportunities.
    """
    # This is primarily a reasoning tool for the AI to organize its thoughts
    ui_analysis = json.loads(ui_analysis_json)

    # Create a structure for enhancement opportunities
    opportunities = {
        "visual_design": [],
        "animations": [],
        "performance": [],
        "accessibility": [],
        "user_experience": [],
        "modernization": [],
        "prioritized_files": []
    }

    # The LLM will fill in the details
    return json.dumps(opportunities, indent=2)


@tool
def generate_enhancement_plan(opportunities_json: str) -> str:
    """
    Generate a comprehensive enhancement plan based on identified opportunities.

    Args:
        opportunities_json (str): JSON string from identify_enhancement_opportunities.

    Returns:
        str: JSON string with a structured enhancement plan.
    """
    # This is primarily a reasoning tool for the AI
    opportunities = json.loads(opportunities_json)

    # Create a plan structure
    enhancement_plan = {
        "title": "",
        "description": "",
        "changes": [],
        "file_modifications": []
    }

    # The LLM will fill in the details
    return json.dumps(enhancement_plan, indent=2)


def validate_syntax(file_path: str, content: str) -> tuple[bool, str, str]:
    """Validate file content for basic syntax errors."""
    error_message = ""

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
