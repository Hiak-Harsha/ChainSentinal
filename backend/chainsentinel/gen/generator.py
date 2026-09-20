"""Main generator orchestrator — generates the complete synthetic dataset.

This is the entry point called by `chainsentinel generate`. It coordinates:
1. Entity population generation (legit + illicit)
2. Transaction generation for each entity
3. Network relay simulation (observations)
4. Serialization to CSV/JSON/XML
5. Ground truth output
"""

from __future__ import annotations

import time
from pathlib import Path

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
from chainsentinel.gen.serializers import write_csv, write_json, write_xml, write_ground_truth, write_config


def run_generator(
    tx_count: int = 100_000,
    seed: int = 42,
    output_dir: str = "data/generated",
    formats: list[str] | None = None,
) -> Path:
    """Run the complete data generation pipeline.

    Args:
        tx_count: Target number of transactions.
        seed: Random seed for reproducibility.
        output_dir: Output directory path.
        formats: List of output formats (csv, json, xml).

    Returns:
        Path to the output directory.
    """
    if formats is None:
        formats = ["csv", "json", "xml"]

    print(f"[ChainSentinel Generator] seed={seed}, target_tx={tx_count:,}")
    t_start = time.time()

    config = GeneratorConfig(
        seed=seed,
        total_tx=tx_count,
        output_dir=output_dir,
        formats=formats,
    )

    # Scale entity counts with tx_count
    scale = tx_count / 100_000
    config.n_retail_users = max(50, int(300 * scale))
    config.n_merchants = max(5, int(25 * scale))
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
    print(f"    -> {len(legit_entities)} legit entities")

    # ── Step 2: Generate illicit scenarios ──
    print("  [2/6] Generating illicit scenarios...")
    entity_counter = [entity_pop._entity_counter]
    cluster_counter = [entity_pop._cluster_counter]
    scenario_counter = [0]

    typology_classes = [
        (RansomwareTypology, config.n_ransomware),
        (DarknetMarketTypology, config.n_darknet),
        (PeelChainTypology, config.n_peel_chain),
        (CoinJoinTypology, config.n_coinjoin),
        (LayeringTypology, config.n_layering),
        (StructuringTypology, config.n_structuring),
        (ExtortionTypology, config.n_extortion),
        (DustingTypology, config.n_dusting),
        (MultiClusterTypology, config.n_multi_cluster),
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
            # Assign obfuscation level
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

    print(f"    -> {len(all_scenarios)} scenarios, {len(illicit_entities)} illicit entities, {len(illicit_txs)} illicit txs")

    # ── Step 3: Generate legit transactions to fill up to target count ──
    print("  [3/6] Generating legitimate transactions...")
    legit_tx_target = max(0, tx_count - len(illicit_txs))
    legit_txs = _generate_legit_transactions(
        rng, tx_builder, legit_entities, legit_tx_target, config
    )
    print(f"    -> {len(legit_txs)} legit txs")

    # ── Step 4: Combine and generate network observations ──
    print("  [4/6] Simulating network relay observations...")
    all_txs = illicit_txs + legit_txs
    # Sort by timestamp for chronological order
    all_txs.sort(key=lambda t: t.timestamp)

    # Build entity IP lookup
    entity_ip_map: dict[str, str] = {}
    for e in legit_entities + illicit_entities:
        for addr, _ in e.addresses:
            if e.operator_ips:
                entity_ip_map[addr] = e.operator_ips[0]

    observations = []
    for tx in all_txs:
        # Determine origin IP from input addresses
        origin_ip = None
        for inp in tx.inputs:
            if inp.address in entity_ip_map:
                origin_ip = entity_ip_map[inp.address]
                break

        if origin_ip is None:
            # Fallback: random relay node
            origin_ip = rng.choice(network.relay_ips)

        # Simulate P2P relay and get sensor observations
        relay_obs = network.simulate_relay(
            origin_ip=origin_ip,
            origin_ts=tx.timestamp,
            relay_mean_delay=config.relay_mean_delay_s,
            gossip_mean_delay=config.gossip_mean_delay_s,
        )

        # Build observation records
        for obs in relay_obs:
            net_info = network.get_network_info(obs["src_ip"])
            record = {
                "timestamp": obs["timestamp"],
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
            }

            # Add geo/ASN if available
            if net_info:
                record["geo_country"] = net_info.country
                record["asn"] = f"AS{net_info.asn}"
            else:
                record["geo_country"] = ""
                record["asn"] = ""

            observations.append(record)

    print(f"    -> {len(observations)} total observations")

    # ── Step 5: Write output files ──
    print("  [5/6] Writing output files...")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if "csv" in formats:
        write_csv(observations, out_path / "observations.csv")
        print(f"    -> observations.csv ({len(observations)} rows)")

    if "json" in formats:
        write_json(observations, out_path / "observations.json")
        print(f"    -> observations.json ({len(observations)} rows)")

    if "xml" in formats:
        write_xml(observations, out_path / "observations.xml")
        print(f"    -> observations.xml ({len(observations)} rows)")

    # ── Step 6: Write ground truth ──
    print("  [6/6] Writing ground truth...")

    # Build cluster mapping
    all_entities = legit_entities + illicit_entities
    clusters: dict[str, list[str]] = {}
    for e in all_entities:
        if e.true_cluster_id:
            clusters.setdefault(e.true_cluster_id, []).append(e.entity_id)

    # Typology counts
    typology_counts: dict[str, int] = {}
    for s in all_scenarios:
        typology_counts[s.typology] = typology_counts.get(s.typology, 0) + 1

    # Obfuscation level distribution
    obf_dist: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
    for s in all_scenarios:
        obf_dist[s.obfuscation_level] += 1

    ground_truth = {
        "generator_version": "1.0.0",
        "seed": seed,
        "config": config.to_dict(),
        "entities": [e.to_ground_truth() for e in all_entities],
        "scenarios": [s.to_ground_truth() for s in all_scenarios],
        "clusters": clusters,
        "statistics": {
            "total_tx": len(all_txs),
            "total_observations": len(observations),
            "illicit_tx": len(illicit_txs),
            "legit_tx": len(legit_txs),
            "illicit_entities": len(illicit_entities),
            "legit_entities": len(legit_entities),
            "n_scenarios": len(all_scenarios),
            "typology_counts": typology_counts,
            "obfuscation_distribution": obf_dist,
        },
    }
    write_ground_truth(ground_truth, out_path / "ground_truth.json")
    write_config(config.to_dict(), out_path / "config.json")

    elapsed = time.time() - t_start
    print(f"\n[Done] Generated {len(all_txs):,} txs, {len(observations):,} observations in {elapsed:.1f}s")
    print(f"  Output: {out_path.resolve()}")

    return out_path


def _generate_legit_transactions(
    rng: Generator,
    tx_builder: TransactionBuilder,
    entities: list[Entity],
    target_count: int,
    config: GeneratorConfig,
) -> list[Transaction]:
    """Generate legitimate transactions between entities.

    Distributes transactions proportionally to each entity's tx_rate_per_day.
    """
    if not entities or target_count <= 0:
        return []

    transactions = []
    time_range = config.end_timestamp - config.start_timestamp
    days = time_range / 86400

    # Calculate expected txs per entity
    total_rate = sum(e.tx_rate_per_day for e in entities)
    if total_rate <= 0:
        return []

    for entity in entities:
        # Number of txs for this entity
        expected = int(entity.tx_rate_per_day * days * (target_count / (total_rate * days)))
        n_txs = max(1, min(expected, target_count // len(entities) * 3))

        for _ in range(n_txs):
            if len(transactions) >= target_count:
                break

            # Generate timestamp within active hours
            ts = _generate_entity_timestamp(rng, entity, config)

            # Pick amount from entity's distribution
            amount = max(
                1000,
                int(rng.normal(entity.amount_mean, max(1, entity.amount_std))),
            )

            if not entity.addresses:
                continue

            # Pick input address from entity
            input_addr = entity.addresses[rng.integers(0, len(entity.addresses))]

            # Pick output — sometimes to another entity, sometimes to new address
            if rng.random() > 0.3 and len(entities) > 1:
                # Send to another entity
                other = entities[rng.integers(0, len(entities))]
                while other is entity and len(entities) > 1:
                    other = entities[rng.integers(0, len(entities))]
                if other.addresses:
                    output_addr = other.addresses[rng.integers(0, len(other.addresses))]
                else:
                    output_addr = tx_builder.addr_gen.generate()
            else:
                output_addr = tx_builder.addr_gen.generate()

            tx = tx_builder.build_simple(
                timestamp=ts,
                input_addresses=[input_addr],
                input_amounts=[amount + int(rng.integers(500, 10000))],
                output_addresses=[output_addr],
            )
            transactions.append(tx)
            entity.transactions.append(tx.txid)

        if len(transactions) >= target_count:
            break

    return transactions[:target_count]


def _generate_entity_timestamp(
    rng: Generator, entity: Entity, config: GeneratorConfig
) -> float:
    """Generate a timestamp respecting entity's active hours and weekend ratio."""
    ts = float(rng.uniform(config.start_timestamp, config.end_timestamp))

    # Adjust for active hours (simple rejection sampling, max 10 tries)
    for _ in range(10):
        # Extract hour of day (UTC)
        hour = int((ts % 86400) / 3600)
        start_h, end_h = entity.active_hours
        if start_h <= hour < end_h:
            break
        ts = float(rng.uniform(config.start_timestamp, config.end_timestamp))

    return ts
