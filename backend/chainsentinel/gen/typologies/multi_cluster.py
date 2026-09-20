"""T9: Multi-cluster operator — seemingly independent clusters sharing IPs/subnets."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.transactions import BTC, Transaction
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult


class MultiClusterTypology(BaseTypology):
    """Multi-cluster operator: 2-4 clusters that appear independent but share IPs/subnets."""

    TYPOLOGY_CODE = "T9"
    TYPOLOGY_NAME = "multi_cluster"

    def generate(self, start_ts: float, end_ts: float, obfuscation_level: int, legit_entities: list[Entity]) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        entities: list[Entity] = []
        transactions: list[Transaction] = []

        n_clusters = int(self.rng.integers(2, 4))
        n_entities_per_cluster = int(self.rng.integers(2, 5))

        # Shared operator IPs
        shared_ips = self.network.allocate_multiple_ips(
            count=int(self.rng.integers(2, 4)),
            is_illicit=True,
            obfuscation_level=obfuscation_level,
            archetype="multi_cluster",
        )
        shared_ip_list = [ip for ip, _ in shared_ips]

        for cluster_i in range(n_clusters):
            cluster_id = self._next_cluster_id()

            for _ in range(n_entities_per_cluster):
                entity = Entity(
                    entity_id=self._next_entity_id(),
                    entity_type=EntityType.MULTI_CLUSTER,
                    role="operator_cluster",
                    is_illicit=True,
                    typology=self.TYPOLOGY_NAME,
                    scenario_id=scenario_id,
                    obfuscation_level=obfuscation_level,
                    true_cluster_id=cluster_id,
                )

                n_addrs = int(self.rng.integers(2, 6))
                addrs = self.addr_gen.generate_batch(n_addrs)
                for a in addrs:
                    entity.add_address(a[0], a[1], role="operator_cluster")

                # Key: share IPs across clusters
                if self.rng.random() > 0.3:
                    entity.operator_ips.append(self.rng.choice(shared_ip_list))
                else:
                    ip, net = self.network.allocate_entity_ip(
                        is_illicit=True,
                        obfuscation_level=obfuscation_level,
                        archetype="multi_cluster",
                    )
                    entity.operator_ips.append(ip)
                    entity.country, entity.asn = net.country, net.asn
                    entity.asn_org = net.asn_org

                ts = self._random_timestamp(start_ts, end_ts)
                n_txs = int(self.rng.integers(2, 8))

                for _ in range(n_txs):
                    ts += self.rng.uniform(600, 86400)
                    if ts > end_ts:
                        break

                    amount = int(self.rng.uniform(0.01 * BTC, 1.5 * BTC))

                    # Counterparty entity for interaction
                    other_addr = self.addr_gen.generate("p2wpkh")
                    cip, cnet = self.network.allocate_entity_ip(archetype="retail", is_illicit=False)
                    counterparty = Entity(
                        entity_id=self._next_entity_id(),
                        entity_type=EntityType.RETAIL,
                        role="counterparty",
                        is_illicit=False,
                        typology=self.TYPOLOGY_NAME,
                        scenario_id=scenario_id,
                        true_cluster_id=self._next_cluster_id(),
                        operator_ips=[cip],
                        country=cnet.country,
                        asn=cnet.asn,
                        asn_org=cnet.asn_org,
                    )
                    counterparty.add_address(other_addr[0], other_addr[1], role="counterparty")
                    entities.append(counterparty)

                    if self.rng.random() > 0.5 and entity.addresses:
                        tx = self.tx_builder.build_simple(
                            timestamp=ts,
                            input_addresses=[self.rng.choice(entity.addresses)],
                            input_amounts=[amount + int(self.rng.integers(500, 10000))],
                            output_addresses=[other_addr],
                        )
                    else:
                        target = self.rng.choice(entity.addresses)
                        tx = self.tx_builder.build_simple(
                            timestamp=ts,
                            input_addresses=[other_addr],
                            input_amounts=[amount + int(self.rng.integers(500, 10000))],
                            output_addresses=[target],
                        )

                    transactions.append(tx)
                    entity.transactions.append(tx.txid)
                    counterparty.transactions.append(tx.txid)

                entities.append(entity)

        return ScenarioResult(
            scenario_id=scenario_id,
            typology=self.TYPOLOGY_NAME,
            entities=entities,
            transactions=transactions,
            obfuscation_level=obfuscation_level,
        )
