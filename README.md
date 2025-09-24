# Autogen Experiments – Prototype Multi‑Agent Playground

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

## Switching LLM Provider / Model

You can change which model (and provider backend) the examples use without touching most example code. The selection logic lives in `utilities.load_model_config()` and the `resources.yaml` file.

### 1. Understand Resolution Order

`load_model_config()` picks a model using (highest precedence first):

1. Explicit argument: `load_model_config(model_name="gpt-5-mini")`
2. Environment variable: `DEFAULT_MODEL_NAME`
3. Internal fallback: `GPT-4.1-Nano` (case-insensitive match against entries in `resources.yaml`).

### 2. Edit / Extend `resources.yaml`

Each entry under `models:` defines one selectable model. Common fields:

- `name`: Identifier you pass as `model_name` (match is case-insensitive)
- `type`: `openai` (includes Azure OpenAI) or `ollama`
- `deployment`: (OpenAI/Azure) Concrete deployment name if different from `name`
- `api-base`, `api-version`: (Azure OpenAI) Endpoint + API version
- `host`: (Ollama) Base URL for local or remote Ollama server
- `info`: Optional capabilities metadata (used to build `ModelInfo`)

Add a new model by appending a block, e.g. for a local Ollama model:

```yaml
- name: "llama3.1:8b"
  type: "ollama"
  host: "http://localhost:11434"  # omit if default
  info:
    family: "llama3.1"
    vision: false
    function_calling: true
    json_output: true
```

Or an Azure OpenAI deployment (be sure the deployment exists):

```yaml
- name: "gpt-5-mini"
  type: "openai"
  deployment: "gpt-5-mini-2025-08-07"
  api-version: "2025-03-01-preview"
  api-base: "https://your-endpoint.openai.azure.com/openai/v1/"
```

### 3. Provide Credentials

- OpenAI / Azure OpenAI: set either `AZURE_OPENAI_API_KEY` (preferred for Azure) or `OPENAI_API_KEY`.
- Ollama (local): no key needed; ensure the server is running (`ollama serve`).
- Ollama (remote): ensure reachable host URL and any required network auth (not handled here).

PowerShell examples:

```powershell
$Env:AZURE_OPENAI_API_KEY = "your_azure_key"   # OR
$Env:OPENAI_API_KEY = "your_openai_key"
$Env:DEFAULT_MODEL_NAME = "gpt-5-mini"         # optional default
```

### 4. Use a Specific Model in Code

Override per run by passing `model_name`:

```python
from utilities import load_model_config, create_chat_completion_client

model_cfg = load_model_config(model_name="qwen3:0.6b")  # overrides DEFAULT_MODEL_NAME
client = create_chat_completion_client(model_cfg)
```

If you omit `model_name`, the function will look at `DEFAULT_MODEL_NAME`, otherwise fall back.

### 5. Troubleshooting

- "Unsupported model type": Check the `type` field is `openai` or `ollama`.
- Key error / list index: The `name` you requested does not exist in `resources.yaml` (spelling / indentation).
- Authentication errors: Confirm the correct API key env var is exported in the active shell / process.
- Slow or hanging Ollama model: Try a smaller variant (e.g. `qwen3:0.6b`) first.

---

*Lightweight experimental space – stability not guaranteed; iterate freely.*
