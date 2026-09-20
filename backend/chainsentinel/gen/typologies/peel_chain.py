"""T3: Peel Chain — sequential peeling of small amounts."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.transactions import BTC, Transaction
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult


class PeelChainTypology(BaseTypology):
    """Peel chain: large input → small peel + large change, repeated."""

    TYPOLOGY_CODE = "T3"
    TYPOLOGY_NAME = "peel_chain"

    def generate(self, start_ts: float, end_ts: float, obfuscation_level: int, legit_entities: list[Entity]) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities: list[Entity] = []
        transactions: list[Transaction] = []

        chain_length = int(self.rng.integers(5, 21))
        initial_amount = int(self.rng.uniform(1 * BTC, 10 * BTC))

        peeler = Entity(
            entity_id=self._next_entity_id(),
            entity_type=EntityType.PEEL_CHAIN,
            role="collector",
            is_illicit=True,
            typology=self.TYPOLOGY_NAME,
            scenario_id=scenario_id,
            obfuscation_level=obfuscation_level,
            true_cluster_id=cluster_id,
        )
        ip, net = self.network.allocate_entity_ip(
            is_illicit=True,
            obfuscation_level=obfuscation_level,
            archetype="peel_chain",
        )
        peeler.operator_ips.append(ip)
        peeler.country, peeler.asn, peeler.asn_org = net.country, net.asn, net.asn_org

        current_amount = initial_amount
        current_addr = self.addr_gen.generate("p2wpkh")
        peeler.add_address(current_addr[0], current_addr[1], role="collector")

        ts = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.3)

        for step in range(chain_length):
            peel_ratio = float(self.rng.uniform(0.05, 0.15))
            peel_amount = max(10000, int(current_amount * peel_ratio))
            fee = int(self.rng.integers(500, 5000))

            change_addr = self.addr_gen.generate("p2wpkh")
            peeler.add_address(change_addr[0], change_addr[1], role="layer")

            # Peel destination: counterparty / cashout
            peel_dest = self.addr_gen.generate("p2wpkh")
            counterparty = Entity(
                entity_id=self._next_entity_id(),
                entity_type=EntityType.MERCHANT,
                role="counterparty",
                is_illicit=False,
                typology=self.TYPOLOGY_NAME,
                scenario_id=scenario_id,
                true_cluster_id=self._next_cluster_id(),
            )
            counterparty.add_address(peel_dest[0], peel_dest[1], role="counterparty")
            entities.append(counterparty)

            change_amount = current_amount - peel_amount - fee
            if change_amount <= 546:
                break

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[current_addr],
                input_amounts=[current_amount],
                output_addresses=[peel_dest, change_addr],
                output_amounts=[peel_amount, change_amount],
                fee=fee,
            )

            transactions.append(tx)
            peeler.transactions.append(tx.txid)

            current_addr = change_addr
            current_amount = change_amount

            delay = self.rng.uniform(
                60 * (1 + obfuscation_level),
                3600 * (1 + obfuscation_level),
            )
            ts += delay

        entities.append(peeler)

        return ScenarioResult(
            scenario_id=scenario_id,
            typology=self.TYPOLOGY_NAME,
            entities=entities,
            transactions=transactions,
            obfuscation_level=obfuscation_level,
        )
