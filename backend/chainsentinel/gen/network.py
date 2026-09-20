"""Realistic IP/ASN/Country pool for synthetic network simulation.

Uses real-world ASN ranges so that GeoIP enrichment produces
realistic country/ASN results. Never uses documentation ranges
(192.0.2.x, 198.51.100.x, 203.0.113.x).
"""

from __future__ import annotations

import struct
import socket
from dataclasses import dataclass
from numpy.random import Generator


@dataclass(frozen=True)
class NetworkInfo:
    """Network info for an IP range."""

    asn: int
    asn_org: str
    country: str
    prefix: str  # e.g. "104.16.0.0/16"
    ip_start: int  # integer form of start IP
    ip_end: int    # integer form of end IP
    is_hosting: bool = False
    is_tor: bool = False
    is_vpn: bool = False


def _ip_to_int(ip: str) -> int:
    """Convert dotted IP string to integer."""
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def _int_to_ip(n: int) -> int | str:
    """Convert integer to dotted IP string."""
    return socket.inet_ntoa(struct.pack("!I", n))


# ~50 realistic ASN/Country/IP combos covering major geographies
# These are real-world ranges that will produce realistic GeoIP lookups
NETWORK_POOL: list[NetworkInfo] = [
    # --- United States ---
    NetworkInfo(13335, "Cloudflare Inc.", "US", "104.16.0.0/16",
                _ip_to_int("104.16.0.0"), _ip_to_int("104.16.255.255"), is_hosting=True),
    NetworkInfo(16509, "Amazon.com Inc. (AWS)", "US", "52.0.0.0/16",
                _ip_to_int("52.0.0.0"), _ip_to_int("52.0.255.255"), is_hosting=True),
    NetworkInfo(15169, "Google LLC", "US", "35.192.0.0/16",
                _ip_to_int("35.192.0.0"), _ip_to_int("35.192.255.255"), is_hosting=True),
    NetworkInfo(7922, "Comcast Cable", "US", "73.0.0.0/16",
                _ip_to_int("73.0.0.0"), _ip_to_int("73.0.255.255")),
    NetworkInfo(22773, "Cox Communications", "US", "68.0.0.0/16",
                _ip_to_int("68.0.0.0"), _ip_to_int("68.0.255.255")),
    NetworkInfo(20115, "Charter Communications", "US", "71.0.0.0/16",
                _ip_to_int("71.0.0.0"), _ip_to_int("71.0.255.255")),
    NetworkInfo(701, "Verizon", "US", "65.24.0.0/16",
                _ip_to_int("65.24.0.0"), _ip_to_int("65.24.255.255")),

    # --- Germany ---
    NetworkInfo(24940, "Hetzner Online GmbH", "DE", "94.130.0.0/16",
                _ip_to_int("94.130.0.0"), _ip_to_int("94.130.255.255"), is_hosting=True),
    NetworkInfo(3320, "Deutsche Telekom AG", "DE", "87.160.0.0/16",
                _ip_to_int("87.160.0.0"), _ip_to_int("87.160.255.255")),
    NetworkInfo(6724, "Strato AG", "DE", "81.169.0.0/16",
                _ip_to_int("81.169.0.0"), _ip_to_int("81.169.255.255"), is_hosting=True),

    # --- Netherlands ---
    NetworkInfo(60781, "LeaseWeb Netherlands", "NL", "5.79.0.0/16",
                _ip_to_int("5.79.0.0"), _ip_to_int("5.79.255.255"), is_hosting=True),
    NetworkInfo(1136, "KPN B.V.", "NL", "145.53.0.0/16",
                _ip_to_int("145.53.0.0"), _ip_to_int("145.53.255.255")),

    # --- France ---
    NetworkInfo(16276, "OVH SAS", "FR", "51.68.0.0/16",
                _ip_to_int("51.68.0.0"), _ip_to_int("51.68.255.255"), is_hosting=True),
    NetworkInfo(3215, "Orange S.A.", "FR", "90.0.0.0/16",
                _ip_to_int("90.0.0.0"), _ip_to_int("90.0.255.255")),

    # --- United Kingdom ---
    NetworkInfo(5089, "Virgin Media", "GB", "82.0.0.0/16",
                _ip_to_int("82.0.0.0"), _ip_to_int("82.0.255.255")),
    NetworkInfo(2856, "BT Group", "GB", "86.128.0.0/16",
                _ip_to_int("86.128.0.0"), _ip_to_int("86.128.255.255")),

    # --- Russia ---
    NetworkInfo(12389, "Rostelecom", "RU", "95.24.0.0/16",
                _ip_to_int("95.24.0.0"), _ip_to_int("95.24.255.255")),
    NetworkInfo(31163, "MTS PJSC", "RU", "83.149.0.0/16",
                _ip_to_int("83.149.0.0"), _ip_to_int("83.149.255.255")),

    # --- China ---
    NetworkInfo(4134, "China Telecom", "CN", "36.0.0.0/16",
                _ip_to_int("36.0.0.0"), _ip_to_int("36.0.255.255")),
    NetworkInfo(4837, "China Unicom", "CN", "60.0.0.0/16",
                _ip_to_int("60.0.0.0"), _ip_to_int("60.0.255.255")),

    # --- Japan ---
    NetworkInfo(2516, "KDDI Corporation", "JP", "106.128.0.0/16",
                _ip_to_int("106.128.0.0"), _ip_to_int("106.128.255.255")),
    NetworkInfo(2914, "NTT America", "JP", "129.250.0.0/16",
                _ip_to_int("129.250.0.0"), _ip_to_int("129.250.255.255")),

    # --- India ---
    NetworkInfo(9829, "BSNL", "IN", "117.192.0.0/16",
                _ip_to_int("117.192.0.0"), _ip_to_int("117.192.255.255")),
    NetworkInfo(55836, "Reliance Jio", "IN", "49.32.0.0/16",
                _ip_to_int("49.32.0.0"), _ip_to_int("49.32.255.255")),

    # --- Brazil ---
    NetworkInfo(7738, "Telemar Norte Leste", "BR", "200.175.0.0/16",
                _ip_to_int("200.175.0.0"), _ip_to_int("200.175.255.255")),
    NetworkInfo(28573, "Claro S.A.", "BR", "187.0.0.0/16",
                _ip_to_int("187.0.0.0"), _ip_to_int("187.0.255.255")),

    # --- Canada ---
    NetworkInfo(577, "Bell Canada", "CA", "76.64.0.0/16",
                _ip_to_int("76.64.0.0"), _ip_to_int("76.64.255.255")),
    NetworkInfo(812, "Rogers Communications", "CA", "99.224.0.0/16",
                _ip_to_int("99.224.0.0"), _ip_to_int("99.224.255.255")),

    # --- Australia ---
    NetworkInfo(1221, "Telstra", "AU", "101.160.0.0/16",
                _ip_to_int("101.160.0.0"), _ip_to_int("101.160.255.255")),

    # --- Singapore ---
    NetworkInfo(4657, "StarHub Ltd.", "SG", "27.104.0.0/16",
                _ip_to_int("27.104.0.0"), _ip_to_int("27.104.255.255")),

    # --- South Korea ---
    NetworkInfo(4766, "Korea Telecom", "KR", "175.192.0.0/16",
                _ip_to_int("175.192.0.0"), _ip_to_int("175.192.255.255")),

    # --- Romania (common for hosting) ---
    NetworkInfo(8708, "RCS & RDS", "RO", "79.112.0.0/16",
                _ip_to_int("79.112.0.0"), _ip_to_int("79.112.255.255")),

    # --- Ukraine ---
    NetworkInfo(13188, "TRIOLAN", "UA", "176.36.0.0/16",
                _ip_to_int("176.36.0.0"), _ip_to_int("176.36.255.255")),

    # --- Turkey ---
    NetworkInfo(9121, "Turk Telekom", "TR", "85.96.0.0/16",
                _ip_to_int("85.96.0.0"), _ip_to_int("85.96.255.255")),

    # --- Iran ---
    NetworkInfo(44244, "Irancell", "IR", "5.112.0.0/16",
                _ip_to_int("5.112.0.0"), _ip_to_int("5.112.255.255")),

    # --- Sweden ---
    NetworkInfo(1257, "Tele2 Sverige AB", "SE", "62.63.0.0/16",
                _ip_to_int("62.63.0.0"), _ip_to_int("62.63.255.255")),

    # --- Switzerland ---
    NetworkInfo(3303, "Swisscom", "CH", "178.192.0.0/16",
                _ip_to_int("178.192.0.0"), _ip_to_int("178.192.255.255")),

    # --- Finland ---
    NetworkInfo(1759, "Telia Finland", "FI", "91.156.0.0/16",
                _ip_to_int("91.156.0.0"), _ip_to_int("91.156.255.255")),

    # --- Czech Republic ---
    NetworkInfo(6830, "Liberty Global (UPC)", "CZ", "89.176.0.0/16",
                _ip_to_int("89.176.0.0"), _ip_to_int("89.176.255.255")),

    # --- Iceland (common for Bitcoin nodes) ---
    NetworkInfo(6677, "Vodafone Iceland", "IS", "82.148.0.0/16",
                _ip_to_int("82.148.0.0"), _ip_to_int("82.148.255.255")),

    # --- Hong Kong ---
    NetworkInfo(9304, "HGC Global Communications", "HK", "119.236.0.0/16",
                _ip_to_int("119.236.0.0"), _ip_to_int("119.236.255.255")),

    # --- Argentina ---
    NetworkInfo(7303, "Telecom Argentina", "AR", "181.14.0.0/16",
                _ip_to_int("181.14.0.0"), _ip_to_int("181.14.255.255")),

    # --- Mexico ---
    NetworkInfo(8151, "Telmex", "MX", "189.128.0.0/16",
                _ip_to_int("189.128.0.0"), _ip_to_int("189.128.255.255")),

    # --- Nigeria ---
    NetworkInfo(29465, "MTN Nigeria", "NG", "196.28.0.0/16",
                _ip_to_int("196.28.0.0"), _ip_to_int("196.28.255.255")),

    # --- South Africa ---
    NetworkInfo(37457, "Telkom SA", "ZA", "197.80.0.0/16",
                _ip_to_int("197.80.0.0"), _ip_to_int("197.80.255.255")),

    # --- Israel ---
    NetworkInfo(12849, "Hot-Net Internet", "IL", "93.172.0.0/16",
                _ip_to_int("93.172.0.0"), _ip_to_int("93.172.255.255")),
]

# Tor exit nodes pool — dedicated IPs that will be flagged as Tor
TOR_EXIT_POOL: list[NetworkInfo] = [
    NetworkInfo(47674, "Tor Exit Node (Quintex)", "DE", "185.220.100.0/24",
                _ip_to_int("185.220.100.0"), _ip_to_int("185.220.100.255"), is_tor=True),
    NetworkInfo(47674, "Tor Exit Node (Quintex)", "DE", "185.220.101.0/24",
                _ip_to_int("185.220.101.0"), _ip_to_int("185.220.101.255"), is_tor=True),
    NetworkInfo(200052, "Tor Exit Node (F3Netze)", "DE", "185.220.102.0/24",
                _ip_to_int("185.220.102.0"), _ip_to_int("185.220.102.255"), is_tor=True),
    NetworkInfo(60729, "Tor Exit Node (Stichting)", "NL", "77.247.181.0/24",
                _ip_to_int("77.247.181.0"), _ip_to_int("77.247.181.255"), is_tor=True),
    NetworkInfo(51167, "Tor Exit Node (Contabo)", "DE", "176.9.0.0/24",
                _ip_to_int("176.9.0.0"), _ip_to_int("176.9.0.255"), is_tor=True),
]

# VPN/hosting ranges used by obfuscated illicit actors
VPN_POOL: list[NetworkInfo] = [
    NetworkInfo(9009, "M247 Ltd (VPN)", "RO", "37.120.0.0/16",
                _ip_to_int("37.120.0.0"), _ip_to_int("37.120.255.255"), is_vpn=True),
    NetworkInfo(20473, "Vultr Holdings (VPN/hosting)", "NL", "45.76.0.0/16",
                _ip_to_int("45.76.0.0"), _ip_to_int("45.76.255.255"), is_vpn=True, is_hosting=True),
    NetworkInfo(20473, "Vultr Holdings (VPN/hosting)", "US", "149.28.0.0/16",
                _ip_to_int("149.28.0.0"), _ip_to_int("149.28.255.255"), is_vpn=True, is_hosting=True),
    NetworkInfo(14061, "DigitalOcean LLC", "US", "164.90.0.0/16",
                _ip_to_int("164.90.0.0"), _ip_to_int("164.90.255.255"), is_vpn=True, is_hosting=True),
    NetworkInfo(14061, "DigitalOcean LLC", "DE", "138.68.0.0/16",
                _ip_to_int("138.68.0.0"), _ip_to_int("138.68.255.255"), is_vpn=True, is_hosting=True),
]


class NetworkSimulator:
    """Manages IP allocation and network relay simulation."""

    def __init__(self, rng: Generator, n_sensors: int = 5, n_relay_nodes: int = 200):
        self.rng = rng
        self.n_sensors = n_sensors
        self.n_relay_nodes = n_relay_nodes

        # Assign sensor IPs from diverse countries
        sensor_nets = self.rng.choice(
            [n for n in NETWORK_POOL if not n.is_hosting],
            size=min(n_sensors, len(NETWORK_POOL)),
            replace=False,
        )
        self.sensor_ips = [self._sample_ip(net) for net in sensor_nets]
        self.sensor_networks = {ip: net for ip, net in zip(self.sensor_ips, sensor_nets)}

        # Assign relay node IPs from diverse networks
        relay_nets = self.rng.choice(NETWORK_POOL, size=n_relay_nodes, replace=True)
        self.relay_ips = [self._sample_ip(net) for net in relay_nets]
        self.relay_networks = {ip: net for ip, net in zip(self.relay_ips, relay_nets)}

        # Build lookup for all known IPs
        self._ip_to_network: dict[str, NetworkInfo] = {}
        self._ip_to_network.update(self.sensor_networks)
        self._ip_to_network.update(self.relay_networks)

    def _sample_ip(self, net: NetworkInfo) -> str:
        """Sample a random IP from a network range."""
        ip_int = self.rng.integers(net.ip_start + 1, net.ip_end)
        return _int_to_ip(int(ip_int))

    def allocate_entity_ip(self, country_hint: str | None = None,
                           use_tor: bool = False, use_vpn: bool = False) -> tuple[str, NetworkInfo]:
        """Allocate an IP for an entity operator.

        Args:
            country_hint: Preferred country code (best effort).
            use_tor: If True, pick from Tor exit pool.
            use_vpn: If True, pick from VPN pool.

        Returns:
            Tuple of (ip_string, NetworkInfo).
        """
        if use_tor:
            net = self.rng.choice(TOR_EXIT_POOL)
        elif use_vpn:
            net = self.rng.choice(VPN_POOL)
        elif country_hint:
            candidates = [n for n in NETWORK_POOL if n.country == country_hint]
            if candidates:
                net = self.rng.choice(candidates)
            else:
                net = self.rng.choice(NETWORK_POOL)
        else:
            net = self.rng.choice(NETWORK_POOL)

        ip = self._sample_ip(net)
        self._ip_to_network[ip] = net
        return ip, net

    def allocate_multiple_ips(self, count: int, country_hint: str | None = None,
                              use_vpn: bool = False) -> list[tuple[str, NetworkInfo]]:
        """Allocate multiple IPs for an entity with IP rotation."""
        results = []
        for _ in range(count):
            results.append(self.allocate_entity_ip(country_hint=country_hint, use_vpn=use_vpn))
        return results

    def simulate_relay(
        self,
        origin_ip: str,
        origin_ts: float,
        relay_mean_delay: float = 2.0,
        gossip_mean_delay: float = 5.0,
    ) -> list[dict]:
        """Simulate P2P relay propagation from an origin node.

        Returns a list of observations as seen by sensor nodes.
        Each observation has: timestamp, src_ip (relay that sent it),
        dst_ip (sensor), src_port, dst_port.
        """
        observations = []

        # The origin broadcasts to some relay nodes
        n_direct_relays = min(8, self.n_relay_nodes)  # Bitcoin Core: 8 outbound

        # Pick which relay nodes see it first (nearest peers of origin)
        direct_relay_indices = self.rng.choice(
            len(self.relay_ips), size=n_direct_relays, replace=False
        )

        # Relay delays (exponential, ~2s mean for direct, ~5s for gossip)
        relay_arrival_times: dict[str, float] = {}
        relay_arrival_times[origin_ip] = origin_ts

        for idx in direct_relay_indices:
            delay = self.rng.exponential(relay_mean_delay)
            relay_ip = self.relay_ips[idx]
            relay_arrival_times[relay_ip] = origin_ts + delay

        # Gossip: some more relays see it through gossip
        n_gossip = min(30, self.n_relay_nodes)
        gossip_indices = self.rng.choice(
            len(self.relay_ips), size=n_gossip, replace=True
        )
        for idx in gossip_indices:
            relay_ip = self.relay_ips[idx]
            if relay_ip not in relay_arrival_times:
                delay = self.rng.exponential(gossip_mean_delay) + self.rng.exponential(relay_mean_delay)
                relay_arrival_times[relay_ip] = origin_ts + delay

        # Sensors observe from relay nodes
        for sensor_ip in self.sensor_ips:
            # Each sensor connects to ~8 relays
            n_sensor_peers = min(8, len(relay_arrival_times))
            sensor_peer_ips = self.rng.choice(
                list(relay_arrival_times.keys()),
                size=n_sensor_peers,
                replace=False,
            )

            # Sensor sees from the relay that had it earliest + network jitter
            best_time = float("inf")
            best_relay = sensor_peer_ips[0]
            for relay_ip in sensor_peer_ips:
                arrival = relay_arrival_times[relay_ip]
                jitter = self.rng.exponential(0.5)  # ~500ms network jitter
                obs_time = arrival + jitter
                if obs_time < best_time:
                    best_time = obs_time
                    best_relay = relay_ip

            # Produce observation
            src_port = int(self.rng.integers(1024, 65535))
            observations.append({
                "timestamp": best_time,
                "src_ip": best_relay,
                "dst_ip": sensor_ip,
                "src_port": src_port,
                "dst_port": 8333,  # Bitcoin P2P default
            })

        return observations

    def get_network_info(self, ip: str) -> NetworkInfo | None:
        """Look up network info for an IP."""
        return self._ip_to_network.get(ip)
