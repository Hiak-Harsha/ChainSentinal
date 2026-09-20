"""Validation engine with Bitcoin-specific format, amount conservation, and timestamp sanity checks."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
import time
from typing import Any


BITCOIN_GENESIS_TS = 1231006505.0  # Jan 3, 2009
HEX_64_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
BASE58_PATTERN = re.compile(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$")
BECH32_PATTERN = re.compile(r"^bc1[a-z0-9]{11,71}$")


class QuarantineReason:
    # Prompt-specified canonical reason codes:
    NEGATIVE_AMOUNT = "negative_amount"
    TIMESTAMP_ANOMALY = "timestamp_anomaly"
    INVALID_ADDRESS = "invalid_address"
    INVALID_IP = "invalid_ip"
    CHECKSUM_MISMATCH = "checksum_mismatch"

    # Additional integrity reasons:
    MISSING_REQUIRED_FIELD = "missing_required_field"
    INVALID_TXID = "invalid_txid"
    EMPTY_INPUTS_OR_OUTPUTS = "empty_inputs_or_outputs"
    INVALID_FEE = "invalid_fee"

    # Backward compatibility aliases:
    NEGATIVE_OR_ZERO_AMOUNT = "negative_amount"
    AMOUNT_MISMATCH = "checksum_mismatch"


@dataclass
class ValidationResult:
    is_valid: bool
    reason_code: str | None = None
    error_details: str | None = None
    cleaned_record: dict[str, Any] | None = None

    @property
    def quarantine_reason(self) -> str | None:
        return self.reason_code


def is_valid_bitcoin_address(addr: str) -> bool:
    """Validate Bitcoin address prefix, format, and length."""
    if not isinstance(addr, str) or not addr:
        return False
    a = addr.strip()
    if a.startswith("1") or a.startswith("3"):
        return 26 <= len(a) <= 35 and bool(re.match(r"^[13][a-zA-Z0-9]+$", a))
    if a.lower().startswith("bc1"):
        return 14 <= len(a) <= 74 and bool(re.match(r"^bc1[a-z0-9]+$", a.lower()))
    return False


def is_valid_ip(ip_str: str) -> bool:
    """Validate IPv4 or IPv6 string."""
    try:
        ipaddress.ip_address(str(ip_str).strip())
        return True
    except ValueError:
        return False


class RecordValidator:
    """Validates raw observation records against integrity rules."""

    def __init__(self, max_future_seconds: float = 86400.0):
        self.max_future_seconds = max_future_seconds

    def validate(self, record: dict[str, Any]) -> ValidationResult:
        """Perform comprehensive integrity validation on an observation record."""
        # 1. Required fields presence
        for req in ("txid", "timestamp", "src_ip", "input_addresses", "input_amounts", "output_addresses", "output_amounts", "fee"):
            if req not in record or record[req] is None:
                return ValidationResult(
                    is_valid=False,
                    reason_code=QuarantineReason.MISSING_REQUIRED_FIELD,
                    error_details=f"Missing required field: {req}",
                )

        txid = str(record["txid"]).strip()
        if not HEX_64_PATTERN.match(txid):
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.INVALID_TXID,
                error_details=f"Invalid TXID hex format: '{txid}'",
            )

        # 2. Timestamp sanity
        try:
            ts = float(record["timestamp"])
            now = time.time()
            if ts < BITCOIN_GENESIS_TS or ts > (now + self.max_future_seconds):
                return ValidationResult(
                    is_valid=False,
                    reason_code=QuarantineReason.TIMESTAMP_ANOMALY,
                    error_details=f"Timestamp {ts} out of realistic range [2009, now+24h]",
                )
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.TIMESTAMP_ANOMALY,
                error_details=f"Invalid timestamp value: {record.get('timestamp')}",
            )

        # 3. IP validation
        src_ip = str(record["src_ip"]).strip()
        if not is_valid_ip(src_ip):
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.INVALID_IP,
                error_details=f"Invalid src_ip format: '{src_ip}'",
            )

        # 4. Inputs & Outputs non-empty
        in_addrs = record["input_addresses"]
        in_amts = record["input_amounts"]
        out_addrs = record["output_addresses"]
        out_amts = record["output_amounts"]

        if not in_addrs or not in_amts or not out_addrs or not out_amts:
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.EMPTY_INPUTS_OR_OUTPUTS,
                error_details="Inputs or outputs array is empty",
            )

        if len(in_addrs) != len(in_amts) or len(out_addrs) != len(out_amts):
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.EMPTY_INPUTS_OR_OUTPUTS,
                error_details="Address count does not match amount count",
            )

        # 5. Address validation
        for a in in_addrs:
            if not is_valid_bitcoin_address(str(a)):
                return ValidationResult(
                    is_valid=False,
                    reason_code=QuarantineReason.INVALID_ADDRESS,
                    error_details=f"Invalid Bitcoin input address: '{a}'",
                )
        for a in out_addrs:
            if not is_valid_bitcoin_address(str(a)):
                return ValidationResult(
                    is_valid=False,
                    reason_code=QuarantineReason.INVALID_ADDRESS,
                    error_details=f"Invalid Bitcoin output address: '{a}'",
                )

        # 6. Amounts & fee validation (must be positive integers)
        try:
            parsed_in_amts = [int(amt) for amt in in_amts]
            parsed_out_amts = [int(amt) for amt in out_amts]
            fee = int(record["fee"])
        except (ValueError, TypeError):
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.NEGATIVE_OR_ZERO_AMOUNT,
                error_details="Amounts or fee could not be parsed as integers",
            )

        if any(amt <= 0 for amt in parsed_in_amts) or any(amt <= 0 for amt in parsed_out_amts):
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.NEGATIVE_OR_ZERO_AMOUNT,
                error_details="All input and output amounts must be strictly positive satoshis",
            )

        if fee <= 0:
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.INVALID_FEE,
                error_details=f"Transaction fee must be positive, got {fee}",
            )

        # 7. Amount conservation: sum(inputs) - sum(outputs) == fee
        total_in = sum(parsed_in_amts)
        total_out = sum(parsed_out_amts)
        if total_in - total_out != fee:
            return ValidationResult(
                is_valid=False,
                reason_code=QuarantineReason.AMOUNT_MISMATCH,
                error_details=f"Conservation failed: total_in({total_in}) - total_out({total_out}) = {total_in - total_out} != fee({fee})",
            )

        # Cleaned record
        cleaned = dict(record)
        cleaned["txid"] = txid.lower()
        cleaned["timestamp"] = ts
        cleaned["src_ip"] = src_ip
        cleaned["dst_ip"] = str(record.get("dst_ip") or "127.0.0.1").strip()
        cleaned["src_port"] = int(record.get("src_port") or 8333)
        cleaned["dst_port"] = int(record.get("dst_port") or 8333)
        cleaned["input_addresses"] = [str(a).strip() for a in in_addrs]
        cleaned["input_amounts"] = parsed_in_amts
        cleaned["output_addresses"] = [str(a).strip() for a in out_addrs]
        cleaned["output_amounts"] = parsed_out_amts
        cleaned["fee"] = fee
        cleaned["total_in"] = total_in
        cleaned["total_out"] = total_out
        cleaned["n_in"] = len(in_addrs)
        cleaned["n_out"] = len(out_addrs)

        return ValidationResult(is_valid=True, cleaned_record=cleaned)
