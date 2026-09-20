"""T8: Dusting — tiny outputs to many addresses for tracking."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.transactions import DUST_LIMIT, Transaction
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult


class DustingTypology(BaseTypology):
    """Dusting: tiny outputs (546-1000 sat) sent to many addresses for deanon."""

    TYPOLOGY_CODE = "T8"
    TYPOLOGY_NAME = "dusting"

    def generate(self, start_ts: float, end_ts: float, obfuscation_level: int, legit_entities: list[Entity]) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities: list[Entity] = []
        transactions: list[Transaction] = []

        n_targets = int(self.rng.integers(20, 60))

        duster = Entity(
            entity_id=self._next_entity_id(),
            entity_type=EntityType.DUSTING,
            role="collector",
            is_illicit=True,
            typology=self.TYPOLOGY_NAME,
            scenario_id=scenario_id,
            obfuscation_level=obfuscation_level,
            true_cluster_id=cluster_id,
        )
        source_addrs = self.addr_gen.generate_batch(3, "p2wpkh")
        for sa in source_addrs:
            duster.add_address(sa[0], sa[1], role="collector")

        ip, net = self.network.allocate_entity_ip(
            is_illicit=True,
            obfuscation_level=obfuscation_level,
            archetype="dusting",
        )
        duster.operator_ips.append(ip)
        duster.country, duster.asn = net.country, net.asn
        duster.asn_org = net.asn_org
        entities.append(duster)

        ts = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.5)

        batch_size = int(self.rng.integers(10, 25))
        for batch_start in range(0, n_targets, batch_size):
            batch_end = min(batch_start + batch_size, n_targets)
            n_batch = batch_end - batch_start

            target_addrs = []
            for _ in range(n_batch):
                if legit_entities and self.rng.random() > 0.4:
                    target_entity = self.rng.choice(legit_entities)
                    if target_entity.addresses:
                        chosen = self.rng.choice(target_entity.addresses)
                        target_entity.address_roles[chosen[0]] = "victim"
                        target_addrs.append(chosen)
                        continue

                # New target victim entity
                t_addr = self.addr_gen.generate("p2wpkh")
                tip, tnet = self.network.allocate_entity_ip(archetype="retail", is_illicit=False)
                victim = Entity(
                    entity_id=self._next_entity_id(),
                    entity_type=EntityType.RETAIL,
                    role="victim",
                    is_illicit=False,
                    typology=self.TYPOLOGY_NAME,
                    scenario_id=scenario_id,
                    true_cluster_id=self._next_cluster_id(),
                    operator_ips=[tip],
                    country=tnet.country,
                    asn=tnet.asn,
                    asn_org=tnet.asn_org,
                )
                victim.add_address(t_addr[0], t_addr[1], role="victim")
                entities.append(victim)
                target_addrs.append(t_addr)

            dust_amounts = [int(self.rng.integers(DUST_LIMIT, 1001)) for _ in range(n_batch)]
            total_dust = sum(dust_amounts)
            fee = int(self.rng.integers(1000, 5000))
            change_amount = int(self.rng.integers(5000, 50000))

            source = source_addrs[batch_start % len(source_addrs)]
            change_addr = self.addr_gen.generate("p2wpkh")
            duster.add_address(change_addr[0], change_addr[1], role="layer")

            all_outputs = target_addrs + [change_addr]
            all_amounts = dust_amounts + [change_amount]

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[source],
                input_amounts=[total_dust + fee + change_amount],
                output_addresses=all_outputs,
                output_amounts=all_amounts,
                fee=fee,
            )
            transactions.append(tx)
            duster.transactions.append(tx.txid)

            ts += self.rng.uniform(3600, 86400)

        return ScenarioResult(
            scenario_id=scenario_id,
            typology=self.TYPOLOGY_NAME,
            entities=entities,
            transactions=transactions,
            obfuscation_level=obfuscation_level,
        )
