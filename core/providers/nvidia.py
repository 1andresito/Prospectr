from providers.openai_compatible import stream_chat_completions

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_MODEL = "meta/llama-3.1-70b-instruct"

MAX_OUTPUT_TOKENS = 8000


def call_streaming(prompt, api_key):
    """Yield the analysis from NVIDIA's OpenAI-compatible endpoint."""
    yield from stream_chat_completions(
        NVIDIA_API_URL,
        api_key,
        NVIDIA_MODEL,
        prompt,
        MAX_OUTPUT_TOKENS,
        "NVIDIA",
    )
