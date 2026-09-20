"""Realistic IP/ASN/Country simulation backed by vendored MaxMind DB (.mmdb).

Uses real-world ASN ranges and MaxMind DB format so that GeoIP enrichment
produces realistic country/ASN results. Never uses documentation ranges
(192.0.2.x, 198.51.100.x, 203.0.113.x).
The enricher and generator share only the .mmdb database file, never a Python table.
"""

from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import maxminddb
from numpy.random import Generator


def _ip_to_int(ip: str) -> int:
    """Convert dotted IP string to integer."""
    return struct.unpack("!I", socket.inet_aton(ip.strip()))[0]


def _int_to_ip(n: int) -> str:
    """Convert integer to dotted IP string."""
    return socket.inet_ntoa(struct.pack("!I", n))


@dataclass(frozen=True)
class NetworkInfo:
    """Network info for an IP range retrieved from MMDB."""

    asn: int
    asn_org: str
    country: str
    prefix: str
    is_hosting: bool = False
    is_tor: bool = False
    is_vpn: bool = False


# Known CIDR blocks indexed in the vendored dbip-country-asn-lite.mmdb database
MMDB_PREFIXES: list[dict[str, Any]] = [
    # United States
    {"prefix": "104.16.0.0/16", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "52.0.0.0/16", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "35.192.0.0/16", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "73.0.0.0/16", "country": "US", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "68.0.0.0/16", "country": "US", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "71.0.0.0/16", "country": "US", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "65.24.0.0/16", "country": "US", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Germany
    {"prefix": "94.130.0.0/16", "country": "DE", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "87.160.0.0/16", "country": "DE", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "81.169.0.0/16", "country": "DE", "is_hosting": True, "is_tor": False, "is_vpn": False},
    # Netherlands
    {"prefix": "5.79.0.0/16", "country": "NL", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "145.53.0.0/16", "country": "NL", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # France
    {"prefix": "51.68.0.0/16", "country": "FR", "is_hosting": True, "is_tor": False, "is_vpn": False},
    {"prefix": "90.0.0.0/16", "country": "FR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # United Kingdom
    {"prefix": "82.0.0.0/16", "country": "GB", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "86.128.0.0/16", "country": "GB", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Russia
    {"prefix": "95.24.0.0/16", "country": "RU", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "83.149.0.0/16", "country": "RU", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # China
    {"prefix": "36.0.0.0/16", "country": "CN", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "60.0.0.0/16", "country": "CN", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Japan
    {"prefix": "106.128.0.0/16", "country": "JP", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "129.250.0.0/16", "country": "JP", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # India
    {"prefix": "117.192.0.0/16", "country": "IN", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "49.32.0.0/16", "country": "IN", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Brazil
    {"prefix": "200.175.0.0/16", "country": "BR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "187.0.0.0/16", "country": "BR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Canada
    {"prefix": "76.64.0.0/16", "country": "CA", "is_hosting": False, "is_tor": False, "is_vpn": False},
    {"prefix": "99.224.0.0/16", "country": "CA", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Australia
    {"prefix": "101.160.0.0/16", "country": "AU", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Singapore
    {"prefix": "27.104.0.0/16", "country": "SG", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # South Korea
    {"prefix": "175.192.0.0/16", "country": "KR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Romania
    {"prefix": "79.112.0.0/16", "country": "RO", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Ukraine
    {"prefix": "176.36.0.0/16", "country": "UA", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Turkey
    {"prefix": "85.96.0.0/16", "country": "TR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Iran
    {"prefix": "5.112.0.0/16", "country": "IR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Sweden
    {"prefix": "62.63.0.0/16", "country": "SE", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Switzerland
    {"prefix": "178.192.0.0/16", "country": "CH", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Finland
    {"prefix": "91.156.0.0/16", "country": "FI", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Czech Republic
    {"prefix": "89.176.0.0/16", "country": "CZ", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Iceland
    {"prefix": "82.148.0.0/16", "country": "IS", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Hong Kong
    {"prefix": "119.236.0.0/16", "country": "HK", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Argentina
    {"prefix": "181.14.0.0/16", "country": "AR", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Mexico
    {"prefix": "189.128.0.0/16", "country": "MX", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Nigeria
    {"prefix": "196.28.0.0/16", "country": "NG", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # South Africa
    {"prefix": "197.80.0.0/16", "country": "ZA", "is_hosting": False, "is_tor": False, "is_vpn": False},
    # Israel
    {"prefix": "93.172.0.0/16", "country": "IL", "is_hosting": False, "is_tor": False, "is_vpn": False},

    # Tor Exit Nodes Pool
    {"prefix": "185.220.100.0/24", "country": "DE", "is_hosting": False, "is_tor": True, "is_vpn": False},
    {"prefix": "185.220.101.0/24", "country": "DE", "is_hosting": False, "is_tor": True, "is_vpn": False},
    {"prefix": "185.220.102.0/24", "country": "DE", "is_hosting": False, "is_tor": True, "is_vpn": False},
    {"prefix": "77.247.181.0/24", "country": "NL", "is_hosting": False, "is_tor": True, "is_vpn": False},
    {"prefix": "176.9.0.0/24", "country": "DE", "is_hosting": False, "is_tor": True, "is_vpn": False},

    # VPN & Commercial Hosting Pool
    {"prefix": "37.120.0.0/16", "country": "RO", "is_hosting": False, "is_tor": False, "is_vpn": True},
    {"prefix": "45.76.0.0/16", "country": "NL", "is_hosting": True, "is_tor": False, "is_vpn": True},
    {"prefix": "149.28.0.0/16", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": True},
    {"prefix": "164.90.0.0/16", "country": "US", "is_hosting": True, "is_tor": False, "is_vpn": True},
    {"prefix": "138.68.0.0/16", "country": "DE", "is_hosting": True, "is_tor": False, "is_vpn": True},
]


def find_geoip_db_path() -> Path:
    """Find the vendored GeoIP MMDB database."""
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


class NetworkSimulator:
    """Manages IP allocation and network relay simulation using vendored MMDB."""

    def __init__(
        self,
        rng: Generator,
        n_sensors: int = 5,
        n_relay_nodes: int = 200,
        mmdb_path: Path | None = None,
    ):
        self.rng = rng
        self.n_sensors = max(5, n_sensors)
        self.n_relay_nodes = n_relay_nodes

        db_file = mmdb_path or find_geoip_db_path()
        self.mmdb_reader = maxminddb.open_database(str(db_file))

        # Sensor vantage points
        standard_prefixes = [p for p in MMDB_PREFIXES if not p["is_hosting"] and not p["is_tor"] and not p["is_vpn"]]
        sensor_choice = self.rng.choice(
            standard_prefixes,
            size=min(self.n_sensors, len(standard_prefixes)),
            replace=False,
        )
        self.sensor_ids = [f"sensor_{i}" for i in range(len(sensor_choice))]
        self.sensor_ips = [self._sample_ip_from_prefix(p["prefix"]) for p in sensor_choice]
        self.sensor_map = {sid: ip for sid, ip in zip(self.sensor_ids, self.sensor_ips)}
        self.ip_to_sensor = {ip: sid for sid, ip in zip(self.sensor_ids, self.sensor_ips)}

        # Relay nodes (drawn across diverse global ranges)
        relay_choice = self.rng.choice(MMDB_PREFIXES, size=n_relay_nodes, replace=True)
        self.relay_ips = [self._sample_ip_from_prefix(p["prefix"]) for p in relay_choice]

        # Internal cache of IP metadata
        self._ip_cache: dict[str, NetworkInfo] = {}
        for ip in self.sensor_ips + self.relay_ips:
            self._lookup_and_cache(ip)

    def close(self) -> None:
        """Close reader database."""
        if hasattr(self, "mmdb_reader") and self.mmdb_reader:
            self.mmdb_reader.close()

    def _sample_ip_from_prefix(self, prefix: str) -> str:
        """Sample an IP inside a CIDR prefix."""
        ip_str, mask_str = prefix.split("/")
        mask = int(mask_str)
        ip_int = _ip_to_int(ip_str)
        host_bits = 32 - mask
        num_hosts = 1 << host_bits
        offset = int(self.rng.integers(2, max(3, num_hosts - 2)))
        return _int_to_ip(ip_int + offset)

    def _lookup_and_cache(self, ip: str) -> NetworkInfo:
        """Query MMDB for an IP and cache."""
        if ip in self._ip_cache:
            return self._ip_cache[ip]

        rec = self.mmdb_reader.get(ip)
        if rec:
            country = rec.get("country", {}).get("iso_code", "US")
            asn_num = rec.get("autonomous_system_number", 0)
            asn_org = rec.get("autonomous_system_organization", "Unknown ISP")
            traits = rec.get("traits", {})
            net_info = NetworkInfo(
                asn=asn_num,
                asn_org=asn_org,
                country=country,
                prefix=rec.get("network", f"{ip}/32"),
                is_hosting=traits.get("is_hosting_provider", False),
                is_tor=traits.get("is_tor_exit_node", False),
                is_vpn=traits.get("is_vpn", False),
            )
        else:
            net_info = NetworkInfo(
                asn=0,
                asn_org="Generic Node",
                country="US",
                prefix=f"{ip}/32",
            )
        self._ip_cache[ip] = net_info
        return net_info

    def get_network_info(self, ip: str) -> NetworkInfo | None:
        """Look up network info for an IP from MMDB."""
        return self._lookup_and_cache(ip)

    def allocate_entity_ip(
        self,
        country_hint: str | None = None,
        use_tor: bool | None = None,
        use_vpn: bool | None = None,
        is_illicit: bool = False,
        obfuscation_level: int = 0,
        archetype: str | None = None,
    ) -> tuple[str, NetworkInfo]:
        """Allocate an IP for an entity operator.

        Removes the deterministic leak:
        - Obfuscation level does NOT perfectly correlate with IP class.
        - Some legit entities use VPN/hosting/Tor (tech users, merchants, exchanges).
        - Some illicit actors use direct residential/mobile IPs.
        """
        # Determine pool category probabilistically if not explicitly forced
        target_tor = use_tor
        target_vpn = use_vpn
        target_hosting = False

        if target_tor is None and target_vpn is None:
            r = float(self.rng.random())
            if is_illicit:
                # Illicit obfuscation levels 0-3
                if obfuscation_level == 0:
                    # Level 0: mostly direct residential/mobile, occasional VPN
                    if r < 0.12:
                        target_vpn = True
                elif obfuscation_level == 1:
                    # Level 1: 50% VPN, 10% Tor, 40% standard
                    if r < 0.50:
                        target_vpn = True
                    elif r < 0.60:
                        target_tor = True
                elif obfuscation_level == 2:
                    # Level 2: 60% VPN/hosting, 25% Tor, 15% standard
                    if r < 0.60:
                        target_vpn = True
                    elif r < 0.85:
                        target_tor = True
                else:
                    # Level 3: 50% Tor, 40% VPN/hosting, 10% standard
                    if r < 0.50:
                        target_tor = True
                    elif r < 0.90:
                        target_vpn = True
            else:
                # Legit entity archetypes
                if archetype in ("exchange_hot", "exchange_cold"):
                    # Exchanges run on cloud hosting (AWS, Google, Hetzner, etc.)
                    target_hosting = True
                elif archetype == "custodial":
                    if r < 0.75:
                        target_hosting = True
                    elif r < 0.90:
                        target_vpn = True
                elif archetype == "merchant":
                    if r < 0.35:
                        target_hosting = True
                    elif r < 0.55:
                        target_vpn = True
                elif archetype == "gambling":
                    if r < 0.40:
                        target_hosting = True
                    elif r < 0.70:
                        target_vpn = True
                elif archetype == "mining_pool":
                    if r < 0.70:
                        target_hosting = True
                elif archetype == "retail":
                    # Retail crypto users frequently use VPNs or privacy tools!
                    if r < 0.18:
                        target_vpn = True
                    elif r < 0.22:
                        target_tor = True

        # Filter prefixes based on resolved category
        if target_tor:
            candidates = [p for p in MMDB_PREFIXES if p["is_tor"]]
        elif target_vpn:
            candidates = [p for p in MMDB_PREFIXES if p["is_vpn"]]
        elif target_hosting:
            candidates = [p for p in MMDB_PREFIXES if p["is_hosting"]]
        elif country_hint:
            candidates = [p for p in MMDB_PREFIXES if p["country"] == country_hint]
            if not candidates:
                candidates = [p for p in MMDB_PREFIXES if not p["is_tor"]]
        else:
            candidates = [p for p in MMDB_PREFIXES if not p["is_tor"] and not p["is_vpn"]]

        if not candidates:
            candidates = MMDB_PREFIXES

        selected_prefix = self.rng.choice(candidates)
        ip = self._sample_ip_from_prefix(selected_prefix["prefix"])
        net_info = self._lookup_and_cache(ip)
        return ip, net_info

    def allocate_multiple_ips(
        self,
        count: int,
        country_hint: str | None = None,
        use_vpn: bool | None = None,
        is_illicit: bool = False,
        obfuscation_level: int = 0,
        archetype: str | None = None,
    ) -> list[tuple[str, NetworkInfo]]:
        """Allocate multiple IPs for an entity with IP rotation."""
        return [
            self.allocate_entity_ip(
                country_hint=country_hint,
                use_vpn=use_vpn,
                is_illicit=is_illicit,
                obfuscation_level=obfuscation_level,
                archetype=archetype,
            )
            for _ in range(count)
        ]

    def simulate_relay(
        self,
        origin_ip: str,
        origin_ts: float,
        relay_mean_delay: float = 2.0,
        gossip_mean_delay: float = 5.0,
    ) -> list[dict]:
        """Simulate P2P relay propagation from an origin node using Poisson trickling.

        Returns a list of observations as seen by sensor nodes.
        Each observation contains:
        - sensor_id: ID of the observing sensor (sensor_0, sensor_1, ...)
        - timestamp: arrival timestamp at sensor
        - src_ip: IP of the peer that delivered the INV/tx to the sensor
        - dst_ip: IP of the sensor node
        - src_port: ephemeral source port
        - dst_port: destination port (8333)
        """
        observations = []

        # Number of outbound connections from origin (Bitcoin Core: 8)
        n_direct_relays = min(8, self.n_relay_nodes)
        direct_indices = self.rng.choice(len(self.relay_ips), size=n_direct_relays, replace=False)

        # Poisson trickling from origin
        relay_arrival_times: dict[str, float] = {origin_ip: origin_ts}
        for idx in direct_indices:
            # Poisson arrival interval
            delay = float(self.rng.exponential(relay_mean_delay))
            relay_ip = self.relay_ips[idx]
            relay_arrival_times[relay_ip] = origin_ts + delay

        # Gossip diffusion to secondary peers
        n_gossip = min(35, self.n_relay_nodes)
        gossip_indices = self.rng.choice(len(self.relay_ips), size=n_gossip, replace=True)
        for idx in gossip_indices:
            relay_ip = self.relay_ips[idx]
            if relay_ip not in relay_arrival_times:
                hop_delay = float(self.rng.exponential(gossip_mean_delay)) + float(self.rng.exponential(relay_mean_delay))
                relay_arrival_times[relay_ip] = origin_ts + hop_delay

        # Probability of direct sensor peering with origin (e.g. 20%)
        sensor_direct_peered = self.rng.random() < 0.20
        direct_sensor_idx = int(self.rng.integers(0, len(self.sensor_ids))) if sensor_direct_peered else -1

        # Each sensor node observes via its peer connections
        for idx, (sensor_id, sensor_ip) in enumerate(zip(self.sensor_ids, self.sensor_ips)):
            if idx == direct_sensor_idx:
                # Sensor directly peered with the origin!
                jitter = float(self.rng.exponential(0.15))
                obs_time = origin_ts + jitter
                src_ip = origin_ip
            else:
                # Sensor connects to random relays from active set
                n_peers = min(8, len(relay_arrival_times))
                peer_relays = self.rng.choice(list(relay_arrival_times.keys()), size=n_peers, replace=False)

                best_time = float("inf")
                best_relay = str(peer_relays[0])
                for r_ip in peer_relays:
                    arrival = relay_arrival_times[r_ip]
                    jitter = float(self.rng.exponential(0.40))  # ~400ms network jitter
                    t = arrival + jitter
                    if t < best_time:
                        best_time = t
                        best_relay = r_ip

                obs_time = best_time
                src_ip = best_relay

            src_port = int(self.rng.integers(1024, 65535))
            observations.append({
                "sensor_id": sensor_id,
                "timestamp": round(obs_time, 4),
                "src_ip": src_ip,
                "dst_ip": sensor_ip,
                "src_port": src_port,
                "dst_port": 8333,
            })

        return observations
