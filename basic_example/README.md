# Basic Multi-Agent Example (AutoGen)

This folder contains a minimal Jupyter Notebook (`main.ipynb`) that demonstrates a very small multi‑agent workflow using **AutoGen AgentChat**. Two assistant agents collaborate in a round‑robin group chat to produce and refine a short joke about a chosen topic.

## What It Does

1. Loads a model configuration via `load_model_config()`.
2. Defines two agents:
   - `Author` – writes a SHORT joke about the topic.
   - `SmartassEditor` – analyzes why it is (or isn’t) funny and makes it funnier without making it longer.
3. Runs a `RoundRobinGroupChat`, allowing each agent a single turn to contribute in sequence.
4. Prints the message sequence plus timing & stop info.

## Example Output

```text
MESSAGE 0 [user]:
Invent a short joke about: Animals

----------------------------------------------------------------
MESSAGE 1 [Author]:
Why don't animals play poker in the jungle? Too many cheetahs.

----------------------------------------------------------------
MESSAGE 2 [SmartassEditor]:
Why it's funny: the joke is a classic pun — "cheetahs" sounds like "cheaters" — combined with the absurd image of animals playing poker. The humor comes from the wordplay and the surprise of the literal animal answer; it's a dad-joke style gag, so it's groan-inducing rather than sophisticated.

Funnier version (shorter and punchier):
Why don't jungle animals play poker? Too many cheetahs.
```

## Quick Start

1. Activate your virtual environment in the project root.
2. Install dependencies (example with uv):

   ```bash
   uv sync
   ```

   Or with pip (editable install):

   ```bash
   pip install -e .
   ```

3. Configure model access

    OpenAI or Azure OpenAI API key require one of `OPENAI_API_KEY` or `AZURE_OPENAI_API_KEY` env variables set (loaded via `.env` if present).
    Alternatively, a local ollama server can be used with a suitable model (changed in `load_model_config()`).

4. Open `basic_example/main.ipynb` in VS Code.
5. Run cells top to bottom; final cells show each message and stop reason.

## Customizing

- Change the topic in `topic = "Animals"`.
- Add or modify roles in the `agentConfig` dict.
- Uncomment `adjust_properties_for_fixed_response(...)` for a deterministic test.
- Use a different model by modifying the `load_model_config()` function in `main.py`.

## Key Functions

- `create_chat_completion_client(model)` – constructs the model client wrapper.
- `AssistantAgent` – defines an autonomous role with a system prompt.
- `RoundRobinGroupChat` – simple orchestrator cycling agents.
- `invent_joke(topic)` – async coroutine that runs the interaction.

---

*Brief by design—see the notebook and `tools.py` for full details. The notebook closes the `model_client` explicitly (`await model_client.close()`).*
