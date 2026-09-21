"""Network layer metadata enrichment: GeoIP, ASN, Organization, and Anonymizer flags.

Queries vendored MaxMind DB (.mmdb) file offline.
Shares ONLY the .mmdb database with the generator, never a Python table.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Any
import maxminddb

logger = logging.getLogger("chainsentinel.ingest.enrichment")


def find_geoip_db_path() -> Path:
    """Locate vendored GeoIP MMDB database."""
    base_dir = Path(__file__).resolve().parent.parent
    candidates = [
        base_dir / "data" / "geoip" / "dbip-country-asn-lite.mmdb",
        Path("backend/chainsentinel/data/geoip/dbip-country-asn-lite.mmdb"),
        Path("data/geoip/dbip-country-asn-lite.mmdb"),
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FileNotFoundError(f"Vendored GeoIP MMDB file not found. Looked in: {[str(c) for c in candidates]}")


@dataclass(frozen=True)
class EnrichmentResult:
    country: str | None
    asn: str | None
    asn_org: str | None
    is_anonymizer: bool
    is_tor: bool
    is_vpn: bool
    is_hosting: bool


class GeoIpEnricher:
    """Fast offline IP metadata resolver backed by vendored MaxMind DB."""

    def __init__(self, mmdb_path: Path | None = None):
        self.db_path = mmdb_path or find_geoip_db_path()
        self._reader = maxminddb.open_database(str(self.db_path))
        self._cache: dict[str, EnrichmentResult] = {}

    def close(self) -> None:
        """Close MMDB reader."""
        if hasattr(self, "_reader") and self._reader:
            self._reader.close()

    def lookup(self, ip_str: str) -> EnrichmentResult:
        """Resolve IP address to country, ASN, ISP, and anonymizer flags."""
        ip = (ip_str or "").strip()
        if not ip:
            return EnrichmentResult(
                country=None,
                asn=None,
                asn_org=None,
                is_anonymizer=False,
                is_tor=False,
                is_vpn=False,
                is_hosting=False,
            )

        if ip in self._cache:
            return self._cache[ip]

        try:
            rec = self._reader.get(ip)
        except Exception as err:
            logger.debug("GeoIP reader lookup failed for IP %s: %s", ip, err)
            rec = None

        if rec:
            country = rec.get("country", {}).get("iso_code")
            asn_num = rec.get("autonomous_system_number")
            asn = f"AS{asn_num}" if asn_num is not None else None
            asn_org = rec.get("autonomous_system_organization")
            traits = rec.get("traits", {})
            is_tor = bool(traits.get("is_tor_exit_node", False))
            is_vpn = bool(traits.get("is_vpn", False))
            is_hosting = bool(traits.get("is_hosting_provider", False))
            is_anon = is_tor or is_vpn or is_hosting
            res = EnrichmentResult(
                country=country,
                asn=asn,
                asn_org=asn_org,
                is_anonymizer=is_anon,
                is_tor=is_tor,
                is_vpn=is_vpn,
                is_hosting=is_hosting,
            )
            self._cache[ip] = res
            return res

        # Missing lookup -> None (NULL), never fake "ZZ"
        res = EnrichmentResult(
            country=None,
            asn=None,
            asn_org=None,
            is_anonymizer=False,
            is_tor=False,
            is_vpn=False,
            is_hosting=False,
        )
        self._cache[ip] = res
        return res


# Global default enricher instance
_default_enricher: GeoIpEnricher | None = None


def get_default_enricher() -> GeoIpEnricher:
    """Lazily instantiate or return default GeoIpEnricher."""
    global _default_enricher
    if _default_enricher is None:
        _default_enricher = GeoIpEnricher()
    return _default_enricher


def enrich_record(record: dict[str, Any], enricher: GeoIpEnricher | None = None) -> dict[str, Any]:
    """Enrich observation record with geo and network metadata."""
    enr = enricher or get_default_enricher()
    res = enr.lookup(str(record.get("src_ip", "")))
    enriched = dict(record)

    # Prefer existing if already populated in file, otherwise use lookup
    if not enriched.get("src_country") and res.country:
        enriched["src_country"] = res.country
    if not enriched.get("src_asn") and res.asn:
        enriched["src_asn"] = res.asn
    if not enriched.get("src_asn_org") and res.asn_org:
        enriched["src_asn_org"] = res.asn_org
    if "is_anonymizer" not in enriched or enriched["is_anonymizer"] is None:
        enriched["is_anonymizer"] = res.is_anonymizer

    return enriched
