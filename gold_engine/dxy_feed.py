"""US Dollar Index (DXY) Correlation Feed & Sentiment Filter for Gold (XAU/USD).

Gold and the US Dollar typically exhibit strong inverse correlation:
- DXY Bullish Expansion -> Gold Headwind (Block longs / Favor short breakdown)
- DXY Bearish Breakdown -> Gold Tailwind (Multi-market confluence for Long breakouts)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DXYStatus:
    dxy_price: float
    trend: str           # 'BULLISH', 'BEARISH', 'NEUTRAL'
    gold_tailwind: str   # 'LONG_FAVORED', 'SHORT_FAVORED', 'NEUTRAL'
    change_pct: float


class DXYCorrelationFeed:
    def __init__(self, base_dxy: float = 104.35):
        self.dxy_price = base_dxy

    def get_status(self, override_dxy: Optional[float] = None) -> DXYStatus:
        if override_dxy is not None:
            self.dxy_price = override_dxy

        # Benchmark: 104.20 - 104.50 baseline
        change_pct = round(((self.dxy_price - 104.30) / 104.30) * 100.0, 2)

        if self.dxy_price > 104.50:
            trend = "BULLISH_EXPANSION"
            gold_tailwind = "SHORT_FAVORED (Dollar Headwind)"
        elif self.dxy_price < 104.15:
            trend = "BEARISH_BREAKDOWN"
            gold_tailwind = "LONG_FAVORED (Dollar Tailwind)"
        else:
            trend = "NEUTRAL"
            gold_tailwind = "BALANCED"

        return DXYStatus(
            dxy_price=round(self.dxy_price, 2),
            trend=trend,
            gold_tailwind=gold_tailwind,
            change_pct=change_pct
        )
