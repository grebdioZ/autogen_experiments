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
from unittest import result

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_core import CancellationToken
from autogen_ext.tools.mcp import StdioServerParams, mcp_server_tools
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from tools import create_chat_completion_client, load_model_config


async def run_agent(image: str, interactive: bool) -> None:
    load_dotenv()

    # FIXME: Due to a version incompatibility, you currently (opencv-mcp-server 0.1.1 with latest FastMCP)
    # need to patch
    #   mcp.server.fastmcp.server.FastMCP.__init__ to add a description parameter:
    #     description: str | None = None,
    # and use the uv run instead of uvx command so that the open CV MCP server works.
    # opencv_server = StdioServerParams(command="uvx", args=["opencv-mcp-server"])
    opencv_server = StdioServerParams(command="uv", args=["run", "opencv-mcp-server"])
    opencv_tools = await mcp_server_tools(opencv_server)

    print("opencv_tools:", [tool.name for tool in opencv_tools])

    system_message = (
        "You are a dermatology image analysis assistant with OpenCV tools. Answer "
        "questions about area, diameters, position or shape in pixel-based terms. Be concise."
    )

    model_config = load_model_config()
    model_client = create_chat_completion_client(model_config)
    agent = AssistantAgent(
        name="lesion_analyst",
        model_client=model_client,
        tools=opencv_tools,  # type: ignore
        reflect_on_tool_use=True,
        system_message=system_message,
        max_tool_iterations=10,
    )

    initial_task = Rf"Segment the lesion of the image at {image} selecting the single largest connected component on the inverted thresholding result. Save a visualization of the uncropped result in a jpg file. Then provide center position, area (px^2), major/minor diameters (px), and mean grey value in [0, 1] of the segmented object."
    result = await Console(
        agent.run_stream(task=initial_task, cancellation_token=CancellationToken())
    )

    print("Total number of messages: ", len(result.messages))
    # print("Stop reason:", result.stop_reason)  # always seems to be "None"
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
        default=R"data\HAM10000_images_part_1\ISIC_0029236_gray.jpg",
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
