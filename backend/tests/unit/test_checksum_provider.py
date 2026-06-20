"""Unit tests for checksum providers."""

from __future__ import annotations

import hashlib

from app.documents.checksum import Sha256ChecksumProvider


def test_sha256_checksum_provider_algorithm() -> None:
    provider = Sha256ChecksumProvider()

    assert provider.algorithm == "sha256"


def test_sha256_checksum_provider_compute() -> None:
    provider = Sha256ChecksumProvider()
    content = b"Employee handbook."

    digest = provider.compute(content)

    assert digest == hashlib.sha256(content).hexdigest()
    assert len(digest) == 64
