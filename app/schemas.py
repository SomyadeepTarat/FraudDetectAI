from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[
    str, Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
]
Money = Annotated[
    Decimal, Field(gt=0, max_digits=18, decimal_places=2, allow_inf_nan=False)
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CustomerCreate(Input):
    customer_id: Identifier | None = None
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(
        min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    phone: str | None = Field(default=None, max_length=30)


class CustomerUpdate(Input):
    status: Literal["ACTIVE", "BLOCKED", "UNDER_REVIEW"]


class AccountCreate(Input):
    account_id: Identifier | None = None
    customer_id: Identifier
    balance: Decimal = Field(
        default=Decimal(0), ge=0, max_digits=18, decimal_places=2, allow_inf_nan=False
    )
    account_type: Literal["SAVINGS", "CURRENT"] = "SAVINGS"
    currency: str = Field(default="INR", pattern="^[A-Z]{3}$")


class DeviceCreate(Input):
    device_id: Identifier | None = None
    customer_id: Identifier
    device_type: str = Field(default="MOBILE", min_length=1, max_length=30)
    device_identifier: str = Field(min_length=1, max_length=120)
    ip_address: str | None = Field(default=None, max_length=45)
    trusted: bool = False


class TransactionCreate(Input):
    customer_id: Identifier
    account_id: Identifier
    destination_account_id: Identifier
    amount: Money
    transaction_type: Literal["TRANSFER"] = "TRANSFER"
    payment_method: Literal["UPI", "NEFT", "IMPS", "CARD", "BANK"] = "UPI"
    device_id: Identifier | None = None
    location: str | None = Field(default=None, min_length=1, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)


class AlertUpdate(Input):
    alert_status: Literal["OPEN", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"]
    reviewed_by: str = Field(min_length=1, max_length=120)
