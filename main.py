# main.py (Revised)
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Import the executor instance
from agent import agent_executor  # Assuming you export the executor


def main():
    """Main entry point for the application."""
    load_dotenv()

    repo_url = os.getenv('REPO_URL')
    target_dir = os.getenv('TARGET_DIR')
    # Ensure TARGET_DIR is an absolute path or resolve it
    if target_dir and not os.path.isabs(target_dir):
        target_dir = os.path.abspath(target_dir)


    if not repo_url:
        raise ValueError("REPO_URL must be set in the .env file")
    if not target_dir:
        raise ValueError("TARGET_DIR must be set in the .env file")

    # Make sure the parent directory for target_dir exists if possible
    target_parent = os.path.dirname(target_dir)
    if target_parent:
        os.makedirs(target_parent, exist_ok=True)

    print(f"Attempting to clone '{repo_url}' into '{target_dir}'")

    try:
        # Use the modern invoke method with a dictionary input
        prompt = f"Clone the repository from '{repo_url}' to '{target_dir}'"
        # Maintain chat history for context (optional but good practice)
        chat_history = []
        result = agent_executor.invoke({
            "input": prompt,
            "chat_history": chat_history  # Start with empty history
        })

        print(f"Agent Result:\n{result['output']}")

        # Example follow-up:
        print("\nAttempting to list directory tree...")
        # Add previous interaction to history
        chat_history.append(HumanMessage(content=prompt))
        chat_history.append(result['output'])  # Or AIMessage(content=result['output'])

        follow_up_prompt = f"List the directory tree for the cloned repository at '{target_dir}'"
        result_tree = agent_executor.invoke({
            "input": follow_up_prompt,
            "chat_history": chat_history
        })
        print(f"Agent Result:\n{result_tree['output']}")


    except Exception as e:
        print(f"Error executing agent: {e}")


if __name__ == "__main__":
    main()