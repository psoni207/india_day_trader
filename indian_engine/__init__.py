"""Indian Equities & Indices Trading Engine for NSE Nifty 50 and BankNifty.

Specialized for:
- 09:15 AM to 03:15 PM IST trading session
- 15-Minute Opening Range Breakout (ORB)
- Central Pivot Range (CPR: Pivot, TC, BC) + VWAP Confluence
- Options Put-Call Ratio (PCR) & Open Interest (OI) strike walls
- Mandatory 03:15 PM IST hard auto-square-off sentinel
"""
