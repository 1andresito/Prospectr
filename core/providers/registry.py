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

KEY_PREFIX_RULES = [
    ("sk-ant-", "claude"),
    ("nvapi-", "nvidia"),
    ("AIza", "gemini"),
    ("sk-", "chatgpt"),
]


def detect_provider(api_key):
    if not api_key:
        return None
    for prefix, provider in KEY_PREFIX_RULES:
        if api_key.startswith(prefix):
            return provider
    return None


def call_provider(provider_name, prompt, api_key):
    call_fn = PROVIDERS.get(provider_name)
    if call_fn is None:
        return None
    return call_fn(prompt, api_key)


def call_provider_streaming(provider_name, prompt, api_key):
    """Routes to the streaming version. Yields nothing for an unknown provider."""
    call_fn = PROVIDERS_STREAMING.get(provider_name)
    if call_fn is None:
        return
    yield from call_fn(prompt, api_key)