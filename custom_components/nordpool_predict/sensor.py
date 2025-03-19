"""Sensor platform for Nordpool price predictions."""
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, Optional
import aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CURRENCY_CENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import template
from homeassistant.util import dt as dt_util
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME

from .const import DOMAIN, PREDICTION_URL, CONF_ADDITIONAL_COSTS, CONF_ACTUAL_PRICE_SENSOR, CONF_UPDATE_INTERVAL, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Define the scan interval as a timedelta
SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nordpool Predict sensor from config entry."""
    config = config_entry.data
    update_interval = timedelta(seconds=config.get(CONF_UPDATE_INTERVAL, SCAN_INTERVAL.total_seconds()))
    additional_costs_script = config.get(CONF_ADDITIONAL_COSTS)
    actual_price_sensor = config.get(CONF_ACTUAL_PRICE_SENSOR)
    
    async_add_entities(
        [
            NordpoolPredictSensor(
                hass,
                additional_costs_script,
                actual_price_sensor,
                update_interval
            )
        ],
        True,
    )

class NordpoolPredictSensor(SensorEntity):
    """Implementation of the Nordpool Predict sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        additional_costs_script: Optional[str] = None,
        actual_price_sensor: Optional[str] = None,
        update_interval: timedelta = SCAN_INTERVAL,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self._hass = hass
        self._predictions: list = []
        self._additional_costs_script = additional_costs_script
        self._actual_price_sensor = actual_price_sensor
        self._prediction_accuracy: Optional[float] = None
        self._attr_name = "Nordpool Price Prediction"
        self._attr_native_unit_of_measurement = "%"
        self._attr_unique_id = "nordpool_predict_next_price"
        self._update_interval = update_interval
        _LOGGER.info("Nordpool Predict sensor initialized with update interval: %s seconds", update_interval.total_seconds())

    @property
    def scan_interval(self) -> timedelta:
        """Return the scanning interval."""
        return self._update_interval

    def _calculate_additional_costs(self, timestamp: str) -> float:
        """Calculate additional costs for a given timestamp."""
        if not self._additional_costs_script:
            return 0

        try:
            # Create a template with the timestamp context
            tpl = template.Template(self._additional_costs_script, self._hass)
            dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
            
            # Render template with timestamp context
            context = {
                "now": dt
            }
            result = tpl.async_render(context)
            return float(result)
        except Exception as err:
            _LOGGER.error("Error calculating additional costs: %s", err)
            return 0

    def _calculate_prediction_accuracy(self) -> Optional[float]:
        """Calculate prediction accuracy by comparing with actual prices."""
        if not self._actual_price_sensor:  # Skip if no sensor configured
            _LOGGER.warning("Actual price sensor not found: %s", self._actual_price_sensor)
            return None
            
        actual_sensor = self._hass.states.get(self._actual_price_sensor)
        if not actual_sensor:
            _LOGGER.warning("Actual price sensor not found: %s", self._actual_price_sensor)
            return None

        try:
            raw_today = actual_sensor.attributes.get('raw_today', [])
            raw_tomorrow = actual_sensor.attributes.get('raw_tomorrow', [])
            
            # Convert raw prices to a format matching predictions
            actual_prices = []
            for price_data in raw_today + raw_tomorrow:
                if isinstance(price_data, dict) and 'start' in price_data and 'value' in price_data:
                    try:
                        if isinstance(price_data['start'], datetime):
                            dt = price_data['start']
                        else:
                            dt = dt_util.parse_datetime(price_data['start'])
                        
                        if dt:
                            actual_prices.append({
                                'timestamp': dt.astimezone(dt_util.UTC).strftime('%Y-%m-%d %H:%M:%S'),
                                'value': price_data['value']
                            })
                    except Exception as err:
                        _LOGGER.error("Error processing price data: %s, Error: %s", price_data, err)
                        continue

            reliability_data = []
            for prediction in self._predictions:
                # Find matching actual price for this prediction
                actual_value = next(
                    (item['value'] for item in actual_prices 
                     if item['timestamp'] == prediction['timestamp']),
                    None
                )
                
                if actual_value is not None:
                    predicted_value = prediction['value']
                    # Calculate accuracy using the repo's method
                    absolute_difference = abs(predicted_value - actual_value)
                    sum_absolute_values = abs(predicted_value) + abs(actual_value)
                    if sum_absolute_values > 0:  # Avoid division by zero
                        relative_difference = absolute_difference / sum_absolute_values
                        accuracy = 1 - relative_difference
                        # Ensure accuracy is between 0 and 1
                        accuracy = max(0, min(accuracy, 1))
                        reliability_data.append(accuracy)
                        _LOGGER.debug(
                            "Matched hour: %s, Predicted: %.2f, Actual: %.2f, Accuracy: %.3f", 
                            prediction['timestamp'], predicted_value, actual_value, accuracy
                        )

            if reliability_data:
                # Calculate average accuracy
                average_accuracy = sum(reliability_data) / len(reliability_data)
                _LOGGER.info(
                    "Calculated prediction accuracy: %.2f%% from %d hours compared",
                    average_accuracy * 100,
                    len(reliability_data)
                )
                return round(average_accuracy, 4)
            
            _LOGGER.warning("No matching hours found between predictions and actual prices")
            return None

        except Exception as err:
            _LOGGER.error("Error calculating prediction accuracy: %s", err)
            return None

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if self._prediction_accuracy is not None:
            return round(self._prediction_accuracy * 100, 2)  # Convert to percentage
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        return {
            "Prediction": self._predictions  # Return the full prediction array
        }

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        _LOGGER.info("Starting update for Nordpool Predict sensor")
        try:
            async with aiohttp.ClientSession() as session:
                _LOGGER.info("Fetching data from: %s", PREDICTION_URL)
                async with session.get(PREDICTION_URL) as response:
                    if response.status == 200:
                        # Read response as text first
                        text_data = await response.text()
                        
                        try:
                            raw_data = await response.json(content_type=None)
                            
                            # Convert raw data to formatted predictions
                            formatted_predictions = []
                            for pair in raw_data:
                                # Convert milliseconds timestamp to local timezone first
                                local_dt = datetime.fromtimestamp(
                                    pair[0] / 1000,  # Convert milliseconds to seconds
                                    tz=dt_util.get_time_zone(self._hass.config.time_zone)
                                )
                                # Convert to UTC for storage
                                utc_dt = local_dt.astimezone(dt_util.UTC)
                                timestamp = utc_dt.strftime("%Y-%m-%d %H:%M:%S")
                                
                                base_value = round(pair[1], 4)
                                
                                if self._additional_costs_script:
                                    try:
                                        # Include detailed breakdown when additional costs are configured
                                        additional_cost = self._calculate_additional_costs(timestamp)
                                        total_value = round(base_value + additional_cost, 3)
                                        formatted_predictions.append({
                                        "timestamp": timestamp,  # Now in format: '2025-03-17 13:00:00'
                                        "value": total_value,
                                        "base_price": round(base_value, 3),
                                        "additional_cost": round(additional_cost, 3)
                                    })
                                    except Exception as err:
                                        _LOGGER.error("Error calculating additional costs: %s", err)
                                        formatted_predictions.append({
                                            "timestamp": timestamp,
                                            "value": round(base_value, 3)
                                        })
                                else:
                                    # Simplified version without cost breakdown
                                    formatted_predictions.append({
                                        "timestamp": timestamp,
                                        "value": round(base_value, 3)
                                    })
                            
                            self._predictions = formatted_predictions

                        except ValueError as err:
                            _LOGGER.error("Failed to parse JSON: %s. Raw data: %s", err, text_data[:200])

                        # Calculate accuracy after updating predictions
                        accuracy = self._calculate_prediction_accuracy()
                        
                        # Sanity check for prediction accuracy
                        if accuracy is not None and 0 <= accuracy <= 1:
                            self._prediction_accuracy = accuracy
                        else:
                            _LOGGER.warning("Invalid accuracy value: %s. It must be between 0 and 1.", accuracy)
                            self._prediction_accuracy = None
                        
                    else:
                        _LOGGER.error("Failed to fetch prediction data: HTTP %s", response.status)
        except aiohttp.ClientError as err:
            _LOGGER.error("Network error while fetching predictions: %s", err)
        except Exception as err:
            _LOGGER.exception("Unexpected error updating Nordpool prediction: %s", err)


