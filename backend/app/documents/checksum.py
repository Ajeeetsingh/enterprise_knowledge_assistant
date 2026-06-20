"""Checksum abstraction for document content identity."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod


class ChecksumProvider(ABC):
    """Compute content fingerprints for duplicate detection and integrity checks.

    Swappable implementations (SHA-512, BLAKE3, etc.) plug in without
    modifying the upload workflow.
    """

    @property
    @abstractmethod
    def algorithm(self) -> str:
        """Return the algorithm identifier (e.g. ``sha256``)."""

    @abstractmethod
    def compute(self, content: bytes) -> str:
        """Return a hex digest of the document content."""


class Sha256ChecksumProvider(ChecksumProvider):
    """SHA-256 checksum provider — default MVP implementation."""

    @property
    def algorithm(self) -> str:
        return "sha256"

    def compute(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
