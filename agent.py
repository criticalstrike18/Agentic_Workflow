from langchain.agents import initialize_agent
from langchain.llms import OpenAI  # Replace with your LLM (e.g., DeepSeek)

from tools import git_clone, get_directory_tree, get_file_content

# Initialize the language model (adjust as per your setup)
llm = OpenAI(temperature=0)

# List of tools for the agent
tools = [git_clone, get_directory_tree, get_file_content]

# Initialize the agent
# noinspection PyTypeChecker
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent="zero-shot-react-description",  # Adjust agent type as needed
    verbose=True
)
