"""T7: Extortion — many small deposits to a single address."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.transactions import BTC, Transaction
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult


class ExtortionTypology(BaseTypology):
    """Extortion: many small deposits from varied sources to a single collection address."""

    TYPOLOGY_CODE = "T7"
    TYPOLOGY_NAME = "extortion"

    def generate(self, start_ts: float, end_ts: float, obfuscation_level: int, legit_entities: list[Entity]) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities: list[Entity] = []
        transactions: list[Transaction] = []

        n_victims = int(self.rng.integers(15, 45))
        extortion_amount = int(self.rng.uniform(0.001 * BTC, 0.01 * BTC))

        extorter = Entity(
            entity_id=self._next_entity_id(),
            entity_type=EntityType.EXTORTION,
            role="collector",
            is_illicit=True,
            typology=self.TYPOLOGY_NAME,
            scenario_id=scenario_id,
            obfuscation_level=obfuscation_level,
            true_cluster_id=cluster_id,
        )
        collection_addr = self.addr_gen.generate("p2wpkh")
        extorter.add_address(collection_addr[0], collection_addr[1], role="collector")

        ip, net = self.network.allocate_entity_ip(
            is_illicit=True,
            obfuscation_level=obfuscation_level,
            archetype="extortion",
        )
        extorter.operator_ips.append(ip)
        extorter.country, extorter.asn = net.country, net.asn
        extorter.asn_org = net.asn_org
        entities.append(extorter)

        ts_start = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.3)
        window = min(14 * 86400, (end_ts - start_ts) * 0.4)

        for _ in range(n_victims):
            ts = ts_start + self.rng.uniform(0, window)
            victim_addr, victim_script = self.addr_gen.generate()
            vip, vnet = self.network.allocate_entity_ip(archetype="retail", is_illicit=False)

            victim = Entity(
                entity_id=self._next_entity_id(),
                entity_type=EntityType.RETAIL,
                role="victim",
                is_illicit=False,
                typology=self.TYPOLOGY_NAME,
                scenario_id=scenario_id,
                true_cluster_id=self._next_cluster_id(),
                operator_ips=[vip],
                country=vnet.country,
                asn=vnet.asn,
                asn_org=vnet.asn_org,
            )
            victim.add_address(victim_addr, victim_script, role="victim")
            entities.append(victim)

            amount = max(1000, extortion_amount + int(self.rng.normal(0, extortion_amount * 0.1)))

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[(victim_addr, victim_script)],
                input_amounts=[amount + int(self.rng.integers(500, 5000))],
                output_addresses=[collection_addr],
            )
            transactions.append(tx)
            extorter.transactions.append(tx.txid)
            victim.transactions.append(tx.txid)

        return ScenarioResult(
            scenario_id=scenario_id,
            typology=self.TYPOLOGY_NAME,
            entities=entities,
            transactions=transactions,
            obfuscation_level=obfuscation_level,
        )
