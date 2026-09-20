"""T5: Layering — pass-through entities with tiny dwell times."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult
from chainsentinel.gen.transactions import BTC, Transaction


class LayeringTypology(BaseTypology):
    """Layering: rapid pass-through with minimal dwell time, possible cycles."""

    TYPOLOGY_CODE = "T5"
    TYPOLOGY_NAME = "layering"

    def generate(self, start_ts, end_ts, obfuscation_level, legit_entities) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities, transactions = [], []

        n_layers = int(self.rng.integers(4, 10))
        initial_amount = int(self.rng.uniform(0.5 * BTC, 5 * BTC))

        ts = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.5)
        current_amount = initial_amount

        source_addr = self.addr_gen.generate("p2wpkh")
        current_addr = source_addr

        for i in range(n_layers):
            layer_entity = Entity(
                entity_id=self._next_entity_id(), entity_type=EntityType.LAYERING,
                is_illicit=True, typology=self.TYPOLOGY_NAME, scenario_id=scenario_id,
                obfuscation_level=obfuscation_level, true_cluster_id=cluster_id,
            )
            ip, net = self.network.allocate_entity_ip(use_vpn=obfuscation_level >= 1)
            layer_entity.operator_ips.append(ip)
            layer_entity.country, layer_entity.asn = net.country, net.asn
            layer_entity.asn_org = net.asn_org

            next_addr = self.addr_gen.generate("p2wpkh")
            layer_entity.addresses.append(next_addr)

            # Tiny dwell time (minutes)
            dwell = self.rng.uniform(60, 3600 * (1 + obfuscation_level * 0.5))
            ts += dwell

            fee = int(self.rng.integers(500, 5000))
            current_amount -= fee

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[current_addr],
                input_amounts=[current_amount],
                output_addresses=[next_addr],
            )
            transactions.append(tx)
            layer_entity.transactions.append(tx.txid)

            current_addr = next_addr
            entities.append(layer_entity)

        return ScenarioResult(scenario_id=scenario_id, typology=self.TYPOLOGY_NAME,
                              entities=entities, transactions=transactions,
                              obfuscation_level=obfuscation_level)
