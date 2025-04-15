# agent.py (Revised)
import os
from typing import List, Optional, Any

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel  # Use BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from openai import OpenAI

from tools import git_clone, get_directory_tree, get_file_content

load_dotenv()

deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
deepseek_api_base = os.getenv('DEEPSEEK_API_BASE')
model_name = os.getenv('DEEPSEEK_MODEL', "deepseek-chat")  # Default or from .env

if not deepseek_api_key:
    raise ValueError("DEEPSEEK_API_KEY must be set")
if not deepseek_api_base:
    raise ValueError("DEEPSEEK_API_BASE must be set")


# --- Custom Chat Model (if needed, or try ChatOpenAI directly) ---
class DeepSeekChat(BaseChatModel):
    client: OpenAI
    model: str = model_name

    def __init__(self, api_key: str, api_base: str, model: str = model_name, **kwargs):
        super().__init__(**kwargs)  # Pass additional args like temperature if needed
        self.client = OpenAI(base_url=api_base, api_key=api_key)
        self.model = model

    def _generate(
            self,
            messages: List[BaseMessage],
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> ChatResult:
        """Implements the chat generation logic."""
        openai_formatted_messages = []
        for msg in messages:
            role = "user"  # Default
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            elif isinstance(msg, SystemMessage):
                role = "system"
            openai_formatted_messages.append({"role": role, "content": msg.content})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_formatted_messages,
                stop=stop,
                **kwargs  # Pass temperature, max_tokens etc here
            )
            content = response.choices[0].message.content or ""
            ai_message = AIMessage(content=content)
            generation = ChatGeneration(message=ai_message)
            return ChatResult(generations=[generation])
        except Exception as e:
            # Log the error appropriately
            print(f"Error calling DeepSeek API: {e}")
            # Return a default or error message
            ai_message = AIMessage(content=f"Error interacting with LLM: {e}")
            generation = ChatGeneration(message=ai_message)
            return ChatResult(generations=[generation])

    @property
    def _llm_type(self) -> str:
        return "deepseek-chat"


# # --- Initialize LLM ---
llm = ChatOpenAI(
    openai_api_key=deepseek_api_key,
    openai_api_base=deepseek_api_base,
    model_name=model_name,
    temperature=0
)

# --- Tools (make sure they are imported correctly from tools.py) ---
tools = [git_clone, get_directory_tree, get_file_content]  # Now these are decorated @tool functions

# --- Prompt ---
# Note: Adjust the system prompt if needed for DeepSeek's behavior
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a helpful assistant that can interact with git repositories and local filesystems using provided "
            "tools."
            "You can clone repos, list directory structures, and read file contents."
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

# --- Agent ---
agent = create_tool_calling_agent(llm, tools, prompt)

# --- Agent Executor ---
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

