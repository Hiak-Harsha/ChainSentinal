"""T6: Structuring/Smurfing — transactions just below thresholds."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult
from chainsentinel.gen.transactions import BTC, Transaction


class StructuringTypology(BaseTypology):
    """Structuring: multiple transactions just below a reporting threshold."""

    TYPOLOGY_CODE = "T6"
    TYPOLOGY_NAME = "structuring"

    def generate(self, start_ts, end_ts, obfuscation_level, legit_entities) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities, transactions = [], []

        threshold = int(1 * BTC)  # 1 BTC threshold
        n_txs = int(self.rng.integers(5, 20))
        target_addr = self.addr_gen.generate("p2wpkh")

        structurer = Entity(
            entity_id=self._next_entity_id(), entity_type=EntityType.STRUCTURING,
            is_illicit=True, typology=self.TYPOLOGY_NAME, scenario_id=scenario_id,
            obfuscation_level=obfuscation_level, true_cluster_id=cluster_id,
        )
        structurer.addresses.append(target_addr)
        ip, net = self.network.allocate_entity_ip(use_vpn=obfuscation_level >= 2)
        structurer.operator_ips.append(ip)
        structurer.country, structurer.asn = net.country, net.asn
        structurer.asn_org = net.asn_org

        ts = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.3)

        # Generate source addresses (multiple smurfs)
        n_source_addrs = max(2, n_txs // 3)
        source_addrs = self.addr_gen.generate_batch(n_source_addrs, "p2wpkh")
        structurer.addresses.extend(source_addrs)

        for i in range(n_txs):
            # Amount just below threshold (85-99% of threshold)
            ratio = float(self.rng.uniform(0.85, 0.99))
            amount = int(threshold * ratio)
            # Add slight randomness to avoid exact patterns
            amount += int(self.rng.integers(-50000, 50000))

            delay = self.rng.uniform(
                1800 * (1 + obfuscation_level),
                86400 * (1 + obfuscation_level * 0.5),
            )
            ts += delay

            source = source_addrs[i % n_source_addrs]

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[source],
                input_amounts=[amount + int(self.rng.integers(500, 10000))],
                output_addresses=[target_addr],
            )
            transactions.append(tx)
            structurer.transactions.append(tx.txid)

        entities.append(structurer)

        return ScenarioResult(scenario_id=scenario_id, typology=self.TYPOLOGY_NAME,
                              entities=entities, transactions=transactions,
                              obfuscation_level=obfuscation_level)
