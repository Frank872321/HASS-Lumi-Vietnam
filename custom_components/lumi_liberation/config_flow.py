from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import uuid4

import paho.mqtt.client as mqtt
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class LumiConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Lumi Vietnam."""

    VERSION = 1

    def __init__(self) -> None:
        self.discovered_host: str | None = None
        self.discovered_port: int | None = None
        self.discovered_name: str | None = None

    async def _async_test_connection(
        self, host: str, port: int, username: str | None, password: str | None
    ) -> bool:
        """Try a real MQTT connect. Returns True on success."""

        def _connect() -> None:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"ha-lumi-probe-{uuid4().hex[:8]}",
            )
            if username:
                client.username_pw_set(username, password or None)
            try:
                client.connect(host, port, keepalive=10)
            finally:
                client.disconnect()

        try:
            await asyncio.wait_for(
                self.hass.async_add_executor_job(_connect), timeout=10
            )
            return True
        except (OSError, asyncio.TimeoutError, mqtt.WebsocketConnectionError) as err:
            _LOGGER.debug("Lumi probe failed: %s", err)
            return False
        except Exception:  # noqa: BLE001 - paho raises a zoo of exceptions
            _LOGGER.exception("Unexpected error probing Lumi broker")
            return False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input["host"]
            port = user_input["port"]
            username = user_input.get("username") or None
            password = user_input.get("password") or None

            if await self._async_test_connection(host, port, username, password):
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured(
                    updates={"host": host, "port": port}
                )
                return self.async_create_entry(
                    title=f"Lumi Gateway ({host})",
                    data={
                        "host": host,
                        "port": port,
                        "username": username,
                        "password": password,
                    },
                )

            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("host"): str,
                    vol.Required("port", default=1883): int,
                    vol.Optional("username"): str,
                    vol.Optional("password"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        host = discovery_info.host
        port = discovery_info.port or 1883
        properties = discovery_info.properties

        unique_id = properties.get("mac", discovery_info.hostname)
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(
            updates={"host": host, "port": port},
            reload_on_update=False,
        )

        self.discovered_host = host
        self.discovered_port = port
        self.discovered_name = discovery_info.name

        self.context["title_placeholders"] = {"name": self.discovered_name}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        assert self.discovered_host and self.discovered_port

        if user_input is not None:
            username = user_input.get("username") or None
            password = user_input.get("password") or None

            if await self._async_test_connection(
                self.discovered_host, self.discovered_port, username, password
            ):
                return self.async_create_entry(
                    title=self.discovered_name
                    or f"Lumi Gateway ({self.discovered_host})",
                    data={
                        "host": self.discovered_host,
                        "port": self.discovered_port,
                        "username": username,
                        "password": password,
                    },
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional("username"): str,
                    vol.Optional("password"): str,
                }
            ),
            description_placeholders={
                "name": self.discovered_name or "Lumi Gateway",
                "host": self.discovered_host,
            },
            errors=errors,
        )