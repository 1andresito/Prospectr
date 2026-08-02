from providers import nvidia, gemini, claude, chatgpt

PROVIDERS = {
    "nvidia": nvidia.call,
    "gemini": gemini.call,
    "claude": claude.call,
    "chatgpt": chatgpt.call,
}

PROVIDERS_STREAMING = {
    "nvidia": nvidia.call_streaming,
    "gemini": gemini.call_streaming,
    "claude": claude.call_streaming,
    "chatgpt": chatgpt.call_streaming,
}


def call_provider(provider_name, prompt, api_key):
    call_fn = PROVIDERS.get(provider_name)
    if call_fn is None:
        raise ValueError(f"Unknown AI provider: {provider_name}")
    return call_fn(prompt, api_key)


def call_provider_streaming(provider_name, prompt, api_key):
    """Route to the selected provider without guessing from the API key."""
    call_fn = PROVIDERS_STREAMING.get(provider_name)
    if call_fn is None:
        raise ValueError(f"Unknown AI provider: {provider_name}")
    yield from call_fn(prompt, api_key)
