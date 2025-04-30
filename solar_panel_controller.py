import requests
from typing import List, Dict, Any

class SolarPanelAPIError(Exception):
    """Raised for any Solar API error (connection issues, bad HTTP status, etc.)."""
    pass

class SolarPanelController:
    """
    Controller for interacting with a Fronius inverter's Solar API.

    Initialize with the inverter's local IP address; use the methods below
    to fetch real-time and historical data in JSON form.
    """

    def __init__(self, ip: str, timeout: int = 5):
        """
        Initialize the controller.

        Parameters:
        -----------
        ip : str
            The local IP address of your Fronius inverter (e.g., "192.168.0.13").
        timeout : int, optional
            Default timeout (in seconds) for HTTP requests. Archive calls may override this.
        """
        self.base = f"http://{ip}/solar_api/v1/"
        self.timeout = timeout

    def _get(self, endpoint: str, timeout: int = None) -> Dict[str, Any]:
        """
        Internal helper to perform a GET request and return parsed JSON.

        Parameters:
        -----------
        endpoint : str
            The API path and query string (e.g., "GetInverterRealtimeData.cgi?Scope=System").
        timeout : int, optional
            Override for this single request’s timeout. Defaults to self.timeout.

        Returns:
        --------
        Dict[str, Any]
            Parsed JSON body of the response.

        Raises:
        -------
        SolarPanelAPIError
            - On timeout (“Request timed out”)
            - On connection failure (“Cannot connect to inverter”)
            - On HTTP errors, with messages like “Endpoint not found (404)”, “Unauthorized (401)”, etc.
            - On any other unexpected exception.
        """
        url = self.base + endpoint
        try:
            resp = requests.get(url, timeout=timeout or self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout as e:
            raise SolarPanelAPIError("Request timed out") from e
        except requests.exceptions.ConnectionError as e:
            raise SolarPanelAPIError("Cannot connect to inverter") from e
        except requests.exceptions.HTTPError as e:
            code = resp.status_code
            if code == 404:
                msg = "Endpoint not found (404)"
            elif code in (401, 403):
                msg = "Unauthorized or forbidden"
            elif code >= 500:
                msg = "Inverter internal error"
            else:
                msg = f"HTTP {code}"
            raise SolarPanelAPIError(msg) from e
        except Exception as e:
            raise SolarPanelAPIError(f"Unexpected error: {e}") from e

    def get_inverter_status(self) -> Dict[str, Any]:
        """
        Fetch live inverter metrics.

        This returns per-inverter data such as current power (W), voltages (V), currents (A), etc.

        Returns:
        --------
        Dict[str, Any]
            JSON containing keys like 'Body' → 'Data' → 'PAC', 'DAY_ENERGY', etc.

        Example:
        --------
        >>> api = SolarPanelController("192.168.0.13")
        >>> status = api.get_inverter_status()
        >>> print(status['Body']['Data']['PAC']['Values']['1'])
        6109
        """
        return self._get("GetInverterRealtimeData.cgi?Scope=System")

    def get_power_flow(self) -> Dict[str, Any]:
        """
        Fetch site-wide power flow data.

        Shows how energy is flowing between PV arrays, loads, grid, and battery (if present).

        Returns:
        --------
        Dict[str, Any]
            JSON with 'Inverters', 'Site', and 'Version' keys.

        Example:
        --------
        >>> power = api.get_power_flow()
        >>> print(power['Body']['Data']['Site']['P_PV'])
        6109
        """
        return self._get("GetPowerFlowRealtimeData.fcgi")

    def get_meter_data(self) -> Dict[str, Any]:
        """
        Fetch real-time data from a connected Fronius Smart Meter.

        Only valid if a meter is installed and wired into the inverter.

        Returns:
        --------
        Dict[str, Any]
            JSON with meter readings: 'E_Day', 'P_Grid', etc.

        Raises:
        -------
        SolarPanelAPIError
            If no meter is present or endpoint returns 404.
        """
        return self._get("GetMeterRealtimeData.cgi?Scope=System")

    def get_storage_data(self) -> Dict[str, Any]:
        """
        Fetch battery/storage system status (for hybrid inverters).

        Only available on supported Fronius models with attached battery.

        Returns:
        --------
        Dict[str, Any]
            JSON including battery state of charge, current in/out, etc.
        """
        return self._get("GetStorageRealtimeData.cgi?Scope=System")

    def get_sensors_data(self) -> Dict[str, Any]:
        """
        Fetch auxiliary sensor readings.

        E.g., solar irradiation, ambient temperature, module temperature—
        requires a SensorCard accessory.

        Returns:
        --------
        Dict[str, Any]
            JSON with sensor channels and their current values.
        """
        return self._get("GetSensorsRealtimeData.cgi?Scope=System")

    def get_switch_settings(self) -> Dict[str, Any]:
        """
        Retrieve the current state of digital outputs (Relays/Switches).

        Useful if you have configured external output relays for alarms or controls.

        Returns:
        --------
        Dict[str, Any]
            JSON listing switches and their on/off status.
        """
        return self._get("GetSwitchesSettings.cgi?Scope=System")

    def get_active_inverters(self) -> Dict[str, Any]:
        """
        List all inverter device IDs on the network.

        Returns:
        --------
        Dict[str, Any]
            JSON with an array of active inverter IDs.
        """
        return self._get("GetActiveInverters.cgi")

    def get_inverter_info(self) -> Dict[str, Any]:
        """
        Retrieve inverter identification and firmware details.

        Returns:
        --------
        Dict[str, Any]
            JSON with 'SerialNumber', 'ProductName', 'FirmwareVersion', etc.
        """
        return self._get("GetInverterInfo.cgi")
    
    def get_realtime_data(self) -> Dict[str, Any]:
        """
        Fetch live inverter metrics (alias for get_inverter_status).

        This returns per-inverter data such as current power (W), voltages (V),
        currents (A), etc.

        Returns:
        --------
        Dict[str, Any]
            JSON containing keys like 'Body' → 'Data' → 'PAC', 'DAY_ENERGY', etc.

        Example:
        --------
        >>> api = SolarPanelController("192.168.0.13")
        >>> realtime = api.get_realtime_data()
        >>> print(realtime['Body']['Data']['PAC']['Values']['1'])
        6109
        """
        return self._get("GetInverterRealtimeData.cgi?Scope=System")

    def get_archive_data(
        self,
        start_date: str,
        end_date: str,
        channels: List[str],
        human_readable: bool = True,
        series_type: str = "Hour",
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch historical data for one or more channels.

        Parameters:
        -----------
        start_date : str
            Beginning of period, format "DD.MM.YYYY" (e.g., "01.04.2025").
        end_date : str
            End of period, same format (e.g., "30.04.2025").
        channels : List[str]
            One or more channel names, e.g. ["EnergyReal_WAC_Sum_Produced"].
        human_readable : bool, optional
            If true, dates/times in response are ISO‐formatted strings.
        series_type : str, optional
            Granularity: "QuarterHour", "Hour", or "Day".
        timeout : int, optional
            Per‐call timeout; archive queries often take longer.

        Returns:
        --------
        Dict[str, Any]
            JSON with time‐series values per channel.

        Raises:
        -------
        SolarPanelAPIError
            If no channels provided, or on timeout/HTTP errors.

        Example:
        --------
        >>> hist = api.get_archive_data(
        ...     start_date="01.04.2025",
        ...     end_date="07.04.2025",
        ...     channels=["EnergyReal_WAC_Sum_Produced", "Temperature_Channel_1"],
        ...     series_type="Day"
        ... )
        >>> # hist['Body']['Data']['EnergyReal_WAC_Sum_Produced']
        """
        if not channels:
            raise SolarPanelAPIError("You must specify at least one channel")
        params = [
            f"Scope=System",
            f"StartDate={start_date}",
            f"EndDate={end_date}",
            f"HumanReadable={'true' if human_readable else 'false'}",
            f"SeriesType={series_type}"
        ] + [f"Channel={ch}" for ch in channels]
        endpoint = "GetArchiveData.cgi?" + "&".join(params)
        return self._get(endpoint, timeout=timeout)
