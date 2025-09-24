import asyncio
import os
import sys

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.tools.mcp import (
    SseMcpToolAdapter,
    SseServerParams,
    StdioServerParams,
    mcp_server_tools,
)
from dotenv import load_dotenv

sys.path.append(os.path.abspath(".."))
from utilities import (
    create_chat_completion_client,
    get_tavily_search_tool,
    load_model_config,
)

# Get environment variables
load_dotenv()

INCLUDE_WEB_SEARCH = True

if (
    INCLUDE_WEB_SEARCH
    and not os.getenv("APIFY_API_KEY")
    and not os.getenv("TAVILY_API_KEY")
):
    raise ValueError(
        "APIFY_API_KEY and TAVILY_API_KEY environment variables are not set."
    )


def subtract(a: float, b: float) -> float:
    """Subtract two numbers"""
    return a - b


def divide(a: float, b: float) -> float:
    """Divide two numbers"""
    return a / b


async def provide_tools() -> list:
    # Setup server params for local filesystem tool access
    math_server = StdioServerParams(
        command="python", args=[os.path.dirname(__file__) + "/math_server.py"]
    )
    add_and_multiply_tools = await mcp_server_tools(math_server)

    # Tools through local synchronous functions
    subtract_and_divide_tools = [subtract, divide]

    # Combine the tools from both sources
    all_tools = add_and_multiply_tools + subtract_and_divide_tools
    if INCLUDE_WEB_SEARCH:
        if False and os.getenv("APIFY_API_KEY"):
            # HTTP MCP server
            # Setup server params for SSE access
            server_params = SseServerParams(
                url="https://rag-web-browser.apify.actor/sse",
                headers={"Authorization": f"Bearer {os.getenv('APIFY_API_KEY')}"},
                timeout=30,
            )
            # Create the tool adapter for the SSE server
            rag_web_search_tool = await SseMcpToolAdapter.from_server_params(
                server_params,
                "rag-web-browser",
            )
            all_tools.append(rag_web_search_tool)

        if os.getenv("TAVILY_API_KEY"):
            # Custom async HTTP search tool
            all_tools.append(await get_tavily_search_tool())  # type: ignore
    return all_tools


async def main() -> None:

    # Create the model client for LLM interactions
    model_config = load_model_config()
    model_client = create_chat_completion_client(model_config)

    # Get the tools to be used by the agent
    tools = await provide_tools()

    # Create the assistant agent with the model client and tools
    agent = AssistantAgent(
        name="demo_agent",
        model_client=model_client,
        tools=tools,  # type: ignore
        reflect_on_tool_use=True,  # allows the agent to post-process tool outputs
        system_message=(
            "You are an intelligent assistant with access to miscellaneous tools. If you need to search the web, "
            "use the 'adapter' or 'tavily search' tool, but always request minimal content. maxResults=1, "
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
