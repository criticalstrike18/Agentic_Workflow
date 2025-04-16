# simplified_main.py
import os

from dotenv import load_dotenv

from agent import enhance_ui


def main():
    """Main entry point for autonomous UI enhancement."""
    load_dotenv()

    repo_url = os.getenv('REPO_URL')
    if not repo_url:
        repo_url = input("Enter GitHub repository URL: ")

    try:
        # Execute the agent
        result = enhance_ui(repo_url)

        # Print summary
        if "error" in result and result["error"]:
            print(f"\n❌ Error during processing: {result['error']}")

        if "summary" in result and result["summary"]:
            print(f"\n{result['summary']}")

        # Show where to find the changes
        target_dir = os.getenv('TARGET_DIR', './enhanced_repo')
        if not os.path.isabs(target_dir):
            target_dir = os.path.abspath(target_dir)

        print(f"\nYou can view the enhanced repository at: {target_dir}")
        print(f"Original files were backed up with the .bak extension.")

    except KeyboardInterrupt:
        print("\n\nProcess aborted by user.")
    except Exception as e:
        print(f"\n\nError during UI enhancement process: {e}")


if __name__ == "__main__":
    main()