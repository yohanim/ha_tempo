from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
import io
import csv
import copy
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    TEMPO_TIMEZONE,
    CONF_CONTRACT,
    CONTRACT_BASE,
    CONTRACT_HEURES_CREUSES,
    CONTRACT_TEMPO,
    DEFAULT_CONTRACT,
    CONF_OFFPEAK_RANGES,
    DEFAULT_OFFPEAK_RANGES,
    CONF_SUBSCRIBED_POWER,
    DEFAULT_SUBSCRIBED_POWER,
    CONF_PRICE_UPDATE_INTERVAL,
    DEFAULT_PRICE_UPDATE_INTERVAL,
    PRICE_BASE_URL,
    PRICE_HPHC_URL,
    PRICE_TEMPO_URL,
)
from .utils import parse_offpeak_ranges, is_offpeak, normalize_contract
from .tempo_coordinator import TempoDataCoordinator
from .utils import get_tempo_date

_LOGGER = logging.getLogger(__name__)

# Fallback prices in case of API failure (updated with lowercase keys)
FALLBACK_PRICES = {
    CONTRACT_BASE: {"HP": 0.2516},
    CONTRACT_HEURES_CREUSES: {"HP": 0.27, "HC": 0.2068},
    CONTRACT_TEMPO: {
        "blue": {"HP": 0.1749, "HC": 0.1486},
        "white": {"HP": 0.363, "HC": 0.1894},
        "red": {"HP": 0.7562, "HC": 0.272},
        "unknown": {"HP": 0, "HC": 0},
    },
}

class PriceCoordinator(DataUpdateCoordinator):
    """Coordinator for managing electricity prices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, tempo_coordinator: TempoDataCoordinator):
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Price Coordinator",
            update_interval=None,  # Updates are triggered by time changes
        )
        self.entry = entry
        self.tempo_coordinator = tempo_coordinator
        self.session = async_get_clientsession(hass)
        self._offpeak_ranges = []
        self._contract = DEFAULT_CONTRACT
        self._subscribed_power = DEFAULT_SUBSCRIBED_POWER
        self._price_update_interval = DEFAULT_PRICE_UPDATE_INTERVAL
        self._prices = copy.deepcopy(FALLBACK_PRICES)
        self._last_price_update = None
        self._store: Store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_prices_cache")
        self._scheduled_update_listeners = []
        self._setup_from_options()

        # Calculate 5 minutes before Tempo day change
        change_time = tempo_coordinator.tempo_day_change_time
        # Create a dummy datetime to perform arithmetic
        dummy_dt = datetime.combine(dt_util.now().date(), change_time)
        update_dt = dummy_dt - timedelta(minutes=5)
        update_time = update_dt.time()

        # Schedule prices update once a day (5 minutes before day change)
        self._scheduled_update_listeners.append(
            async_track_time_change(
                hass,
                self._update_prices,
                hour=update_time.hour,
                minute=update_time.minute,
                second=update_time.second,
            )
        )
        # Initial prices fetch
        self.hass.async_create_task(self._update_prices())

    @callback
    def _setup_from_options(self):
        """Set up the coordinator from config entry options."""
        options = self.entry.options
        self._contract = normalize_contract(options.get(CONF_CONTRACT, DEFAULT_CONTRACT))
        self._subscribed_power = options.get(CONF_SUBSCRIBED_POWER, DEFAULT_SUBSCRIBED_POWER)
        self._price_update_interval = options.get(CONF_PRICE_UPDATE_INTERVAL, DEFAULT_PRICE_UPDATE_INTERVAL)
        offpeak_ranges_str = options.get(CONF_OFFPEAK_RANGES, DEFAULT_OFFPEAK_RANGES)
        self._offpeak_ranges = parse_offpeak_ranges(offpeak_ranges_str)
        _LOGGER.info(
            "Price coordinator setup: Contract='%s', Power='%s kVA', Off-peak ranges=%s, Update interval: %s day(s)",
            self._contract,
            self._subscribed_power,
            offpeak_ranges_str,
            self._price_update_interval,
        )
        self._schedule_listeners()

    def _schedule_listeners(self):
        """Schedule updates at specific times."""
        # Clear existing listeners
        for remove_listener in self._scheduled_update_listeners:
            remove_listener()
        self._scheduled_update_listeners.clear()

        trigger_times = set()
        
        # Add offpeak ranges transitions
        for start, end in self._offpeak_ranges:
            trigger_times.add(start)
            trigger_times.add(end)
            
        # Add Tempo day change time
        trigger_times.add(self.tempo_coordinator.tempo_day_change_time)

        _LOGGER.debug("Scheduling prices updates at: %s", [t.strftime("%H:%M:%S") for t in trigger_times])

        for t in trigger_times:
            self._scheduled_update_listeners.append(
                async_track_time_change(self.hass, self._async_scheduled_refresh, hour=t.hour, minute=t.minute, second=t.second)
            )

    async def _async_scheduled_refresh(self, _now: datetime) -> None:
        """Trigger a refresh of the coordinator data."""
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        """Release scheduled listeners and coordinator timers."""
        for remove_listener in self._scheduled_update_listeners:
            remove_listener()
        self._scheduled_update_listeners.clear()
        await super().async_shutdown()

    async def async_load_cache(self) -> None:
        """Restore cached price grid from disk (called before first refresh)."""
        stored = await self._store.async_load()
        if not stored or not isinstance(stored, dict):
            return
        if stored.get("contract") == self._contract and stored.get("prices"):
            self._prices = stored["prices"]
            last_update_str = stored.get("last_update")
            if last_update_str:
                try:
                    self._last_price_update = datetime.fromisoformat(last_update_str)
                except ValueError:
                    pass
            _LOGGER.debug("Restored cached prices for contract %s from storage", self._contract)

    async def async_force_prices_update(self) -> None:
        """Force an immediate price grid refresh (bypasses the update interval)."""
        await self._update_prices(force=True)

    async def _update_prices(
        self, _now: datetime | None = None, *, force: bool = False
    ) -> None:
        """Fetch and parse prices from data.gouv.fr."""
        # Check if update is needed based on interval
        if not force and self._last_price_update:
            # Ensure interval is at least 1
            interval = max(1, self._price_update_interval)
            days_since_last_update = (dt_util.now() - self._last_price_update).days
            if days_since_last_update < interval:
                _LOGGER.debug(
                    "Price update skipped, only %s day(s) since last update (interval: %s days)",
                    days_since_last_update,
                    interval,
                )
                return

        _LOGGER.info("Attempting to update prices from data.gouv.fr for contract: %s", self._contract)
        
        new_prices = self._prices.copy()
        has_updated = False
        
        try:
            if self._contract == CONTRACT_BASE:
                try:
                    base_prices = await self._fetch_and_parse_csv(PRICE_BASE_URL, self._parse_base_prices)
                    if base_prices:
                        new_prices[CONTRACT_BASE] = base_prices
                        has_updated = True
                except Exception as e:
                    _LOGGER.warning("Failed to update Base prices: %s", e)

            elif self._contract == CONTRACT_HEURES_CREUSES:
                try:
                    hphc_prices = await self._fetch_and_parse_csv(PRICE_HPHC_URL, self._parse_hphc_prices)
                    if hphc_prices:
                        new_prices[CONTRACT_HEURES_CREUSES] = hphc_prices
                        has_updated = True
                except Exception as e:
                    _LOGGER.warning("Failed to update HP/HC prices: %s", e)

            elif self._contract == CONTRACT_TEMPO:
                try:
                    tempo_prices = await self._fetch_and_parse_csv(PRICE_TEMPO_URL, self._parse_tempo_prices)
                    if tempo_prices:
                        if CONTRACT_TEMPO not in new_prices:
                            new_prices[CONTRACT_TEMPO] = {}
                        new_prices[CONTRACT_TEMPO].update(tempo_prices)
                        has_updated = True
                except Exception as e:
                    _LOGGER.warning("Failed to update Tempo prices: %s", e)
            
            if not has_updated:
                _LOGGER.warning("Failed to update prices for %s. Keeping previous prices.", self._contract)
            else:
                self._prices = new_prices
                self._last_price_update = dt_util.now()
                _LOGGER.info("Successfully updated prices from data.gouv.fr")
                self.hass.async_create_task(self._store.async_save({
                    "contract": self._contract,
                    "prices": self._prices,
                    "last_update": self._last_price_update.isoformat(),
                }))
                await self.async_refresh()

        except Exception as e:
            _LOGGER.error("Unexpected error during price update: %s. Keeping previous prices.", e, exc_info=True)

    async def _fetch_and_parse_csv(self, url: str, parser_func: callable) -> dict:
        """Generic function to fetch a CSV and parse it."""
        async with asyncio.timeout(20):
            response = await self.session.get(url)
            response.raise_for_status()
            content_bytes = await response.read()
        
        # Tentative de décodage UTF-8 (avec gestion du BOM), sinon repli sur Latin-1
        try:
            content = content_bytes.decode('utf-8')
            if content.startswith('\ufeff'):
                content = content[1:]
        except UnicodeDecodeError:
            content = content_bytes.decode('latin-1')

        csv_file = io.StringIO(content)
        return parser_func(csv_file)

    def _get_csv_reader(self, csv_file: io.StringIO) -> csv.DictReader:
        """Create a DictReader with cleaned headers."""
        # Détermination du délimiteur et nettoyage des entêtes
        pos = csv_file.tell()
        first_line = csv_file.readline()
        csv_file.seek(pos)
        
        delimiter = ';' if ';' in first_line else ','
        
        # Lecture des entêtes pour les nettoyer (strip)
        reader = csv.reader(csv_file, delimiter=delimiter)
        try:
            headers = next(reader)
        except StopIteration:
            return csv.DictReader(csv_file, delimiter=delimiter)
            
        cleaned_headers = [h.strip() for h in headers]
        return csv.DictReader(csv_file, fieldnames=cleaned_headers, delimiter=delimiter)

    def _parse_date(self, date_str: str) -> date | None:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                pass
        return None

    def _is_row_active(self, row: dict, target_date: date) -> bool:
        start_date = self._parse_date(row.get("DATE_DEBUT"))
        end_date = self._parse_date(row.get("DATE_FIN"))
        
        if not start_date:
            return False
        
        if start_date > target_date:
            return False
        
        if end_date and end_date < target_date:
            return False
            
        return True

    def _parse_base_prices(self, csv_file: io.StringIO) -> dict:
        """Parse Base price CSV."""
        reader = self._get_csv_reader(csv_file)
        target_date = dt_util.now(dt_util.get_time_zone(TEMPO_TIMEZONE)).date()

        for row in reader:
            if row.get("P_SOUSCRITE", "").strip() != self._subscribed_power:
                continue
            
            if not self._is_row_active(row, target_date):
                continue

            try:
                price = float(row["PART_VARIABLE_TTC"].replace(',', '.'))
                _LOGGER.debug("Found Base price for %s kVA: %s", self._subscribed_power, price)
                return {"HP": price}
            except ValueError:
                continue
        _LOGGER.warning("Base price not found for %s kVA", self._subscribed_power)
        return {}

    def _parse_hphc_prices(self, csv_file: io.StringIO) -> dict:
        """Parse HP/HC price CSV."""
        reader = self._get_csv_reader(csv_file)
        target_date = dt_util.now(dt_util.get_time_zone(TEMPO_TIMEZONE)).date()

        for row in reader:
            if row.get("P_SOUSCRITE", "").strip() != self._subscribed_power:
                continue
            
            if not self._is_row_active(row, target_date):
                continue

            try:
                hp_price = float(row["PART_VARIABLE_HP_TTC"].replace(',', '.'))
                hc_price = float(row["PART_VARIABLE_HC_TTC"].replace(',', '.'))
                prices = {"HP": hp_price, "HC": hc_price}
                _LOGGER.debug("Found HP/HC prices for %s kVA: %s", self._subscribed_power, prices)
                return prices
            except ValueError:
                continue
        
        _LOGGER.warning("HP/HC prices not fully found for %s kVA", self._subscribed_power)
        return {}

    def _parse_tempo_prices(self, csv_file: io.StringIO) -> dict:
        """Parse Tempo price CSV."""
        reader = self._get_csv_reader(csv_file)
        target_date = dt_util.now(dt_util.get_time_zone(TEMPO_TIMEZONE)).date()

        for row in reader:
            if row.get("P_SOUSCRITE", "").strip() != self._subscribed_power:
                continue
            
            if not self._is_row_active(row, target_date):
                continue

            try:
                prices = {"blue": {}, "white": {}, "red": {}}
                
                prices["blue"]["HC"] = float(row["PART_VARIABLE_HCBleu_TTC"].replace(',', '.'))
                prices["blue"]["HP"] = float(row["PART_VARIABLE_HPBleu_TTC"].replace(',', '.'))
                prices["white"]["HC"] = float(row["PART_VARIABLE_HCBlanc_TTC"].replace(',', '.'))
                prices["white"]["HP"] = float(row["PART_VARIABLE_HPBlanc_TTC"].replace(',', '.'))
                prices["red"]["HC"] = float(row["PART_VARIABLE_HCRouge_TTC"].replace(',', '.'))
                prices["red"]["HP"] = float(row["PART_VARIABLE_HPRouge_TTC"].replace(',', '.'))
                
                _LOGGER.debug("Found Tempo prices for %s kVA: %s", self._subscribed_power, prices)
                return prices
            except ValueError:
                continue

        _LOGGER.warning("Tempo prices not fully found for %s kVA", self._subscribed_power)
        return {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Calculate the current prices data."""
        now = dt_util.now(dt_util.get_time_zone(TEMPO_TIMEZONE))
        
        # Determine current period (HP/HC)
        if self._contract == CONTRACT_BASE:
            is_hc = False
            current_period = "HP"
        else:
            is_hc = is_offpeak(now, self._offpeak_ranges)
            current_period = "HC" if is_hc else "HP"

        price = 0.0
        tempo_color = "unknown"

        if self._contract == CONTRACT_BASE:
            price = self._prices.get(CONTRACT_BASE, {}).get("HP", 0.0)
        elif self._contract == CONTRACT_HEURES_CREUSES:
            price = self._prices.get(CONTRACT_HEURES_CREUSES, {}).get(current_period, 0.0)
        elif self._contract == CONTRACT_TEMPO:
            tempo_day_change_time_str = self.tempo_coordinator.tempo_day_change_time_str
            today_date_str = get_tempo_date(0, tempo_day_change_time_str)
            tempo_color = self.tempo_coordinator.get_data(today_date_str) or "unknown"
            tempo_color = tempo_color.lower()

            price = self._prices.get(CONTRACT_TEMPO, {}).get(tempo_color, {}).get(current_period, 0.0)

        # Calculate next change time
        next_change = None
        trigger_times = set()
        for start, end in self._offpeak_ranges:
            trigger_times.add(start)
            trigger_times.add(end)
        trigger_times.add(self.tempo_coordinator.tempo_day_change_time)
        
        current_time = now.time()
        sorted_triggers = sorted(list(trigger_times))
        
        for t in sorted_triggers:
            if t > current_time:
                next_change = t
                break
        
        if next_change is None and sorted_triggers:
            next_change = sorted_triggers[0]

        return {
            "price": price,
            "is_hc": is_hc,
            "is_hp": not is_hc,
            "current_period": current_period,
            "contract": self._contract,
            "tempo_color": tempo_color if self._contract == CONTRACT_TEMPO else None,
            "last_update": now.isoformat(),
            "prices_last_update": self._last_price_update.isoformat() if self._last_price_update else None,
            "contract_prices": self._prices.get(self._contract, {}),
            "subscribed_power": self._subscribed_power,
            # Combined boolean attributes for easier automations
            "is_blue_hp": tempo_color == "blue" and current_period == "HP",
            "is_blue_hc": tempo_color == "blue" and current_period == "HC",
            "is_white_hp": tempo_color == "white" and current_period == "HP",
            "is_white_hc": tempo_color == "white" and current_period == "HC",
            "is_red_hp": tempo_color == "red" and current_period == "HP",
            "is_red_hc": tempo_color == "red" and current_period == "HC",
            "next_period_change": next_change.strftime("%H:%M:%S") if next_change else None,
        }
