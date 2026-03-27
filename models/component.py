"""
🧩 COMPONENT - ICT Component Data Model
Defines the Component dataclass used by the V2 detectors and engines.

Author: galinborisov10-art
Version: 2.0
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ComponentType(Enum):
    """ICT component types"""
    ORDER_BLOCK = "ORDER_BLOCK"
    FAIR_VALUE_GAP = "FAIR_VALUE_GAP"
    LIQUIDITY_ZONE = "LIQUIDITY_ZONE"
    BREAKER_BLOCK = "BREAKER_BLOCK"
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    MARKET_STRUCTURE_SHIFT = "MARKET_STRUCTURE_SHIFT"
    CHANGE_OF_CHARACTER = "CHANGE_OF_CHARACTER"
    OPTIMAL_TRADE_ENTRY = "OPTIMAL_TRADE_ENTRY"
    PREMIUM_DISCOUNT = "PREMIUM_DISCOUNT"


class ComponentPolarity(Enum):
    """Component directional polarity"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ComponentStatus(Enum):
    """Component lifecycle status"""
    ACTIVE = "ACTIVE"
    TESTED = "TESTED"
    MITIGATED = "MITIGATED"
    INVALIDATED = "INVALIDATED"
    BREACHED = "BREACHED"


@dataclass
class Component:
    """
    V2 ICT Component Data Model

    Represents a single ICT market structure component detected by the V2 detectors.
    Components are building blocks for signal generation.

    Attributes:
        component_id: Unique identifier
        component_type: Type of ICT component
        polarity: BULLISH or BEARISH
        price_high: Upper price boundary of component
        price_low: Lower price boundary of component
        price_mid: Midpoint of component zone
        strength: Component strength score (0-100)
        candle_index: Index in the source dataframe
        timestamp: When the component was formed
        timeframe: Chart timeframe where detected
        status: Current lifecycle status
        volume_ratio: Volume relative to average at formation
        displacement_pct: Price displacement percentage
        touch_count: Number of times price has retested this component
        confluence_score: Confluence with other components (0-100)
        metadata: Additional component-specific data
    """
    component_id: str
    component_type: ComponentType
    polarity: ComponentPolarity
    price_high: float
    price_low: float
    price_mid: float
    strength: float
    candle_index: int
    timestamp: datetime
    timeframe: str = "1H"
    status: ComponentStatus = ComponentStatus.ACTIVE
    volume_ratio: float = 1.0
    displacement_pct: float = 0.0
    touch_count: int = 0
    confluence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize component to dictionary"""
        return {
            "component_id": self.component_id,
            "component_type": self.component_type.value,
            "polarity": self.polarity.value,
            "price_high": self.price_high,
            "price_low": self.price_low,
            "price_mid": self.price_mid,
            "strength": self.strength,
            "candle_index": self.candle_index,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "status": self.status.value,
            "volume_ratio": self.volume_ratio,
            "displacement_pct": self.displacement_pct,
            "touch_count": self.touch_count,
            "confluence_score": self.confluence_score,
        }

    @property
    def zone_size(self) -> float:
        """Size of the component price zone"""
        return self.price_high - self.price_low

    @property
    def zone_size_pct(self) -> float:
        """Zone size as percentage of mid price"""
        if self.price_mid <= 0:
            return 0.0
        return (self.zone_size / self.price_mid) * 100.0

    @property
    def is_active(self) -> bool:
        """Whether the component is still active"""
        return self.status == ComponentStatus.ACTIVE

    def contains_price(self, price: float) -> bool:
        """Check if a price is within this component's zone"""
        return self.price_low <= price <= self.price_high

    def overlaps_with(self, other: "Component") -> bool:
        """Check if this component overlaps price-wise with another"""
        return self.price_low <= other.price_high and self.price_high >= other.price_low


# Backward-compatibility alias
ComponentV2 = Component
