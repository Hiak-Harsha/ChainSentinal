"""T4: CoinJoin/Mixer — equal-value outputs mixing transaction."""

from __future__ import annotations

from chainsentinel.gen.entities import Entity, EntityType
from chainsentinel.gen.typologies.base import BaseTypology, ScenarioResult
from chainsentinel.gen.transactions import BTC, Transaction


class CoinJoinTypology(BaseTypology):
    """CoinJoin/mixer: multiple participants create txs with equal-value outputs."""

    TYPOLOGY_CODE = "T4"
    TYPOLOGY_NAME = "coinjoin_mixer"

    def generate(self, start_ts, end_ts, obfuscation_level, legit_entities) -> ScenarioResult:
        scenario_id = self._next_scenario_id()
        cluster_id = self._next_cluster_id()
        entities, transactions = [], []

        n_participants = int(self.rng.integers(5, 51))
        n_rounds = int(self.rng.integers(1, 4))
        denomination = int(self.rng.choice([
            int(0.01 * BTC), int(0.05 * BTC), int(0.1 * BTC), int(0.5 * BTC),
        ]))

        mixer_entity = Entity(
            entity_id=self._next_entity_id(), entity_type=EntityType.MIXER,
            is_illicit=True, typology=self.TYPOLOGY_NAME, scenario_id=scenario_id,
            obfuscation_level=obfuscation_level, true_cluster_id=cluster_id,
        )
        ip, net = self.network.allocate_entity_ip(use_tor=True)
        mixer_entity.operator_ips.append(ip)
        mixer_entity.country, mixer_entity.asn = net.country, net.asn
        mixer_entity.asn_org = net.asn_org

        ts = self._random_timestamp(start_ts, start_ts + (end_ts - start_ts) * 0.5)

        for _round in range(n_rounds):
            # All participants contribute inputs
            input_addrs = []
            input_amounts = []
            for _ in range(n_participants):
                addr = self.addr_gen.generate("p2wpkh")
                input_addrs.append(addr)
                # Input = denomination + fee share + random excess
                input_amounts.append(denomination + int(self.rng.integers(1000, 50000)))

            # Equal-value outputs for all participants
            output_addrs = []
            for _ in range(n_participants):
                addr = self.addr_gen.generate("p2wpkh")
                output_addrs.append(addr)
                mixer_entity.addresses.append(addr)

            # Change outputs for excess
            change_addrs = []
            for _ in range(n_participants):
                if self.rng.random() > 0.3:  # Not all have change
                    addr = self.addr_gen.generate("p2wpkh")
                    change_addrs.append(addr)

            total_in = sum(input_amounts)
            total_denom = denomination * n_participants
            fee = int(self.rng.integers(5000, 30000))
            if total_in <= total_denom + fee + 546:
                fee = max(1000, total_in - total_denom - 1000)

            remaining = total_in - total_denom - fee

            final_outputs = list(output_addrs)
            final_amounts = [denomination] * n_participants

            if change_addrs and remaining >= len(change_addrs) * 546:
                from chainsentinel.gen.transactions import partition_amount
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

            ts += self.rng.uniform(3600, 86400)

        entities.append(mixer_entity)

        return ScenarioResult(scenario_id=scenario_id, typology=self.TYPOLOGY_NAME,
                              entities=entities, transactions=transactions,
                              obfuscation_level=obfuscation_level)
