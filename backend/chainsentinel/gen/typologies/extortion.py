"""T7: Extortion — many small deposits to a single address."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult
from chainsentinel.gen.transactions import BTC, Transaction


class ExtortionTypology(BaseTypology):
    """Extortion: many small deposits from varied sources to a single collection address."""

    TYPOLOGY_CODE = "T7"
    TYPOLOGY_NAME = "extortion"

    def generate(self, start_ts, end_ts, obfuscation_level, legit_entities) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities, transactions = [], []

        n_victims = int(self.rng.integers(50, 201))
        extortion_amount = int(self.rng.uniform(0.001 * BTC, 0.01 * BTC))

        extorter = Entity(
            entity_id=self._next_entity_id(), entity_type=EntityType.EXTORTION,
            is_illicit=True, typology=self.TYPOLOGY_NAME, scenario_id=scenario_id,
            obfuscation_level=obfuscation_level, true_cluster_id=cluster_id,
        )
        collection_addr = self.addr_gen.generate("p2wpkh")
        extorter.addresses.append(collection_addr)
        ip, net = self.network.allocate_entity_ip(use_tor=obfuscation_level >= 1)
        extorter.operator_ips.append(ip)
        extorter.country, extorter.asn = net.country, net.asn
        extorter.asn_org = net.asn_org

        ts_start = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.3)
        window = min(14 * 86400, (end_ts - start_ts) * 0.4)

        for _ in range(n_victims):
            ts = ts_start + self.rng.uniform(0, window)
            victim_addr, victim_script = self.addr_gen.generate()
            amount = extortion_amount + int(self.rng.normal(0, extortion_amount * 0.1))
            amount = max(1000, amount)

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[(victim_addr, victim_script)],
                input_amounts=[amount + int(self.rng.integers(500, 5000))],
                output_addresses=[collection_addr],
            )
            transactions.append(tx)
            extorter.transactions.append(tx.txid)

        entities.append(extorter)

        return ScenarioResult(scenario_id=scenario_id, typology=self.TYPOLOGY_NAME,
                              entities=entities, transactions=transactions,
                              obfuscation_level=obfuscation_level)
