"""T1: Ransomware — collection → consolidation → layering → cash-out."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.transactions import BTC, Transaction
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult


class RansomwareTypology(BaseTypology):
    """Ransomware campaign: victims pay to collection addresses,
    funds consolidate, layer through intermediaries, cash out to exchange.
    """

    TYPOLOGY_CODE = "T1"
    TYPOLOGY_NAME = "ransomware"

    def generate(
        self,
        start_ts: float,
        end_ts: float,
        obfuscation_level: int,
        legit_entities: list[Entity],
    ) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities: list[Entity] = []
        transactions: list[Transaction] = []

        # Phase 1: Collection — victims pay to unique collection addresses
        n_victims = int(self.rng.integers(10, 51))
        ransom_amount = int(self.rng.choice([
            int(0.05 * BTC), int(0.1 * BTC), int(0.5 * BTC), int(1.0 * BTC),
        ]))

        collector = Entity(
            entity_id=self._next_entity_id(),
            entity_type=EntityType.RANSOMWARE,
            role="collector",
            is_illicit=True,
            typology=self.TYPOLOGY_NAME,
            scenario_id=scenario_id,
            obfuscation_level=obfuscation_level,
            true_cluster_id=cluster_id,
        )

        collection_addrs = self.addr_gen.generate_batch(n_victims, "p2wpkh")
        for ca in collection_addrs:
            collector.add_address(ca[0], ca[1], role="collector")

        # Probabilistic IP allocation (no deterministic leak)
        ip, net = self.network.allocate_entity_ip(
            is_illicit=True,
            obfuscation_level=obfuscation_level,
            archetype="ransomware",
        )
        collector.operator_ips.append(ip)
        collector.country = net.country
        collector.asn = net.asn
        collector.asn_org = net.asn_org

        collection_window = min(7 * 86400, (end_ts - start_ts) * 0.3)
        collection_start = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.2)

        collected_amounts: list[tuple[str, str, int]] = []

        # Generate each victim with ground truth label
        for i in range(n_victims):
            ts = collection_start + self.rng.uniform(0, collection_window)
            victim_addr, victim_script = self.addr_gen.generate()
            vip, vnet = self.network.allocate_entity_ip(archetype="retail", is_illicit=False)

            victim_entity = Entity(
                entity_id=self._next_entity_id(),
                entity_type=EntityType.RETAIL,
                role="victim",
                is_illicit=False,
                typology=self.TYPOLOGY_NAME,
                scenario_id=scenario_id,
                obfuscation_level=0,
                true_cluster_id=self._next_cluster_id(),
                operator_ips=[vip],
                country=vnet.country,
                asn=vnet.asn,
                asn_org=vnet.asn_org,
            )
            victim_entity.add_address(victim_addr, victim_script, role="victim")
            entities.append(victim_entity)

            variation = int(self.rng.normal(0, ransom_amount * 0.05))
            amount = max(1000, ransom_amount + variation)

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[(victim_addr, victim_script)],
                input_amounts=[amount + int(self.rng.integers(500, 5000))],
                output_addresses=[collection_addrs[i]],
            )
            transactions.append(tx)
            collected_amounts.append((collection_addrs[i][0], collection_addrs[i][1], amount))

        # Phase 2: Consolidation — sweep collection to a consolidation address
        consolidation_addr = self.addr_gen.generate("p2wpkh")
        collector.add_address(consolidation_addr[0], consolidation_addr[1], role="collector")

        consol_ts = collection_start + collection_window + self.rng.uniform(3600, 86400)

        batch_size = int(self.rng.integers(5, 11))
        for batch_start in range(0, len(collected_amounts), batch_size):
            batch = collected_amounts[batch_start:batch_start + batch_size]
            tx = self.tx_builder.build_simple(
                timestamp=consol_ts + self.rng.uniform(0, 3600),
                input_addresses=[(a, s) for a, s, _ in batch],
                input_amounts=[amt for _, _, amt in batch],
                output_addresses=[consolidation_addr],
            )
            transactions.append(tx)

        # Phase 3: Layering — split through intermediaries
        n_layers = 3 + obfuscation_level
        layer_entities: list[Entity] = []

        current_addr = consolidation_addr
        total_collected = sum(a for _, _, a in collected_amounts)
        current_amount = total_collected

        layer_ts = consol_ts + self.rng.uniform(3600, 43200)

        for layer_i in range(n_layers):
            layer_entity = Entity(
                entity_id=self._next_entity_id(),
                entity_type=EntityType.RANSOMWARE,
                role="layer",
                is_illicit=True,
                typology=self.TYPOLOGY_NAME,
                scenario_id=scenario_id,
                obfuscation_level=obfuscation_level,
                true_cluster_id=cluster_id,
            )

            next_addr = self.addr_gen.generate("p2wpkh")
            layer_entity.add_address(next_addr[0], next_addr[1], role="layer")

            lip, lnet = self.network.allocate_entity_ip(
                is_illicit=True,
                obfuscation_level=obfuscation_level,
                archetype="ransomware",
            )
            layer_entity.operator_ips.append(lip)
            layer_entity.country = lnet.country
            layer_entity.asn = lnet.asn
            layer_entity.asn_org = lnet.asn_org

            delay = self.rng.uniform(
                600 * (obfuscation_level + 1),
                7200 * (obfuscation_level + 1),
            )
            layer_ts += delay

            fee = int(self.rng.integers(1000, 10000))
            current_amount = max(1000, current_amount - fee)

            tx = self.tx_builder.build_simple(
                timestamp=layer_ts,
                input_addresses=[current_addr],
                input_amounts=[current_amount],
                output_addresses=[next_addr],
            )
            transactions.append(tx)

            current_addr = next_addr
            layer_entities.append(layer_entity)

        # Phase 4: Cash-out to exchange
        cashout_ts = layer_ts + self.rng.uniform(3600, 86400)
        exchange_entities = [e for e in legit_entities if e.entity_type == EntityType.EXCHANGE_HOT]
        if exchange_entities:
            target_exchange = self.rng.choice(exchange_entities)
            target_addr = self.rng.choice(target_exchange.addresses)
            target_exchange.address_roles[target_addr[0]] = "counterparty"
        else:
            target_addr = self.addr_gen.generate("p2wpkh")
            counterparty_entity = Entity(
                entity_id=self._next_entity_id(),
                entity_type=EntityType.EXCHANGE_HOT,
                role="counterparty",
                is_illicit=False,
                typology=self.TYPOLOGY_NAME,
                scenario_id=scenario_id,
                true_cluster_id=self._next_cluster_id(),
            )
            counterparty_entity.add_address(target_addr[0], target_addr[1], role="counterparty")
            entities.append(counterparty_entity)

        fee = int(self.rng.integers(1000, 10000))
        tx = self.tx_builder.build_simple(
            timestamp=cashout_ts,
            input_addresses=[current_addr],
            input_amounts=[max(1000, current_amount - fee)],
            output_addresses=[target_addr],
        )
        transactions.append(tx)

        entities.append(collector)
        entities.extend(layer_entities)

        for tx in transactions:
            collector.transactions.append(tx.txid)

        return ScenarioResult(
            scenario_id=scenario_id,
            typology=self.TYPOLOGY_NAME,
            entities=entities,
            transactions=transactions,
            obfuscation_level=obfuscation_level,
        )
