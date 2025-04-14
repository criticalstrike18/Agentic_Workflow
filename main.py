import os

from dotenv import load_dotenv

from agent import agent


def main():
    """Main entry point for the application."""
    # Load environment variables from .env
    load_dotenv()

    # Retrieve environment variables
    repo_url = os.getenv('REPO_URL')
    target_dir = os.getenv('TARGET_DIR')

    # Validate required variables
    if not repo_url:
        raise ValueError("REPO_URL must be set in the .env file")
    if not target_dir:
        raise ValueError("TARGET_DIR must be set in the .env file")

    try:
        # Example: Use the agent to clone the repository
        prompt = f"Clone the repository from '{repo_url}' to '{target_dir}'"
        result = agent.run(prompt)
        print(f"Result: {result}")

    except Exception as e:
        print(f"Error executing agent: {e}")


if __name__ == "__main__":
    main()
