from datetime import UTC, datetime, timedelta, timezone

MOSCOW = timezone(timedelta(hours=3), name="Europe/Moscow")


def moscow_today():
    return datetime.now(MOSCOW).date()


def utc_naive(value: datetime) -> datetime:
    """Accept explicit offsets; dates without an offset refer to university local time."""
    return (
        (value if value.tzinfo else value.replace(tzinfo=MOSCOW))
        .astimezone(UTC)
        .replace(tzinfo=None)
    )
