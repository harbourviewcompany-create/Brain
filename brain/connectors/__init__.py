"""Automated external observation connectors for the Brain sensory inbox."""

from .http_client import HttpClient, HttpClientError
from .http_json import HttpJsonConnector
from .protocol import (
    AccessDisposition,
    ConnectorKind,
    ConnectorSource,
    FetchResult,
    FetchStatus,
    RawObservationItem,
)
from .rss import RssConnector
from .service import IngestBatchResult, IngestService, IngestSourceResult
from .store import InMemoryConnectorRegistry

__all__ = [
    "AccessDisposition",
    "ConnectorKind",
    "ConnectorSource",
    "FetchResult",
    "FetchStatus",
    "HttpClient",
    "HttpClientError",
    "HttpJsonConnector",
    "InMemoryConnectorRegistry",
    "IngestBatchResult",
    "IngestService",
    "IngestSourceResult",
    "RawObservationItem",
    "RssConnector",
]
