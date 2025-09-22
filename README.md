# AG2 / Autogen Experiments – Prototype Multi‑Agent Playground

Collection of small experiments exploring **AutoGen AgentChat**, multi‑agent prompting patterns, tool integration (MCP + custom + web search), and research workflows. Each subfolder has its own README, but they share python environment and some utility code from the ``tools.py`` module.

## Repository Structure

- [`tool_use_example/`](tool_use_example/README.md) – Single agent using mixed MCP + native Python tools (math + optional web search) with reflection.
- [`opencv_example/`](opencv_example/README.md) – OpenCV based exploratory image processing (grayscale transforms, thresholding, contour / shape extraction).
- [`basic_example/`](basic_example/README.md) – Minimal two‑agent joke generation & refinement demo.
- [`deep_research_example/`](deep_research_example/README.md) – Multi‑role research pipeline (research, fact check, critique, summarize) with transcript + token logging.
- [`utilities/`](/utilities) – Shared utility functions for model loading, token counting, tool wrapping, etc.

## Prerequisites

- Python 3.11+ (project uses `pyproject.toml` and `uv.lock`).
- API keys for any LLM / tool providers you intend to exercise (e.g. `OPENAI_API_KEY`, `TAVILY_API_KEY`).
- (Optional) Additional keys for Apify or other MCP-integrated services if you enable those flows.

## Setup

Using `uv` (recommended):

```bash
uv sync
```

Or with `pip` (fallback):

```bash
pip install -e .
```

Export environment variables (PowerShell examples):

```powershell
$Env:OPENAI_API_KEY = "your_key"
$Env:TAVILY_API_KEY = "your_tavily_key"   # optional
```

## Quick Start

1. Pick a subfolder and open its README.md for further instructions on how to operate the notebook or script.
2. Ensure the virtual environment is active and keys are exported.
3. Inspect any generated transcripts, logs, or image artifacts.

## License

MIT (see [`LICENSE`](LICENSE)).

---

*Lightweight experimental space – stability not guaranteed; iterate freely.*

