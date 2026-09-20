"""Entity behavioral typing classifier."""

from __future__ import annotations

from typing import Any


class EntityClassifier:
    """Classifies resolved address clusters into functional entity types:
    - EXCHANGE: High volume, large address clusters, batch payouts
    - MIXER: CoinJoin participation, equal-denomination churn
    - COLLECTOR_HUB: Consolidation of funds from many distinct deposit addresses
    - SERVICE: Regular incoming payments, periodic settlements
    - INDIVIDUAL: Small address clusters (1-5), low volume/frequency
    """

    @staticmethod
    def classify(
        member_addrs: list[str],
        incoming_txs: list[dict[str, Any]],
        outgoing_txs: list[dict[str, Any]],
        total_received: int,
        total_sent: int,
        coinjoin_tx_count: int = 0,
    ) -> tuple[str, float, dict[str, Any]]:
        """Determine entity type and confidence score.

        Returns:
            (entity_type, confidence, metrics_summary)
        """
        n_addrs = len(member_addrs)
        n_in_tx = len(incoming_txs)
        n_out_tx = len(outgoing_txs)
        total_tx = n_in_tx + n_out_tx

        # Metrics
        volume_btc = (total_received + total_sent) / 100_000_000.0
        avg_fan_out = (
            sum(len(tx.get("outputs", [])) for tx in outgoing_txs) / max(1, n_out_tx)
            if outgoing_txs else 1.0
        )
        avg_fan_in = (
            sum(len(tx.get("inputs", [])) for tx in incoming_txs) / max(1, n_in_tx)
            if incoming_txs else 1.0
        )

        metrics = {
            "address_count": n_addrs,
            "incoming_tx_count": n_in_tx,
            "outgoing_tx_count": n_out_tx,
            "total_tx_count": total_tx,
            "volume_btc": round(volume_btc, 4),
            "coinjoin_tx_count": coinjoin_tx_count,
            "avg_fan_out": round(avg_fan_out, 2),
            "avg_fan_in": round(avg_fan_in, 2),
        }

        # 1. Mixer Check
        if coinjoin_tx_count >= 2 or (total_tx > 0 and (coinjoin_tx_count / total_tx) >= 0.25):
            conf = min(0.95, 0.6 + (0.1 * coinjoin_tx_count))
            return "MIXER", round(conf, 2), metrics

        # 2. Exchange Check
        if (n_addrs >= 20 and volume_btc >= 50.0) or (avg_fan_out >= 8.0 and total_tx >= 15):
            conf = min(0.96, 0.7 + 0.01 * min(25, n_addrs))
            return "EXCHANGE", round(conf, 2), metrics

        # 3. Collector / Consolidator Hub
        # High fan-in ratio with many incoming deposits compared to outgoing sweeps
        if n_in_tx >= 8 and (n_in_tx / max(1, n_out_tx)) >= 3.0:
            conf = min(0.92, 0.65 + 0.02 * min(12, n_in_tx))
            return "COLLECTOR_HUB", round(conf, 2), metrics

        # 4. Service / Merchant
        if n_in_tx >= 5 and total_tx >= 8:
            conf = 0.75
            return "SERVICE", conf, metrics

        # 5. Default: Individual / Retail User
        conf = 0.85 if n_addrs <= 3 else 0.70
        return "INDIVIDUAL", conf, metrics
