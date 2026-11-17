"""Mandatory 03:15 PM IST Auto-Square-Off Sentinel for Indian Markets.

Protects intraday equity & options traders from:
- Overnight gap risk (gap-down/gap-up overnight)
- Broker auto-square-off penalty charges (Zerodha/Groww/Dhan charge Rs 50 + GST per order)
- Late 03:15 - 03:30 PM volatility squawks
"""

from typing import Tuple, Optional
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


class IndianAutoExitSentinel:
    """Monitors IST clock to enforce hard auto-square-off at 03:15 PM."""

    def __init__(self, auto_exit_hour: int = 15, auto_exit_minute: int = 15):
        self.auto_exit_hour = auto_exit_hour
        self.auto_exit_minute = auto_exit_minute

    def is_auto_exit_time(self, dt_ist: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Returns (True, reason) if current IST time is at or past 03:15 PM IST
        and within the market session day.
        """
        if dt_ist is None:
            dt_ist = datetime.now(IST)
        else:
            dt_ist = dt_ist.astimezone(IST)

        # Indian market trading hours: 09:15 to 15:30 IST
        hour = dt_ist.hour
        minute = dt_ist.minute

        # If past 15:15 IST
        if (hour > self.auto_exit_hour) or (hour == self.auto_exit_hour and minute >= self.auto_exit_minute):
            return True, f"🔒 MANDATORY AUTO-EXIT TRIGGERED (03:15 PM IST): All intraday positions squared off."

        # If before market open (before 09:15 IST)
        if hour < 9 or (hour == 9 and minute < 15):
            return False, "MARKET_CLOSED_PRE_OPEN"

        mins_to_exit = ((self.auto_exit_hour * 60) + self.auto_exit_minute) - ((hour * 60) + minute)
        return False, f"ACTIVE_SESSION ({mins_to_exit}m until 03:15 PM auto-exit)"
