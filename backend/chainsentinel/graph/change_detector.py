"""Change address detection heuristics with confidence scoring."""

from __future__ import annotations

from typing import Any


class ChangeAddressDetector:
    """Detects change outputs in Bitcoin transactions using multi-signal heuristics:
    1. Address freshness (never seen before this tx)
    2. Script type affinity (matches input script type)
    3. Round-number payment heuristic (payment is round, change has irregular sats)
    4. Value bounds (change < sum(inputs))
    """

    def __init__(self, confidence_threshold: float = 0.75) -> None:
        self.confidence_threshold = confidence_threshold

    def detect_change(
        self,
        inputs: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
        address_first_seen: dict[str, float] | None = None,
        tx_timestamp: float | None = None,
    ) -> tuple[str | None, float, dict[str, Any]]:
        """Identify which output is most likely the change address.

        Returns:
            (change_address, confidence, heuristic_details)
        """
        # Change heuristics primarily apply to 2-output transactions (1 payment, 1 change)
        if len(outputs) != 2:
            return None, 0.0, {"reason": f"Outputs count is {len(outputs)}, change heuristic requires 2 outputs"}

        out0, out1 = outputs[0], outputs[1]
        addr0, addr1 = out0.get("address"), out1.get("address")
        amt0, amt1 = int(out0.get("amount", 0)), int(out1.get("amount", 0))
        script0, script1 = out0.get("script_type"), out1.get("script_type")

        if not addr0 or not addr1 or addr0 == addr1:
            return None, 0.0, {"reason": "Duplicate or missing output addresses"}

        input_addrs = {inp.get("address") for inp in inputs if inp.get("address")}
        # If one output sends back to one of the input addresses (address reuse)
        if addr0 in input_addrs and addr1 not in input_addrs:
            return addr0, 0.95, {"reason": "Exact address reuse back to input address"}
        if addr1 in input_addrs and addr0 not in input_addrs:
            return addr1, 0.95, {"reason": "Exact address reuse back to input address"}

        # Infer input script types
        # Extract script type from prefix first
        def get_script(addr: str, explicit: str | None = None) -> str:
            if addr.startswith("bc1p"):
                return "p2tr"
            if addr.startswith("bc1q"):
                return "p2wpkh"
            if addr.startswith("3"):
                return "p2sh"
            if addr.startswith("1"):
                return "p2pkh"
            return explicit or "unknown"

        in_scripts = [get_script(inp["address"], inp.get("script_type")) for inp in inputs if inp.get("address")]
        common_in_script = in_scripts[0] if in_scripts and all(s == in_scripts[0] for s in in_scripts) else None

        # Helper to check if an amount is "round"
        def is_round(sats: int) -> bool:
            if sats <= 0:
                return False
            # Check if multiple of 1,000,000 (0.01 BTC) or 100,000 (0.001 BTC) or 50,000 sats
            return sats % 100_000 == 0 or sats % 50_000 == 0

        score0 = 0.0
        score1 = 0.0
        reasons0: list[str] = []
        reasons1: list[str] = []

        # Heuristic 1: Address Freshness
        if address_first_seen and tx_timestamp:
            fs0 = address_first_seen.get(addr0, tx_timestamp)
            fs1 = address_first_seen.get(addr1, tx_timestamp)
            if fs0 >= tx_timestamp - 1.0 and fs1 < tx_timestamp - 60.0:
                score0 += 0.35
                reasons0.append("fresh_address")
            elif fs1 >= tx_timestamp - 1.0 and fs0 < tx_timestamp - 60.0:
                score1 += 0.35
                reasons1.append("fresh_address")

        # Heuristic 2: Script Type Affinity
        if common_in_script:
            type0 = get_script(addr0, script0)
            type1 = get_script(addr1, script1)
            if type0 == common_in_script and type1 != common_in_script:
                score0 += 0.40
                reasons0.append("script_type_match")
            elif type1 == common_in_script and type0 != common_in_script:
                score1 += 0.40
                reasons1.append("script_type_match")

        # Heuristic 3: Round decimal payment
        round0 = is_round(amt0)
        round1 = is_round(amt1)
        if round0 and not round1:
            # Output 0 is round payment, Output 1 is irregular change
            score1 += 0.35
            reasons1.append("non_round_sats_vs_round_payment")
        elif round1 and not round0:
            # Output 1 is round payment, Output 0 is irregular change
            score0 += 0.35
            reasons0.append("non_round_sats_vs_round_payment")

        # Heuristic 4: Asymmetric Value / Peel Pattern
        # In retail payments or peel chains, change is often noticeably larger than payment
        total_out = amt0 + amt1
        if total_out > 0:
            ratio0 = amt0 / total_out
            ratio1 = amt1 / total_out
            if ratio0 >= 0.70 and "script_type_match" in reasons0:
                score0 += 0.20
                reasons0.append("dominant_peel_amount")
            elif ratio1 >= 0.70 and "script_type_match" in reasons1:
                score1 += 0.20
                reasons1.append("dominant_peel_amount")

        # Determine winner
        if score0 > score1 and score0 >= self.confidence_threshold:
            return addr0, round(min(score0, 0.99), 3), {
                "candidate": addr0,
                "confidence": round(score0, 3),
                "signals": reasons0,
            }
        elif score1 > score0 and score1 >= self.confidence_threshold:
            return addr1, round(min(score1, 0.99), 3), {
                "candidate": addr1,
                "confidence": round(score1, 3),
                "signals": reasons1,
            }

        return None, 0.0, {
            "reason": "No candidate passed confidence threshold",
            "score0": round(score0, 3),
            "score1": round(score1, 3),
        }
