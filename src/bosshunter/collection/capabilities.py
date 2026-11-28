"""Server-side capability boundaries for platform-specific workflows."""

PLATFORM_CAPABILITIES: dict[str, frozenset[str]] = {
    "boss": frozenset({"collect", "score", "greet", "deliver", "monitor"}),
    "zhilian": frozenset({"collect", "score", "greet"}),
    "51job": frozenset({"collect", "score", "greet"}),
    "liepin": frozenset({"collect", "score", "greet"}),
}


def platform_supports(platform: str, capability: str, config: dict | None = None) -> bool:
    if capability == "monitor" and platform not in {"boss", "zhilian"}:
        return False
    if capability == "inspect_feedback" and platform not in {"51job", "zhilian"}:
        return False
    if capability not in {"deliver", "monitor", "inspect_feedback"}:
        return capability in PLATFORM_CAPABILITIES.get(platform, ())
    if platform not in PLATFORM_CAPABILITIES:
        return False
    delivery = (config or {}).get("delivery")
    delivery = delivery if isinstance(delivery, dict) else {}
    platforms = delivery.get("platforms")
    options = platforms.get(platform) if isinstance(platforms, dict) else None
    if platform == "boss":
        return not isinstance(options, dict) or options.get("enabled") is not False
    if not isinstance(options, dict):
        return False
    space = delivery.get("ego_task_space_id")
    return type(space) is int and space > 0 and options.get("enabled") is True


def delivery_capabilities(config: dict) -> dict:
    return {
        platform: {
            "enabled": platform_supports(platform, "deliver", config),
            "action_id": delivery_action(config, platform),
            "action_label": ("聊一聊：招呼语及附件简历" if platform == "liepin" and delivery_action(config, platform) == "greeting" else
                             "发招呼语" if platform == "boss" else "投递简历"),
        }
        for platform in PLATFORM_CAPABILITIES
    }


def enabled_resume_platforms(config: dict) -> tuple[str, ...]:
    return tuple(platform for platform in ("liepin", "zhilian", "51job") if platform_supports(platform, "deliver", config))


def delivery_action(config: dict, platform: str) -> str:
    if platform == "boss":
        return "greeting"
    options = config.get("delivery", {}).get("platforms", {}).get(platform, {})
    return "greeting" if platform == "liepin" and options.get("action") == "chat" else "apply_resume"
