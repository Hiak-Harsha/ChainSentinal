"""Network layer metadata enrichment: GeoIP, ASN, Organization, and Anonymizer flags."""

from __future__ import annotations

import bisect
from dataclasses import dataclass
import socket
import struct
from typing import Any

from chainsentinel.gen.network import NETWORK_POOL, NetworkInfo


def _ip_to_int(ip: str) -> int:
    """Convert dotted IPv4 string to integer."""
    try:
        return struct.unpack("!I", socket.inet_aton(ip.strip()))[0]
    except Exception:
        return 0


@dataclass(frozen=True)
class EnrichmentResult:
    country: str
    asn: str
    asn_org: str
    is_anonymizer: bool
    is_tor: bool
    is_vpn: bool
    is_hosting: bool


class GeoIpEnricher:
    """Fast in-memory IP metadata resolver using real-world ASN ranges and anonymizer lists."""

    def __init__(self, networks: list[NetworkInfo] | None = None):
        self.networks = sorted(networks or NETWORK_POOL, key=lambda n: n.ip_start)
        self._starts = [n.ip_start for n in self.networks]

    def lookup(self, ip_str: str) -> EnrichmentResult:
        """Resolve IP address to country, ASN, ISP, and anonymizer flags."""
        ip_int = _ip_to_int(ip_str)
        if ip_int == 0:
            return EnrichmentResult(
                country="UNKNOWN",
                asn="UNKNOWN",
                asn_org="Unknown",
                is_anonymizer=False,
                is_tor=False,
                is_vpn=False,
                is_hosting=False,
            )

        # Binary search for matching range
        idx = bisect.bisect_right(self._starts, ip_int) - 1
        if 0 <= idx < len(self.networks):
            net = self.networks[idx]
            if net.ip_start <= ip_int <= net.ip_end:
                is_anon = net.is_tor or net.is_vpn or net.is_hosting
                return EnrichmentResult(
                    country=net.country,
                    asn=f"AS{net.asn}",
                    asn_org=net.asn_org,
                    is_anonymizer=is_anon,
                    is_tor=net.is_tor,
                    is_vpn=net.is_vpn,
                    is_hosting=net.is_hosting,
                )

        # Default fallback
        return EnrichmentResult(
            country="ZZ",
            asn="AS0",
            asn_org="Generic Relay Node",
            is_anonymizer=False,
            is_tor=False,
            is_vpn=False,
            is_hosting=False,
        )


# Global default enricher instance
_default_enricher = GeoIpEnricher()


def enrich_record(record: dict[str, Any], enricher: GeoIpEnricher | None = None) -> dict[str, Any]:
    """Enrich observation record with geo and network metadata."""
    res = (enricher or _default_enricher).lookup(str(record.get("src_ip", "")))
    enriched = dict(record)
    # Prefer existing if already populated in file, otherwise use lookup
    if not enriched.get("src_country"):
        enriched["src_country"] = res.country
    if not enriched.get("src_asn"):
        enriched["src_asn"] = res.asn
    if not enriched.get("src_asn_org"):
        enriched["src_asn_org"] = res.asn_org
    if "is_anonymizer" not in enriched or enriched["is_anonymizer"] is None:
        enriched["is_anonymizer"] = res.is_anonymizer
    return enriched
