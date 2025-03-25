"""Config flow for Nordpool Predict integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.const import CONF_NAME

from .const import DOMAIN, CONF_UPDATE_INTERVAL, CONF_ADDITIONAL_COSTS, CONF_ACTUAL_PRICE_SENSOR

class NordpoolPredictConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nordpool Predict."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Optional(CONF_NAME, default="Nordpool Predict"): str,
                    vol.Optional(CONF_UPDATE_INTERVAL, default=900): int,
                    vol.Optional(CONF_ADDITIONAL_COSTS): str,
                    vol.Optional(CONF_ACTUAL_PRICE_SENSOR): str,
                })
            )

        # Ensure all necessary fields are included in the entry
        return self.async_create_entry(title=user_input[CONF_NAME], data={
            CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
            CONF_ADDITIONAL_COSTS: user_input.get(CONF_ADDITIONAL_COSTS, ""),
            CONF_ACTUAL_PRICE_SENSOR: user_input.get(CONF_ACTUAL_PRICE_SENSOR, ""),
        })

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NordpoolPredictOptionsFlow:
        """Get the options flow for this handler."""
        return NordpoolPredictOptionsFlow(config_entry)

class NordpoolPredictOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()  # Initialize the base class
        self.config_entry = config_entry  # Store the config entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, 900
                    ),
                ): int,
                vol.Optional(
                    CONF_ADDITIONAL_COSTS,
                    default=self.config_entry.options.get(CONF_ADDITIONAL_COSTS, ""),
                ): str,
                vol.Optional(
                    CONF_ACTUAL_PRICE_SENSOR,
                    default=self.config_entry.options.get(CONF_ACTUAL_PRICE_SENSOR, ""),
                ): str,
            })
        ) 