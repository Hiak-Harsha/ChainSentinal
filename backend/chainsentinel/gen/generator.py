"""Main generator orchestrator — generates the complete synthetic dataset v2.

Coordinating:
1. Legitimate entity population with diverse archetypes
2. Illicit scenarios across 9 typologies with probabilistic IP allocation
3. Realistic legitimate traffic generation (batched withdrawals 20-200, sweeps, co-spends, payroll)
4. Strict invariant: legit traffic share >= 90% and never zero
5. 100% ground truth coverage per entity AND per address
6. Network simulation with Poisson trickling and sensor_id vantage points
7. Serialization to CSV, JSON (array AND NDJSON), XML, ground_truth.json, config.json
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
from numpy.random import Generator

from chainsentinel.gen.config import GeneratorConfig
from chainsentinel.gen.entities import Entity, EntityPopulation, EntityType
from chainsentinel.gen.network import NetworkSimulator
from chainsentinel.gen.transactions import (
    AddressGenerator,
    TransactionBuilder,
    Transaction,
    BTC,
    DUST_LIMIT,
)
from chainsentinel.gen.typologies.base import ScenarioResult
from chainsentinel.gen.typologies.ransomware import RansomwareTypology
from chainsentinel.gen.typologies.darknet import DarknetMarketTypology
from chainsentinel.gen.typologies.peel_chain import PeelChainTypology
from chainsentinel.gen.typologies.coinjoin import CoinJoinTypology
from chainsentinel.gen.typologies.layering import LayeringTypology
from chainsentinel.gen.typologies.structuring import StructuringTypology
from chainsentinel.gen.typologies.extortion import ExtortionTypology
from chainsentinel.gen.typologies.dusting import DustingTypology
from chainsentinel.gen.typologies.multi_cluster import MultiClusterTypology
from chainsentinel.gen.serializers import (
    write_csv,
    write_json,
    write_ndjson,
    write_xml,
    write_ground_truth,
    write_config,
)


def run_generator(
    tx_count: int = 100_000,
    seed: int = 42,
    output_dir: str = "data/generated",
    formats: list[str] | None = None,
    preset: str | None = None,
) -> Path:
    """Run the complete synthetic data generation pipeline v2."""
    if formats is None:
        formats = ["csv", "json", "xml"]

    config = GeneratorConfig(
        seed=seed,
        total_tx=tx_count,
        output_dir=output_dir,
        formats=formats,
        preset=preset,
    )
    target_total = config.total_tx

    print(f"[ChainSentinel Generator v2] seed={seed}, target_tx={target_total:,}, preset={preset or 'custom'}")
    t_start = time.time()

    # Scale entity counts with target_total
    scale = target_total / 100_000
    config.n_retail_users = max(30, int(300 * scale))
    config.n_merchants = max(4, int(25 * scale))
    config.n_exchange_hot = max(2, int(8 * scale))
    config.n_exchange_cold = max(1, int(4 * scale))
    config.n_payroll = max(2, int(10 * scale))
    config.n_mining_pools = max(1, int(5 * scale))
    config.n_gambling = max(2, int(8 * scale))
    config.n_custodial = max(2, int(10 * scale))

    rng = np.random.default_rng(seed)
    addr_gen = AddressGenerator(rng)
    tx_builder = TransactionBuilder(rng)
    network = NetworkSimulator(rng, n_sensors=config.n_sensors, n_relay_nodes=config.n_relay_nodes)

    # ── Step 1: Generate legit entities ──
    print("  [1/6] Generating legitimate entities...")
    entity_pop = EntityPopulation(rng, addr_gen, network)
    legit_entities = entity_pop.generate_all_legit(
        n_retail=config.n_retail_users,
        n_merchant=config.n_merchants,
        n_exchange_hot=config.n_exchange_hot,
        n_exchange_cold=config.n_exchange_cold,
        n_payroll=config.n_payroll,
        n_mining=config.n_mining_pools,
        n_gambling=config.n_gambling,
        n_custodial=config.n_custodial,
    )
    print(f"    -> {len(legit_entities)} legit entities created")

    # ── Step 2: Compute target legit share BEFORE scenarios & generate illicit ──
    print("  [2/6] Generating illicit scenarios (max allowed <= 10% of total)...")
    entity_counter = [entity_pop._entity_counter]
    cluster_counter = [entity_pop._cluster_counter]
    scenario_counter = [0]

    # For smaller test runs (e.g. 500 tx), scale scenario repetitions to keep illicit <= 10%
    scenario_scale = min(1.0, max(0.15, target_total / 100_000))
    typology_classes = [
        (RansomwareTypology, max(1, int(config.n_ransomware * scenario_scale))),
        (DarknetMarketTypology, max(1, int(config.n_darknet * scenario_scale))),
        (PeelChainTypology, max(1, int(config.n_peel_chain * scenario_scale))),
        (CoinJoinTypology, max(1, int(config.n_coinjoin * scenario_scale))),
        (LayeringTypology, max(1, int(config.n_layering * scenario_scale))),
        (StructuringTypology, max(1, int(config.n_structuring * scenario_scale))),
        (ExtortionTypology, max(1, int(config.n_extortion * scenario_scale))),
        (DustingTypology, max(1, int(config.n_dusting * scenario_scale))),
        (MultiClusterTypology, max(1, int(config.n_multi_cluster * scenario_scale))),
    ]

    all_scenarios: list[ScenarioResult] = []
    illicit_entities: list[Entity] = []
    illicit_txs: list[Transaction] = []

    for typ_class, count in typology_classes:
        typology = typ_class(
            rng=rng,
            addr_gen=addr_gen,
            tx_builder=tx_builder,
            network=network,
            entity_counter=entity_counter,
            cluster_counter=cluster_counter,
            scenario_counter=scenario_counter,
        )
        for _ in range(count):
            obf_level = int(rng.choice([0, 1, 2, 3], p=config.obfuscation_weights))
            scenario = typology.generate(
                start_ts=config.start_timestamp,
                end_ts=config.end_timestamp,
                obfuscation_level=obf_level,
                legit_entities=legit_entities,
            )
            all_scenarios.append(scenario)
            illicit_entities.extend(scenario.entities)
            illicit_txs.extend(scenario.transactions)

    print(f"    -> {len(all_scenarios)} scenarios generated ({len(illicit_txs)} illicit transactions)")

    # ── Step 3: Enforce legit share >= 90% and generate realistic legit transactions ──
    print("  [3/6] Generating realistic legitimate transactions (target >= 90% legit share)...")
    min_required_legit = int(np.ceil(len(illicit_txs) * (config.min_legit_ratio / (1.0 - config.min_legit_ratio))))
    legit_target = max(int(target_total * config.min_legit_ratio), min_required_legit, target_total - len(illicit_txs))
    if legit_target <= 0:
        legit_target = max(100, min_required_legit)

    legit_txs = _generate_legit_transactions_v2(
        rng=rng,
        tx_builder=tx_builder,
        entities=legit_entities,
        target_count=legit_target,
        config=config,
    )
    print(f"    -> {len(legit_txs)} legit transactions generated")

    all_txs = illicit_txs + legit_txs
    total_tx_actual = len(all_txs)
    legit_share = len(legit_txs) / total_tx_actual if total_tx_actual > 0 else 0.0

    # Invariant assertion
    if legit_share < config.min_legit_ratio or len(legit_txs) == 0:
        raise ValueError(
            f"Generation failed invariant: legit share {legit_share:.3f} < {config.min_legit_ratio:.3f} or legit_txs is zero"
        )
    print(f"    -> Legit traffic share: {legit_share * 100:.2f}% (>= 90.0% invariant verified)")

    # Sort all transactions chronologically
    all_txs.sort(key=lambda t: t.timestamp)

    # ── Step 4: Network simulation with Poisson trickling & sensor_id ──
    print("  [4/6] Simulating network relay observations with Poisson trickling & sensor vantage points...")
    all_entities_list = legit_entities + illicit_entities
    entity_ip_map: dict[str, str] = {}
    for e in all_entities_list:
        for addr, _ in e.addresses:
            if e.operator_ips:
                entity_ip_map[addr] = e.operator_ips[0]

    observations = []
    for tx in all_txs:
        origin_ip = None
        for inp in tx.inputs:
            if inp.address in entity_ip_map:
                origin_ip = entity_ip_map[inp.address]
                break

        if origin_ip is None:
            origin_ip = str(rng.choice(network.relay_ips))

        relay_obs = network.simulate_relay(
            origin_ip=origin_ip,
            origin_ts=tx.timestamp,
            relay_mean_delay=config.relay_mean_delay_s,
            gossip_mean_delay=config.gossip_mean_delay_s,
        )

        for obs in relay_obs:
            net_info = network.get_network_info(obs["src_ip"])
            record = {
                "timestamp": obs["timestamp"],
                "sensor_id": obs["sensor_id"],
                "src_ip": obs["src_ip"],
                "dst_ip": obs["dst_ip"],
                "src_port": obs["src_port"],
                "dst_port": obs["dst_port"],
                "txid": tx.txid,
                "input_addresses": [inp.address for inp in tx.inputs],
                "input_amounts": [inp.amount for inp in tx.inputs],
                "output_addresses": [out.address for out in tx.outputs],
                "output_amounts": [out.amount for out in tx.outputs],
                "fee": tx.fee,
                "script_type": tx.script_types[0] if tx.script_types else "p2wpkh",
                "geo_country": net_info.country if net_info else "US",
                "asn": f"AS{net_info.asn}" if net_info and net_info.asn else "AS0",
                "is_anonymizer": bool(net_info.is_tor or net_info.is_vpn or net_info.is_hosting) if net_info else False,
            }
            observations.append(record)

    observations.sort(key=lambda o: o["timestamp"])
    print(f"    -> {len(observations)} total observations created")

    # ── Step 5: Ground truth with 100% address label coverage ──
    print("  [5/6] Compiling ground truth (verifying 100% address label coverage)...")
    clusters: dict[str, list[str]] = {}
    for e in all_entities_list:
        if e.true_cluster_id:
            clusters.setdefault(e.true_cluster_id, []).append(e.entity_id)

    # Address ground truth dictionary
    address_ground_truth: dict[str, dict[str, Any]] = {}
    for e in all_entities_list:
        address_ground_truth.update(e.get_address_ground_truth())

    # Verify 100% label coverage across all transactions
    missing_addrs = set()
    for tx in all_txs:
        for inp in tx.inputs:
            if inp.address not in address_ground_truth:
                missing_addrs.add(inp.address)
        for out in tx.outputs:
            if out.address not in address_ground_truth:
                missing_addrs.add(out.address)

    if missing_addrs:
        raise AssertionError(f"Ground truth label coverage failure: {len(missing_addrs)} unlabeled addresses found! Example: {list(missing_addrs)[:5]}")
    print(f"    -> 100% address label coverage verified ({len(address_ground_truth)} unique addresses labeled)")

    typology_counts: dict[str, int] = {}
    for s in all_scenarios:
        typology_counts[s.typology] = typology_counts.get(s.typology, 0) + 1

    obf_dist: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
    for s in all_scenarios:
        obf_dist[s.obfuscation_level] += 1

    ground_truth = {
        "generator_version": "2.0.0",
        "seed": seed,
        "config": config.to_dict(),
        "entities": [e.to_ground_truth() for e in all_entities_list],
        "addresses": address_ground_truth,
        "scenarios": [s.to_ground_truth() for s in all_scenarios],
        "clusters": clusters,
        "statistics": {
            "total_tx": len(all_txs),
            "total_observations": len(observations),
            "illicit_tx": len(illicit_txs),
            "legit_tx": len(legit_txs),
            "legit_share": round(legit_share, 4),
            "label_coverage": 1.0,
            "illicit_entities": len(illicit_entities),
            "legit_entities": len(legit_entities),
            "n_scenarios": len(all_scenarios),
            "typology_counts": typology_counts,
            "obfuscation_distribution": obf_dist,
        },
    }

    # ── Step 6: Write output files ──
    print("  [6/6] Writing output files (CSV, JSON array, NDJSON, XML, ground_truth, config)...")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if "csv" in formats:
        write_csv(observations, out_path / "observations.csv")
        print(f"    -> observations.csv ({len(observations):,} rows)")

    if "json" in formats:
        # Emit standard JSON array
        write_json(observations, out_path / "observations.json", as_array=True)
        # Also emit NDJSON for high-performance streaming ingest
        write_ndjson(observations, out_path / "observations.ndjson")
        print(f"    -> observations.json (array) and observations.ndjson ({len(observations):,} records)")

    if "xml" in formats:
        write_xml(observations, out_path / "observations.xml")
        print(f"    -> observations.xml ({len(observations):,} records)")

    write_ground_truth(ground_truth, out_path / "ground_truth.json")
    write_config(config.to_dict(), out_path / "config.json")

    network.close()
    elapsed = time.time() - t_start
    print(f"\n[Done] Generated {len(all_txs):,} txs ({legit_share * 100:.1f}% legit), {len(observations):,} observations in {elapsed:.1f}s")
    print(f"  Output directory: {out_path.resolve()}")

    return out_path


def _generate_legit_transactions_v2(
    rng: Generator,
    tx_builder: TransactionBuilder,
    entities: list[Entity],
    target_count: int,
    config: GeneratorConfig,
) -> list[Transaction]:
    """Generate realistic legitimate transactions representing distinct archetypes:

    - Retail wallets: multi-input co-spend across own addresses + change output
    - Merchants: periodic sweep / consolidation (many inputs -> 1-2 outputs)
    - Exchanges: batched customer withdrawals (20-100 outputs) + cold sweeps
    - Payroll: one-to-many batched salary payouts
    - Mining pools: pool payouts (1 input -> 15-40 miner outputs + pool fee)
    - Gambling: rapid in/out round amounts
    - Custodial: deposits and sweeps
    """
    if not entities or target_count <= 0:
        return []

    transactions: list[Transaction] = []

    # Partition entities by archetype
    retail = [e for e in entities if e.entity_type == EntityType.RETAIL]
    merchants = [e for e in entities if e.entity_type == EntityType.MERCHANT]
    exchange_hot = [e for e in entities if e.entity_type == EntityType.EXCHANGE_HOT]
    exchange_cold = [e for e in entities if e.entity_type == EntityType.EXCHANGE_COLD]
    payrolls = [e for e in entities if e.entity_type == EntityType.PAYROLL]
    miners = [e for e in entities if e.entity_type == EntityType.MINING_POOL]
    gambling = [e for e in entities if e.entity_type == EntityType.GAMBLING]
    custodial = [e for e in entities if e.entity_type == EntityType.CUSTODIAL]

    time_span = config.end_timestamp - config.start_timestamp

    # 1. Retail multi-input co-spend with change (45% of traffic)
    n_retail_tx = int(target_count * 0.45)
    for _ in range(n_retail_tx):
        if len(transactions) >= target_count:
            break
        u = rng.choice(retail)
        ts = float(rng.uniform(config.start_timestamp, config.end_timestamp))

        # Select 1 to 3 inputs from retail user's addresses
        n_in = int(rng.integers(1, min(4, len(u.addresses) + 1)))
        in_choices = rng.choice(len(u.addresses), size=n_in, replace=False)
        input_tuples = []
        for idx in in_choices:
            addr, st = u.addresses[idx]
            amt = int(rng.integers(50_000, 3_000_000))
            input_tuples.append((addr, st, amt))

        total_in = sum(amt for _, _, amt in input_tuples)

        # Destination entity: merchant, another retail user, exchange, or gambling
        dest_roll = rng.random()
        if dest_roll < 0.50 and merchants:
            dest_entity = rng.choice(merchants)
        elif dest_roll < 0.75 and len(retail) > 1:
            dest_entity = rng.choice([r for r in retail if r is not u] or retail)
        elif dest_roll < 0.90 and exchange_hot:
            dest_entity = rng.choice(exchange_hot)
        elif gambling:
            dest_entity = rng.choice(gambling)
        else:
            dest_entity = rng.choice(entities)

        dest_addr = dest_entity.addresses[rng.integers(0, len(dest_entity.addresses))]

        # Generate a registered change address for retail user
        change_addr = tx_builder.addr_gen.generate("p2wpkh")
        u.add_address(change_addr[0], change_addr[1], role="retail_change")

        payment_amt = max(1000, int(total_in * rng.uniform(0.15, 0.65)))

        tx = tx_builder.build_retail_cospend(
            timestamp=ts,
            inputs=input_tuples,
            dest_addr=dest_addr,
            payment_amount=payment_amt,
            change_addr=change_addr,
        )
        transactions.append(tx)
        u.transactions.append(tx.txid)
        dest_entity.transactions.append(tx.txid)

    # 2. Merchant consolidation sweeps (many small in -> 1-2 outputs) (15% of traffic)
    n_merchant_tx = int(target_count * 0.15)
    for _ in range(n_merchant_tx):
        if len(transactions) >= target_count:
            break
        m = rng.choice(merchants)
        ts = float(rng.uniform(config.start_timestamp, config.end_timestamp))

        # Sweep 5-15 merchant deposit addresses
        n_in = int(rng.integers(3, min(16, len(m.addresses) + 1)))
        in_choices = rng.choice(len(m.addresses), size=n_in, replace=False)
        input_tuples = []
        for idx in in_choices:
            addr, st = m.addresses[idx]
            amt = int(rng.integers(20_000, 500_000))
            input_tuples.append((addr, st, amt))

        # Destination: merchant treasury address or cold storage
        vault_addr = tx_builder.addr_gen.generate("p2wpkh")
        m.add_address(vault_addr[0], vault_addr[1], role="merchant_sweep")

        tx = tx_builder.build_merchant_sweep(
            timestamp=ts,
            inputs=input_tuples,
            dest_addrs=[vault_addr],
        )
        transactions.append(tx)
        m.transactions.append(tx.txid)

    # 3. Exchange batched withdrawals (20-100 outputs) & rebalances (15% of traffic)
    n_exchange_tx = int(target_count * 0.15)
    for _ in range(n_exchange_tx):
        if len(transactions) >= target_count:
            break
        ex = rng.choice(exchange_hot)
        ts = float(rng.uniform(config.start_timestamp, config.end_timestamp))

        # 1-3 inputs from exchange hot wallet
        n_in = int(rng.integers(1, min(4, len(ex.addresses) + 1)))
        in_choices = rng.choice(len(ex.addresses), size=n_in, replace=False)
        input_tuples = []
        for idx in in_choices:
            addr, st = ex.addresses[idx]
            amt = int(rng.integers(5_000_000, 50_000_000))
            input_tuples.append((addr, st, amt))

        # Batched customer withdrawal recipients (drawn from retail users)
        # Requirement: batched withdrawals with 20-200 outputs
        n_recipients = int(rng.integers(20, min(101, max(21, len(retail) * 2))))
        customer_addrs = []
        for _ in range(n_recipients):
            u = rng.choice(retail)
            c_addr = u.addresses[rng.integers(0, len(u.addresses))]
            customer_addrs.append(c_addr)

        # Exchange change address
        ex_change = tx_builder.addr_gen.generate("p2wpkh")
        ex.add_address(ex_change[0], ex_change[1], role="exchange_change")

        tx = tx_builder.build_exchange_batch(
            timestamp=ts,
            inputs=input_tuples,
            customer_addrs=customer_addrs,
            change_addr=ex_change,
        )
        transactions.append(tx)
        ex.transactions.append(tx.txid)

    # 4. Payroll one-to-many batching (8% of traffic)
    n_payroll_tx = int(target_count * 0.08)
    for _ in range(n_payroll_tx):
        if len(transactions) >= target_count:
            break
        p = rng.choice(payrolls)
        ts = float(rng.uniform(config.start_timestamp, config.end_timestamp))

        p_in_addr, p_in_st = p.addresses[rng.integers(0, len(p.addresses))]
        n_employees = int(rng.integers(10, min(35, len(retail) + 1)))
        employee_addrs = []
        for emp_u in rng.choice(retail, size=n_employees, replace=False):
            employee_addrs.append(emp_u.addresses[0])

        salary_base = int(rng.integers(500_000, 3_000_000))
        total_salary_needed = salary_base * n_employees + 100_000

        p_change = tx_builder.addr_gen.generate("p2wpkh")
        p.add_address(p_change[0], p_change[1], role="payroll_change")

        tx = tx_builder.build_payroll_batch(
            timestamp=ts,
            inputs=[(p_in_addr, p_in_st, total_salary_needed + 500_000)],
            employee_addrs=employee_addrs,
            salary_base=salary_base,
            change_addr=p_change,
        )
        transactions.append(tx)
        p.transactions.append(tx.txid)

    # 5. Mining pool payouts (7% of traffic)
    n_mining_tx = int(target_count * 0.07)
    for _ in range(n_mining_tx):
        if len(transactions) >= target_count:
            break
        pool = rng.choice(miners)
        ts = float(rng.uniform(config.start_timestamp, config.end_timestamp))

        coinbase_addr, cb_st = pool.addresses[0]
        n_miners = int(rng.integers(10, min(30, len(retail) + 1)))
        miner_addrs = []
        for m_user in rng.choice(retail, size=n_miners, replace=False):
            miner_addrs.append(m_user.addresses[0])

        pool_fee_addr = tx_builder.addr_gen.generate("p2wpkh")
        pool.add_address(pool_fee_addr[0], pool_fee_addr[1], role="pool_fee")

        reward = int(3.125 * BTC)
        tx = tx_builder.build_mining_payout(
            timestamp=ts,
            coinbase_input=(coinbase_addr, cb_st, reward),
            miner_addrs=miner_addrs,
            pool_fee_addr=pool_fee_addr,
        )
        transactions.append(tx)
        pool.transactions.append(tx.txid)

    # 6. Gambling and Custodial fills the remainder
    remainder = max(0, target_count - len(transactions))
    for _ in range(remainder):
        g = rng.choice(gambling)
        u = rng.choice(retail)
        ts = float(rng.uniform(config.start_timestamp, config.end_timestamp))

        u_addr, u_st = u.addresses[0]
        g_addr, g_st = g.addresses[0]

        # Round amount
        amount = int(rng.choice([100_000, 250_000, 500_000, 1_000_000, 2_500_000]))
        fee = int(rng.integers(500, 3000))

        if rng.random() > 0.4:
            # User deposit to gambling house
            ch_addr = tx_builder.addr_gen.generate("p2wpkh")
            u.add_address(ch_addr[0], ch_addr[1], role="retail_change")
            tx = tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[(u_addr, u_st)],
                input_amounts=[amount + fee + 50_000],
                output_addresses=[(g_addr, g_st), ch_addr],
                output_amounts=[amount, 50_000],
                fee=fee,
            )
        else:
            # Gambling payout to user
            g_ch = tx_builder.addr_gen.generate("p2wpkh")
            g.add_address(g_ch[0], g_ch[1], role="gambling_change")
            tx = tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[(g_addr, g_st)],
                input_amounts=[amount + fee + 200_000],
                output_addresses=[(u_addr, u_st), g_ch],
                output_amounts=[amount, 200_000],
                fee=fee,
            )

        transactions.append(tx)
        g.transactions.append(tx.txid)
        u.transactions.append(tx.txid)

    return transactions
