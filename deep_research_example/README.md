# Deep Research Example (Multi-Agent + Tools)

This folder contains a notebook (`deep_research.ipynb`) and sample output transcripts (`examples/`) demonstrating a structured, multi‑role deep research workflow using AutoGen AgentChat. Multiple specialized agents collaborate to research, fact‑check, critique, revise, and summarize a user query, optionally leveraging web search tooling for verification.

**Note**: Before you start tweaking this example, be aware that `AG2` now comes with a dedicated [*Deep Research Tool*](https://docs.ag2.ai/latest/docs/user-guide/reference-tools/deep-research/) that should probably be preferred.

## What It Does

1. Orchestrates a sequence of role agents (e.g., **Researcher, FactChecker, Revisor, Critic, Summarizer, Editor**).
2. Each agent adds value: proposing searches, validating claims, refining prose, identifying weaknesses, and producing a concise final answer.
3. (Optionally) invokes a **web search tool** (e.g., Tavily) for targeted fact retrieval / verification.
4. **Tracks approximate token usage** (see `token_usage_log.csv`) for observability & cost awareness.

## Quick Start

1. Activate your virtual environment at the project root.
2. Install dependencies (example with uv):

   ```bash
   uv sync
   ```

3. Export required environment keys (PowerShell example):

   ```powershell
   $Env:OPENAI_API_KEY = "your_key_here"
   $Env:TAVILY_API_KEY = "your_tavily_key"   # optional (web verification)
   ```

4. Open `deep_research_example/deep_research.ipynb` in VS Code / Jupyter.
5. Run cells top → bottom; supply or modify the research question prompt.
6. Review generated transcript messages and (optionally) inspect token usage CSV.

## Customizing

- Use a different (better) model by modifying the `load_model_config()` call or setting `DEFAULT_MODEL_NAME` in `.env` to get a better, though slower/more costly, result.
- Use a different topic by changing the `research_question` variable.
- Add/remove agent roles or adjust their system prompts (e.g., make the Critic harsher or add a SourcingAgent).
- Insert additional tools (fact check, citation extraction, entity linking) by attaching them to specific agents.
- Change termination strategy (max messages vs. content-based stopping).
- Adjust web tool query strategy to constrain max results or cost.

## Key Components

- `deep_research.ipynb` – orchestrates the multi-agent research workflow.
- `examples/` – archived example session outputs (Markdown transcripts) for different model or configuration variants.
- Role Agents – Researcher (expand problem / propose searches), FactChecker (validate or flag uncertainty), Revisor (improve structure), Critic (surface weaknesses), Summarizer/Editor (final synthesis & polish).

## Token Usage Estimation

| Scenario | What Happens |
|----------|--------------|
| Model returns OpenAI-style `usage` | Wrapped `create` accumulates exact counts |
| Model returns no usage (e.g. some local Ollama builds) | Estimation via `tiktoken` (if installed) else heuristic |
| You call `print_token_usage_with_estimate` before any native stats | It prompts you to provide messages for estimation |

Trade-off: The heuristic is coarse; use it only for order-of-magnitude comparisons.

## Interpreting Example Transcripts

Each `examples/*.md` file shows:

- Stop reason (if exposed)
- Ordered message sequence with role labels
- Raw agent commentary, tool call candidates (queries), and refinement passes

See [./examples/fme_with_gpt5-mini.md](./examples/fme_with_gpt5-mini.md) for GPT-5-mini's extensive example answer to the question "What is Fraunhofer MEVIS?" (GPT-4.1 was much less verbose).
