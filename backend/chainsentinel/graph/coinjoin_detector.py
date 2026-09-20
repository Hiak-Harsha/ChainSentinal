"""CoinJoin and mixer transaction detector to prevent cluster collapse."""

from __future__ import annotations

from collections import Counter
from typing import Any


class CoinJoinDetector:
    """Detects multi-party CoinJoin transactions (e.g., Wasabi, JoinMarket, Whirlpool).

    CRITICAL RULE:
    Transactions flagged as CoinJoin must NEVER have their inputs clustered together
    under the Common-Input Ownership Heuristic (CIOH), as each input belongs to a
    different, independent entity.
    """

    def __init__(self, min_equal_outputs: int = 3, min_inputs: int = 2) -> None:
        self.min_equal_outputs = min_equal_outputs
        self.min_inputs = min_inputs

    def analyze(
        self,
        inputs: list[dict[str, Any]],
        outputs: list[dict[str, Any]],
    ) -> tuple[bool, float, dict[str, Any]]:
        """Analyze transaction inputs and outputs to determine if it is a CoinJoin.

        Returns:
            (is_coinjoin, confidence_score, details_dict)
        """
        # A CoinJoin requires multiple inputs and multiple outputs
        input_addrs = {inp.get("address") for inp in inputs if inp.get("address")}
        if len(input_addrs) < self.min_inputs or len(outputs) < self.min_equal_outputs:
            return False, 0.0, {"reason": "Insufficient inputs or outputs"}

        # Count frequencies of output amounts
        output_amounts = [int(out.get("amount", 0)) for out in outputs if int(out.get("amount", 0)) > 0]
        if not output_amounts:
            return False, 0.0, {"reason": "No positive outputs"}

        amount_counts = Counter(output_amounts)
        most_common_amount, most_common_count = amount_counts.most_common(1)[0]

        # Check for equal-denomination outputs
        if most_common_count < self.min_equal_outputs:
            # Check for 2-party coinjoin with equal outputs and 2 distinct inputs
            if len(input_addrs) >= 2 and most_common_count == 2 and len(outputs) in (2, 3, 4):
                # Potential Stonewall or 2-party JoinMarket
                confidence = 0.65
                return True, confidence, {
                    "reason": "2-party equal denomination match",
                    "equal_amount_sats": most_common_amount,
                    "equal_count": most_common_count,
                    "total_outputs": len(outputs),
                    "unique_inputs": len(input_addrs),
                }
            return False, 0.0, {"reason": f"Max equal outputs is {most_common_count} < {self.min_equal_outputs}"}

        # Calculate CoinJoin confidence score
        # Factors:
        # 1. Equal output count vs input count
        # 2. Proportion of outputs that are equal-denominated
        equal_output_ratio = most_common_count / len(outputs)
        input_parity_ratio = min(len(input_addrs), most_common_count) / max(len(input_addrs), most_common_count)

        confidence = 0.5 + (0.3 * min(1.0, most_common_count / 5.0)) + (0.2 * equal_output_ratio)
        confidence = min(0.99, max(0.5, confidence))

        details = {
            "reason": "Multi-party equal denomination detected",
            "equal_amount_sats": most_common_amount,
            "equal_count": most_common_count,
            "total_outputs": len(outputs),
            "unique_inputs": len(input_addrs),
            "equal_output_ratio": round(equal_output_ratio, 3),
            "input_parity_ratio": round(input_parity_ratio, 3),
        }

        return True, round(confidence, 3), details
