"""Base connector interface for external integrations."""

from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """Abstract base for Slack, Teams, SharePoint connectors."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the external service."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the external service."""
