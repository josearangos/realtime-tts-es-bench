"""Data types for the Spanish call center test corpus."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Campaign(str, Enum):
    OUTBOUND_SALES = "outbound_sales"
    COLLECTIONS = "collections"
    INBOUND = "inbound"


class Scenario(str, Enum):
    # outbound_sales
    MOBILE_PREPAID = "mobile_prepaid"
    MOBILE_POSTPAID = "mobile_postpaid"
    PORTABILITY = "portability"
    DEVICE_PROMO = "device_promo"
    INTERNET_FIBER = "internet_fiber"
    UPGRADE = "upgrade"
    PRICING = "pricing"
    OBJECTION = "objection"
    # collections
    CARD_BALANCE = "card_balance"
    OVERDUE_INSTALLMENT = "overdue_installment"
    DUE_DATE = "due_date"
    PAYMENT_AGREEMENT = "payment_agreement"
    PAYMENT_CHANNEL = "payment_channel"
    PAYMENT_REMINDER = "payment_reminder"
    # inbound
    GREETING = "greeting"
    IDENTITY_VERIFICATION = "identity_verification"
    BILLING_QUERY = "billing_query"
    COMPLAINT = "complaint"
    TECH_SUPPORT = "tech_support"
    PLAN_CHANGE = "plan_change"
    CLOSING = "closing"
    # any campaign
    DISCLOSURE = "disclosure"
    SHORT_RESPONSE = "short_response"


class Tag(str, Enum):
    AMOUNT_COP = "amount_cop"
    NUMBER = "number"
    DATETIME = "datetime"
    ACRONYM = "acronym"
    PROPER_NAME = "proper_name"
    QUESTION = "question"
    LONG = "long"
    SHORT = "short"
    HARD_WORD = "hard_word"


class Address(str, Enum):
    USTED = "usted"
    TU = "tu"
    VOS = "vos"
    NONE = "none"


class Probe(str, Enum):
    AMOUNT = "amount"
    PHONE_OR_ACCOUNT = "phone_or_account"
    DATETIME = "datetime"
    ACRONYM = "acronym"
    NAME = "name"
    LONG_DISCLOSURE = "long_disclosure"
    FAST_ACK = "fast_ack"
    REGIONALISM = "regionalism"
    PROSODY_QUESTION = "prosody_question"
    HARD_WORD = "hard_word"


class Subset(str, Enum):
    MAIN = "main"
    CLONING = "cloning"


CAMPAIGN_SCENARIOS: dict[Campaign, tuple[Scenario, ...]] = {
    Campaign.OUTBOUND_SALES: (
        Scenario.MOBILE_PREPAID, Scenario.MOBILE_POSTPAID, Scenario.PORTABILITY,
        Scenario.DEVICE_PROMO, Scenario.INTERNET_FIBER, Scenario.UPGRADE,
        Scenario.PRICING, Scenario.OBJECTION,
    ),
    Campaign.COLLECTIONS: (
        Scenario.CARD_BALANCE, Scenario.OVERDUE_INSTALLMENT, Scenario.DUE_DATE,
        Scenario.PAYMENT_AGREEMENT, Scenario.PAYMENT_CHANNEL, Scenario.PAYMENT_REMINDER,
    ),
    Campaign.INBOUND: (
        Scenario.GREETING, Scenario.IDENTITY_VERIFICATION, Scenario.BILLING_QUERY,
        Scenario.COMPLAINT, Scenario.TECH_SUPPORT, Scenario.PLAN_CHANGE, Scenario.CLOSING,
    ),
}
CROSS_CUTTING_SCENARIOS = (Scenario.DISCLOSURE, Scenario.SHORT_RESPONSE)

ID_PREFIXES = {"VEN", "COB", "ENT", "CLO"}

# probe -> tag that a sentence with that probe must carry (data-model.md)
PROBE_TAG = {
    Probe.AMOUNT: Tag.AMOUNT_COP,
    Probe.PHONE_OR_ACCOUNT: Tag.NUMBER,
    Probe.DATETIME: Tag.DATETIME,
    Probe.ACRONYM: Tag.ACRONYM,
    Probe.NAME: Tag.PROPER_NAME,
    Probe.LONG_DISCLOSURE: Tag.LONG,
    Probe.FAST_ACK: Tag.SHORT,
    Probe.PROSODY_QUESTION: Tag.QUESTION,
    Probe.HARD_WORD: Tag.HARD_WORD,
}


@dataclass(frozen=True)
class Sentence:
    id: str
    text: str
    campaign: Campaign
    scenario: Scenario
    tags: tuple[Tag, ...]
    probes: Probe
    address: Address = Address.USTED
    spoken: str | None = None
    reviewed: bool = False
    subset: Subset = Subset.MAIN

    @property
    def speak_text(self) -> str:
        """Text to send to an engine that needs a normalized reading."""
        return self.spoken if self.spoken is not None else self.text


@dataclass(frozen=True)
class CorpusVersion:
    version: str
    date: str
    counts: dict = field(default_factory=dict)
    content_sha256: str = ""
