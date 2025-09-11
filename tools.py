import os
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo, ChatCompletionClient


def create_chat_completion_client(model) -> ChatCompletionClient:
    if model["type"] == "openai":
        model_client = OpenAIChatCompletionClient(
            model=model.get("deployment", model["name"]),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            base_url=model.get("api-base", None),
            api_version=model.get("api-version", None),
            model_info=ModelInfo(**model["info"]) if "info" in model else None,
        )
    else:
        model_info = ModelInfo(**model["info"]) if "info" in model else None
        if model["type"] == "ollama":
            # Initialize the model client
            model_client = OllamaChatCompletionClient(
                model=model["name"],
                model_info=model_info,
                parallel_tool_calls=False,
            )
        else:
            raise ValueError(f"Unsupported model type: {model['type']}")
    return model_client
