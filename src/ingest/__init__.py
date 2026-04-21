"""Data ingestion module - Parsers for D-PLACE, Seshat, and DRH."""

from src.ingest.dplace import parse_dplace
from src.ingest.seshat import parse_seshat
from src.ingest.drh import parse_drh

__all__ = ["parse_dplace", "parse_seshat", "parse_drh"]
