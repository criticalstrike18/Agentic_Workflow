import json
import os
import re

from langchain.tools import tool


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
            print(e)
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
