"""T4: CoinJoin/Mixer — equal-value outputs mixing transaction."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.transactions import BTC, Transaction, partition_amount
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult


class CoinJoinTypology(BaseTypology):
    """CoinJoin/mixer: multiple participants create txs with equal-value outputs."""

    TYPOLOGY_CODE = "T4"
    TYPOLOGY_NAME = "coinjoin_mixer"

    def generate(self, start_ts: float, end_ts: float, obfuscation_level: int, legit_entities: list[Entity]) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities: list[Entity] = []
        transactions: list[Transaction] = []

        n_participants = int(self.rng.integers(5, 25))
        n_rounds = int(self.rng.integers(1, 3))
        denomination = int(self.rng.choice([
            int(0.01 * BTC), int(0.05 * BTC), int(0.1 * BTC), int(0.5 * BTC),
        ]))

        mixer_entity = Entity(
            entity_id=self._next_entity_id(),
            entity_type=EntityType.MIXER,
            role="mixer_coordinator",
            is_illicit=True,
            typology=self.TYPOLOGY_NAME,
            scenario_id=scenario_id,
            obfuscation_level=obfuscation_level,
            true_cluster_id=cluster_id,
        )
        ip, net = self.network.allocate_entity_ip(
            is_illicit=True,
            obfuscation_level=obfuscation_level,
            archetype="mixer",
        )
        mixer_entity.operator_ips.append(ip)
        mixer_entity.country, mixer_entity.asn = net.country, net.asn
        mixer_entity.asn_org = net.asn_org
        entities.append(mixer_entity)

        # Generate participant entities (mix of illicit actors and legit counterparties)
        participants: list[Entity] = []
        for i in range(n_participants):
            is_ill = (i < max(2, n_participants // 3))
            p_entity = Entity(
                entity_id=self._next_entity_id(),
                entity_type=EntityType.MIXER if is_ill else EntityType.RETAIL,
                role="mix_participant" if is_ill else "counterparty",
                is_illicit=is_ill,
                typology=self.TYPOLOGY_NAME if is_ill else None,
                scenario_id=scenario_id if is_ill else None,
                obfuscation_level=obfuscation_level if is_ill else 0,
                true_cluster_id=cluster_id if is_ill else self._next_cluster_id(),
            )
            pip, pnet = self.network.allocate_entity_ip(
                is_illicit=is_ill,
                obfuscation_level=obfuscation_level if is_ill else 0,
                archetype="retail",
            )
            p_entity.operator_ips.append(pip)
            p_entity.country, p_entity.asn, p_entity.asn_org = pnet.country, pnet.asn, pnet.asn_org
            participants.append(p_entity)
            entities.append(p_entity)

        ts = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.5)

        for _round in range(n_rounds):
            input_addrs = []
            input_amounts = []
            output_addrs = []
            change_addrs = []

            for p in participants:
                in_addr = self.addr_gen.generate("p2wpkh")
                p.add_address(in_addr[0], in_addr[1], role=p.role)
                input_addrs.append(in_addr)
                input_amounts.append(denomination + int(self.rng.integers(5000, 50000)))

                out_addr = self.addr_gen.generate("p2wpkh")
                p.add_address(out_addr[0], out_addr[1], role="mixed_output")
                output_addrs.append(out_addr)

                if self.rng.random() > 0.3:
                    ch_addr = self.addr_gen.generate("p2wpkh")
                    p.add_address(ch_addr[0], ch_addr[1], role="change")
                    change_addrs.append(ch_addr)

            total_in = sum(input_amounts)
            total_denom = denomination * len(participants)
            fee = int(self.rng.integers(5000, 25000))
            if total_in <= total_denom + fee + 546:
                fee = max(1000, total_in - total_denom - 1000)

            remaining = total_in - total_denom - fee
            final_outputs = list(output_addrs)
            final_amounts = [denomination] * len(participants)

            if change_addrs and remaining >= len(change_addrs) * 546:
                change_amounts = partition_amount(self.rng, remaining, len(change_addrs), min_per_item=546)
                final_outputs.extend(change_addrs)
                final_amounts.extend(change_amounts)
            else:
                fee += max(0, remaining)

            tx = self.tx_builder.build_simple(
                timestamp=ts,
                input_addresses=input_addrs,
                input_amounts=input_amounts,
                output_addresses=final_outputs,
                output_amounts=final_amounts,
                fee=fee,
            )

            transactions.append(tx)
            mixer_entity.transactions.append(tx.txid)
            for p in participants:
                p.transactions.append(tx.txid)

            ts += self.rng.uniform(3600, 86400)

        return ScenarioResult(
            scenario_id=scenario_id,
            typology=self.TYPOLOGY_NAME,
            entities=entities,
            transactions=transactions,
            obfuscation_level=obfuscation_level,
        )
