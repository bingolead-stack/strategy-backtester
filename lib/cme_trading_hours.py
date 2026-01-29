"""
CME Equity Index Futures Trading Hours Utility

Handles trading hour restrictions for CME equity index futures (MES/ES).
Uses exchange time (America/Chicago) to properly handle DST transitions.

Standard Trading Day:
- Daily close: 4:00 PM CT (Central Time)
- Reopens: 5:00 PM CT

Operational Rules:
- Flatten positions: 3:40 PM CT (20 minutes before close)
- Allow trading again: 5:00 PM CT (market reopen)

Important Notes:
- Sunday session opens at 5:00 PM CT (same as weekday reopen)
- Early closes on certain holidays are handled via an optional calendar
"""

from datetime import datetime, time, timedelta
from typing import Optional, Tuple
import logging

try:
    import pytz
    HAS_PYTZ = True
except ImportError:
    HAS_PYTZ = False

try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    HAS_ZONEINFO = False

logger = logging.getLogger('strategy')


class CMETradingHours:
    """
    Manages CME equity index futures trading hours with proper timezone handling.
    """

    # Standard CME equity index futures times (in Chicago/Central time)
    DAILY_CLOSE_TIME = time(16, 0)  # 4:00 PM CT
    DAILY_REOPEN_TIME = time(17, 0)  # 5:00 PM CT
    FLATTEN_MINUTES_BEFORE_CLOSE = 20  # Flatten 20 minutes before close

    # Known early close dates (month, day) -> close time in CT
    # These are typical early close dates; update as needed
    EARLY_CLOSE_DATES = {
        # Day after Thanksgiving (4th Friday of November) - typically 12:15 PM CT
        # Christmas Eve (Dec 24) - typically 12:15 PM CT
        # New Year's Eve (Dec 31) - typically 12:15 PM CT
        # Note: Actual dates vary by year, so this is a simplified approach
    }

    def __init__(self, early_close_calendar: Optional[dict] = None):
        """
        Initialize CME trading hours handler.

        Args:
            early_close_calendar: Optional dict mapping date strings (YYYY-MM-DD)
                                  to early close times as (hour, minute) tuples.
                                  Example: {"2024-11-29": (12, 15), "2024-12-24": (12, 15)}
        """
        self.early_close_calendar = early_close_calendar or {}
        self._chicago_tz = self._get_chicago_timezone()

    def _get_chicago_timezone(self):
        """Get Chicago timezone object, handling different Python versions."""
        if HAS_ZONEINFO:
            return ZoneInfo("America/Chicago")
        elif HAS_PYTZ:
            return pytz.timezone("America/Chicago")
        else:
            logger.warning("Neither zoneinfo nor pytz available. Using naive datetime handling.")
            return None

    def _to_chicago_time(self, dt: datetime) -> datetime:
        """
        Convert a datetime to Chicago time.

        Args:
            dt: Input datetime (can be naive or timezone-aware)

        Returns:
            Datetime in Chicago time
        """
        if self._chicago_tz is None:
            # Fallback: assume input is already in CT or close enough
            return dt

        if dt.tzinfo is None:
            # Naive datetime - assume it's already in Chicago time for backtesting
            if HAS_ZONEINFO:
                return dt.replace(tzinfo=self._chicago_tz)
            elif HAS_PYTZ:
                return self._chicago_tz.localize(dt)
        else:
            # Convert to Chicago time
            if HAS_ZONEINFO:
                return dt.astimezone(self._chicago_tz)
            elif HAS_PYTZ:
                return dt.astimezone(self._chicago_tz)

        return dt

    def _get_close_time_for_date(self, dt: datetime) -> time:
        """
        Get the market close time for a specific date.

        Args:
            dt: The datetime to check

        Returns:
            Close time for that date
        """
        date_str = dt.strftime("%Y-%m-%d")

        # Check early close calendar
        if date_str in self.early_close_calendar:
            hour, minute = self.early_close_calendar[date_str]
            return time(hour, minute)

        return self.DAILY_CLOSE_TIME

    def _get_flatten_time_for_date(self, dt: datetime) -> time:
        """
        Get the flatten time for a specific date (20 min before close).

        Args:
            dt: The datetime to check

        Returns:
            Flatten time for that date
        """
        close_time = self._get_close_time_for_date(dt)
        # Create a datetime to do the subtraction
        close_dt = datetime.combine(dt.date(), close_time)
        flatten_dt = close_dt - timedelta(minutes=self.FLATTEN_MINUTES_BEFORE_CLOSE)
        return flatten_dt.time()

    def is_market_closed(self, dt: datetime) -> bool:
        """
        Check if the market is closed at the given time.

        Market is closed between close time (4:00 PM CT) and reopen time (5:00 PM CT).
        On weekends (Saturday all day, Sunday until 5:00 PM CT).

        Args:
            dt: Datetime to check

        Returns:
            True if market is closed, False if open
        """
        chicago_dt = self._to_chicago_time(dt)
        current_time = chicago_dt.time()
        weekday = chicago_dt.weekday()  # Monday=0, Sunday=6

        close_time = self._get_close_time_for_date(chicago_dt)

        # Saturday is always closed
        if weekday == 5:
            return True

        # Sunday is closed until 5:00 PM CT
        if weekday == 6:
            return current_time < self.DAILY_REOPEN_TIME

        # Monday-Friday: closed between close_time and reopen_time
        if close_time <= current_time < self.DAILY_REOPEN_TIME:
            return True

        return False

    def should_flatten_positions(self, dt: datetime) -> bool:
        """
        Check if we should flatten positions (20 minutes before market close).

        Args:
            dt: Datetime to check

        Returns:
            True if we should flatten positions, False otherwise
        """
        chicago_dt = self._to_chicago_time(dt)
        current_time = chicago_dt.time()
        weekday = chicago_dt.weekday()

        # Don't need to flatten on Saturday or Sunday before open
        if weekday == 5:
            return False
        if weekday == 6 and current_time < self.DAILY_REOPEN_TIME:
            return False

        flatten_time = self._get_flatten_time_for_date(chicago_dt)
        close_time = self._get_close_time_for_date(chicago_dt)

        # Flatten if we're in the flatten window (between flatten time and close time)
        if flatten_time <= current_time < close_time:
            return True

        return False

    def is_trading_allowed(self, dt: datetime) -> bool:
        """
        Check if trading is allowed at the given time.

        Trading is NOT allowed:
        - During market closed hours
        - During the flatten window (20 min before close)

        Args:
            dt: Datetime to check

        Returns:
            True if trading is allowed, False otherwise
        """
        if self.is_market_closed(dt):
            return False

        if self.should_flatten_positions(dt):
            return False

        return True

    def get_trading_status(self, dt: datetime) -> Tuple[bool, str]:
        """
        Get detailed trading status for logging/debugging.

        Args:
            dt: Datetime to check

        Returns:
            Tuple of (is_trading_allowed, status_message)
        """
        chicago_dt = self._to_chicago_time(dt)
        current_time = chicago_dt.time()
        weekday = chicago_dt.weekday()
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        if weekday == 5:
            return False, f"Market closed (Saturday)"

        if weekday == 6 and current_time < self.DAILY_REOPEN_TIME:
            return False, f"Market closed (Sunday, opens at {self.DAILY_REOPEN_TIME})"

        close_time = self._get_close_time_for_date(chicago_dt)
        flatten_time = self._get_flatten_time_for_date(chicago_dt)

        if close_time <= current_time < self.DAILY_REOPEN_TIME:
            return False, f"Market closed ({close_time} - {self.DAILY_REOPEN_TIME} CT)"

        if flatten_time <= current_time < close_time:
            return False, f"Flatten window ({flatten_time} - {close_time} CT)"

        return True, f"Trading allowed ({day_names[weekday]} {current_time} CT)"


# Convenience function for simple usage
def is_trading_allowed(dt: datetime, early_close_calendar: Optional[dict] = None) -> bool:
    """
    Quick check if trading is allowed at the given time.

    Args:
        dt: Datetime to check
        early_close_calendar: Optional dict of early close dates

    Returns:
        True if trading is allowed
    """
    handler = CMETradingHours(early_close_calendar)
    return handler.is_trading_allowed(dt)


def should_flatten_positions(dt: datetime, early_close_calendar: Optional[dict] = None) -> bool:
    """
    Quick check if positions should be flattened.

    Args:
        dt: Datetime to check
        early_close_calendar: Optional dict of early close dates

    Returns:
        True if positions should be flattened
    """
    handler = CMETradingHours(early_close_calendar)
    return handler.should_flatten_positions(dt)
