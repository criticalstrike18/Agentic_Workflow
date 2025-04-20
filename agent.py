import json
import os
from enum import Enum
from typing import Dict, List, Any, Optional, TypedDict, cast

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# Import tools as t
import tools as t

# Load environment variables
load_dotenv()

deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
deepseek_api_base = os.getenv('DEEPSEEK_API_BASE')
model_name = os.getenv('DEEPSEEK_MODEL', "deepseek-reasoner")

if not deepseek_api_key:
    raise ValueError("DEEPSEEK_API_KEY must be set")
if not deepseek_api_base:
    raise ValueError("DEEPSEEK_API_BASE must be set")

# Create language model
llm = ChatOpenAI(
    openai_api_key=deepseek_api_key,
    openai_api_base=deepseek_api_base,
    model_name=model_name,
    temperature=0.4
)


# Define phases for the workflow
class Phase(str, Enum):
    CLONE_REPO = "clone_repo"
    SCAN_UI_FILES = "scan_ui_files"
    ANALYZE_UI = "analyze_ui"
    IDENTIFY_OPPORTUNITIES = "identify_opportunities"
    GENERATE_PLAN = "generate_plan"
    IMPLEMENT_ENHANCEMENTS = "implement_enhancements"
    VERIFY_CHANGES = "verify_changes"
    SUMMARIZE = "summarize"
    COMPLETE = "complete"


# Define a state type with total=False to make all fields optional
class State(TypedDict, total=False):
    phase: str
    enhancement_prompt: str
    repo_url: str
    repo_dir: str
    ui_files: Dict[str, Any]
    ui_analysis: Dict[str, Any]
    primary_focus: str
    design_approach: str
    enhancement_opportunities: Dict[str, Any]
    enhancement_plan: Dict[str, Any]
    files_to_enhance: List[Dict[str, Any]]
    current_file_index: int
    enhanced_files: List[Dict[str, Any]]
    verification_result: Dict[str, Any]
    summary: str
    error: Optional[str]
    log: List[str]


# Helper function to ensure all required state fields are present
def ensure_complete_state(state: State) -> State:
    # Default values for all required fields
    default_state: State = {
        "phase": Phase.CLONE_REPO,
        "enhancement_prompt": "",
        "repo_url": "",
        "repo_dir": "",
        "ui_files": {},
        "ui_analysis": {},
        "primary_focus": "",
        "design_approach": "",
        "enhancement_opportunities": {},
        "enhancement_plan": {},
        "files_to_enhance": [],
        "current_file_index": 0,
        "enhanced_files": [],
        "verification_result": {},
        "summary": "",
        "error": None,
        "log": []
    }

    # Merge the provided state with defaults
    complete_state = {**default_state, **state}
    return cast(State, complete_state)


# Define the node functions
def clone_repository(state: State) -> State:
    try:
        repo_url = state.get("repo_url", "")
        target_dir = os.getenv('TARGET_DIR', './enhanced_repo')
        if not os.path.isabs(target_dir):
            target_dir = os.path.abspath(target_dir)

        log_message = f"Cloning repository: {repo_url} to {target_dir}"
        print(log_message)

        result = t.git_clone.invoke({"repo_url": repo_url, "target_dir": target_dir})
        print(f"Clone result: {result}")

        new_log = state.get("log", []) + [log_message, f"Clone complete: {result}"]

        updated_state = {
            **state,
            "repo_dir": target_dir,
            "phase": Phase.SCAN_UI_FILES,
            "log": new_log
        }
        return ensure_complete_state(updated_state)
    except Exception as e:
        error_message = f"Error in clone_repository: {e}"
        print(error_message)
        updated_state = {
            **state,
            "error": str(e),
            "phase": Phase.COMPLETE,
            "log": state.get("log", []) + [error_message]
        }
        return ensure_complete_state(updated_state)


def scan_ui_files(state: State) -> State:
    try:
        repo_dir = state.get("repo_dir", "")
        log_message = f"Scanning for UI files in: {repo_dir}"
        print(log_message)

        # Get directory tree, but we don't need to use it directly
        t.get_directory_tree.invoke({"root_dir": repo_dir})  # Just invoke but don't store result
        scan_result = t.scan_for_ui_files.invoke({"repo_dir": repo_dir})
        ui_files = json.loads(scan_result)

        total_files = ui_files.get("summary", {}).get("total_files", 0)

        log_messages = [
            log_message,
            f"Found {total_files} UI-related files"
        ]

        for aspect, files in ui_files.get("ui_files", {}).items():
            log_messages.append(f"- {aspect}: {len(files)} files")

        print("\n".join(log_messages))

        updated_state = {
            **state,
            "ui_files": ui_files,
            "phase": Phase.ANALYZE_UI if total_files > 0 else Phase.COMPLETE,
            "log": state.get("log", []) + log_messages,
            "error": None if total_files > 0 else "No UI files found"
        }
        return ensure_complete_state(updated_state)
    except Exception as e:
        error_message = f"Error in scan_ui_files: {e}"
        print(error_message)
        updated_state = {
            **state,
            "error": str(e),
            "phase": Phase.COMPLETE,
            "log": state.get("log", []) + [error_message]
        }
        return ensure_complete_state(updated_state)


def analyze_ui(state: State) -> State:
    try:
        repo_dir = state.get("repo_dir", "")
        ui_files = state.get("ui_files", {})
        ui_files_json = json.dumps(ui_files)

        log_message = "Analyzing UI capabilities..."
        print(log_message)

        analysis_result = t.analyze_ui_capabilities.invoke({
            "repo_dir": repo_dir,
            "ui_files_json": ui_files_json
        })

        ui_analysis = json.loads(analysis_result)

        detected_frameworks = ui_analysis.get("framework", {}).get("detected", [])
        framework = detected_frameworks[0] if detected_frameworks else "Unknown"

        ui_libs = ui_analysis.get("ui_libraries", {}).get("detected", [])
        anim_types = ui_analysis.get("animation_system", {}).get("types", [])

        log_messages = [
            log_message,
            f"Analysis complete: Found {framework} framework with {', '.join(ui_libs) if ui_libs else 'no UI libraries'}"
        ]

        if anim_types:
            log_messages.append(f"Animation types: {', '.join(anim_types)}")

        print("\n".join(log_messages))

        updated_state = {
            **state,
            "ui_analysis": ui_analysis,
            "phase": Phase.IDENTIFY_OPPORTUNITIES,
            "log": state.get("log", []) + log_messages
        }
        return ensure_complete_state(updated_state)
    except Exception as e:
        error_message = f"Error in analyze_ui: {e}"
        print(error_message)
        updated_state = {
            **state,
            "error": str(e),
            "phase": Phase.COMPLETE,
            "log": state.get("log", []) + [error_message]
        }
        return ensure_complete_state(updated_state)


def identify_opportunities(state: State) -> State:
    try:
        enhancement_prompt = state.get("enhancement_prompt", "")
        ui_analysis = state.get("ui_analysis", {})
        ui_analysis_json = json.dumps(ui_analysis)
        repo_dir = state.get("repo_dir", "")

        log_message = f"Identifying enhancement opportunities based on: '{enhancement_prompt}'"
        print(log_message)

        # Step 1: Identify the primary focus area
        focus_prompt = f"""
        Based on the user's enhancement directive: "{enhancement_prompt}", identify the primary UI aspect to focus on.
        Choose a specific element or feature, such as:
        - Color scheme
        - Typography (fonts, text styles)
        - Button design
        - Layout and spacing
        - Image and media presentation (e.g., photo grid size)
        - Animations and transitions
        - Form elements
        - Navigation elements

        If the directive is general, select one specific aspect that could have the most impact based on the UI analysis.
        Return only the name of the primary aspect.
        """

        focus_result = llm.invoke([HumanMessage(content=focus_prompt)])
        primary_focus = focus_result.content.strip()

        # Step 2: Propose a specific design approach
        design_approach_prompt = f"""
        For the primary focus area: {primary_focus}, propose a specific design approach or style to apply consistently across the application.
        For example:
        - If color scheme: Suggest a color palette (e.g., primary, secondary, accent colors with hex codes)
        - If typography: Suggest font families, sizes, weights
        - If button design: Suggest styles (e.g., rounded, flat, with shadows, sizes)
        - If image and media presentation: Suggest grid sizes or layout styles
        Provide a brief description of the proposed design approach.
        """

        design_approach_result = llm.invoke([HumanMessage(content=design_approach_prompt)])
        design_approach = design_approach_result.content.strip()

        # Step 3: Identify opportunities based on primary focus
        refinement_prompt = f"""
        You are a UI/UX expert analyzing a web application.

        User's enhancement directive: "{enhancement_prompt}"

        Primary focus area: {primary_focus}

        Proposed design approach: {design_approach}

        UI analysis:
        {ui_analysis_json}

        Based on the UI analysis, identify specific enhancement opportunities focused solely on {primary_focus}.
        All opportunities should align with the proposed design approach and enhance {primary_focus} consistently across the application.
        Consider UI/UX best practices, but limit the scope to {primary_focus}.

        For each category, list concrete, specific opportunities for improvement related to {primary_focus}.
        Be creative but practical, considering the existing framework and libraries.

        Provide opportunities structured as JSON with these categories:
        - visual_design: Visual improvements related to {primary_focus}
        - animations: Animation enhancements (if related to {primary_focus})
        - user_experience: UX enhancements tied to {primary_focus}
        - prioritized_files: List of specific files to enhance, with clear reasons tied to {primary_focus}
        """

        refinement_result = llm.invoke([HumanMessage(content=refinement_prompt)])

        # Extract JSON from the response
        import re
        json_match = re.search(r'```json\n(.*?)\n```', refinement_result.content, re.DOTALL)
        if json_match:
            opportunities_json = json_match.group(1)
        else:
            try:
                opportunities = json.loads(refinement_result.content)
                opportunities_json = json.dumps(opportunities)
            except:
                opportunities_result = t.identify_enhancement_opportunities.invoke({
                    "repo_dir": repo_dir,
                    "ui_analysis_json": ui_analysis_json
                })
                opportunities_json = opportunities_result

        try:
            enhancement_opportunities = json.loads(opportunities_json)
            log_messages = [
                log_message,
                f"Primary focus: {primary_focus}",
                f"Design approach: {design_approach}",
                f"Identified opportunities in categories: {', '.join(enhancement_opportunities.keys())}"
            ]

            for category, opps in enhancement_opportunities.items():
                if isinstance(opps, list) and opps:
                    if category == "prioritized_files":
                        log_messages.append(f"- {len(opps)} files prioritized for enhancement")
                    else:
                        log_messages.append(f"- {category}: {len(opps)} opportunities")

            print("\n".join(log_messages))

            updated_state = {
                **state,
                "primary_focus": primary_focus,
                "design_approach": design_approach,
                "enhancement_opportunities": enhancement_opportunities,
                "phase": Phase.GENERATE_PLAN,
                "log": state.get("log", []) + log_messages
            }
            return ensure_complete_state(updated_state)
        except Exception as e:
            error_message = f"Error parsing opportunities JSON: {e}"
            print(error_message)
            updated_state = {
                **state,
                "error": error_message,
                "phase": Phase.COMPLETE,
                "log": state.get("log", []) + [log_message, error_message]
            }
            return ensure_complete_state(updated_state)
    except Exception as e:
        error_message = f"Error in identify_opportunities: {e}"
        print(error_message)
        updated_state = {
            **state,
            "error": str(e),
            "phase": Phase.COMPLETE,
            "log": state.get("log", []) + [error_message]
        }
        return ensure_complete_state(updated_state)


def generate_plan(state: State) -> State:
    try:
        enhancement_prompt = state.get("enhancement_prompt", "")
        primary_focus = state.get("primary_focus", "")
        design_approach = state.get("design_approach", "")
        enhancement_opportunities = state.get("enhancement_opportunities", {})
        opportunities_json = json.dumps(enhancement_opportunities)
        ui_analysis = state.get("ui_analysis", {})
        ui_analysis_json = json.dumps(ui_analysis)
        repo_dir = state.get("repo_dir", "")

        log_message = "Generating detailed enhancement plan..."
        print(log_message)

        ui_files = state.get("ui_files", {})
        all_ui_files = []
        for category, files in ui_files.get("ui_files", {}).items():
            all_ui_files.extend(files)

        existing_file_paths = [file_info["path"] for file_info in all_ui_files]
        print(f"Found {len(existing_file_paths)} UI files that exist in the repository")

        plan_prompt = f"""
        You are a UI/UX expert creating an enhancement plan for a web application.

        User's directive: "{enhancement_prompt}"

        Primary focus area: {primary_focus}

        Proposed design approach: {design_approach}

        UI analysis:
        {ui_analysis_json}

        Enhancement opportunities:
        {opportunities_json}

        IMPORTANT: Here are the actual UI files that exist in the repository that you can modify:
        {json.dumps(existing_file_paths, indent=2)}

        Create a detailed, actionable enhancement plan that:
        1. Has a clear title and description centered on enhancing {primary_focus}
        2. Lists specific changes to implement, all related to {primary_focus} and adhering to the design approach: {design_approach}
        3. ONLY includes file modifications for files in the list of actual UI files above
        4. For each file to modify, include:
           - File path (exactly as it appears in the list above)
           - Enhancement type (specific to {primary_focus})
           - Specific changes to make, ensuring consistency with the design approach
           - Expected impact on {primary_focus}

        If {primary_focus} requires global changes (e.g., color scheme or typography), include steps to define these globally (e.g., in a CSS file or theme configuration) and reference them in individual files.
        Ensure all changes are consistent and cohesive across all modified files, following the proposed design approach.

        Return your plan as a structured JSON object with:
        - title: A descriptive title focused on {primary_focus}
        - description: Overall plan description emphasizing {primary_focus} and the design approach
        - changes: Array of high-level changes related to {primary_focus}
        - file_modifications: Array of specific file changes with details, all tied to {primary_focus}
        """

        plan_result = llm.invoke([HumanMessage(content=plan_prompt)])

        # Extract JSON from the response
        import re
        json_match = re.search(r'```json\n(.*?)\n```', plan_result.content, re.DOTALL)
        if json_match:
            plan_json = json_match.group(1)
        else:
            try:
                plan = json.loads(plan_result.content)
                plan_json = json.dumps(plan)
            except:
                plan_json = t.generate_enhancement_plan.invoke({
                    "opportunities_json": opportunities_json
                })

        try:
            enhancement_plan = json.loads(plan_json)
            files_to_enhance = []
            for file_mod in enhancement_plan.get("file_modifications", []):
                file_path = file_mod.get("file_path", "")
                full_path = os.path.join(repo_dir, file_path)
                if os.path.exists(full_path):
                    files_to_enhance.append({
                        "path": file_path,
                        "enhancement_type": file_mod.get("enhancement_type", ""),
                        "changes": file_mod.get("changes", ""),
                        "impact": file_mod.get("impact", "")
                    })
                    print(f"Verified file exists: {file_path}")
                else:
                    print(f"WARNING: File does not exist: {file_path} - This file will be skipped")

            log_messages = [
                log_message,
                f"Plan generated: {enhancement_plan.get('title', 'UI Enhancement Plan')}",
                f"Changes planned: {len(enhancement_plan.get('changes', []))}",
                f"Files to modify: {len(files_to_enhance)} (after verification)"
            ]

            print("\n".join(log_messages))

            updated_state = {
                **state,
                "enhancement_plan": enhancement_plan,
                "files_to_enhance": files_to_enhance,
                "current_file_index": 0,
                "enhanced_files": [],
                "phase": Phase.IMPLEMENT_ENHANCEMENTS if files_to_enhance else Phase.SUMMARIZE,
                "log": state.get("log", []) + log_messages
            }
            return ensure_complete_state(updated_state)
        except Exception as e:
            error_message = f"Error parsing plan JSON: {e}"
            print(error_message)
            updated_state = {
                **state,
                "error": error_message,
                "phase": Phase.COMPLETE,
                "log": state.get("log", []) + [log_message, error_message]
            }
            return ensure_complete_state(updated_state)
    except Exception as e:
        error_message = f"Error in generate_plan: {e}"
        print(error_message)
        updated_state = {
            **state,
            "error": str(e),
            "phase": Phase.COMPLETE,
            "log": state.get("log", []) + [error_message]
        }
        return ensure_complete_state(updated_state)


def implement_enhancements(state: State) -> State:
    try:
        repo_dir = state.get("repo_dir", "")
        files_to_enhance = state.get("files_to_enhance", [])
        current_index = state.get("current_file_index", 0)
        enhanced_files = state.get("enhanced_files", [])
        ui_analysis = state.get("ui_analysis", {})

        if current_index >= len(files_to_enhance):
            log_message = f"All {len(enhanced_files)} files enhanced successfully"
            print(log_message)
            updated_state = {
                **state,
                "phase": Phase.VERIFY_CHANGES,
                "log": state.get("log", []) + [log_message]
            }
            return ensure_complete_state(updated_state)

        file_info = files_to_enhance[current_index]
        file_path = file_info["path"]
        enhancement_type = file_info["enhancement_type"]
        planned_changes = file_info["changes"]

        log_message = f"Enhancing file {current_index + 1}/{len(files_to_enhance)}: {file_path}"
        print(log_message)

        try:
            full_path = os.path.join(repo_dir, file_path)
            if not os.path.exists(full_path):
                error_message = f"File {file_path} does not exist - skipping"
                print(error_message)
                updated_state = {
                    **state,
                    "current_file_index": current_index + 1,
                    "log": state.get("log", []) + [log_message, error_message]
                }
                return ensure_complete_state(updated_state)

            original_content = t.get_file_content.invoke({
                "repo_dir": repo_dir,
                "relative_path": file_path
            })

            if original_content.startswith("Error reading file"):
                error_message = f"Failed to read {file_path}: {original_content}"
                print(error_message)
                updated_state = {
                    **state,
                    "current_file_index": current_index + 1,
                    "log": state.get("log", []) + [log_message, error_message]
                }
                return ensure_complete_state(updated_state)

            framework_info = f"Framework: {', '.join(ui_analysis.get('framework', {}).get('detected', ['Unknown']))}"
            libraries_info = f"UI Libraries: {', '.join(ui_analysis.get('ui_libraries', {}).get('detected', ['None detected']))}"

            enhancement_prompt = f"""
            You are a UI/UX expert enhancing a React and Astro web application file.

            {framework_info}
            {libraries_info}

            File path: {file_path}

            Original file content:
            ```
            {original_content}
            ```

            Enhancement type: {enhancement_type}

            Planned changes:
            {planned_changes}

            Create an enhanced version of this file that:
            1. Implements the planned changes
            2. Maintains all original functionality
            3. Uses best practices for the file type
            4. Makes visually noticeable improvements
            5. PRESERVES all important original code structures and functionality

            Return ONLY the complete enhanced file content without any explanation.
            Do not include markdown code blocks or any explanatory text - your output will be directly written to the file.
            """
            file_ext = os.path.splitext(file_path)[1].lower()

            if file_ext == '.astro':
                enhancement_prompt += """
                IMPORTANT CONSTRAINTS FOR ASTRO FILES:
                1. DO NOT add client:load or ANY client hydration directives
                2. ONLY modify the <style> section for visual improvements
                3. Keep all frontmatter (between --- tags) unchanged
                4. Use vanilla <script> tags for minimal interactivity
                5. TEST YOUR SYNTAX - ensure all tags and braces match
                """
            elif file_ext == '.js':
                enhancement_prompt += """
                IMPORTANT CONSTRAINTS FOR JAVASCRIPT:
                1. Ensure all parentheses in if-statements are balanced - if (condition) { ... }
                2. Double-check all bracket pairs {} [] ()
                3. All if/for/while statements must have complete syntax
                4. DO NOT change core function signatures or exports
                5. Focus on readability and performance improvements only
                """

            enhancement_result = llm.invoke([HumanMessage(content=enhancement_prompt)])
            enhanced_content = enhancement_result.content

            import re
            code_block_match = re.search(r'```(?:\w+)?\n(.*?)\n```', enhanced_content, re.DOTALL)
            if code_block_match:
                enhanced_content = code_block_match.group(1)
                print(f"Extracted code from markdown code block")

            print(f"Enhanced content type: {type(enhanced_content)}, length: {len(enhanced_content)}")
            print(f"First 50 chars of enhanced content: {enhanced_content[:50]}")

            modification_result = t.modify_ui_file.invoke({
                "repo_dir": repo_dir,
                "file_path": file_path,
                "enhancement_type": enhancement_type,
                "enhanced_content": enhanced_content
            })

            try:
                modification_data = json.loads(modification_result)
                success = modification_data.get("success", False)

                if success:
                    print(f"Successfully enhanced {file_path}")
                    enhanced_files.append({
                        "path": file_path,
                        "enhancement_type": enhancement_type,
                        "success": True
                    })
                else:
                    error = modification_data.get("error", "Unknown error")
                    print(f"Failed to enhance {file_path}: {error}")
                    enhanced_files.append({
                        "path": file_path,
                        "enhancement_type": enhancement_type,
                        "success": False,
                        "error": error
                    })

                updated_state = {
                    **state,
                    "current_file_index": current_index + 1,
                    "enhanced_files": enhanced_files,
                    "phase": Phase.IMPLEMENT_ENHANCEMENTS,
                    "log": state.get("log", []) + [log_message,
                                                   f"{'Successfully enhanced' if success else 'Failed to enhance'} {file_path}"]
                }
                return ensure_complete_state(updated_state)
            except Exception as e:
                log_messages = [log_message, f"Error processing modification result: {e}"]
                print("\n".join(log_messages))
                updated_state = {
                    **state,
                    "current_file_index": current_index + 1,
                    "enhanced_files": enhanced_files,
                    "phase": Phase.IMPLEMENT_ENHANCEMENTS,
                    "log": state.get("log", []) + log_messages
                }
                return ensure_complete_state(updated_state)
        except Exception as e:
            log_messages = [log_message, f"Error enhancing file {file_path}: {e}"]
            print("\n".join(log_messages))
            updated_state = {
                **state,
                "current_file_index": current_index + 1,
                "enhanced_files": enhanced_files,
                "phase": Phase.IMPLEMENT_ENHANCEMENTS,
                "log": state.get("log", []) + log_messages
            }
            return ensure_complete_state(updated_state)
    except Exception as e:
        error_message = f"Error in implement_enhancements: {e}"
        print(error_message)
        updated_state = {
            **state,
            "phase": Phase.VERIFY_CHANGES,
            "log": state.get("log", []) + [error_message]
        }
        return ensure_complete_state(updated_state)


def verify_changes(state: State) -> State:
    try:
        repo_dir = state.get("repo_dir", "")
        enhanced_files = state.get("enhanced_files", [])

        if not enhanced_files:
            log_message = "No files were enhanced, skipping verification"
            print(log_message)
            updated_state = {
                **state,
                "phase": Phase.SUMMARIZE,
                "log": state.get("log", []) + [log_message]
            }
            return ensure_complete_state(updated_state)

        log_message = f"Verifying {len(enhanced_files)} enhanced files..."
        print(log_message)

        modified_files_json = json.dumps({"files": enhanced_files})
        verification_result = t.verify_ui_changes.invoke({
            "repo_dir": repo_dir,
            "modified_files_json": modified_files_json
        })

        try:
            verification_data = json.loads(verification_result)
            success = verification_data.get("success", True)
            issues = verification_data.get("potential_issues", [])

            log_messages = [
                log_message,
                f"Verification {'successful' if success else 'found issues'}"
            ]

            if issues:
                log_messages.append(f"Found {len(issues)} potential issues")
                files_to_revert = [issue["file"] for issue in issues if
                                   "syntax error" in issue.get("issue", "").lower()]
                if files_to_revert:
                    revert_result = t.revert_ui_changes.invoke({
                        "repo_dir": repo_dir,
                        "files_to_revert": files_to_revert
                    })
                    try:
                        revert_data = json.loads(revert_result)
                        reverted = len(revert_data.get("successful_reverts", []))
                        log_messages.append(f"Reverted {reverted} problematic files")
                    except Exception as e:
                        log_messages.append(f"Failed to revert problematic files: {str(e)}")

            print("\n".join(log_messages))

            updated_state = {
                **state,
                "verification_result": verification_data,
                "phase": Phase.SUMMARIZE,
                "log": state.get("log", []) + log_messages
            }
            return ensure_complete_state(updated_state)
        except Exception as e:
            log_messages = [log_message, f"Error processing verification result: {e}"]
            print("\n".join(log_messages))
            updated_state = {
                **state,
                "phase": Phase.SUMMARIZE,
                "log": state.get("log", []) + log_messages
            }
            return ensure_complete_state(updated_state)
    except Exception as e:
        error_message = f"Error in verify_changes: {e}"
        print(error_message)
        updated_state = {
            **state,
            "phase": Phase.SUMMARIZE,
            "log": state.get("log", []) + [error_message]
        }
        return ensure_complete_state(updated_state)


def create_summary(state: State) -> State:
    try:
        enhanced_files = state.get("enhanced_files", [])
        enhancement_plan = state.get("enhancement_plan", {})
        verification_result = state.get("verification_result", {})
        enhancement_prompt = state.get("enhancement_prompt", "")

        log_message = "Creating enhancement summary..."
        print(log_message)

        summary_prompt = f"""
        You are a UI/UX expert who has just completed enhancements to a web application.

        Original enhancement directive: "{enhancement_prompt}"

        Enhancement plan: {json.dumps(enhancement_plan, indent=2)}

        Enhanced files: {json.dumps(enhanced_files, indent=2)}

        Verification results: {json.dumps(verification_result, indent=2)}

        Create a comprehensive, well-formatted summary of the enhancements that:
        1. Explains what was accomplished
        2. Highlights the most significant improvements
        3. Describes the visual and functional changes
        4. Notes any issues that were encountered

        Make the summary conversational and engaging, focusing on the value delivered.
        """

        summary_result = llm.invoke([HumanMessage(content=summary_prompt)])
        summary = summary_result.content

        print(f"Summary generated successfully")

        updated_state = {
            **state,
            "summary": summary,
            "phase": Phase.COMPLETE,
            "log": state.get("log", []) + [log_message, "Summary generated successfully"]
        }
        return ensure_complete_state(updated_state)
    except Exception as e:
        error_message = f"Error in create_summary: {e}"
        print(error_message)
        minimal_summary = f"""
        # UI Enhancement Summary

        Enhanced {len(state.get('enhanced_files', []))} files based on prompt: "{state.get('enhancement_prompt', '')}"

        Error occurred during summary generation: {str(e)}
        """
        updated_state = {
            **state,
            "summary": minimal_summary,
            "phase": Phase.COMPLETE,
            "log": state.get("log", []) + [error_message]
        }
        return ensure_complete_state(updated_state)


def get_next_step(state: State) -> str:
    return state.get("phase", Phase.COMPLETE)


workflow = StateGraph(State)

workflow.add_node(Phase.CLONE_REPO, clone_repository)
workflow.add_node(Phase.SCAN_UI_FILES, scan_ui_files)
workflow.add_node(Phase.ANALYZE_UI, analyze_ui)
workflow.add_node(Phase.IDENTIFY_OPPORTUNITIES, identify_opportunities)
workflow.add_node(Phase.GENERATE_PLAN, generate_plan)
workflow.add_node(Phase.IMPLEMENT_ENHANCEMENTS, implement_enhancements)
workflow.add_node(Phase.VERIFY_CHANGES, verify_changes)
workflow.add_node(Phase.SUMMARIZE, create_summary)

workflow.add_conditional_edges(
    Phase.CLONE_REPO,
    get_next_step,
    {Phase.SCAN_UI_FILES: Phase.SCAN_UI_FILES, Phase.COMPLETE: END}
)

workflow.add_conditional_edges(
    Phase.SCAN_UI_FILES,
    get_next_step,
    {Phase.ANALYZE_UI: Phase.ANALYZE_UI, Phase.COMPLETE: END}
)

workflow.add_conditional_edges(
    Phase.ANALYZE_UI,
    get_next_step,
    {Phase.IDENTIFY_OPPORTUNITIES: Phase.IDENTIFY_OPPORTUNITIES, Phase.COMPLETE: END}
)

workflow.add_conditional_edges(
    Phase.IDENTIFY_OPPORTUNITIES,
    get_next_step,
    {Phase.GENERATE_PLAN: Phase.GENERATE_PLAN, Phase.COMPLETE: END}
)

workflow.add_conditional_edges(
    Phase.GENERATE_PLAN,
    get_next_step,
    {Phase.IMPLEMENT_ENHANCEMENTS: Phase.IMPLEMENT_ENHANCEMENTS, Phase.SUMMARIZE: Phase.SUMMARIZE, Phase.COMPLETE: END}
)

workflow.add_conditional_edges(
    Phase.IMPLEMENT_ENHANCEMENTS,
    get_next_step,
    {Phase.IMPLEMENT_ENHANCEMENTS: Phase.IMPLEMENT_ENHANCEMENTS, Phase.VERIFY_CHANGES: Phase.VERIFY_CHANGES,
     Phase.COMPLETE: END}
)

workflow.add_conditional_edges(
    Phase.VERIFY_CHANGES,
    get_next_step,
    {Phase.SUMMARIZE: Phase.SUMMARIZE, Phase.COMPLETE: END}
)

workflow.add_conditional_edges(
    Phase.SUMMARIZE,
    get_next_step,
    {Phase.COMPLETE: END}
)

workflow.set_entry_point(Phase.CLONE_REPO)
agent = workflow.compile()


def enhance_ui(repo_url: str, enhancement_prompt: str = "Enhance the UI") -> Dict[str, Any]:
    print(f"Starting UI enhancement for: {repo_url}")
    print(f"Enhancement prompt: {enhancement_prompt}")

    initial_state = {
        "phase": Phase.CLONE_REPO,
        "enhancement_prompt": enhancement_prompt,
        "repo_url": repo_url,
        "repo_dir": "",
        "ui_files": {},
        "ui_analysis": {},
        "primary_focus": "",
        "design_approach": "",
        "enhancement_opportunities": {},
        "enhancement_plan": {},
        "files_to_enhance": [],
        "current_file_index": 0,
        "enhanced_files": [],
        "verification_result": {},
        "summary": "",
        "error": None,
        "log": []
    }

    try:
        result = agent.invoke(initial_state)
        return result
    except Exception as e:
        print(f"Error running UI enhancement agent: {e}")
        return {
            "error": str(e),
            "summary": "UI enhancement failed due to an error."
        }