"""Main script: single-shot or interactive lesion image analysis via OpenCV MCP tools.

Usage examples:
  uv run python main.py --image data/HAM10000_images_part_1/ISIC_0024306.jpg
  uv run python main.py --image data/HAM10000_images_part_1/ISIC_0024306.jpg --interactive
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from venv import create

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools import create_chat_completion_client, load_model_config


async def run_agent(image: str, interactive: bool) -> None:
    load_dotenv()
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "No OpenAI API key found (AZURE_OPENAI_API_KEY or OPENAI_API_KEY)"
        )

    opencv_server = StdioServerParams(command="uvx", args=["opencv-mcp-server"])
    opencv_tools = await mcp_server_tools(opencv_server)

    print("opencv_tools:", [tool.name for tool in opencv_tools])

    system_message = (
        "You are a dermatology image analysis assistant with OpenCV tools. Always first segment the lesion, then answer "
        "questions about area, diameters, color, and shape in pixel-based terms. Be concise. If classification is requested, "
        "note that a classifier is not yet integrated."
    )

    model_config = load_model_config()
    model_client = create_chat_completion_client(model_config)
    agent = AssistantAgent(
        name="lesion_analyst",
        model_client=model_client,
        tools=opencv_tools,
        reflect_on_tool_use=True,
        system_message=system_message,
    )

    initial_task = f"Detect and segment the lesion using a DNN in the image at: {image}. Save a visualization of the result in a jpg file in the C:\dev\git\skin_lesion_classification\results folder. Then provide area (px^2), major/minor diameters (px), and mean BGR color."
    await Console(
        agent.run_stream(task=initial_task, cancellation_token=CancellationToken())
    )

    if not interactive:
        return

    print("\nInteractive mode. Ask follow-up questions (type 'exit' to quit).")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue
        await Console(agent.run_stream(task=q, cancellation_token=CancellationToken()))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lesion image analysis (OpenCV MCP + AutoGen)"
    )
    parser.add_argument(
        "--image",
        required=False,
        default=R"data\HAM10000_images_part_1\ISIC_0029236.jpg",
        help="Path to lesion image",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter interactive Q&A mode after initial summary",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    if not os.path.exists(args.image):
        raise FileNotFoundError(args.image)
    await run_agent(args.image, args.interactive)


if __name__ == "__main__":  # pragma: no cover
    asyncio.run(main())
