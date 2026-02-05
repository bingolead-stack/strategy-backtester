"""
CME Equity Index Futures Trading Hours Utility

Handles trading hour restrictions for CME equity index futures (MES/ES).
Uses exchange time (America/Chicago) to properly handle DST transitions.

Standard Trading Hours (Eastern Time):
- Sunday 6:00 PM ET - Friday 5:00 PM ET
- Daily maintenance: 5:00 PM - 6:00 PM ET (Mon-Thu)

Standard Trading Hours (Central Time - Exchange Time):
- Sunday 5:00 PM CT - Friday 4:00 PM CT
- Daily maintenance: 4:00 PM - 5:00 PM CT (Mon-Thu)

Market Holidays (Full Closure):
- New Year's Day
- Good Friday
- Memorial Day
- Independence Day
- Labor Day
- Thanksgiving
- Christmas

Early Close Days (1:00 PM ET / 12:00 PM CT):
- Day before Independence Day (July 3, or July 2 if July 4 is Monday)
- Day before Thanksgiving (Wednesday)
- Christmas Eve (Dec 24, unless weekend)
"""

from datetime import datetime, time, date, timedelta
from typing import Optional, Tuple, Set
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


def _calculate_easter(year: int) -> date:
    """
    Calculate Easter Sunday for a given year using the Anonymous Gregorian algorithm.

    Args:
        year: The year to calculate Easter for

    Returns:
        Date of Easter Sunday
    """
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _get_good_friday(year: int) -> date:
    """Get Good Friday (2 days before Easter) for a given year."""
    easter = _calculate_easter(year)
    return easter - timedelta(days=2)


def _get_memorial_day(year: int) -> date:
    """Get Memorial Day (last Monday of May) for a given year."""
    # Start from May 31 and go backwards to find Monday
    d = date(year, 5, 31)
    while d.weekday() != 0:  # 0 = Monday
        d -= timedelta(days=1)
    return d


def _get_labor_day(year: int) -> date:
    """Get Labor Day (first Monday of September) for a given year."""
    # Start from September 1 and find first Monday
    d = date(year, 9, 1)
    while d.weekday() != 0:
        d += timedelta(days=1)
    return d


def _get_thanksgiving(year: int) -> date:
    """Get Thanksgiving (4th Thursday of November) for a given year."""
    # Find first Thursday of November
    d = date(year, 11, 1)
    while d.weekday() != 3:  # 3 = Thursday
        d += timedelta(days=1)
    # Add 3 weeks to get 4th Thursday
    return d + timedelta(weeks=3)


def _adjust_for_weekend(d: date, observed: bool = True) -> date:
    """
    Adjust a holiday date if it falls on a weekend.

    If Saturday -> observed Friday
    If Sunday -> observed Monday

    Args:
        d: The holiday date
        observed: Whether to return observed date (default True)

    Returns:
        Adjusted date (or original if not on weekend)
    """
    if not observed:
        return d
    if d.weekday() == 5:  # Saturday
        return d - timedelta(days=1)  # Friday
    elif d.weekday() == 6:  # Sunday
        return d + timedelta(days=1)  # Monday
    return d


def get_market_holidays(year: int) -> Set[date]:
    """
    Get all CME equity futures market holidays for a given year.

    Args:
        year: The year to get holidays for

    Returns:
        Set of dates when market is fully closed
    """
    holidays = set()

    # New Year's Day (Jan 1)
    new_years = date(year, 1, 1)
    holidays.add(_adjust_for_weekend(new_years))

    # Good Friday
    holidays.add(_get_good_friday(year))

    # Memorial Day (last Monday of May)
    holidays.add(_get_memorial_day(year))

    # Independence Day (July 4)
    july_4 = date(year, 7, 4)
    holidays.add(_adjust_for_weekend(july_4))

    # Labor Day (first Monday of September)
    holidays.add(_get_labor_day(year))

    # Thanksgiving (4th Thursday of November)
    holidays.add(_get_thanksgiving(year))

    # Christmas (Dec 25)
    christmas = date(year, 12, 25)
    holidays.add(_adjust_for_weekend(christmas))

    return holidays


def get_early_close_days(year: int) -> dict:
    """
    Get all early close days for a given year.

    Early close is typically 12:00 PM CT (1:00 PM ET).

    Args:
        year: The year to get early close days for

    Returns:
        Dict mapping date to close time tuple (hour, minute) in CT
    """
    early_closes = {}

    # Get holidays to avoid conflicts
    holidays = get_market_holidays(year)

    # Day before Independence Day
    july_4 = date(year, 7, 4)

    if july_4.weekday() == 0:  # Monday - early close on Friday July 2
        early_close_day = july_4 - timedelta(days=3)
    elif july_4.weekday() == 5:  # Saturday - Friday is holiday, early close Thursday July 2
        early_close_day = july_4 - timedelta(days=2)
    elif july_4.weekday() == 6:  # Sunday - Monday is holiday, no early close
        early_close_day = None
    else:
        early_close_day = july_4 - timedelta(days=1)

    # Only add if it's a weekday and not a holiday
    if early_close_day and early_close_day.weekday() < 5 and early_close_day not in holidays:
        early_closes[early_close_day] = (12, 0)  # 12:00 PM CT

    # Day before Thanksgiving (Wednesday)
    thanksgiving = _get_thanksgiving(year)
    day_before_thanksgiving = thanksgiving - timedelta(days=1)
    early_closes[day_before_thanksgiving] = (12, 0)  # 12:00 PM CT

    # Christmas Eve (Dec 24) - if it's a weekday
    christmas_eve = date(year, 12, 24)
    if christmas_eve.weekday() < 5:  # Weekday
        early_closes[christmas_eve] = (12, 0)  # 12:00 PM CT

    # Day after Thanksgiving (Friday) - also early close
    day_after_thanksgiving = thanksgiving + timedelta(days=1)
    early_closes[day_after_thanksgiving] = (12, 15)  # 12:15 PM CT

    # New Year's Eve (Dec 31) - if it's a weekday
    new_years_eve = date(year, 12, 31)
    if new_years_eve.weekday() < 5:  # Weekday
        early_closes[new_years_eve] = (12, 0)  # 12:00 PM CT

    return early_closes


class CMETradingHours:
    """
    Manages CME equity index futures trading hours with proper timezone handling.

    Automatically calculates US market holidays and early close days.
    """

    # Standard CME equity index futures times (in Chicago/Central time)
    DAILY_CLOSE_TIME = time(16, 0)  # 4:00 PM CT (5:00 PM ET)
    DAILY_REOPEN_TIME = time(17, 0)  # 5:00 PM CT (6:00 PM ET)
    FLATTEN_MINUTES_BEFORE_CLOSE = 20  # Flatten 20 minutes before close

    def __init__(self, early_close_calendar: Optional[dict] = None):
        """
        Initialize CME trading hours handler.

        Args:
            early_close_calendar: Optional dict mapping date strings (YYYY-MM-DD)
                                  to early close times as (hour, minute) tuples.
                                  This allows manual overrides for special cases.
                                  Example: {"2024-11-29": (12, 15), "2024-12-24": (12, 15)}
        """
        self.manual_early_close_calendar = early_close_calendar or {}
        self._chicago_tz = self._get_chicago_timezone()
        self._holiday_cache = {}  # Cache holidays by year
        self._early_close_cache = {}  # Cache early closes by year

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

    def _get_holidays_for_year(self, year: int) -> Set[date]:
        """Get holidays for a year, using cache."""
        if year not in self._holiday_cache:
            self._holiday_cache[year] = get_market_holidays(year)
        return self._holiday_cache[year]

    def _get_early_closes_for_year(self, year: int) -> dict:
        """Get early close days for a year, using cache."""
        if year not in self._early_close_cache:
            self._early_close_cache[year] = get_early_close_days(year)
        return self._early_close_cache[year]

    def is_market_holiday(self, dt: datetime) -> bool:
        """
        Check if a given date is a market holiday (full closure).

        Args:
            dt: Datetime to check

        Returns:
            True if it's a market holiday
        """
        chicago_dt = self._to_chicago_time(dt)
        current_date = chicago_dt.date()
        holidays = self._get_holidays_for_year(current_date.year)
        return current_date in holidays

    def _get_close_time_for_date(self, dt: datetime) -> time:
        """
        Get the market close time for a specific date.

        Args:
            dt: The datetime to check

        Returns:
            Close time for that date
        """
        chicago_dt = self._to_chicago_time(dt)
        current_date = chicago_dt.date()
        date_str = current_date.strftime("%Y-%m-%d")

        # Check manual early close calendar first (for overrides)
        if date_str in self.manual_early_close_calendar:
            hour, minute = self.manual_early_close_calendar[date_str]
            return time(hour, minute)

        # Check auto-calculated early closes
        early_closes = self._get_early_closes_for_year(current_date.year)
        if current_date in early_closes:
            hour, minute = early_closes[current_date]
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
        close_dt = datetime.combine(dt.date(), close_time)
        flatten_dt = close_dt - timedelta(minutes=self.FLATTEN_MINUTES_BEFORE_CLOSE)
        return flatten_dt.time()

    def is_market_closed(self, dt: datetime) -> bool:
        """
        Check if the market is closed at the given time.

        Market is closed:
        - On market holidays (full day)
        - Between close time (4:00 PM CT) and reopen time (5:00 PM CT)
        - On weekends (Saturday all day, Sunday until 5:00 PM CT)

        Args:
            dt: Datetime to check

        Returns:
            True if market is closed, False if open
        """
        chicago_dt = self._to_chicago_time(dt)
        current_time = chicago_dt.time()
        weekday = chicago_dt.weekday()  # Monday=0, Sunday=6

        # Check if it's a holiday
        if self.is_market_holiday(chicago_dt):
            return True

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

        # Don't need to flatten on holidays
        if self.is_market_holiday(chicago_dt):
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
        - On market holidays
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

        # Check holiday first
        if self.is_market_holiday(chicago_dt):
            return False, f"Market closed (Holiday: {chicago_dt.date()})"

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

    def get_next_market_open(self, dt: datetime) -> datetime:
        """
        Get the next market open time after the given datetime.

        Args:
            dt: Current datetime

        Returns:
            Datetime of next market open
        """
        chicago_dt = self._to_chicago_time(dt)
        current_date = chicago_dt.date()

        # Start checking from today
        check_date = current_date
        max_days = 10  # Safety limit

        for _ in range(max_days):
            weekday = check_date.weekday()

            # Skip Saturday
            if weekday == 5:
                check_date += timedelta(days=1)
                continue

            # Skip holidays
            if check_date in self._get_holidays_for_year(check_date.year):
                check_date += timedelta(days=1)
                continue

            # Sunday opens at 5 PM CT
            if weekday == 6:
                open_time = datetime.combine(check_date, self.DAILY_REOPEN_TIME)
                if self._chicago_tz:
                    if HAS_ZONEINFO:
                        open_time = open_time.replace(tzinfo=self._chicago_tz)
                    elif HAS_PYTZ:
                        open_time = self._chicago_tz.localize(open_time)
                if open_time > chicago_dt:
                    return open_time
                check_date += timedelta(days=1)
                continue

            # Monday-Friday: opens at 5 PM CT (after maintenance)
            open_time = datetime.combine(check_date, self.DAILY_REOPEN_TIME)
            if self._chicago_tz:
                if HAS_ZONEINFO:
                    open_time = open_time.replace(tzinfo=self._chicago_tz)
                elif HAS_PYTZ:
                    open_time = self._chicago_tz.localize(open_time)

            if open_time > chicago_dt:
                return open_time

            check_date += timedelta(days=1)

        # Fallback
        return chicago_dt + timedelta(days=1)


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


def is_market_holiday(dt: datetime) -> bool:
    """
    Quick check if date is a market holiday.

    Args:
        dt: Datetime to check

    Returns:
        True if it's a market holiday
    """
    handler = CMETradingHours()
    return handler.is_market_holiday(dt)
