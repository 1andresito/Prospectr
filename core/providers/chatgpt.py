from providers.openai_compatible import stream_chat_completions

CHATGPT_API_URL = "https://api.openai.com/v1/chat/completions"
CHATGPT_MODEL = "gpt-4o-mini"

MAX_OUTPUT_TOKENS = 16000


def call_streaming(prompt, api_key):
    """Yield the analysis from OpenAI's chat-completions endpoint."""
    yield from stream_chat_completions(
        CHATGPT_API_URL,
        api_key,
        CHATGPT_MODEL,
        prompt,
        MAX_OUTPUT_TOKENS,
        "ChatGPT",
    )
