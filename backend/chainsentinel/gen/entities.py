"""Entity population — generates legitimate and illicit entity archetypes.

Legit entities are designed as "hard negatives" that look busy/weird
enough that detection isn't trivial.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from numpy.random import Generator

from chainsentinel.gen.network import NetworkSimulator
from chainsentinel.gen.transactions import AddressGenerator


class EntityType(str, Enum):
    """Entity archetype classification."""

    # Legitimate
    RETAIL = "retail"
    MERCHANT = "merchant"
    EXCHANGE_HOT = "exchange_hot"
    EXCHANGE_COLD = "exchange_cold"
    PAYROLL = "payroll"
    MINING_POOL = "mining_pool"
    GAMBLING = "gambling"
    CUSTODIAL = "custodial"

    # Illicit
    RANSOMWARE = "ransomware"
    DARKNET_MARKET = "darknet_market"
    PEEL_CHAIN = "peel_chain"
    MIXER = "mixer"
    LAYERING = "layering"
    STRUCTURING = "structuring"
    EXTORTION = "extortion"
    DUSTING = "dusting"
    MULTI_CLUSTER = "multi_cluster"


@dataclass
class Entity:
    """A synthetic entity (wallet cluster)."""

    entity_id: str
    entity_type: EntityType
    is_illicit: bool = False
    typology: str | None = None
    scenario_id: str | None = None
    obfuscation_level: int = 0
    role: str = ""

    # Addresses owned by this entity
    addresses: list[tuple[str, str]] = field(default_factory=list)  # (addr, script_type)
    address_roles: dict[str, str] = field(default_factory=dict)  # addr -> role

    # Operator IPs
    operator_ips: list[str] = field(default_factory=list)

    # Network info for primary IP
    country: str = "US"
    asn: int = 0
    asn_org: str = ""

    # Behavioral parameters
    tx_rate_per_day: float = 2.0
    amount_mean: int = 1_000_000  # satoshis (~0.01 BTC)
    amount_std: int = 500_000
    active_hours: tuple[int, int] = (8, 22)  # UTC hours
    weekend_ratio: float = 0.3  # Fraction of weekend activity

    # Tracking
    true_cluster_id: str | None = None  # For ground truth
    transactions: list[str] = field(default_factory=list)  # txids

    def add_address(self, addr: str, script_type: str = "p2wpkh", role: str | None = None) -> tuple[str, str]:
        """Register a new address with an assigned role."""
        pair = (addr, script_type)
        if pair not in self.addresses:
            self.addresses.append(pair)
        self.address_roles[addr] = role or self.role or self.entity_type.value
        return pair

    def to_ground_truth(self) -> dict[str, Any]:
        """Serialize for entity ground truth output."""
        return {
            "entity_id": self.entity_id,
            "role": self.role or self.entity_type.value,
            "type": "illicit" if self.is_illicit else ("victim" if self.role == "victim" else "legit"),
            "archetype": self.entity_type.value,
            "typology": self.typology,
            "scenario_id": self.scenario_id,
            "obfuscation_level": self.obfuscation_level,
            "addresses": [addr for addr, _ in self.addresses],
            "operator_ips": self.operator_ips,
            "true_cluster": self.true_cluster_id,
        }

    def get_address_ground_truth(self) -> dict[str, dict[str, Any]]:
        """Return ground truth records for all addresses belonging to this entity."""
        res: dict[str, dict[str, Any]] = {}
        for addr, _ in self.addresses:
            res[addr] = {
                "address": addr,
                "entity_id": self.entity_id,
                "true_cluster": self.true_cluster_id,
                "role": self.address_roles.get(addr, self.role or self.entity_type.value),
                "type": "illicit" if self.is_illicit else ("victim" if self.role == "victim" else "legit"),
                "archetype": self.entity_type.value,
                "typology": self.typology,
                "scenario_id": self.scenario_id,
                "operator_ips": self.operator_ips,
                "obfuscation_level": self.obfuscation_level,
            }
        return res


class EntityPopulation:
    """Generates the full entity population for a synthetic dataset."""

    def __init__(self, rng: Generator, addr_gen: AddressGenerator, network: NetworkSimulator):
        self.rng = rng
        self.addr_gen = addr_gen
        self.network = network
        self._entity_counter = 0
        self._cluster_counter = 0

    def _next_entity_id(self) -> str:
        """Generate the next entity ID."""
        self._entity_counter += 1
        return f"E-{self._entity_counter:04d}"

    def _next_cluster_id(self) -> str:
        """Generate the next cluster ID."""
        self._cluster_counter += 1
        return f"C-{self._cluster_counter:04d}"

    def generate_retail_users(self, count: int) -> list[Entity]:
        """Generate retail user entities.

        Retail users: 1-5 tx/day, varied amounts, 1-3 addresses.
        """
        entities = []
        for _ in range(count):
            eid = self._next_entity_id()
            cid = self._next_cluster_id()

            n_addrs = int(self.rng.integers(1, 4))
            addrs = self.addr_gen.generate_batch(n_addrs)
            ip, net = self.network.allocate_entity_ip(archetype="retail", is_illicit=False)

            entity = Entity(
                entity_id=eid,
                entity_type=EntityType.RETAIL,
                role="retail_user",
                addresses=addrs,
                operator_ips=[ip],
                country=net.country,
                asn=net.asn,
                asn_org=net.asn_org,
                tx_rate_per_day=float(self.rng.uniform(0.5, 5.0)),
                amount_mean=int(self.rng.integers(50_000, 5_000_000)),
                amount_std=int(self.rng.integers(10_000, 2_000_000)),
                active_hours=(int(self.rng.integers(6, 12)), int(self.rng.integers(18, 24))),
                weekend_ratio=float(self.rng.uniform(0.1, 0.5)),
                true_cluster_id=cid,
            )
            for a, _ in addrs:
                entity.address_roles[a] = "retail_user"
            entities.append(entity)
        return entities

    def generate_merchants(self, count: int) -> list[Entity]:
        """Generate merchant entities.

        Merchants: high fan-in, periodic withdrawals, 5-20 addresses.
        Hard negative: looks like collection.
        """
        entities = []
        for _ in range(count):
            eid = self._next_entity_id()
            cid = self._next_cluster_id()

            n_addrs = int(self.rng.integers(5, 21))
            addrs = self.addr_gen.generate_batch(n_addrs)
            ip, net = self.network.allocate_entity_ip(archetype="merchant", is_illicit=False)

            entity = Entity(
                entity_id=eid,
                entity_type=EntityType.MERCHANT,
                role="merchant",
                addresses=addrs,
                operator_ips=[ip],
                country=net.country,
                asn=net.asn,
                asn_org=net.asn_org,
                tx_rate_per_day=float(self.rng.uniform(10, 100)),
                amount_mean=int(self.rng.integers(100_000, 10_000_000)),
                amount_std=int(self.rng.integers(50_000, 5_000_000)),
                active_hours=(8, 22),
                weekend_ratio=0.2,
                true_cluster_id=cid,
            )
            for a, _ in addrs:
                entity.address_roles[a] = "merchant_deposit"
            entities.append(entity)
        return entities

    def generate_exchange_hot(self, count: int) -> list[Entity]:
        """Generate exchange hot wallet entities.

        Hot wallets: massive fan-in/out, batching, 20-100 addresses.
        Hard negative: looks like mixer/hub.
        """
        entities = []
        for _ in range(count):
            eid = self._next_entity_id()
            cid = self._next_cluster_id()

            n_addrs = int(self.rng.integers(20, 101))
            addrs = self.addr_gen.generate_batch(n_addrs)
            ip, net = self.network.allocate_entity_ip(archetype="exchange_hot", is_illicit=False)

            entity = Entity(
                entity_id=eid,
                entity_type=EntityType.EXCHANGE_HOT,
                role="exchange_hot",
                addresses=addrs,
                operator_ips=[ip],
                country=net.country,
                asn=net.asn,
                asn_org=net.asn_org,
                tx_rate_per_day=float(self.rng.uniform(100, 1000)),
                amount_mean=int(self.rng.integers(1_000_000, 100_000_000)),
                amount_std=int(self.rng.integers(500_000, 50_000_000)),
                active_hours=(0, 24),
                weekend_ratio=0.9,
                true_cluster_id=cid,
            )
            for a, _ in addrs:
                entity.address_roles[a] = "exchange_hot"
            entities.append(entity)
        return entities

    def generate_exchange_cold(self, count: int) -> list[Entity]:
        """Generate exchange cold wallet entities.

        Cold wallets: periodic large sweeps, 2-5 addresses.
        Hard negative: looks like consolidation.
        """
        entities = []
        for _ in range(count):
            eid = self._next_entity_id()
            cid = self._next_cluster_id()

            n_addrs = int(self.rng.integers(2, 6))
            addrs = self.addr_gen.generate_batch(n_addrs)
            ip, net = self.network.allocate_entity_ip(archetype="exchange_cold", is_illicit=False)

            entity = Entity(
                entity_id=eid,
                entity_type=EntityType.EXCHANGE_COLD,
                role="exchange_cold",
                addresses=addrs,
                operator_ips=[ip],
                country=net.country,
                asn=net.asn,
                asn_org=net.asn_org,
                tx_rate_per_day=float(self.rng.uniform(0.1, 1.0)),
                amount_mean=int(self.rng.integers(100_000_000, 1_000_000_000)),
                amount_std=int(self.rng.integers(50_000_000, 500_000_000)),
                active_hours=(0, 24),
                weekend_ratio=0.5,
                true_cluster_id=cid,
            )
            for a, _ in addrs:
                entity.address_roles[a] = "exchange_cold"
            entities.append(entity)
        return entities

    def generate_payroll(self, count: int) -> list[Entity]:
        """Generate payroll batcher entities.

        Payroll: periodic batch sends, similar amounts, 3-10 addresses.
        Hard negative: looks like structuring.
        """
        entities = []
        for _ in range(count):
            eid = self._next_entity_id()
            cid = self._next_cluster_id()

            n_addrs = int(self.rng.integers(3, 11))
            addrs = self.addr_gen.generate_batch(n_addrs)
            ip, net = self.network.allocate_entity_ip(archetype="payroll", is_illicit=False)

            entity = Entity(
                entity_id=eid,
                entity_type=EntityType.PAYROLL,
                role="payroll_sender",
                addresses=addrs,
                operator_ips=[ip],
                country=net.country,
                asn=net.asn,
                asn_org=net.asn_org,
                tx_rate_per_day=float(self.rng.uniform(0.1, 2.0)),
                amount_mean=int(self.rng.integers(500_000, 5_000_000)),
                amount_std=int(self.rng.integers(50_000, 500_000)),
                active_hours=(8, 18),
                weekend_ratio=0.05,
                true_cluster_id=cid,
            )
            for a, _ in addrs:
                entity.address_roles[a] = "payroll_sender"
            entities.append(entity)
        return entities

    def generate_mining_pools(self, count: int) -> list[Entity]:
        """Generate mining pool entities.

        Mining pools: coinbase txs, large payouts, 5-15 addresses.
        """
        entities = []
        for _ in range(count):
            eid = self._next_entity_id()
            cid = self._next_cluster_id()

            n_addrs = int(self.rng.integers(5, 16))
            addrs = self.addr_gen.generate_batch(n_addrs)
            ip, net = self.network.allocate_entity_ip(archetype="mining_pool", is_illicit=False)

            entity = Entity(
                entity_id=eid,
                entity_type=EntityType.MINING_POOL,
                role="mining_pool",
                addresses=addrs,
                operator_ips=[ip],
                country=net.country,
                asn=net.asn,
                asn_org=net.asn_org,
                tx_rate_per_day=float(self.rng.uniform(5, 50)),
                amount_mean=int(self.rng.integers(10_000_000, 500_000_000)),
                amount_std=int(self.rng.integers(5_000_000, 100_000_000)),
                active_hours=(0, 24),
                weekend_ratio=0.95,
                true_cluster_id=cid,
            )
            for a, _ in addrs:
                entity.address_roles[a] = "mining_pool"
            entities.append(entity)
        return entities

    def generate_gambling(self, count: int) -> list[Entity]:
        """Generate gambling service entities.

        Gambling: fast in/out, round amounts, 5-20 addresses.
        Hard negative: looks like layering.
        """
        entities = []
        for _ in range(count):
            eid = self._next_entity_id()
            cid = self._next_cluster_id()

            n_addrs = int(self.rng.integers(5, 21))
            addrs = self.addr_gen.generate_batch(n_addrs)
            ip, net = self.network.allocate_entity_ip(archetype="gambling", is_illicit=False)

            entity = Entity(
                entity_id=eid,
                entity_type=EntityType.GAMBLING,
                role="gambling_house",
                addresses=addrs,
                operator_ips=[ip],
                country=net.country,
                asn=net.asn,
                asn_org=net.asn_org,
                tx_rate_per_day=float(self.rng.uniform(20, 200)),
                amount_mean=int(self.rng.integers(100_000, 10_000_000)),
                amount_std=int(self.rng.integers(50_000, 5_000_000)),
                active_hours=(0, 24),
                weekend_ratio=0.8,
                true_cluster_id=cid,
            )
            for a, _ in addrs:
                entity.address_roles[a] = "gambling_house"
            entities.append(entity)
        return entities

    def generate_custodial(self, count: int) -> list[Entity]:
        """Generate custodial wallet entities.

        Custodial wallets: mixed patterns, 3-15 addresses.
        """
        entities = []
        for _ in range(count):
            eid = self._next_entity_id()
            cid = self._next_cluster_id()

            n_addrs = int(self.rng.integers(3, 16))
            addrs = self.addr_gen.generate_batch(n_addrs)
            ip, net = self.network.allocate_entity_ip(archetype="custodial", is_illicit=False)

            entity = Entity(
                entity_id=eid,
                entity_type=EntityType.CUSTODIAL,
                role="custodial_service",
                addresses=addrs,
                operator_ips=[ip],
                country=net.country,
                asn=net.asn,
                asn_org=net.asn_org,
                tx_rate_per_day=float(self.rng.uniform(5, 50)),
                amount_mean=int(self.rng.integers(200_000, 20_000_000)),
                amount_std=int(self.rng.integers(100_000, 10_000_000)),
                active_hours=(0, 24),
                weekend_ratio=0.7,
                true_cluster_id=cid,
            )
            for a, _ in addrs:
                entity.address_roles[a] = "custodial_service"
            entities.append(entity)
        return entities

    def generate_all_legit(
        self,
        n_retail: int = 300,
        n_merchant: int = 25,
        n_exchange_hot: int = 8,
        n_exchange_cold: int = 4,
        n_payroll: int = 10,
        n_mining: int = 5,
        n_gambling: int = 8,
        n_custodial: int = 10,
    ) -> list[Entity]:
        """Generate the full legitimate entity population."""
        entities = []
        entities.extend(self.generate_retail_users(n_retail))
        entities.extend(self.generate_merchants(n_merchant))
        entities.extend(self.generate_exchange_hot(n_exchange_hot))
        entities.extend(self.generate_exchange_cold(n_exchange_cold))
        entities.extend(self.generate_payroll(n_payroll))
        entities.extend(self.generate_mining_pools(n_mining))
        entities.extend(self.generate_gambling(n_gambling))
        entities.extend(self.generate_custodial(n_custodial))
        return entities
