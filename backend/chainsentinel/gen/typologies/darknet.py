"""T2: Darknet Market — escrow hub with buyers and vendor payouts."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult
from chainsentinel.gen.transactions import BTC, Transaction


class DarknetMarketTypology(BaseTypology):
    """Darknet market escrow hub: buyers deposit → hub → vendor batch payouts."""

    TYPOLOGY_CODE = "T2"
    TYPOLOGY_NAME = "darknet_market"

    def generate(self, start_ts, end_ts, obfuscation_level, legit_entities) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities, transactions = [], []

        n_buyers = int(self.rng.integers(20, 101))
        n_vendors = int(self.rng.integers(5, 21))
        commission_rate = float(self.rng.uniform(0.02, 0.05))

        # Hub entity
        hub = Entity(
            entity_id=self._next_entity_id(), entity_type=EntityType.DARKNET_MARKET,
            is_illicit=True, typology=self.TYPOLOGY_NAME, scenario_id=scenario_id,
            obfuscation_level=obfuscation_level, true_cluster_id=cluster_id,
        )
        hub_addrs = self.addr_gen.generate_batch(n_buyers + 5, "p2sh")
        hub.addresses.extend(hub_addrs)
        ip, net = self.network.allocate_entity_ip(use_tor=obfuscation_level >= 1)
        hub.operator_ips.append(ip)
        hub.country, hub.asn, hub.asn_org = net.country, net.asn, net.asn_org

        # Vendor entities
        vendor_entities = []
        vendor_addrs = []
        for _ in range(n_vendors):
            v = Entity(
                entity_id=self._next_entity_id(), entity_type=EntityType.DARKNET_MARKET,
                is_illicit=True, typology=self.TYPOLOGY_NAME, scenario_id=scenario_id,
                obfuscation_level=obfuscation_level, true_cluster_id=cluster_id,
            )
            va = self.addr_gen.generate("p2wpkh")
            v.addresses.append(va)
            vip, vnet = self.network.allocate_entity_ip(use_tor=obfuscation_level >= 2)
            v.operator_ips.append(vip)
            v.country, v.asn, v.asn_org = vnet.country, vnet.asn, vnet.asn_org
            vendor_entities.append(v)
            vendor_addrs.append(va)

        # Buyer deposits over the time range
        op_window = (end_ts - start_ts) * 0.6
        op_start = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.2)
        vendor_pools = [0] * n_vendors  # Track pending amounts per vendor

        for i in range(n_buyers):
            ts = op_start + self.rng.uniform(0, op_window)
            buyer_addr, buyer_script = self.addr_gen.generate()
            amount = int(self.rng.uniform(0.001 * BTC, 0.5 * BTC))
            vendor_idx = int(self.rng.integers(0, n_vendors))

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[(buyer_addr, buyer_script)],
                input_amounts=[amount + int(self.rng.integers(500, 5000))],
                output_addresses=[hub_addrs[i % len(hub_addrs)]],
            )
            transactions.append(tx)
            vendor_pools[vendor_idx] += amount

        # Periodic vendor payouts (batch)
        n_payout_rounds = int(self.rng.integers(3, 8))
        payout_ts = op_start + op_window * 0.5

        for _round in range(n_payout_rounds):
            payout_ts += self.rng.uniform(12 * 3600, 48 * 3600)
            # Pay out vendors with accumulated funds
            hub_input_addr = self.rng.choice(hub_addrs)
            payout_outputs = []
            payout_amounts = []
            total_payout = 0

            for vi in range(n_vendors):
                if vendor_pools[vi] > 0:
                    payout_amount = int(vendor_pools[vi] * (1 - commission_rate) / n_payout_rounds)
                    if payout_amount >= 546:
                        payout_outputs.append(vendor_addrs[vi])
                        payout_amounts.append(payout_amount)
                        total_payout += payout_amount

            if payout_outputs and total_payout > 0:
                fee = int(self.rng.integers(2000, 10000))
                tx = self.tx_builder.build_simple(
                    timestamp=payout_ts,
                    input_addresses=[hub_input_addr],
                    input_amounts=[total_payout + fee],
                    output_addresses=payout_outputs,
                    output_amounts=payout_amounts,
                    fee=fee,
                )
                transactions.append(tx)

        entities.append(hub)
        entities.extend(vendor_entities)
        for tx in transactions:
            hub.transactions.append(tx.txid)

        return ScenarioResult(scenario_id=scenario_id, typology=self.TYPOLOGY_NAME,
                              entities=entities, transactions=transactions,
                              obfuscation_level=obfuscation_level)
