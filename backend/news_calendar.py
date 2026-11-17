"""Macroeconomic News Calendar & Blackout Sentinel for High-Leverage Intraday Trading.

Protects 100x-500x high-leverage scalping positions from catastrophic spread widening
and 1,000-point slippage spikes by blacking out entries +-15 minutes around high-impact
US macroeconomic announcements (US CPI, NFP, FOMC rate decisions, Fed Chair speeches).
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))


class MacroNewsSentinel:
    """Monitors high-impact macroeconomic announcements to prevent spread blowouts."""

    def __init__(self, buffer_minutes: int = 15):
        self.buffer_minutes = buffer_minutes
        # Scheduled recurring & milestone high-impact US macro events (IST schedule)
        # In production, this can also sync with live ForexFactory / Economic Calendar APIs
        self.scheduled_events: List[Dict[str, Any]] = [
            {
                "name": "US CPI (Consumer Price Index Inflation)",
                "impact": "CRITICAL",
                "typical_time_ist": "18:30 IST",
                "days_of_month": [10, 11, 12, 13, 14], # Mid-month release
                "hour_ist": 18,
                "minute_ist": 30
            },
            {
                "name": "US Non-Farm Payrolls (NFP) & Unemployment",
                "impact": "CRITICAL",
                "typical_time_ist": "18:30 IST",
                "day_of_week": 4, # Friday
                "first_week": True,
                "hour_ist": 18,
                "minute_ist": 30
            },
            {
                "name": "FOMC Interest Rate Decision & Fed Policy Statement",
                "impact": "CRITICAL",
                "typical_time_ist": "23:30 IST",
                "hour_ist": 23,
                "minute_ist": 30
            },
            {
                "name": "Fed Chair Press Conference",
                "impact": "CRITICAL",
                "typical_time_ist": "00:00 IST",
                "hour_ist": 0,
                "minute_ist": 0
            },
            {
                "name": "US Core PPI (Producer Price Index)",
                "impact": "HIGH",
                "typical_time_ist": "18:30 IST",
                "hour_ist": 18,
                "minute_ist": 30
            }
        ]

    def is_news_blackout(self, dt_ist: Optional[datetime] = None) -> Tuple[bool, Optional[str]]:
        """
        Evaluates whether the current IST time is within the +-15m blackout window
        of any critical macroeconomic announcement.
        """
        if dt_ist is None:
            dt_ist = datetime.now(IST)
        else:
            dt_ist = dt_ist.astimezone(IST)

        for event in self.scheduled_events:
            ev_hour = event.get("hour_ist")
            ev_min = event.get("minute_ist")
            if ev_hour is None or ev_min is None:
                continue

            # Create event datetime on the current day
            event_dt = dt_ist.replace(hour=ev_hour, minute=ev_min, second=0, microsecond=0)
            diff_seconds = abs((dt_ist - event_dt).total_seconds())

            if diff_seconds <= (self.buffer_minutes * 60):
                # Within +-15 minutes!
                mins_remaining = int(diff_seconds // 60)
                status_desc = f"{event['name']} ({event['impact']}) active window (+-{self.buffer_minutes}m)"
                return True, status_desc

        return False, None

    def get_sentinel_status(self, dt_ist: Optional[datetime] = None) -> Dict[str, Any]:
        is_blackout, event_name = self.is_news_blackout(dt_ist)
        if dt_ist is None:
            dt_ist = datetime.now(IST)

        return {
            "is_blackout": is_blackout,
            "status": "BLACKOUT ACTIVE (TRADING FROZEN)" if is_blackout else "CLEAR (NO HIGH-IMPACT NEWS)",
            "active_event": event_name,
            "buffer_minutes": self.buffer_minutes,
            "current_ist": dt_ist.strftime('%Y-%m-%d %H:%M:%S IST')
        }
