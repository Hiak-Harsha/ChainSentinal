"""T1: Ransomware — collection → consolidation → layering → cash-out."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult
from chainsentinel.gen.transactions import BTC, Transaction


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

        # Phase 1: Collection — victims pay to unique addresses
        n_victims = int(self.rng.integers(10, 51))
        ransom_amount = int(self.rng.choice([
            int(0.05 * BTC), int(0.1 * BTC), int(0.5 * BTC), int(1.0 * BTC),
        ]))

        collector = Entity(
            entity_id=self._next_entity_id(),
            entity_type=EntityType.RANSOMWARE,
            is_illicit=True,
            typology=self.TYPOLOGY_NAME,
            scenario_id=scenario_id,
            obfuscation_level=obfuscation_level,
            true_cluster_id=cluster_id,
        )

        # Collector gets unique collection addresses
        collection_addrs = self.addr_gen.generate_batch(n_victims, "p2wpkh")
        collector.addresses.extend(collection_addrs)

        # Allocate operator IP
        use_tor = obfuscation_level >= 2
        use_vpn = obfuscation_level >= 1
        ip, net = self.network.allocate_entity_ip(use_tor=use_tor, use_vpn=use_vpn)
        collector.operator_ips.append(ip)
        collector.country = net.country
        collector.asn = net.asn
        collector.asn_org = net.asn_org

        # Generate victim payments over a few days
        collection_window = min(7 * 86400, (end_ts - start_ts) * 0.3)
        collection_start = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.2)

        collected_amounts: list[tuple[str, str, int]] = []  # (addr, script, amount)

        for i in range(n_victims):
            ts = collection_start + self.rng.uniform(0, collection_window)
            victim_addr, victim_script = self.addr_gen.generate()

            # Some variation in ransom amount
            variation = int(self.rng.normal(0, ransom_amount * 0.05))
            amount = ransom_amount + variation

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[(victim_addr, victim_script)],
                input_amounts=[amount + int(self.rng.integers(500, 5000))],
                output_addresses=[collection_addrs[i]],
            )
            transactions.append(tx)
            collected_amounts.append((collection_addrs[i][0], collection_addrs[i][1], amount))

        # Phase 2: Consolidation — sweep collection to 1-2 addresses
        consolidation_addr = self.addr_gen.generate("p2wpkh")
        collector.addresses.append(consolidation_addr)

        consol_ts = collection_start + collection_window + self.rng.uniform(3600, 86400)

        # Batch consolidation transactions (groups of 5-10 inputs)
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
                is_illicit=True,
                typology=self.TYPOLOGY_NAME,
                scenario_id=scenario_id,
                obfuscation_level=obfuscation_level,
                true_cluster_id=cluster_id,
            )

            next_addr = self.addr_gen.generate("p2wpkh")
            layer_entity.addresses.append(next_addr)

            lip, lnet = self.network.allocate_entity_ip(use_vpn=use_vpn, use_tor=use_tor)
            layer_entity.operator_ips.append(lip)
            layer_entity.country = lnet.country
            layer_entity.asn = lnet.asn
            layer_entity.asn_org = lnet.asn_org

            # Apply delay based on obfuscation
            delay = self.rng.uniform(
                600 * (obfuscation_level + 1),
                7200 * (obfuscation_level + 1),
            )
            layer_ts += delay

            fee = int(self.rng.integers(1000, 10000))
            current_amount -= fee

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
        # Pick a legit exchange to cash out to
        exchange_entities = [e for e in legit_entities if e.entity_type == EntityType.EXCHANGE_HOT]
        if exchange_entities:
            target_exchange = self.rng.choice(exchange_entities)
            target_addr = self.rng.choice(target_exchange.addresses)
        else:
            target_addr = self.addr_gen.generate("p2wpkh")

        fee = int(self.rng.integers(1000, 10000))
        tx = self.tx_builder.build_simple(
            timestamp=cashout_ts,
            input_addresses=[current_addr],
            input_amounts=[current_amount - fee],
            output_addresses=[target_addr],
        )
        transactions.append(tx)

        # Collect all entities
        entities.append(collector)
        entities.extend(layer_entities)

        # Record txids on entities
        for tx in transactions:
            collector.transactions.append(tx.txid)

        return ScenarioResult(
            scenario_id=scenario_id,
            typology=self.TYPOLOGY_NAME,
            entities=entities,
            transactions=transactions,
            obfuscation_level=obfuscation_level,
        )
