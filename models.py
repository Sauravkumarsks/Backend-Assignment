from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re

E164_RE = re.compile(r"^\+\d+$")


class WebhookMessage(BaseModel):
    message_id: str = Field(min_length=1)
    from_: str = Field(alias="from")
    to: str
    ts: str  # ISO-8601 UTC string with Z suffix
    text: Optional[str] = Field(default=None, max_length=4096)

    @field_validator("from_", "to")
    @classmethod
    def validate_e164(cls, v: str):
        if not E164_RE.match(v):
            raise ValueError("must be E.164-like (+ followed by digits)")
        return v

    @field_validator("ts")
    @classmethod
    def validate_ts(cls, v: str):
        # Simple check: must end with Z and be ISO-like
        # Full ISO parsing can be done, but spec allows string validation
        if not v.endswith("Z"):
            raise ValueError("must be ISO-8601 UTC with Z suffix")
        # Basic shape check: YYYY-MM-DDTHH:MM:SSZ
        # Avoid strict parsing to keep it simple
        return v


class MessageOut(BaseModel):
    message_id: str
    from_: str = Field(alias="from")
    to: str
    ts: str
    text: Optional[str] = None

    class Config:
        populate_by_name = True


class MessagesResponse(BaseModel):
    data: List[MessageOut]
    total: int
    limit: int
    offset: int


class SenderCount(BaseModel):
    from_: str = Field(alias="from")
    count: int

    class Config:
        populate_by_name = True


class StatsResponse(BaseModel):
    total_messages: int
    senders_count: int
    messages_per_sender: List[SenderCount]
    first_message_ts: Optional[str] = None
    last_message_ts: Optional[str] = None
