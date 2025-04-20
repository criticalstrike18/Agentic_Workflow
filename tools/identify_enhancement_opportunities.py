import json

from langchain.tools import tool


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
