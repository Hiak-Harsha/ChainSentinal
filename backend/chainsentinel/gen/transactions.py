"""Transaction builder — creates realistic Bitcoin-like transactions.

Generates transaction structures with proper inputs, outputs, fees,
addresses, and script types. All amounts are in integer satoshis.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from numpy.random import Generator


# Bitcoin address prefixes by script type
ADDRESS_PREFIXES = {
    "p2pkh": "1",
    "p2sh": "3",
    "p2wpkh": "bc1q",
    "p2tr": "bc1p",
}

# Realistic script type distribution
SCRIPT_TYPE_WEIGHTS = {
    "p2pkh": 0.30,
    "p2sh": 0.15,
    "p2wpkh": 0.40,
    "p2tr": 0.15,
}

SCRIPT_TYPES = list(SCRIPT_TYPE_WEIGHTS.keys())
SCRIPT_WEIGHTS = list(SCRIPT_TYPE_WEIGHTS.values())

# Amount constants (in satoshis)
SATOSHI = 1
BTC = 100_000_000
DUST_LIMIT = 546  # Standard dust limit in satoshis

# Fee rate distribution parameters (sat/vB)
FEE_RATE_MIN = 1
FEE_RATE_MAX = 100
FEE_RATE_MEAN = 15
FEE_RATE_STD = 20


@dataclass
class TxInput:
    """A transaction input."""

    address: str
    amount: int  # satoshis
    script_type: str = "p2wpkh"


@dataclass
class TxOutput:
    """A transaction output."""

    address: str
    amount: int  # satoshis
    script_type: str = "p2wpkh"


@dataclass
class Transaction:
    """A complete synthetic transaction."""

    txid: str
    timestamp: float  # Unix timestamp
    inputs: list[TxInput] = field(default_factory=list)
    outputs: list[TxOutput] = field(default_factory=list)
    fee: int = 0  # satoshis
    vsize: int = 0

    @property
    def total_in(self) -> int:
        """Total input amount."""
        return sum(inp.amount for inp in self.inputs)

    @property
    def total_out(self) -> int:
        """Total output amount."""
        return sum(out.amount for out in self.outputs)

    @property
    def n_in(self) -> int:
        """Number of inputs."""
        return len(self.inputs)

    @property
    def n_out(self) -> int:
        """Number of outputs."""
        return len(self.outputs)

    @property
    def fee_rate(self) -> float:
        """Fee rate in sat/vB."""
        return self.fee / max(self.vsize, 1)

    @property
    def script_types(self) -> list[str]:
        """Unique script types used in this tx."""
        types = set()
        for inp in self.inputs:
            types.add(inp.script_type)
        for out in self.outputs:
            types.add(out.script_type)
        return sorted(types)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "txid": self.txid,
            "timestamp": self.timestamp,
            "input_addresses": [inp.address for inp in self.inputs],
            "input_amounts": [inp.amount for inp in self.inputs],
            "output_addresses": [out.address for out in self.outputs],
            "output_amounts": [out.amount for out in self.outputs],
            "fee": self.fee,
            "script_type": self.script_types[0] if self.script_types else "p2wpkh",
        }


class AddressGenerator:
    """Generates deterministic, realistic-format Bitcoin addresses."""

    def __init__(self, rng: Generator):
        self.rng = rng
        self._counter = 0

    def generate(self, script_type: str | None = None) -> tuple[str, str]:
        """Generate a new address.

        Args:
            script_type: Specific script type, or None for random weighted choice.

        Returns:
            Tuple of (address_string, script_type).
        """
        if script_type is None:
            script_type = self.rng.choice(SCRIPT_TYPES, p=SCRIPT_WEIGHTS)

        self._counter += 1
        # Generate deterministic but realistic-looking address
        seed_bytes = self.rng.bytes(20)
        addr_hash = hashlib.sha256(
            seed_bytes + self._counter.to_bytes(4, "big")
        ).hexdigest()

        prefix = ADDRESS_PREFIXES[script_type]

        if script_type == "p2pkh":
            # 1 + 33 chars (simplified)
            addr = prefix + addr_hash[:33]
        elif script_type == "p2sh":
            # 3 + 33 chars
            addr = prefix + addr_hash[:33]
        elif script_type == "p2wpkh":
            # bc1q + 38 chars (bech32-like)
            addr = prefix + addr_hash[:38]
        elif script_type == "p2tr":
            # bc1p + 58 chars (bech32m-like)
            addr = prefix + addr_hash[:58]
        else:
            addr = "1" + addr_hash[:33]
            script_type = "p2pkh"

        return addr, script_type

    def generate_batch(self, count: int, script_type: str | None = None) -> list[tuple[str, str]]:
        """Generate multiple addresses."""
        return [self.generate(script_type) for _ in range(count)]


class TxidGenerator:
    """Generates deterministic, realistic-format transaction IDs."""

    def __init__(self, rng: Generator):
        self.rng = rng
        self._counter = 0

    def generate(self) -> str:
        """Generate a 64-character hex TXID."""
        self._counter += 1
        seed_bytes = self.rng.bytes(32)
        txid = hashlib.sha256(
            seed_bytes + self._counter.to_bytes(4, "big")
        ).hexdigest()
        return txid


def _normalize_addr(addr_spec: Any) -> tuple[str, str]:
    """Normalize an address specification to (address, script_type)."""
    if isinstance(addr_spec, (tuple, list)):
        return str(addr_spec[0]), str(addr_spec[1])
    if hasattr(addr_spec, "__len__") and not isinstance(addr_spec, (str, bytes)):
        if len(addr_spec) == 2:
            return str(addr_spec[0]), str(addr_spec[1])
        if len(addr_spec) == 1:
            addr_spec = str(addr_spec[0])
    addr_str = str(addr_spec)
    if addr_str.startswith("bc1q"):
        return addr_str, "p2wpkh"
    if addr_str.startswith("bc1p"):
        return addr_str, "p2tr"
    if addr_str.startswith("3"):
        return addr_str, "p2sh"
    return addr_str, "p2pkh"


def partition_amount(rng: Generator, total: int, count: int, min_per_item: int = DUST_LIMIT) -> list[int]:
    """Partitions integer satoshis across count items such that each item is >= 1.

    If total >= count * min_per_item, each item is guaranteed >= min_per_item.
    The sum of the resulting list is guaranteed to equal `total` exactly.
    """
    if count <= 0:
        return []
    if count == 1:
        return [total]

    if total < count * min_per_item:
        min_per_item = max(1, total // count)

    excess = total - count * min_per_item
    if excess <= 0:
        base = total // count
        rem = total % count
        return [base + (1 if i < rem else 0) for i in range(count)]

    # Generate random positive weights using exponential distribution
    weights = rng.exponential(scale=1.0, size=count)
    weight_sum = float(weights.sum())
    if weight_sum <= 0:
        weights = [1.0] * count
        weight_sum = float(count)

    proportions = [float(w) / weight_sum for w in weights]
    allocations = [int(excess * p) for p in proportions]
    rem = excess - sum(allocations)
    allocations[-1] += rem

    return [min_per_item + a for a in allocations]


class TransactionBuilder:
    """Builds synthetic transactions with realistic properties."""

    def __init__(self, rng: Generator):
        self.rng = rng
        self.addr_gen = AddressGenerator(rng)
        self.txid_gen = TxidGenerator(rng)

    def build_simple(
        self,
        timestamp: float,
        input_addresses: list[tuple[str, str] | str],
        input_amounts: list[int],
        output_count: int | None = None,
        output_addresses: list[tuple[str, str] | str] | None = None,
        output_amounts: list[int] | None = None,
        change_address: tuple[str, str] | str | None = None,
        fee_rate: float | None = None,
        fee: int | None = None,
    ) -> Transaction:
        """Build a transaction with given inputs and outputs.

        Guarantees:
        1. sum(inputs) - sum(outputs) == fee
        2. fee > 0
        3. All input and output amounts > 0
        """
        norm_inputs = [_normalize_addr(a) for a in input_addresses]
        inputs = [
            TxInput(address=addr, amount=amt, script_type=st)
            for (addr, st), amt in zip(norm_inputs, input_amounts)
        ]
        total_in = sum(input_amounts)

        if output_addresses is not None:
            norm_outputs = [_normalize_addr(a) for a in output_addresses]
        else:
            n_out = output_count or int(self.rng.integers(1, 4))
            norm_outputs = [self.addr_gen.generate() for _ in range(n_out)]

        n_in = len(inputs)
        n_out = len(norm_outputs)
        vsize = 10 + n_in * 68 + n_out * 34

        if fee is None:
            if fee_rate is None:
                fee_rate = max(
                    FEE_RATE_MIN,
                    min(FEE_RATE_MAX, float(self.rng.normal(FEE_RATE_MEAN, FEE_RATE_STD))),
                )
            fee = max(int(fee_rate * vsize), 200)

        # Ensure fee allows at least 1 satoshi per output
        if total_in <= fee + len(norm_outputs):
            fee = max(1, total_in - len(norm_outputs))

        total_out = total_in - fee

        outputs: list[TxOutput] = []
        if output_amounts is not None:
            # Explicit output amounts provided
            req_out = sum(output_amounts)
            final_amounts = list(output_amounts)

            if req_out + fee > total_in:
                # Need to scale outputs down to fit
                avail = max(len(final_amounts), total_in - 1)
                fee = total_in - avail
                scale = avail / max(req_out, 1)
                final_amounts = [max(1, int(a * scale)) for a in final_amounts]
                diff = avail - sum(final_amounts)
                final_amounts[-1] = max(1, final_amounts[-1] + diff)
            elif total_in > req_out + fee and change_address is not None:
                leftover = total_in - req_out - fee
                if leftover >= DUST_LIMIT:
                    c_addr, c_st = _normalize_addr(change_address)
                    norm_outputs.append((c_addr, c_st))
                    final_amounts.append(leftover)
                else:
                    fee += leftover
            else:
                fee = total_in - sum(final_amounts)

            for (addr, st), amt in zip(norm_outputs, final_amounts):
                outputs.append(TxOutput(address=addr, amount=amt, script_type=st))
        else:
            amounts = partition_amount(self.rng, total_out, len(norm_outputs), min_per_item=DUST_LIMIT)
            for (addr, st), amt in zip(norm_outputs, amounts):
                outputs.append(TxOutput(address=addr, amount=amt, script_type=st))

        actual_fee = total_in - sum(out.amount for out in outputs)
        if actual_fee <= 0:
            actual_fee = 1
            outputs[-1].amount = max(1, outputs[-1].amount - 1)

        txid = self.txid_gen.generate()
        return Transaction(
            txid=txid,
            timestamp=timestamp,
            inputs=inputs,
            outputs=outputs,
            fee=actual_fee,
            vsize=vsize,
        )

    def build_transfer(
        self,
        timestamp: float,
        from_addr: str,
        from_script: str,
        to_addr: str,
        to_script: str,
        amount: int,
        include_change: bool = True,
    ) -> Transaction:
        """Build a simple A->B transfer transaction."""
        fee = int(self.rng.integers(500, 3000))
        change_amt = int(self.rng.integers(5000, 50000)) if include_change else 0
        total_in = amount + fee + change_amt

        output_addrs: list[tuple[str, str]] = [(to_addr, to_script)]
        output_amts: list[int] = [amount]

        if include_change and change_amt >= DUST_LIMIT:
            change_addr = self.addr_gen.generate(from_script)
            output_addrs.append(change_addr)
            output_amts.append(change_amt)

        return self.build_simple(
            timestamp=timestamp,
            input_addresses=[(from_addr, from_script)],
            input_amounts=[total_in],
            output_addresses=output_addrs,
            output_amounts=output_amts,
            fee=fee,
        )

