"""Entity resolution pipeline orchestrating CIOH, CoinJoin exclusion, and change heuristics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import hashlib
import time
from typing import Any

from chainsentinel.graph.change_detector import ChangeAddressDetector
from chainsentinel.graph.coinjoin_detector import CoinJoinDetector
from chainsentinel.graph.entity_classifier import EntityClassifier
from chainsentinel.graph.hetero_graph import HeteroGraph
from chainsentinel.graph.union_find import DisjointSet
from chainsentinel.storage.db import DatabaseManager


@dataclass
class ResolutionSummary:
    total_addresses: int = 0
    total_entities: int = 0
    coinjoin_txs_excluded: int = 0
    change_addresses_linked: int = 0
    largest_cluster_size: int = 0
    entity_type_breakdown: dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_addresses": self.total_addresses,
            "total_entities": self.total_entities,
            "coinjoin_txs_excluded": self.coinjoin_txs_excluded,
            "change_addresses_linked": self.change_addresses_linked,
            "largest_cluster_size": self.largest_cluster_size,
            "entity_type_breakdown": self.entity_type_breakdown,
            "duration_seconds": round(self.duration_seconds, 3),
        }


class EntityResolver:
    """Orchestrates multi-input co-spend clustering, change-address linking, and graph generation."""

    def __init__(
        self,
        db: DatabaseManager,
        change_threshold: float = 0.75,
        min_coinjoin_outputs: int = 3,
    ) -> None:
        self.db = db
        self.change_threshold = change_threshold
        self.cj_detector = CoinJoinDetector(min_equal_outputs=min_coinjoin_outputs)
        self.change_detector = ChangeAddressDetector(confidence_threshold=change_threshold)

    def run(self) -> tuple[ResolutionSummary, HeteroGraph]:
        """Execute complete entity resolution and heterogeneous graph construction."""
        start_time = time.time()
        summary = ResolutionSummary()

        # 1. Fetch data from DuckDB
        data = self.db.get_clustering_data()
        txs = data["transactions"]
        inputs = data["inputs"]
        outputs = data["outputs"]
        observations = data["observations"]

        # Group inputs and outputs by txid
        tx_inputs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for inp in inputs:
            tx_inputs[inp["txid"]].append(inp)

        tx_outputs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for out in outputs:
            tx_outputs[out["txid"]].append(out)

        tx_map: dict[str, dict[str, Any]] = {tx["txid"]: tx for tx in txs}

        # Track address first seen timestamps
        addr_first_seen: dict[str, float] = {}
        for inp in inputs:
            addr = inp.get("address")
            tx = tx_map.get(inp["txid"])
            if addr and tx:
                ts = float(tx.get("first_seen_ts", 0.0))
                addr_first_seen[addr] = min(addr_first_seen.get(addr, ts), ts)

        for out in outputs:
            addr = out.get("address")
            tx = tx_map.get(out["txid"])
            if addr and tx:
                ts = float(tx.get("first_seen_ts", 0.0))
                addr_first_seen[addr] = min(addr_first_seen.get(addr, ts), ts)

        dsu: DisjointSet[str] = DisjointSet()
        address_method: dict[str, tuple[str, float]] = {}

        # 2. CoinJoin detection pass (exclude from CIOH)
        coinjoin_txids: set[str] = set()
        for txid, in_list in tx_inputs.items():
            out_list = tx_outputs.get(txid, [])
            is_cj, cj_conf, _ = self.cj_detector.analyze(in_list, out_list)
            if is_cj and cj_conf >= 0.6:
                coinjoin_txids.add(txid)

        summary.coinjoin_txs_excluded = len(coinjoin_txids)

        # 3. Multi-Input Co-spend Clustering (CIOH)
        for txid, in_list in tx_inputs.items():
            if txid in coinjoin_txids:
                # SKIP Common-Input heuristic on CoinJoin to prevent cluster collapse
                for inp in in_list:
                    if inp.get("address"):
                        dsu.add(inp["address"])
                continue

            # Gather valid addresses
            addrs = [inp["address"] for inp in in_list if inp.get("address")]
            if not addrs:
                continue

            root_addr = addrs[0]
            dsu.add(root_addr)
            if root_addr not in address_method:
                address_method[root_addr] = ("CIOH_BASE", 1.0)

            for other_addr in addrs[1:]:
                dsu.add(other_addr)
                dsu.union(root_addr, other_addr)
                address_method[other_addr] = ("CIOH_COSPEND", 1.0)

        # 4. Change-Address Heuristic pass
        change_linked_count = 0
        for txid, in_list in tx_inputs.items():
            if txid in coinjoin_txids:
                continue

            out_list = tx_outputs.get(txid, [])
            if len(out_list) != 2:
                continue

            tx = tx_map.get(txid)
            tx_ts = float(tx.get("first_seen_ts", 0.0)) if tx else None

            chg_addr, chg_conf, _ = self.change_detector.detect_change(
                inputs=in_list,
                outputs=out_list,
                address_first_seen=addr_first_seen,
                tx_timestamp=tx_ts,
            )

            if chg_addr and chg_conf >= self.change_threshold:
                # Merge change address with first input address
                first_in_addr = in_list[0].get("address")
                if first_in_addr:
                    dsu.add(chg_addr)
                    dsu.union(first_in_addr, chg_addr)
                    address_method[chg_addr] = ("CHANGE_HEURISTIC", chg_conf)
                    change_linked_count += 1

        summary.change_addresses_linked = change_linked_count

        # 5. Ensure all output addresses are registered in DSU
        for out_list in tx_outputs.values():
            for out in out_list:
                addr = out.get("address")
                if addr:
                    dsu.add(addr)
                    if addr not in address_method:
                        address_method[addr] = ("OUTPUT_SINGLETON", 1.0)

        # 6. Extract components and build Entity records
        components = dsu.get_components()
        summary.total_addresses = len(dsu)
        summary.total_entities = len(components)

        entities_batch: list[dict[str, Any]] = []
        aem_batch: list[dict[str, Any]] = []
        now_ts = time.time()

        # Map each address to its entity_id
        addr_to_entity: dict[str, str] = {}
        entity_stats: dict[str, dict[str, Any]] = {}

        for root, addrs in components.items():
            if len(addrs) > summary.largest_cluster_size:
                summary.largest_cluster_size = len(addrs)

            # Deterministic entity id from sorted addresses
            sorted_addrs = sorted(addrs)
            ent_hash = hashlib.sha256(":".join(sorted_addrs[:10]).encode()).hexdigest()[:12]
            entity_id = f"ENT_{ent_hash}"

            for a in addrs:
                addr_to_entity[a] = entity_id
                method, conf = address_method.get(a, ("SINGLETON", 1.0))
                aem_batch.append({
                    "address": a,
                    "entity_id": entity_id,
                    "confidence": conf,
                    "method": method,
                })

            entity_stats[entity_id] = {
                "entity_id": entity_id,
                "addrs": addrs,
                "total_received": 0,
                "total_sent": 0,
                "incoming_txs": [],
                "outgoing_txs": [],
                "first_seen": min(addr_first_seen.get(a, now_ts) for a in addrs),
                "last_seen": max(addr_first_seen.get(a, 0.0) for a in addrs),
                "coinjoin_count": 0,
            }

        # 7. Aggregate financial metrics & classify entity types
        for txid, in_list in tx_inputs.items():
            for inp in in_list:
                addr = inp.get("address")
                if addr and addr in addr_to_entity:
                    ent_id = addr_to_entity[addr]
                    entity_stats[ent_id]["total_sent"] += int(inp.get("amount", 0))
                    entity_stats[ent_id]["outgoing_txs"].append(tx_map.get(txid, {}))
                    if txid in coinjoin_txids:
                        entity_stats[ent_id]["coinjoin_count"] += 1

        for txid, out_list in tx_outputs.items():
            for out in out_list:
                addr = out.get("address")
                if addr and addr in addr_to_entity:
                    ent_id = addr_to_entity[addr]
                    entity_stats[ent_id]["total_received"] += int(out.get("amount", 0))
                    entity_stats[ent_id]["incoming_txs"].append(tx_map.get(txid, {}))

        for ent_id, stat in entity_stats.items():
            etype, econf, _ = EntityClassifier.classify(
                member_addrs=stat["addrs"],
                incoming_txs=stat["incoming_txs"],
                outgoing_txs=stat["outgoing_txs"],
                total_received=stat["total_received"],
                total_sent=stat["total_sent"],
                coinjoin_tx_count=stat["coinjoin_count"],
            )
            summary.entity_type_breakdown[etype] = summary.entity_type_breakdown.get(etype, 0) + 1

            entities_batch.append({
                "entity_id": ent_id,
                "entity_type": etype,
                "member_count": len(stat["addrs"]),
                "resolution_conf": econf,
                "first_seen": stat["first_seen"],
                "last_seen": stat["last_seen"],
                "total_received_sat": stat["total_received"],
                "total_sent_sat": stat["total_sent"],
                "created_at": now_ts,
            })

        # 8. Build Heterogeneous Graph
        graph = HeteroGraph()

        # Add entity nodes
        for ent in entities_batch:
            graph.add_node(
                node_id=ent["entity_id"],
                node_type="Entity",
                label=ent["entity_id"],
                entity_type=ent["entity_type"],
                member_count=ent["member_count"],
                volume_sats=ent["total_received_sat"] + ent["total_sent_sat"],
            )

        # Add address nodes and member_of edges
        for aem in aem_batch:
            graph.add_node(
                node_id=aem["address"],
                node_type="Address",
                label=aem["address"][:8] + "...",
                entity_id=aem["entity_id"],
            )
            graph.add_edge(
                source=aem["address"],
                target=aem["entity_id"],
                edge_type="member_of",
                weight=aem["confidence"],
                method=aem["method"],
            )

        # Add transaction nodes and spend/fund edges
        for tx in txs:
            txid = tx["txid"]
            graph.add_node(
                node_id=txid,
                node_type="Transaction",
                label=txid[:8] + "...",
                timestamp=tx.get("first_seen_ts", 0.0),
                total_sat=tx.get("total_in", 0),
                fee_sat=tx.get("fee_sat", 0),
            )

        for inp in inputs:
            addr = inp.get("address")
            if addr:
                graph.add_edge(
                    source=addr,
                    target=inp["txid"],
                    edge_type="spends",
                    weight=float(inp.get("amount", 1)),
                )

        for out in outputs:
            addr = out.get("address")
            if addr:
                graph.add_edge(
                    source=out["txid"],
                    target=addr,
                    edge_type="funds",
                    weight=float(out.get("amount", 1)),
                )

        # Add IP nodes and observed_from edges
        for ob in observations:
            src_ip = ob.get("src_ip")
            txid = ob.get("txid")
            if src_ip and txid:
                if src_ip not in graph.nodes:
                    graph.add_node(
                        node_id=src_ip,
                        node_type="IP",
                        label=src_ip,
                        country=ob.get("src_country", ""),
                        asn=ob.get("src_asn", ""),
                        is_anonymizer=bool(ob.get("is_anonymizer", False)),
                    )
                graph.add_edge(
                    source=txid,
                    target=src_ip,
                    edge_type="observed_from",
                    weight=1.0,
                    timestamp=ob.get("ts", 0.0),
                )

        # 9. Persist to DuckDB
        self.db.clear_graph_resolution()
        self.db.insert_entities_batch(entities_batch)
        self.db.insert_address_entity_map_batch(aem_batch)
        summary.duration_seconds = time.time() - start_time
        return summary, graph

    def merge_incremental(
        self,
        new_inputs: list[dict[str, Any]],
        new_outputs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Incrementally merge newly ingested transaction inputs and outputs into existing clusters.

        Avoids full table re-clustering by resolving only the affected addresses via Union-Find,
        updating their cluster entity IDs in DuckDB in O(k * alpha(N)) time.
        """
        start_time = time.time()
        conn = self.db.conn

        # 1. Group inputs by txid
        tx_inputs: dict[str, list[str]] = defaultdict(list)
        for inp in new_inputs:
            addr = inp.get("address")
            txid = inp.get("txid")
            if addr and txid:
                tx_inputs[txid].append(addr)

        all_affected_addrs: set[str] = set()
        for addrs in tx_inputs.values():
            all_affected_addrs.update(addrs)

        if not all_affected_addrs:
            return {"merged_addresses": 0, "entities_updated": 0, "duration_sec": 0.0}

        # 2. Fetch current entity mappings for affected addresses
        placeholders = ", ".join(["?"] * len(all_affected_addrs))
        rows = conn.execute(
            f"SELECT address, entity_id FROM address_entity_map WHERE address IN ({placeholders})",
            list(all_affected_addrs),
        ).fetchall()
        existing_aem: dict[str, str] = dict(rows)

        # 3. Use DisjointSet to union co-spends in new transactions
        dsu: DisjointSet[str] = DisjointSet()
        for txid, addrs in tx_inputs.items():
            if len(addrs) >= 2:
                for i in range(len(addrs) - 1):
                    dsu.union(addrs[i], addrs[i + 1])

        # 4. Map each component to existing entity ID or generate a new entity ID
        components = dsu.components()
        updated_aem: list[dict[str, Any]] = []
        entities_updated = 0

        for comp in components:
            # Check if any address already has an entity ID
            known_entity_ids = {existing_aem[addr] for addr in comp if addr in existing_aem}
            if known_entity_ids:
                target_entity = sorted(known_entity_ids)[0]
            else:
                seed = sorted(comp)[0]
                target_entity = f"ent_{hashlib.sha256(seed.encode()).hexdigest()[:12]}"

            for addr in comp:
                updated_aem.append({
                    "address": addr,
                    "entity_id": target_entity,
                    "confidence": 1.0,
                    "method": "CIOH_INCREMENTAL",
                })
            entities_updated += 1

        # 5. Persist batch updates
        if updated_aem:
            self.db.insert_address_entity_map_batch(updated_aem)

        duration = time.time() - start_time
        return {
            "merged_addresses": len(updated_aem),
            "entities_updated": entities_updated,
            "duration_sec": round(duration, 4),
        }
