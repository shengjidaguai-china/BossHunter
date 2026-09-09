"""Server-side capability boundaries for platform-specific workflows."""

PLATFORM_CAPABILITIES: dict[str, frozenset[str]] = {
    "boss": frozenset({"collect", "score", "greet", "deliver", "monitor"}),
    # Zhilian and Liepin stay collection-only until a dedicated apply adapter
    # is verified. 51job can apply the existing online resume after manual
    # confirmation; it still does not monitor chats or upload attachment resumes.
    "zhilian": frozenset({"collect", "score", "greet"}),
    "51job": frozenset({"collect", "score", "greet", "deliver"}),
    "liepin": frozenset({"collect", "score", "greet"}),
}


def platform_supports(platform: str, capability: str) -> bool:
    return capability in PLATFORM_CAPABILITIES.get(str(platform), frozenset())
