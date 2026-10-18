"""Exact marginal recent-funding bounds; amounts are Decimal, never probabilities."""

from decimal import Decimal


def funding_bounds(opening, movements, target):
    balance = Decimal(opening)
    lower = upper = Decimal(0)
    if balance < 0 or target <= 0:
        raise ValueError("Invalid opening balance or target")
    for side, amount in movements:
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError("Movement must be positive")
        if side == "CREDIT":
            balance += amount
            lower += amount
            upper += amount
        elif side == "DEBIT" and amount <= balance:
            lower = max(Decimal(0), lower - amount)
            upper = min(upper, balance - amount)
            balance -= amount
        else:
            raise ValueError("Invalid side or overdraft")
    if target > balance:
        raise ValueError("Target exceeds balance")
    return max(Decimal(0), target - (balance - lower)), min(target, upper)
