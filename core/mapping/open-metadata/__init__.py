"""OpenMetadata SDK mapping contracts and Oracle implementation."""

from .IOpenMetadataMapper import IOpenMetadataMapper
from .oracle_mapping import OracleMapper

__all__ = ["IOpenMetadataMapper", "OracleMapper"]
