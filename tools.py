import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv
import httpx
import yaml
from autogen_agentchat.agents import AssistantAgent
from autogen_core.models import ChatCompletionClient, ModelInfo
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseMcpToolAdapter, SseServerParams

load_dotenv()


def load_model_config(
    config_path: str | None = None, model_name: str | None = None
) -> Dict[str, Any]:
    """Load configuration from a YAML file."""
    file_path = os.path.dirname(__file__)
    if config_path is None:
        config_path = file_path + "/resources.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)

    model_name = model_name or os.getenv("DEFAULT_MODEL_NAME") or "GPT-4.1-Nano"
    model = [
        m for m in config["models"] if m.get("name", "").lower() == model_name.lower()
    ][0]
    print("Using model:", model["name"], "type:", model["type"])

    return model


def create_chat_completion_client(model_config) -> ChatCompletionClient:
    if model_config["type"] == "openai":
        api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "No OpenAI API key found (AZURE_OPENAI_API_KEY or OPENAI_API_KEY)"
            )
        model_client = OpenAIChatCompletionClient(
            model=model_config.get("deployment", model_config["name"]),
            api_key=api_key,
            base_url=model_config.get("api-base", None),
            api_version=model_config.get("api-version", None),  # type: ignore
            model_info=(
                ModelInfo(**model_config["info"]) if "info" in model_config else None
            ),
        )
    else:
        model_info = (
            ModelInfo(**model_config["info"]) if "info" in model_config else None
        )
        if model_config["type"] == "ollama":
            # Initialize the model client
            model_client = OllamaChatCompletionClient(
                host=model_config.get("host", "http://localhost:11434"),
                model=model_config["name"],
                model_info=model_info,
                parallel_tool_calls=False,  # type: ignore
            )
        else:
            raise ValueError(f"Unsupported model type: {model_config['type']}")
    return model_client


def current_datetime_utc_tool() -> Any:
    """Return a callable tool that provides the current date and time."""
    return datetime.utcnow().isoformat()


def get_attributes(obj):
    return [attr for attr in dir(obj) if not attr.startswith("_")]


async def get_rag_web_browser_tool():
    """
    Not recommended, use the Tavily search tool instead.
    """
    assert os.getenv("APIFY_API_KEY"), "APIFY_API_KEY environment variable is not set."
    # Setup server params for SSE access
    server_params = SseServerParams(
        url="https://rag-web-browser.apify.actor/sse",  # Removed limits from URL
        headers={"Authorization": f"Bearer {os.getenv('APIFY_API_KEY')}"},
        timeout=30,
    )

    # Create the tool adapter for the SSE server
    # Note: The tool adapter is created using the server_params and the tool name.
    # Ensure the tool name matches the one expected by the server
    # You may need to adjust this based on the actual tool name provided by the server
    rag_web_browser_tool = await SseMcpToolAdapter.from_server_params(
        server_params,
        "rag-web-browser",
    )
    return rag_web_browser_tool


def adjust_properties_for_fixed_response(props: dict, fixed_response: str) -> None:
    def provide_response_tool(question: str) -> str:
        return fixed_response

    props.update(
        {
            "system_message": "Use this tool to provide the response to any question",
            "tools": [provide_response_tool],
            "reflect_on_tool_use": False,
        }
    )


# ---------------- Tavily Search Tool -----------------
async def _tavily_search(
    query: str, max_results: int = 5, search_depth: str = "basic"
) -> Dict[str, Any]:
    """Call Tavily API and return structured search results.

    Parameters:
        query: search query string
        max_results: number of results to request (1-10 typical)
        search_depth: "basic" or "advanced" per Tavily API
    Returns:
        dict with keys: query, results (list of {title,url,content})
    """
    api_key = os.getenv("TAVILY_API_KEY")
    assert api_key, "TAVILY_API_KEY environment variable is not set."

    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "max_results": max(1, min(max_results, 10)),
        "search_depth": search_depth,
        "include_answer": False,
        "include_images": False,
        "include_raw_content": False,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    # Normalize result list
    results = []
    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "content": item.get("content"),
            }
        )
    return {"query": query, "results": results}


def _format_tavily_results(result: Dict[str, Any]) -> str:
    lines = [f"Search Query: {result['query']}", "Results:"]
    for idx, r in enumerate(result["results"], 1):
        lines.append(
            f"{idx}. {r['title']}\nURL: {r['url']}\nSnippet: {r['content'][:500]}\n"
        )
    return "\n".join(lines)


async def get_tavily_search_tool():
    """Return a callable tool for agents to perform Tavily web search."""

    async def tavily_tool(query: str, max_results: int = 5) -> str:
        result = await _tavily_search(query, max_results=max_results)
        return _format_tavily_results(result)

    # Attach simple metadata attributes (some tooling inspects these)
    tavily_tool.__name__ = "tavily_search"
    tavily_tool.__doc__ = (
        "Perform a web search via Tavily API and return top results with snippets."
    )
    return tavily_tool
