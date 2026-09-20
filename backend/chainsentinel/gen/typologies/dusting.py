"""T8: Dusting — tiny outputs to many addresses for tracking."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult
from chainsentinel.gen.transactions import DUST_LIMIT, Transaction


class DustingTypology(BaseTypology):
    """Dusting: tiny outputs (546-1000 sat) sent to many addresses for deanon."""

    TYPOLOGY_CODE = "T8"
    TYPOLOGY_NAME = "dusting"

    def generate(self, start_ts, end_ts, obfuscation_level, legit_entities) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities, transactions = [], []

        n_targets = int(self.rng.integers(50, 200))

        duster = Entity(
            entity_id=self._next_entity_id(), entity_type=EntityType.DUSTING,
            is_illicit=True, typology=self.TYPOLOGY_NAME, scenario_id=scenario_id,
            obfuscation_level=obfuscation_level, true_cluster_id=cluster_id,
        )
        source_addrs = self.addr_gen.generate_batch(3, "p2wpkh")
        duster.addresses.extend(source_addrs)
        ip, net = self.network.allocate_entity_ip(use_vpn=obfuscation_level >= 1)
        duster.operator_ips.append(ip)
        duster.country, duster.asn = net.country, net.asn
        duster.asn_org = net.asn_org

        ts = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.5)

        # Dust in batches (10-30 outputs per tx)
        batch_size = int(self.rng.integers(10, 31))
        for batch_start in range(0, n_targets, batch_size):
            batch_end = min(batch_start + batch_size, n_targets)
            n_batch = batch_end - batch_start

            # Generate target addresses (pick from legit entities if available)
            target_addrs = []
            for _ in range(n_batch):
                if legit_entities and self.rng.random() > 0.3:
                    target_entity = self.rng.choice(legit_entities)
                    if target_entity.addresses:
                        target_addrs.append(self.rng.choice(target_entity.addresses))
                        continue
                target_addrs.append(self.addr_gen.generate())

            # Each dust output is 546-1000 satoshis
            dust_amounts = [int(self.rng.integers(DUST_LIMIT, 1001)) for _ in range(n_batch)]
            total_dust = sum(dust_amounts)
            fee = int(self.rng.integers(1000, 5000))
            change_amount = int(self.rng.integers(5000, 50000))

            source = source_addrs[batch_start % len(source_addrs)]
            change_addr = self.addr_gen.generate("p2wpkh")

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[source],
                input_amounts=[total_dust + fee + change_amount],
                output_addresses=target_addrs + [change_addr],
                output_amounts=dust_amounts + [change_amount],
                fee=fee,
            )

            transactions.append(tx)
            duster.transactions.append(tx.txid)
            ts += self.rng.uniform(60, 3600)

        entities.append(duster)

        return ScenarioResult(scenario_id=scenario_id, typology=self.TYPOLOGY_NAME,
                              entities=entities, transactions=transactions,
                              obfuscation_level=obfuscation_level)
