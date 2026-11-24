"""PaySim secondary protocol: pre-transfer inputs vs explicit outcome diagnostic."""

import math

KINDS = ("TRANSFER", "CASH_OUT", "CASH_IN", "PAYMENT", "DEBIT")
PRE_TRANSFER_NAMES = ("log_amount", "log_sender_balance_before", "log_receiver_balance_before", "hour") + tuple(f"type_{kind}" for kind in KINDS)
POST_TRANSFER_NAMES = PRE_TRANSFER_NAMES + ("sender_balance_residual", "receiver_balance_residual")


def transaction_features(row: dict[str, str], *, post_transfer: bool = False) -> tuple[float, ...]:
    amount = float(row["amount"])
    before_sender, before_receiver = float(row["oldbalanceOrg"]), float(row["oldbalanceDest"])
    if min(amount, before_sender, before_receiver) < 0 or not all(math.isfinite(v) for v in (amount, before_sender, before_receiver)):
        raise ValueError("Invalid pre-transfer money fields")
    if row["type"] not in KINDS:
        raise ValueError("Unknown PaySim transaction kind")
    result = (math.log1p(amount), math.log1p(before_sender), math.log1p(before_receiver), float(int(row["step"]) % 24)) + tuple(float(row["type"] == kind) for kind in KINDS)
    if post_transfer:
        residuals = (before_sender - float(row["newbalanceOrig"]) - amount,
                     before_receiver + amount - float(row["newbalanceDest"]))
        if not all(math.isfinite(value) for value in residuals):
            raise ValueError("Invalid post-transfer balances")
        result += tuple(math.copysign(math.log1p(abs(value)), value) for value in residuals)
    return result
