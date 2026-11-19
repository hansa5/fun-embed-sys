"""Run wheel checks during market hours and one daily market radar scan."""
from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from backend import market_radar, wheel
from backend.main import EARNINGS_WATCHLIST, POPULAR_STOCKS

logger = logging.getLogger("market_monitor")
NY = ZoneInfo("America/New_York")


def main() -> None:
    now = datetime.now(NY)
    if now.weekday() < 5 and (now.hour, now.minute) >= (9, 30) and (now.hour, now.minute) < (16, 0):
        result = market_radar.run_wheel_monitor()
        logger.info("Wheel monitor: %s", result)
    latest = market_radar.latest_radar()
    if market_radar.should_scan_after_close(now, latest):
        universe = list(POPULAR_STOCKS)
        known = {item["symbol"] for item in universe}
        universe.extend(item for item in EARNINGS_WATCHLIST if item["symbol"] not in known)
        universe.extend({"symbol": cycle["symbol"], "name": cycle["symbol"]} for cycle in wheel.list_cycles())
        universe.extend(market_radar.list_watchlist())
        logger.info("Market radar scan: %s", market_radar.run_radar(universe))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
