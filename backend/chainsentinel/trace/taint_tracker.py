"""Forensic taint tracking engine supporting forward, backward, and multi-model decay propagation."""

from __future__ import annotations

from collections import deque
import math
import time
from typing import Any

from chainsentinel.storage.db import DatabaseManager


class TaintTracker:
    """Propagates and accounts for satoshi taint across Bitcoin transaction graphs."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def trace(
        self,
        root_ref: str,
        direction: str = "forward",
        initial_taint_sat: int | None = None,
        max_hops: int = 5,
        decay_model: str = "proportional",
        min_taint_ratio: float = 0.01,
        stop_at_exchange: bool = True,
        stop_at_mixer: bool = True,
    ) -> dict[str, Any]:
        """Execute taint tracing from a root transaction hash, address, or entity ID."""
        direction = direction.lower()
        decay_model = decay_model.lower()

        if direction == "forward":
            return self._trace_forward(
                root_ref=root_ref,
                initial_taint_sat=initial_taint_sat,
                max_hops=max_hops,
                decay_model=decay_model,
                min_taint_ratio=min_taint_ratio,
                stop_at_exchange=stop_at_exchange,
                stop_at_mixer=stop_at_mixer,
            )
        elif direction == "backward":
            return self._trace_backward(
                root_ref=root_ref,
                target_taint_sat=initial_taint_sat,
                max_hops=max_hops,
                decay_model=decay_model,
                min_taint_ratio=min_taint_ratio,
                stop_at_exchange=stop_at_exchange,
                stop_at_mixer=stop_at_mixer,
            )
        elif direction == "both":
            fwd = self._trace_forward(
                root_ref=root_ref,
                initial_taint_sat=initial_taint_sat,
                max_hops=max_hops,
                decay_model=decay_model,
                min_taint_ratio=min_taint_ratio,
                stop_at_exchange=stop_at_exchange,
                stop_at_mixer=stop_at_mixer,
            )
            bwd = self._trace_backward(
                root_ref=root_ref,
                target_taint_sat=initial_taint_sat,
                max_hops=max_hops,
                decay_model=decay_model,
                min_taint_ratio=min_taint_ratio,
                stop_at_exchange=stop_at_exchange,
                stop_at_mixer=stop_at_mixer,
            )
            return self._combine_traces(fwd, bwd, root_ref, decay_model, max_hops)
        else:
            raise ValueError(f"Invalid trace direction '{direction}'. Must be 'forward', 'backward', or 'both'.")

    def _get_entity_info(self, address: str) -> tuple[str, str]:
        """Lookup entity ID and classification for an address."""
        conn = self.db.conn
        row = conn.execute(
            """
            SELECT m.entity_id, COALESCE(e.entity_type, 'INDIVIDUAL')
            FROM address_entity_map m
            LEFT JOIN entities e ON m.entity_id = e.entity_id
            WHERE m.address = ?
            """,
            [address],
        ).fetchone()
        if row:
            return str(row[0]), str(row[1])
        return f"ADDR_{address[:8]}", "INDIVIDUAL"

    def _get_tx_origin_ip(self, txid: str) -> str:
        """Fetch estimated or earliest origin IP for a transaction."""
        conn = self.db.conn
        row = conn.execute("SELECT origin_ip FROM tx_origins WHERE txid = ?", [txid]).fetchone()
        if row and row[0]:
            return str(row[0])
        obs_row = conn.execute(
            "SELECT src_ip FROM observations WHERE txid = ? ORDER BY ts ASC LIMIT 1", [txid]
        ).fetchone()
        return str(obs_row[0]) if obs_row and obs_row[0] else "UNKNOWN"

    def _trace_forward(
        self,
        root_ref: str,
        initial_taint_sat: int | None,
        max_hops: int,
        decay_model: str,
        min_taint_ratio: float,
        stop_at_exchange: bool,
        stop_at_mixer: bool,
    ) -> dict[str, Any]:
        conn = self.db.conn

        # Resolve starting transactions and taint amount
        start_txids: list[tuple[str, str, int]] = []  # (txid, source_addr, taint_sat)
        if len(root_ref) == 64 and not (root_ref.startswith("ENT-") or root_ref.startswith("ENT_")):
            # Root is a TXID
            tx_row = conn.execute(
                "SELECT txid, total_in, total_out, first_seen_ts FROM transactions WHERE txid = ?",
                [root_ref],
            ).fetchone()
            if not tx_row:
                return self._empty_trace(root_ref, "forward", decay_model, max_hops)
            in_rows = conn.execute("SELECT address, amount FROM tx_inputs WHERE txid = ?", [root_ref]).fetchall()
            src_addr = in_rows[0][0] if in_rows else "UNKNOWN"
            taint_val = initial_taint_sat if initial_taint_sat is not None else int(tx_row[2])
            start_txids.append((root_ref, src_addr, taint_val))
        else:
            # Root is an Address or Entity ID
            addr_filter = "address = ?"
            params = [root_ref]
            if root_ref.startswith("ENT-") or root_ref.startswith("ENT_") or root_ref.startswith("CLUST_"):
                addr_filter = "address IN (SELECT address FROM address_entity_map WHERE entity_id = ?)"

            tx_rows = conn.execute(
                f"""
                SELECT o.txid, o.address, o.amount
                FROM tx_outputs o
                WHERE {addr_filter}
                ORDER BY o.amount DESC
                LIMIT 10
                """,
                params,
            ).fetchall()
            for tid, a, amt in tx_rows:
                t_val = initial_taint_sat if initial_taint_sat is not None else int(amt)
                start_txids.append((tid, a, t_val))

        visited_txs: set[str] = set()
        hops: list[dict[str, Any]] = []
        endpoints: list[dict[str, Any]] = []
        cashout_exchanges: set[str] = set()
        mixers_reached: set[str] = set()
        operator_ips: set[str] = set()

        # Queue items: (current_txid, current_addr, current_taint_sat, hop_depth, prev_ts)
        queue: deque[tuple[str, str, int, int, float]] = deque()
        for tid, addr, t_sat in start_txids:
            ts_row = conn.execute("SELECT first_seen_ts FROM transactions WHERE txid = ?", [tid]).fetchone()
            first_ts = float(ts_row[0]) if ts_row and ts_row[0] is not None else time.time()
            queue.append((tid, addr, t_sat, 0, first_ts))

        while queue:
            curr_txid, src_addr, curr_taint, hop_idx, prev_ts = queue.popleft()
            if curr_txid in visited_txs or hop_idx >= max_hops:
                continue
            visited_txs.add(curr_txid)

            origin_ip = self._get_tx_origin_ip(curr_txid)
            if origin_ip != "UNKNOWN":
                operator_ips.add(origin_ip)

            # Get transaction outputs
            out_rows = conn.execute(
                "SELECT address, amount FROM tx_outputs WHERE txid = ? ORDER BY idx ASC",
                [curr_txid],
            ).fetchall()
            if not out_rows:
                continue

            total_out = sum(int(r[1]) for r in out_rows)
            if total_out <= 0:
                continue

            tx_ts_row = conn.execute("SELECT first_seen_ts FROM transactions WHERE txid = ?", [curr_txid]).fetchone()
            curr_ts = float(tx_ts_row[0]) if tx_ts_row and tx_ts_row[0] is not None else prev_ts
            dwell_time = max(0.0, curr_ts - prev_ts)

            # Compute output taints based on decay model
            output_taints: list[tuple[str, int, int, float]] = []  # (addr, amount, tainted_sat, taint_pct)

            if decay_model == "proportional":
                ratio = min(1.0, curr_taint / max(1, total_out))
                for out_addr, out_amt in out_rows:
                    out_amt_int = int(out_amt)
                    t_amt = round(out_amt_int * ratio)
                    t_pct = (t_amt / max(1, out_amt_int)) * 100.0
                    output_taints.append((out_addr, out_amt_int, t_amt, t_pct))

            elif decay_model == "fifo":
                rem_taint = curr_taint
                for out_addr, out_amt in out_rows:
                    out_amt_int = int(out_amt)
                    t_amt = min(rem_taint, out_amt_int)
                    rem_taint -= t_amt
                    t_pct = (t_amt / max(1, out_amt_int)) * 100.0
                    output_taints.append((out_addr, out_amt_int, t_amt, t_pct))

            elif decay_model == "poison":
                ratio = curr_taint / max(1, total_out)
                is_poisoned = ratio >= min_taint_ratio
                for out_addr, out_amt in out_rows:
                    out_amt_int = int(out_amt)
                    t_amt = out_amt_int if is_poisoned else 0
                    t_pct = 100.0 if is_poisoned else 0.0
                    output_taints.append((out_addr, out_amt_int, t_amt, t_pct))
            else:
                ratio = min(1.0, curr_taint / max(1, total_out))
                for out_addr, out_amt in out_rows:
                    out_amt_int = int(out_amt)
                    t_amt = round(out_amt_int * ratio)
                    output_taints.append((out_addr, out_amt_int, t_amt, (t_amt / max(1, out_amt_int)) * 100.0))

            from_ent, from_etype = self._get_entity_info(src_addr)

            for out_addr, out_amt, t_sat, t_pct in output_taints:
                if t_sat <= 0:
                    continue

                to_ent, to_etype = self._get_entity_info(out_addr)
                is_terminal = False
                stop_reason = None

                # Check Stop Conditions
                if stop_at_exchange and to_etype.upper() == "EXCHANGE":
                    is_terminal = True
                    stop_reason = "EXCHANGE_DEPOSIT"
                    cashout_exchanges.add(to_ent)
                elif stop_at_mixer and to_etype.upper() == "MIXER":
                    is_terminal = True
                    stop_reason = "MIXER_ENTRY"
                    mixers_reached.add(to_ent)
                elif (t_sat / max(1, out_amt)) < min_taint_ratio:
                    is_terminal = True
                    stop_reason = "TAINT_DILUTED"
                elif hop_idx + 1 >= max_hops:
                    is_terminal = True
                    stop_reason = "MAX_HOPS_REACHED"

                # Check for spending tx (if dormant / unspent, it's cold storage / terminal)
                spend_txs = conn.execute(
                    "SELECT txid FROM tx_inputs WHERE address = ? LIMIT 5", [out_addr]
                ).fetchall()

                if not spend_txs and not is_terminal:
                    is_terminal = True
                    stop_reason = "COLD_STORAGE_DORMANT"

                hop_record = {
                    "hop_index": hop_idx + 1,
                    "direction": "FORWARD",
                    "txid": curr_txid,
                    "from_address": src_addr,
                    "to_address": out_addr,
                    "from_entity": from_ent,
                    "to_entity": to_ent,
                    "source_entity": from_ent,
                    "target_entity": to_ent,
                    "from_entity_type": from_etype,
                    "to_entity_type": to_etype,
                    "source_type": from_etype,
                    "target_type": to_etype,
                    "transferred_sat": out_amt,
                    "tainted_sat": t_sat,
                    "taint_pct": round(t_pct, 2),
                    "dwell_time_sec": round(dwell_time, 1),
                    "origin_ip": origin_ip,
                    "is_terminal": is_terminal,
                    "stop_reason": stop_reason,
                }
                hops.append(hop_record)

                if is_terminal:
                    endpoints.append({
                        "entity_id": to_ent,
                        "address": out_addr,
                        "entity_type": to_etype,
                        "tainted_sat": t_sat,
                        "stop_reason": stop_reason,
                    })
                elif spend_txs:
                    # Enqueue forward spends
                    for s_tid in spend_txs:
                        next_txid = s_tid[0]
                        if next_txid not in visited_txs:
                            queue.append((next_txid, out_addr, t_sat, hop_idx + 1, curr_ts))

        trace_id = f"TRC-FWD-{int(time.time())}"
        summary = {
            "root_ref": root_ref,
            "direction": "FORWARD",
            "decay_model": decay_model,
            "max_hops": max_hops,
            "total_hops": len(hops),
            "total_transferred_sat": sum(h["transferred_sat"] for h in hops),
            "total_tainted_sat": sum(h["tainted_sat"] for h in hops),
            "endpoints_count": len(endpoints),
            "cashout_exchanges": sorted(list(cashout_exchanges)),
            "mixers_reached": sorted(list(mixers_reached)),
            "operator_ips": sorted(list(operator_ips)),
        }

        self.db.save_taint_trace(
            trace_id=trace_id,
            root_ref=root_ref,
            direction="FORWARD",
            decay_model=decay_model,
            max_hops=max_hops,
            hops=hops,
            summary=summary,
        )

        return {
            "trace_id": trace_id,
            "summary": summary,
            "hops": hops,
            "endpoints": endpoints,
        }

    def _trace_backward(
        self,
        root_ref: str,
        target_taint_sat: int | None,
        max_hops: int,
        decay_model: str,
        min_taint_ratio: float,
        stop_at_exchange: bool,
        stop_at_mixer: bool,
    ) -> dict[str, Any]:
        conn = self.db.conn

        start_txids: list[tuple[str, str, int]] = []
        if len(root_ref) == 64 and not (root_ref.startswith("ENT-") or root_ref.startswith("ENT_")):
            tx_row = conn.execute("SELECT total_out FROM transactions WHERE txid = ?", [root_ref]).fetchone()
            out_rows = conn.execute("SELECT address FROM tx_outputs WHERE txid = ?", [root_ref]).fetchall()
            out_addr = out_rows[0][0] if out_rows else "UNKNOWN"
            t_val = target_taint_sat if target_taint_sat is not None else (int(tx_row[0]) if tx_row else 100000)
            start_txids.append((root_ref, out_addr, t_val))
        else:
            addr_filter = "address = ?"
            params = [root_ref]
            if root_ref.startswith("ENT-") or root_ref.startswith("ENT_") or root_ref.startswith("CLUST_"):
                addr_filter = "address IN (SELECT address FROM address_entity_map WHERE entity_id = ?)"

            tx_rows = conn.execute(
                f"""
                SELECT i.txid, i.address, i.amount
                FROM tx_inputs i
                WHERE {addr_filter}
                ORDER BY i.amount DESC
                LIMIT 10
                """,
                params,
            ).fetchall()
            for tid, a, amt in tx_rows:
                t_val = target_taint_sat if target_taint_sat is not None else int(amt)
                start_txids.append((tid, a, t_val))

        visited_txs: set[str] = set()
        hops: list[dict[str, Any]] = []
        endpoints: list[dict[str, Any]] = []
        source_entities: set[str] = set()
        operator_ips: set[str] = set()

        queue: deque[tuple[str, str, int, int, float]] = deque()
        for tid, addr, t_sat in start_txids:
            ts_row = conn.execute("SELECT first_seen_ts FROM transactions WHERE txid = ?", [tid]).fetchone()
            first_ts = float(ts_row[0]) if ts_row and ts_row[0] is not None else time.time()
            queue.append((tid, addr, t_sat, 0, first_ts))

        while queue:
            curr_txid, dst_addr, curr_taint, hop_idx, next_ts = queue.popleft()
            if curr_txid in visited_txs or hop_idx >= max_hops:
                continue
            visited_txs.add(curr_txid)

            origin_ip = self._get_tx_origin_ip(curr_txid)
            if origin_ip != "UNKNOWN":
                operator_ips.add(origin_ip)

            # Look up transaction inputs (ancestors)
            in_rows = conn.execute(
                "SELECT address, amount FROM tx_inputs WHERE txid = ? ORDER BY idx ASC",
                [curr_txid],
            ).fetchall()
            if not in_rows:
                continue

            total_in = sum(int(r[1]) for r in in_rows)
            if total_in <= 0:
                continue

            tx_ts_row = conn.execute("SELECT first_seen_ts FROM transactions WHERE txid = ?", [curr_txid]).fetchone()
            curr_ts = float(tx_ts_row[0]) if tx_ts_row and tx_ts_row[0] is not None else next_ts
            dwell_time = max(0.0, next_ts - curr_ts)

            ratio = min(1.0, curr_taint / max(1, total_in))
            to_ent, to_etype = self._get_entity_info(dst_addr)

            for in_addr, in_amt in in_rows:
                in_amt_int = int(in_amt)
                t_amt = round(in_amt_int * ratio)
                if t_amt <= 0:
                    continue
                t_pct = (t_amt / max(1, in_amt_int)) * 100.0

                from_ent, from_etype = self._get_entity_info(in_addr)
                is_terminal = False
                stop_reason = None

                if stop_at_exchange and from_etype.upper() == "EXCHANGE":
                    is_terminal = True
                    stop_reason = "EXCHANGE_SOURCE"
                elif stop_at_mixer and from_etype.upper() == "MIXER":
                    is_terminal = True
                    stop_reason = "MIXER_ORIGIN"
                elif hop_idx + 1 >= max_hops:
                    is_terminal = True
                    stop_reason = "MAX_HOPS_REACHED"

                # Find ancestor transaction that created this input UTXO
                parent_txs = conn.execute(
                    "SELECT txid FROM tx_outputs WHERE address = ? LIMIT 5", [in_addr]
                ).fetchall()

                if not parent_txs and not is_terminal:
                    is_terminal = True
                    stop_reason = "COINBASE_OR_ORIGIN"

                hop_record = {
                    "hop_index": hop_idx + 1,
                    "direction": "BACKWARD",
                    "txid": curr_txid,
                    "from_address": in_addr,
                    "to_address": dst_addr,
                    "from_entity": from_ent,
                    "to_entity": to_ent,
                    "source_entity": from_ent,
                    "target_entity": to_ent,
                    "from_entity_type": from_etype,
                    "to_entity_type": to_etype,
                    "source_type": from_etype,
                    "target_type": to_etype,
                    "transferred_sat": in_amt_int,
                    "tainted_sat": t_amt,
                    "taint_pct": round(t_pct, 2),
                    "dwell_time_sec": round(dwell_time, 1),
                    "origin_ip": origin_ip,
                    "is_terminal": is_terminal,
                    "stop_reason": stop_reason,
                }
                hops.append(hop_record)

                if is_terminal:
                    endpoints.append({
                        "entity_id": from_ent,
                        "address": in_addr,
                        "entity_type": from_etype,
                        "tainted_sat": t_amt,
                        "stop_reason": stop_reason,
                    })
                    source_entities.add(from_ent)
                elif parent_txs:
                    for p_tid in parent_txs:
                        prev_txid = p_tid[0]
                        if prev_txid not in visited_txs:
                            queue.append((prev_txid, in_addr, t_amt, hop_idx + 1, curr_ts))

        trace_id = f"TRC-BWD-{int(time.time())}"
        summary = {
            "root_ref": root_ref,
            "direction": "BACKWARD",
            "decay_model": decay_model,
            "max_hops": max_hops,
            "total_hops": len(hops),
            "total_transferred_sat": sum(h["transferred_sat"] for h in hops),
            "total_tainted_sat": sum(h["tainted_sat"] for h in hops),
            "source_entities": sorted(list(source_entities)),
            "operator_ips": sorted(list(operator_ips)),
        }

        self.db.save_taint_trace(
            trace_id=trace_id,
            root_ref=root_ref,
            direction="BACKWARD",
            decay_model=decay_model,
            max_hops=max_hops,
            hops=hops,
            summary=summary,
        )

        return {
            "trace_id": trace_id,
            "summary": summary,
            "hops": hops,
            "endpoints": endpoints,
        }

    def _combine_traces(
        self,
        fwd: dict[str, Any],
        bwd: dict[str, Any],
        root_ref: str,
        decay_model: str,
        max_hops: int,
    ) -> dict[str, Any]:
        combined_hops = bwd.get("hops", []) + fwd.get("hops", [])
        combined_endpoints = bwd.get("endpoints", []) + fwd.get("endpoints", [])
        combined_ips = sorted(list(set(fwd["summary"].get("operator_ips", []) + bwd["summary"].get("operator_ips", []))))

        trace_id = f"TRC-BOTH-{int(time.time())}"
        summary = {
            "root_ref": root_ref,
            "direction": "BOTH",
            "decay_model": decay_model,
            "max_hops": max_hops,
            "total_hops": len(combined_hops),
            "forward_hops": len(fwd.get("hops", [])),
            "backward_hops": len(bwd.get("hops", [])),
            "cashout_exchanges": fwd["summary"].get("cashout_exchanges", []),
            "source_entities": bwd["summary"].get("source_entities", []),
            "operator_ips": combined_ips,
        }

        self.db.save_taint_trace(
            trace_id=trace_id,
            root_ref=root_ref,
            direction="BOTH",
            decay_model=decay_model,
            max_hops=max_hops,
            hops=combined_hops,
            summary=summary,
        )

        return {
            "trace_id": trace_id,
            "summary": summary,
            "hops": combined_hops,
            "endpoints": combined_endpoints,
        }

    def _empty_trace(self, root_ref: str, direction: str, decay_model: str, max_hops: int) -> dict[str, Any]:
        return {
            "trace_id": f"TRC-{direction[:3].upper()}-{int(time.time())}",
            "summary": {
                "root_ref": root_ref,
                "direction": direction.upper(),
                "decay_model": decay_model,
                "max_hops": max_hops,
                "total_hops": 0,
                "endpoints_count": 0,
            },
            "hops": [],
            "endpoints": [],
        }
