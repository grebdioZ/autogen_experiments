import asyncio
import os
import sys

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import (
    SseMcpToolAdapter,
    SseServerParams,
    StdioServerParams,
    mcp_server_tools,
)
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools import create_chat_completion_client, load_model_config

# Get environment variables
load_dotenv()
model_config = load_model_config()
print("Used model:", model_config["name"])
OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
APIFY_API_KEY = os.getenv("APIFY_API_KEY")

INCLUDE_WEB_SEARCH = False

if INCLUDE_WEB_SEARCH and not APIFY_API_KEY:
    raise ValueError("APIFY_API_KEY environment variable is not set.")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")


def subtract(a: float, b: float) -> float:
    """Subtract two numbers"""
    return a - b


def divide(a: float, b: float) -> float:
    """Divide two numbers"""
    return a / b


async def main() -> None:

    # Setup server params for local filesystem access
    math_server = StdioServerParams(
        command="python", args=[os.path.dirname(__file__) + "/math_server.py"]
    )
    add_and_multiply_tools = await mcp_server_tools(math_server)
    subttract_and_divide_tools = [subtract, divide]

    # Combine the tools from both servers into a single list
    all_tools = add_and_multiply_tools + subttract_and_divide_tools

    if INCLUDE_WEB_SEARCH:
        # Setup server params for SSE access
        server_params = SseServerParams(
            url="https://rag-web-browser.apify.actor/sse",  # Removed limits from URL
            headers={"Authorization": f"Bearer {APIFY_API_KEY}"},
            timeout=30,
        )

        # Create the tool adapter for the SSE server
        # Note: The tool adapter is created using the server_params and the tool name.
        # Ensure the tool name matches the one expected by the server
        # You may need to adjust this based on the actual tool name provided by the server
        rag_web_search_tool = await SseMcpToolAdapter.from_server_params(
            server_params,
            "rag-web-browser",
        )
        all_tools.append(rag_web_search_tool)

    model_config = load_model_config()
    model_client = create_chat_completion_client(model_config)
    agent = AssistantAgent(
        name="demo_agent",
        model_client=model_client,
        tools=all_tools,
        reflect_on_tool_use=True,
        system_message=(
            "You are an intelligent assistant with access to tools such as 'adapter', "
            "which connects to Apify's rag-web-browser. If you need to search the web, "
            "use the 'adapter' tool, but always request minimal content. maxResults=1, "
            "Only fetch the most relevant and recent information. Avoid large responses "
            "that may exceed token limits by limiting page content size and page count."
        ),
    )

    if INCLUDE_WEB_SEARCH:
        await Console(
            agent.run_stream(
                task="Summarise the latest news of Iran and US negotiations in one small concise paragraph.",
                cancellation_token=CancellationToken(),
            )
        )
    await Console(
        agent.run_stream(
            task="what's (3 * 5) - 12?", cancellation_token=CancellationToken()
        )
    )


asyncio.run(main())
