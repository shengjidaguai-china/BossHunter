"""Server-side capability boundaries for platform-specific workflows."""

PLATFORM_CAPABILITIES: dict[str, frozenset[str]] = {
    "boss": frozenset({"collect", "score", "greet", "deliver", "monitor"}),
    # Native application only: no chat monitoring or automatic resume follow-up.
    # Adapters fail closed on unknown DOM, risk signals and unverified receipts.
    "zhilian": frozenset({"collect", "score", "greet", "deliver"}),
    "51job": frozenset({"collect", "score", "greet", "deliver"}),
    "liepin": frozenset({"collect", "score", "greet", "deliver"}),
}


def platform_supports(platform: str, capability: str) -> bool:
    return capability in PLATFORM_CAPABILITIES.get(str(platform), frozenset())
