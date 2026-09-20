"""T2: Darknet Market — escrow hub with buyers and vendor payouts."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.transactions import BTC, Transaction
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult


class DarknetMarketTypology(BaseTypology):
    """Darknet market escrow hub: buyers deposit → hub → vendor batch payouts."""

    TYPOLOGY_CODE = "T2"
    TYPOLOGY_NAME = "darknet_market"

    def generate(self, start_ts: float, end_ts: float, obfuscation_level: int, legit_entities: list[Entity]) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities: list[Entity] = []
        transactions: list[Transaction] = []

        n_buyers = int(self.rng.integers(15, 45))
        n_vendors = int(self.rng.integers(3, 10))
        commission_rate = float(self.rng.uniform(0.02, 0.05))

        # Hub entity
        hub = Entity(
            entity_id=self._next_entity_id(),
            entity_type=EntityType.DARKNET_MARKET,
            role="darknet_market",
            is_illicit=True,
            typology=self.TYPOLOGY_NAME,
            scenario_id=scenario_id,
            obfuscation_level=obfuscation_level,
            true_cluster_id=cluster_id,
        )
        hub_addrs = self.addr_gen.generate_batch(n_buyers + 5, "p2sh")
        for ha in hub_addrs:
            hub.add_address(ha[0], ha[1], role="market_escrow")

        ip, net = self.network.allocate_entity_ip(
            is_illicit=True,
            obfuscation_level=obfuscation_level,
            archetype="darknet_market",
        )
        hub.operator_ips.append(ip)
        hub.country, hub.asn, hub.asn_org = net.country, net.asn, net.asn_org
        entities.append(hub)

        # Vendor entities
        vendor_entities: list[Entity] = []
        vendor_addrs: list[tuple[str, str]] = []
        for _ in range(n_vendors):
            v = Entity(
                entity_id=self._next_entity_id(),
                entity_type=EntityType.DARKNET_MARKET,
                role="vendor",
                is_illicit=True,
                typology=self.TYPOLOGY_NAME,
                scenario_id=scenario_id,
                obfuscation_level=obfuscation_level,
                true_cluster_id=cluster_id,
            )
            va = self.addr_gen.generate("p2wpkh")
            v.add_address(va[0], va[1], role="vendor")

            vip, vnet = self.network.allocate_entity_ip(
                is_illicit=True,
                obfuscation_level=obfuscation_level,
                archetype="darknet_market",
            )
            v.operator_ips.append(vip)
            v.country, v.asn, v.asn_org = vnet.country, vnet.asn, vnet.asn_org
            vendor_entities.append(v)
            vendor_addrs.append(va)
            entities.append(v)

        # Buyer deposits
        op_window = (end_ts - start_ts) * 0.6
        op_start = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.2)
        vendor_pools = [0] * n_vendors

        for i in range(n_buyers):
            ts = op_start + self.rng.uniform(0, op_window)
            b_addr = self.addr_gen.generate("p2wpkh")
            bip, bnet = self.network.allocate_entity_ip(archetype="retail", is_illicit=False)

            buyer = Entity(
                entity_id=self._next_entity_id(),
                entity_type=EntityType.RETAIL,
                role="buyer",
                is_illicit=False,
                typology=self.TYPOLOGY_NAME,
                scenario_id=scenario_id,
                true_cluster_id=self._next_cluster_id(),
                operator_ips=[bip],
                country=bnet.country,
                asn=bnet.asn,
                asn_org=bnet.asn_org,
            )
            buyer.add_address(b_addr[0], b_addr[1], role="buyer")
            entities.append(buyer)

            deposit_amount = int(self.rng.uniform(0.01 * BTC, 0.5 * BTC))
            vendor_idx = int(self.rng.integers(0, n_vendors))
            vendor_pools[vendor_idx] += int(deposit_amount * (1 - commission_rate))

            escrow_addr = hub_addrs[i]

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[b_addr],
                input_amounts=[deposit_amount + int(self.rng.integers(500, 5000))],
                output_addresses=[escrow_addr],
            )
            transactions.append(tx)
            hub.transactions.append(tx.txid)
            buyer.transactions.append(tx.txid)

        # Vendor batch payouts
        payout_ts = op_start + op_window + self.rng.uniform(3600, 86400)
        for v_idx, pool_amount in enumerate(vendor_pools):
            if pool_amount <= 546:
                continue
            v_addr = vendor_addrs[v_idx]
            fee = int(self.rng.integers(1000, 5000))
            hub_funding = [hub_addrs[(v_idx * 3 + j) % len(hub_addrs)] for j in range(2)]

            tx = self.tx_builder.build_simple(
                timestamp=payout_ts + v_idx * 300,
                input_addresses=hub_funding,
                input_amounts=[pool_amount // 2 + fee, pool_amount - pool_amount // 2],
                output_addresses=[v_addr],
                fee=fee,
            )
            transactions.append(tx)
            hub.transactions.append(tx.txid)
            vendor_entities[v_idx].transactions.append(tx.txid)

        return ScenarioResult(
            scenario_id=scenario_id,
            typology=self.TYPOLOGY_NAME,
            entities=entities,
            transactions=transactions,
            obfuscation_level=obfuscation_level,
        )
