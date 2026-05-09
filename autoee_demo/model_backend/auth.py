from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatGPTOAuthPlaceholder:
    """Reserved hook for a future ChatGPT Apps/Actions account-linking flow."""

    status: str = "reserved"
    display_name: str = "ChatGPT OAuth"

    def describe(self) -> str:
        return (
            "Reserved / Not used for API billing. Desktop AutoEE uses provider API keys "
            "for model calls; ChatGPT OAuth is only for a future ChatGPT app integration."
        )

