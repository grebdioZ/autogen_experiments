# Autogen Experiments – Prototype Multi‑Agent Playground

Exploratory sandbox for experimenting with **multi-agent LLM workflows** using the `autogen-agentchat` / `autogen-ext` stack, mixing **local Ollama models** and **Azure OpenAI** deployments, plus lightweight **token usage tracking** and **model configuration via YAML**.

⚠️ This is a **prototype / research playground** – not production software. Expect rough edges, evolving patterns, and opinionated simplifications.

---

## 1. Why This Exists

The goal is to quickly iterate on ideas for:

* Composing multiple agents (researcher, fact checker, critic, summarizer, editor, etc.)
* Swapping between local small models (e.g. `gemma3:1b`, `qwen3:0.6b`) and hosted models (`gpt-4.1-nano` via Azure OpenAI)
* Measuring / estimating token usage when native accounting isn’t exposed
* Capturing experiment artifacts (conversation transcripts, token logs)
* Keeping configuration external (YAML) while keeping the core Python surface minimal

Rather than “solve a problem,” this repository serves as a **template of patterns** for people exploring *how* to wire up multi-agent loops.

---

## 2. High-Level Architecture

```text
resources.yaml        -> Declarative list of model backends (local + hosted)
tools.py              -> create_chat_completion_client(): unified client factory
token_counting.py     -> Wrappers + heuristics for token usage tracking/logging
deep_research.ipynb   -> Interactive experiments / orchestration playground
examples/*.md         -> Raw conversation transcripts from multi-agent runs
token_usage_log.csv   -> Append-only log of usage metrics per experiment topic
```

Conceptual flow:

```text
┌────────────────┐    load / pick     ┌────────────────────────┐
│ resources.yaml │ ─────────────────▶ │ create_chat_completion │
└────────────────┘                    │  (factory)             │
                                      └─────────┬──────────────┘
                                                │ returns model client
                                      wrap for  │
                                      tokens ───▶ via wrap_chat_client_for_tokens()
                                                │
                                      orchestrate multi-agent prompts (notebook)
                                                │
                                      log_token_usage(...) → token_usage_log.csv
```

---

## 3. Key Components

### 3.1 `resources.yaml`

Defines available model endpoints. Example snippet:

```yaml
models:
    - name: "gemma3:1b"
        type: "ollama"
        info:
            family: "gemma3"
            function_calling: true
    - name: "gpt-4.1-nano"
        type: "openai"
        default: true
        deployment: "gpt-4.1-nano-2025-04-14"
        api-version: "2025-03-01-preview"
        api-base: "https://<your-azure-endpoint>/openai/v1/"
```

Add or remove entries to experiment with different providers / model families.

### 3.2 `tools.py`

Provides `create_chat_completion_client(model_dict)` which:

* Accepts a parsed dict from `resources.yaml`
* Returns an `OpenAIChatCompletionClient` or `OllamaChatCompletionClient`
* Normalizes optional `ModelInfo` metadata (e.g., capabilities) for downstream logic

Extend it if you want to support more backends (Anthropic, local server, etc.).

### 3.3 `token_counting.py`

Utilities for both **native** and **estimated** token accounting:

* `wrap_chat_client_for_tokens(client)` – monkey patches async `create` to accumulate usage (if the client returns OpenAI-style `usage` fields)
* `estimate_conversation_tokens(messages, participantNames)` – fallback using `tiktoken` if installed, else a simple heuristic (≈4 chars ≈ 1 token)
* `log_token_usage(topic, client, messages, ...)` – writes to `token_usage_log.csv`

This lets you compare real vs estimated token consumption across model mixes, even when local inference backends don’t expose usage metrics.

### 3.4 Notebooks & Examples

* `deep_research.ipynb` – primary exploration environment (multi-agent loop prototypes).
* `examples/*.md` – captured raw multi-agent transcripts. These illustrate **failure modes** and evaluation thinking, not polished outputs.

---

## 4. Getting Started

### 4.1 Prerequisites

* Python `>=3.13` (as specified in `pyproject.toml`)
* (Optional) [Ollama](https://ollama.com/) running locally for small models
* (Optional) Azure OpenAI resource + deployment (if using `type: openai` entries)
* (Recommended) `uv` or `pip` for dependency installation

### 4.2 Install Dependencies

Using `uv` (fast, resolves from `pyproject.toml` + `uv.lock`):

```pwsh
uv sync
```

Or with plain `pip`:

```pwsh
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -U pip
pip install -e .
```

### 4.3 Environment Variables

If you use Azure OpenAI entries, define:

```pwsh
$env:AZURE_OPENAI_API_KEY = "<your-key>"
```

You may also set `OLLAMA_HOST` if running Ollama remotely.

### 4.4 Launch the Notebook

```pwsh
uv run python -m ipykernel install --user --name autogen-experiments
uv run jupyter notebook  # or jupyter lab
```

Open `deep_research.ipynb` and run cells to iterate.

---

## 5. Minimal Usage (Script Style)

```python
import yaml
from tools import create_chat_completion_client
from token_counting import wrap_chat_client_for_tokens, log_token_usage

# Load first (or default) model from resources.yaml
with open("resources.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
model_cfg = next((m for m in cfg["models"] if m.get("default")), cfg["models"][0])

client = create_chat_completion_client(model_cfg)
wrap_chat_client_for_tokens(client)

messages = [
    {"role": "user", "content": "Summarize why multi-agent experimentation is useful."}
]

response = await client.create(messages=messages)  # in an async context
print(response)

# Log tokens (native if available, else estimated)
log_token_usage("trial-run", client, messages + getattr(response, "output_text", []))
```

> Note: Adjust attribute access depending on the exact response object autogen returns for the configured client version.

---

## 6. Token Usage Strategy

| Scenario | What Happens |
|----------|--------------|
| Model returns OpenAI-style `usage` | Wrapped `create` accumulates exact counts |
| Model returns no usage (e.g. some local Ollama builds) | Estimation via `tiktoken` (if installed) else heuristic |
| You call `print_token_usage_with_estimate` before any native stats | It prompts you to provide messages for estimation |

Trade-off: The heuristic is coarse; use it only for order-of-magnitude comparisons.

---

## 7. Multi-Agent Patterns (Conceptual)

Although orchestration logic lives in the notebook, typical loop structure looks like:

1. Seed a topic / research question.
2. Researcher agent drafts structured points.
3. Fact Checker critiques / annotates or adds references.
4. Critic agent flags redundancy / logical gaps.
5. Summarizer condenses.
6. Editor polishes language.
7. Repeat for N rounds or converge early if delta below a threshold.

You can evaluate **dysfunction** (e.g., stagnant outputs) by diffing successive agent turns – several `.md` examples highlight this.

---

## 8. Extending the Playground

| Goal | How |
|------|-----|
| Add a new model provider | Extend `create_chat_completion_client` with a new branch and add entry to `resources.yaml` |
| Persist full conversation JSON | Serialize agent message objects to a timestamped folder per run |
| Add automatic evaluation | Introduce a scoring agent producing structured JSON; parse & aggregate over rounds |
| Track cost $ | Map tokens → pricing per model in a cost registry; augment `log_token_usage` |
| CLI runner | Add a `cli.py` that accepts a question and runs a fixed multi-agent pipeline |

---

## 9. Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| `ValueError: Unsupported model type` | Missing branch for a new `type` | Extend factory in `tools.py` |
| Azure calls fail (401) | Missing / wrong `AZURE_OPENAI_API_KEY` | Export correct key; check permission scope |
| Ollama model not found | Not pulled locally | `ollama pull gemma3:1b` (example) |
| No token usage shown | Model didn’t return `usage` | Provide messages to estimator or switch model |
| Notebook hangs on first await | Missing `nest-asyncio` in Jupyter | Ensure dependency installed (already in `pyproject`) |

---

## 10. Design Decisions & Rationale

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| YAML for model config | Easy diff / manual edits; no code change for swapping models | Not validated against a schema yet |
| Monkey patch for usage | Zero changes to upstream clients | Fragile if method signature changes |
| Heuristic token fallback | Works w/o external deps | Inaccurate vs real tokenizer |
| Keep orchestration in notebook | Fast iteration, visual inspection | Harder to reuse headlessly |

---

## 11. Suggested Next Steps (If You Fork This)

* Add a `schema.json` (or Pydantic model) to validate `resources.yaml`
* Introduce a lightweight agent orchestration class (pure Python) to reduce notebook glue code
* Store structured run metadata (JSON) in `runs/<timestamp>/`
* Add unit tests for token accounting edge cases (empty content, alternating roles, missing roles)

---

## 12. FAQ

**Q: Is “Model Context Protocol” (MCP) a formal standard?**  
No—references in example transcripts are exploratory; treat them as conceptual framing, not an adopted spec.

**Q: Can I plug in Anthropic / Gemini / etc.?**  
Yes—add a new client import + branch in `tools.py` and a model entry in `resources.yaml`.

**Q: Why are some multi-agent runs repetitive?**  
Demonstrates *stagnation detection* and evaluation challenges; you can build heuristics to terminate early.

**Q: Is token logging accurate for local models?**  
Only if they emit usage; otherwise it’s an approximation.

---

## 13. License

Released under the **MIT License**. See the `LICENSE` file for full text.

---

## 14. Credits

Built on top of:

* `autogen-agentchat` & `autogen-ext`
* Local inference via `ollama`
* Azure OpenAI (optional)

Authored as an internal exploration; feel free to adapt & extend.

---

## 15. Quick Reference Commands

```pwsh
# Install
uv sync

# Run notebook
uv run jupyter lab

# Pull an Ollama model (example)
ollama pull gemma3:1b

# Set Azure key (PowerShell)
$env:AZURE_OPENAI_API_KEY = "<key>"
```

---

Happy experimenting! If you add interesting orchestration patterns, consider documenting them in a new `examples/` file so others can learn from successes *and* failures.
