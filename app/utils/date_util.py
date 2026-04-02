"""Date utility functions for generating partition strings and business dates.

Provides convenient functions for calculating relative dates and formatting them
as partition identifiers used in data pipelines and ETL jobs.

All dates are timezone-aware and use the timezone configured in app.configs.config.

Usage:
    from app.utils.date_util import get_partition, get_bizdate

    # Get yesterday as YYYYMMDD partition
    partition = get_partition()  # Returns "20240115" for Jan 15, 2024

    # Get first day of the month as datetime format
    month_start = get_partition(timedelta(days=1), is_start_month=True, is_datetime=True)

    # Get business date (DataWorks convention)
    bizdate = get_bizdate()  # Returns "2024-01-15"

Date Calculation:
    - All functions use `now` from app.configs.config (loaded at import time)
    - `now` is timezone-aware using configured timezone (Asia/Jakarta by default)
    - date_add parameter specifies how many days back from now:
      - timedelta(days=1): yesterday (default for partition/bizdate)
      - timedelta(days=0): today
      - timedelta(days=2): day before yesterday
      - negative values: future dates

Output Formats:
    - YYYYMMDD: "20240115" - used for partition identifiers
    - YYYY-MM-DD: "2024-01-15" - DataWorks bizdate format
    - YYYY-MM-DD 00:00:00: "2024-01-15 00:00:00" - datetime with time component

Template Customization:
    To use in another workspace:
    1. Copy this file to your project's app/utils/ directory
    2. Ensure app/configs/config.py is in place and loads correctly
    3. Import functions directly; no additional setup needed
    4. Customize timezone in config.py if needed for your region
"""

from datetime import timedelta

from app.configs.config import now


def get_partition(
    date_add: timedelta = timedelta(days=1),
    is_start_month: bool = False,
    is_datetime: bool = False,
    time_format: str = "00:00:00",
) -> str:
    """Return a partition date string derived from the current date.

    Commonly used for generating partition identifiers in data warehouses
    (e.g., day partitions, week partitions for ETL jobs).

    Args:
        date_add: Timedelta to subtract from current time (default: 1 day for yesterday).
            Use timedelta(days=0) for today, timedelta(days=2) for day before yesterday.
        is_start_month: If True, return the first day of the resulting month.
        is_datetime: If True, return datetime format ('YYYY-MM-DD 00:00:00').
            If False, return compact format ('YYYYMMDD').
        time_format: Time string to append when is_datetime=True (default: "00:00:00").

    Returns:
        Date string in 'YYYYMMDD' (compact) or 'YYYY-MM-DD HH:MM:SS' (datetime) format.

    Example:
        >>> get_partition()  # Yesterday in compact format
        '20240115'

        >>> get_partition(timedelta(days=2), is_datetime=True)
        '2024-01-13 00:00:00'

        >>> get_partition(is_start_month=True)
        '20240101'  # First day of current month
    """
    yesterday = now - date_add
    if is_start_month:
        yesterday = yesterday.replace(day=1)

    if is_datetime:
        return yesterday.strftime(f"%Y-%m-%d {time_format}")

    return yesterday.strftime("%Y%m%d")


def get_bizdate(date_add: timedelta = timedelta(days=1), is_datetime: bool = False) -> str:
    """Return the business date string for DataWorks bizdate convention.

    DataWorks uses 'bizdate' for pipeline execution dates and scheduling.
    In most systems, bizdate refers to the date of the business day (previous day for overnight jobs).

    Args:
        date_add: Timedelta to subtract from current time (default: 1 day for yesterday).
        is_datetime: If True, return datetime format ('YYYY-MM-DD 00:00:00').
            If False, return date-only format ('YYYY-MM-DD').

    Returns:
        Date string in 'YYYY-MM-DD' (date only) or 'YYYY-MM-DD 00:00:00' (with time) format.

    Example:
        >>> get_bizdate()
        '2024-01-15'

        >>> get_bizdate(is_datetime=True)
        '2024-01-15 00:00:00'

        >>> get_bizdate(timedelta(days=0))  # Today
        '2024-01-16'
    """
    bizdate = now - date_add
    if is_datetime:
        return bizdate.strftime("%Y-%m-%d 00:00:00")
    return bizdate.strftime("%Y-%m-%d")


def get_bizdate_with_time(
    date_add: timedelta = timedelta(days=0),
    time_format: str = "00:00:00",
) -> str:
    """Return a date with appended time in 'YYYY-MM-DD HH:MM:SS' format for DataWorks.

    Convenience function for generating timestamps with custom time components.

    Args:
        date_add: Timedelta to subtract from current time (default: 0 for today).
        time_format: Time string to append (default: "00:00:00").

    Returns:
        Date-time string in 'YYYY-MM-DD HH:MM:SS' format.

    Example:
        >>> get_bizdate_with_time()
        '2024-01-16 00:00:00'

        >>> get_bizdate_with_time(time_format="12:30:45")
        '2024-01-16 12:30:45'

        >>> get_bizdate_with_time(timedelta(days=1), "23:59:59")
        '2024-01-15 23:59:59'
    """
    bizdate = get_bizdate(date_add)
    return f"{bizdate} {time_format}"
