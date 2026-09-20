"""Build a vendored GeoIP/ASN MaxMind DB (.mmdb) file for offline forensic simulation.

Compatible with DB-IP Lite / MaxMind GeoLite2 specification under CC BY 4.0.
Used exclusively by both generator and ingest enricher without sharing Python tables.
"""

from __future__ import annotations

import os
from pathlib import Path
import netaddr
from mmdb_writer import MMDBWriter

GEOIP_NETWORKS = [
    # --- United States ---
    {"prefix": "104.16.0.0/16", "asn": 13335, "org": "Cloudflare Inc.", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "52.0.0.0/16", "asn": 16509, "org": "Amazon.com Inc. (AWS)", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "35.192.0.0/16", "asn": 15169, "org": "Google LLC", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "73.0.0.0/16", "asn": 7922, "org": "Comcast Cable", "country": "US", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "68.0.0.0/16", "asn": 22773, "org": "Cox Communications", "country": "US", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "71.0.0.0/16", "asn": 20115, "org": "Charter Communications", "country": "US", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "65.24.0.0/16", "asn": 701, "org": "Verizon", "country": "US", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Germany ---
    {"prefix": "94.130.0.0/16", "asn": 24940, "org": "Hetzner Online GmbH", "country": "DE", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "87.160.0.0/16", "asn": 3320, "org": "Deutsche Telekom AG", "country": "DE", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "81.169.0.0/16", "asn": 6724, "org": "Strato AG", "country": "DE", "is_hosting": True, "is_tor": False, "is_vpn": False},
    # --- Netherlands ---
    {"prefix": "5.79.0.0/16", "asn": 60781, "org": "LeaseWeb Netherlands", "country": "NL", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "145.53.0.0/16", "asn": 1136, "org": "KPN B.V.", "country": "NL", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- France ---
    {"prefix": "51.68.0.0/16", "asn": 16276, "org": "OVH SAS", "country": "FR", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "90.0.0.0/16", "asn": 3215, "org": "Orange S.A.", "country": "FR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- United Kingdom ---
    {"prefix": "82.0.0.0/16", "asn": 5089, "org": "Virgin Media", "country": "GB", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "86.128.0.0/16", "asn": 2856, "org": "BT Group", "country": "GB", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Russia ---
    {"prefix": "95.24.0.0/16", "asn": 12389, "org": "Rostelecom", "country": "RU", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "83.149.0.0/16", "asn": 31163, "org": "MTS PJSC", "country": "RU", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- China ---
    {"prefix": "36.0.0.0/16", "asn": 4134, "org": "China Telecom", "country": "CN", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "60.0.0.0/16", "asn": 4837, "org": "China Unicom", "country": "CN", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Japan ---
    {"prefix": "106.128.0.0/16", "asn": 2516, "org": "KDDI Corporation", "country": "JP", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "129.250.0.0/16", "asn": 2914, "org": "NTT America", "country": "JP", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- India ---
    {"prefix": "117.192.0.0/16", "asn": 9829, "org": "BSNL", "country": "IN", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "49.32.0.0/16", "asn": 55836, "org": "Reliance Jio", "country": "IN", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Brazil ---
    {"prefix": "200.175.0.0/16", "asn": 7738, "org": "Telemar Norte Leste", "country": "BR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "187.0.0.0/16", "asn": 28573, "org": "Claro S.A.", "country": "BR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Canada ---
    {"prefix": "76.64.0.0/16", "asn": 577, "org": "Bell Canada", "country": "CA", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "99.224.0.0/16", "asn": 812, "org": "Rogers Communications", "country": "CA", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Australia ---
    {"prefix": "101.160.0.0/16", "asn": 1221, "org": "Telstra", "country": "AU", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Singapore ---
    {"prefix": "27.104.0.0/16", "asn": 4657, "org": "StarHub Ltd.", "country": "SG", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- South Korea ---
    {"prefix": "175.192.0.0/16", "asn": 4766, "org": "Korea Telecom", "country": "KR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Romania ---
    {"prefix": "79.112.0.0/16", "asn": 8708, "org": "RCS & RDS", "country": "RO", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Ukraine ---
    {"prefix": "176.36.0.0/16", "asn": 13188, "org": "TRIOLAN", "country": "UA", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Turkey ---
    {"prefix": "85.96.0.0/16", "asn": 9121, "org": "Turk Telekom", "country": "TR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Iran ---
    {"prefix": "5.112.0.0/16", "asn": 44244, "org": "Irancell", "country": "IR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Sweden ---
    {"prefix": "62.63.0.0/16", "asn": 1257, "org": "Tele2 Sverige AB", "country": "SE", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Switzerland ---
    {"prefix": "178.192.0.0/16", "asn": 3303, "org": "Swisscom", "country": "CH", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Finland ---
    {"prefix": "91.156.0.0/16", "asn": 1759, "org": "Telia Finland", "country": "FI", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Czech Republic ---
    {"prefix": "89.176.0.0/16", "asn": 6830, "org": "Liberty Global (UPC)", "country": "CZ", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Iceland ---
    {"prefix": "82.148.0.0/16", "asn": 6677, "org": "Vodafone Iceland", "country": "IS", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Hong Kong ---
    {"prefix": "119.236.0.0/16", "asn": 9304, "org": "HGC Global Communications", "country": "HK", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Argentina ---
    {"prefix": "181.14.0.0/16", "asn": 7303, "org": "Telecom Argentina", "country": "AR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Mexico ---
    {"prefix": "189.128.0.0/16", "asn": 8151, "org": "Telmex", "country": "MX", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Nigeria ---
    {"prefix": "196.28.0.0/16", "asn": 29465, "org": "MTN Nigeria", "country": "NG", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- South Africa ---
    {"prefix": "197.80.0.0/16", "asn": 37457, "org": "Telkom SA", "country": "ZA", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # --- Israel ---
    {"prefix": "93.172.0.0/16", "asn": 12849, "org": "Hot-Net Internet", "country": "IL", "is_hosting": False, "is_tor": False, "is_vpn": False},

    # --- Tor Exit Nodes Pool ---
    {"prefix": "185.220.100.0/24", "asn": 47674, "org": "Tor Exit Node (Quintex)", "country": "DE", "is_hosting": False, "is_tor": True, "is_vpn": False},
    {"prefix": "185.220.101.0/24", "asn": 47674, "org": "Tor Exit Node (Quintex)", "country": "DE", "is_hosting": False, "is_tor": True, "is_vpn": False},
    {"prefix": "185.220.102.0/24", "asn": 200052, "org": "Tor Exit Node (F3Netze)", "country": "DE", "is_hosting": False, "is_tor": True, "is_vpn": False},
    {"prefix": "77.247.181.0/24", "asn": 60729, "org": "Tor Exit Node (Stichting)", "country": "NL", "is_hosting": False, "is_tor": True, "is_vpn": False},
    {"prefix": "176.9.0.0/24", "asn": 51167, "org": "Tor Exit Node (Contabo)", "country": "DE", "is_hosting": False, "is_tor": True, "is_vpn": False},

    # --- VPN & Commercial Hosting Pool ---
    {"prefix": "37.120.0.0/16", "asn": 9009, "org": "M247 Ltd (VPN)", "country": "RO", "is_hosting": False, "is_tor": False, "is_vpn": True},
    {"prefix": "45.76.0.0/16", "asn": 20473, "org": "Vultr Holdings (VPN/hosting)", "country": "NL", "is_hosting": True, "is_tor": False, "is_vpn": True},
    {"prefix": "149.28.0.0/16", "asn": 20473, "org": "Vultr Holdings (VPN/hosting)", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": True},
    {"prefix": "164.90.0.0/16", "asn": 14061, "org": "DigitalOcean LLC", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": True},
    {"prefix": "138.68.0.0/16", "asn": 14061, "org": "DigitalOcean LLC", "country": "DE", "is_hosting": True, "is_tor": False, "is_vpn": True},
]


def build_mmdb(output_path: Path) -> None:
    """Build a compliant .mmdb file containing network records."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = MMDBWriter(ip_version=4)

    for net in GEOIP_NETWORKS:
        ip_net = netaddr.IPNetwork(net["prefix"])
        ip_set = netaddr.IPSet([ip_net])
        record = {
            "country": {
                "iso_code": net["country"],
            },
            "autonomous_system_number": net["asn"],
            "autonomous_system_organization": net["org"],
            "traits": {
                "is_hosting_provider": net["is_hosting"],
                "is_tor_exit_node": net["is_tor"],
                "is_vpn": net["is_vpn"],
            },
            "network": net["prefix"],
        }
        writer.insert_network(ip_set, record)

    writer.to_db_file(str(output_path))
    print(f"[GeoIP Build] Successfully generated {output_path} with {len(GEOIP_NETWORKS)} networks.")


if __name__ == "__main__":
    out_file = Path("backend/chainsentinel/data/geoip/dbip-country-asn-lite.mmdb")
    build_mmdb(out_file)
