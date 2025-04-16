# simplified_ui_agent.py
import json
import os
from enum import Enum
from typing import Dict, List, Any, Optional, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

# Import tools
from tools import git_clone, get_directory_tree, get_file_content
from tools.autonomous_ui_tools import (
    scan_codebase_for_ui_components,
    analyze_ui_component,
    regenerate_ui_component
)

# Load environment variables
load_dotenv()

deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
deepseek_api_base = os.getenv('DEEPSEEK_API_BASE')
model_name = os.getenv('DEEPSEEK_MODEL', "deepseek-chat")

if not deepseek_api_key:
    raise ValueError("DEEPSEEK_API_KEY must be set")
if not deepseek_api_base:
    raise ValueError("DEEPSEEK_API_BASE must be set")

# Create language model
llm = ChatOpenAI(
    openai_api_key=deepseek_api_key,
    openai_api_base=deepseek_api_base,
    model_name="deepseek-chat",
    temperature=0
)


# Define phases for the workflow
class Phase(str, Enum):
    CLONE_REPO = "clone_repo"
    SCAN_CODEBASE = "scan_codebase"
    ANALYZE_COMPONENTS = "analyze_components"
    ENHANCE_COMPONENTS = "enhance_components"
    SUMMARIZE = "summarize"
    COMPLETE = "complete"


# Define a simplified state type
class State(TypedDict):
    phase: str
    repo_url: str
    repo_dir: str
    components: List[Dict[str, Any]]
    current_component_index: int
    enhanced_components: List[Dict[str, Any]]
    summary: str
    error: Optional[str]


# Define the node functions
def clone_repository(state: State) -> State:
    """Clone the repository to a local directory."""
    try:
        repo_url = state["repo_url"]
        target_dir = os.getenv('TARGET_DIR', './enhanced_repo')
        if not os.path.isabs(target_dir):
            target_dir = os.path.abspath(target_dir)

        print(f"Cloning repository: {repo_url} to {target_dir}")
        result = git_clone.invoke({"repo_url": repo_url, "target_dir": target_dir})
        print(f"Clone result: {result}")

        # Update state with new directory and proceed to next phase
        return {
            **state,
            "repo_dir": target_dir,
            "phase": Phase.SCAN_CODEBASE
        }
    except Exception as e:
        print(f"Error in clone_repository: {e}")
        return {
            **state,
            "error": str(e),
            "phase": Phase.COMPLETE
        }


def scan_for_components(state: State) -> State:
    """Scan the repository for UI components."""
    try:
        repo_dir = state["repo_dir"]
        print(f"Scanning for UI components in: {repo_dir}")

        # Get repo structure
        directory_structure = get_directory_tree.invoke({"root_dir": repo_dir})
        print(f"Repository structure: {directory_structure[:100]}...")

        # Scan for UI components
        scan_result = scan_codebase_for_ui_components.invoke({"repo_dir": repo_dir})
        scan_data = json.loads(scan_result)

        components = scan_data.get("ui_components", [])
        print(f"Found {len(components)} UI components")

        return {
            **state,
            "components": components,
            "current_component_index": 0,
            "phase": Phase.ANALYZE_COMPONENTS if components else Phase.SUMMARIZE
        }
    except Exception as e:
        print(f"Error in scan_for_components: {e}")
        return {
            **state,
            "error": str(e),
            "phase": Phase.COMPLETE
        }


def analyze_and_enhance_component(state: State) -> State:
    """Analyze a component, then enhance it if needed."""
    try:
        components = state["components"]
        current_index = state["current_component_index"]
        repo_dir = state["repo_dir"]
        enhanced_components = state.get("enhanced_components", [])

        # Check if we've processed all components
        if current_index >= len(components):
            return {
                **state,
                "phase": Phase.SUMMARIZE
            }

        # Get current component
        component = components[current_index]
        file_path = component["path"]
        print(f"Processing component {current_index + 1}/{len(components)}: {file_path}")

        # Analyze the component
        analysis_result = analyze_ui_component.invoke({
            "repo_dir": repo_dir,
            "file_path": file_path
        })

        analysis_data = json.loads(analysis_result)

        # Get original content
        original_content = get_file_content.invoke({
            "repo_dir": repo_dir,
            "relative_path": file_path
        })

        # Generate enhanced version using LLM
        enhancement_prompt = f"""
        I need to enhance the following UI component without any specific user direction.
        I'll make autonomous improvements that make it more modern, visually appealing, and user-friendly.

        File path: {file_path}

        Analysis: {json.dumps(analysis_data, indent=2)}

        Original content:
        ```
        {original_content}
        ```

        Generate an improved version of this component with:
        1. Modern styling improvements
        2. Better user experience elements
        3. Cleaner, more maintainable code
        4. Preserved functionality

        Return ONLY the complete new source code without explanation.
        """

        enhancement_result = llm.invoke([HumanMessage(content=enhancement_prompt)])
        new_content = enhancement_result.content

        # Clean the response to extract only the code
        import re
        code_block_match = re.search(r'```(?:\w+)?\n(.*?)\n```', new_content, re.DOTALL)
        if code_block_match:
            new_content = code_block_match.group(1)

        # Apply the changes
        regenerate_result = regenerate_ui_component.invoke({
            "repo_dir": repo_dir,
            "file_path": file_path,
            "new_content": new_content,
            "backup": True
        })

        regenerate_data = json.loads(regenerate_result)

        # Add to enhanced components list
        enhanced_components.append({
            "file_path": file_path,
            "success": regenerate_data.get("success", False),
            "message": regenerate_data.get("message", ""),
        })

        # Move to next component
        return {
            **state,
            "current_component_index": current_index + 1,
            "enhanced_components": enhanced_components,
            "phase": Phase.ANALYZE_COMPONENTS  # Stay in the same phase for next component
        }

    except Exception as e:
        print(f"Error in analyze_and_enhance_component: {e}")
        # Continue to next component even if one fails
        return {
            **state,
            "current_component_index": state["current_component_index"] + 1,
            "phase": Phase.ANALYZE_COMPONENTS
        }


def create_summary(state: State) -> State:
    """Create a summary of the enhancements."""
    try:
        enhanced_components = state.get("enhanced_components", [])

        # Generate summary text
        summary = "# UI Enhancement Summary\n\n"
        summary += f"Enhanced {len(enhanced_components)} UI components:\n\n"

        for component in enhanced_components:
            file_path = component["file_path"]
            success = component.get("success", False)
            message = component.get("message", "")

            if success:
                summary += f"✅ {file_path} - {message}\n"
            else:
                summary += f"❌ {file_path} - Failed to enhance\n"

        print(summary)

        return {
            **state,
            "summary": summary,
            "phase": Phase.COMPLETE
        }
    except Exception as e:
        print(f"Error in create_summary: {e}")
        return {
            **state,
            "error": str(e),
            "phase": Phase.COMPLETE
        }


# Define routing logic
def get_next_step(state: State) -> str:
    return state["phase"]


# Build the workflow
workflow = StateGraph(State)

# Add nodes
workflow.add_node(Phase.CLONE_REPO, clone_repository)
workflow.add_node(Phase.SCAN_CODEBASE, scan_for_components)
workflow.add_node(Phase.ANALYZE_COMPONENTS, analyze_and_enhance_component)
workflow.add_node(Phase.SUMMARIZE, create_summary)

# Add conditional edges
workflow.add_conditional_edges(
    Phase.CLONE_REPO,
    get_next_step,
    {
        Phase.SCAN_CODEBASE: Phase.SCAN_CODEBASE,
        Phase.COMPLETE: END
    }
)

workflow.add_conditional_edges(
    Phase.SCAN_CODEBASE,
    get_next_step,
    {
        Phase.ANALYZE_COMPONENTS: Phase.ANALYZE_COMPONENTS,
        Phase.SUMMARIZE: Phase.SUMMARIZE,
        Phase.COMPLETE: END
    }
)

workflow.add_conditional_edges(
    Phase.ANALYZE_COMPONENTS,
    get_next_step,
    {
        Phase.ANALYZE_COMPONENTS: Phase.ANALYZE_COMPONENTS,
        Phase.SUMMARIZE: Phase.SUMMARIZE,
        Phase.COMPLETE: END
    }
)

workflow.add_conditional_edges(
    Phase.SUMMARIZE,
    get_next_step,
    {
        Phase.COMPLETE: END
    }
)

# Set entry point
workflow.set_entry_point(Phase.CLONE_REPO)

# Compile the graph
agent = workflow.compile()


# Function to run the agent
def enhance_ui(repo_url: str) -> Dict[str, Any]:
    """
    Enhance UI components in a repository.

    Args:
        repo_url (str): Repository URL

    Returns:
        dict: The final state with summary of changes
    """
    print(f"Starting UI enhancement for: {repo_url}")

    # Initial state
    initial_state = {
        "phase": Phase.CLONE_REPO,
        "repo_url": repo_url,
        "repo_dir": "",
        "components": [],
        "current_component_index": 0,
        "enhanced_components": [],
        "summary": "",
        "error": None
    }

    # Run the agent
    try:
        result = agent.invoke(initial_state)
        return result
    except Exception as e:
        print(f"Error running UI enhancement agent: {e}")
        return {
            "error": str(e),
            "summary": "UI enhancement failed due to an error."
        }
