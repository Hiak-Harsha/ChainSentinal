"""Base class for illicit typology generators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from numpy.random import Generator

from chainsentinel.gen.entities import Entity
from chainsentinel.gen.network import NetworkSimulator
from chainsentinel.gen.transactions import AddressGenerator, Transaction, TransactionBuilder


@dataclass
class ScenarioResult:
    """Output of a typology scenario generation."""

    scenario_id: str
    typology: str
    entities: list[Entity] = field(default_factory=list)
    transactions: list[Transaction] = field(default_factory=list)
    obfuscation_level: int = 0

    def to_ground_truth(self) -> dict[str, Any]:
        """Serialize for ground truth."""
        return {
            "scenario_id": self.scenario_id,
            "typology": self.typology,
            "obfuscation_level": self.obfuscation_level,
            "entity_ids": [e.entity_id for e in self.entities],
            "txids": [t.txid for t in self.transactions],
        }


class BaseTypology(ABC):
    """Abstract base class for illicit typology generators."""

    TYPOLOGY_CODE: str = "T0"
    TYPOLOGY_NAME: str = "base"

    def __init__(
        self,
        rng: Generator,
        addr_gen: AddressGenerator,
        tx_builder: TransactionBuilder,
        network: NetworkSimulator,
        entity_counter: list[int],
        cluster_counter: list[int],
        scenario_counter: list[int],
    ):
        self.rng = rng
        self.addr_gen = addr_gen
        self.tx_builder = tx_builder
        self.network = network
        self._entity_counter = entity_counter  # Mutable ref for shared counting
        self._cluster_counter = cluster_counter
        self._scenario_counter = scenario_counter

    def _next_entity_id(self) -> str:
        self._entity_counter[0] += 1
        return f"E-{self._entity_counter[0]:04d}"

    def _next_cluster_id(self) -> str:
        self._cluster_counter[0] += 1
        return f"C-{self._cluster_counter[0]:04d}"

    def _next_scenario_id(self) -> str:
        self._scenario_counter[0] += 1
        return f"S-{self.TYPOLOGY_CODE}-{self._scenario_counter[0]:03d}"

    def _random_timestamp(self, start: float, end: float) -> float:
        """Generate a random timestamp in the given range."""
        return float(self.rng.uniform(start, end))

    @abstractmethod
    def generate(
        self,
        start_ts: float,
        end_ts: float,
        obfuscation_level: int,
        legit_entities: list[Entity],
    ) -> ScenarioResult:
        """Generate one instance of this typology scenario.

        Args:
            start_ts: Start of time range (Unix timestamp).
            end_ts: End of time range.
            obfuscation_level: 0-3 difficulty level.
            legit_entities: Available legit entities for interactions.

        Returns:
            ScenarioResult with entities and transactions.
        """
        ...
