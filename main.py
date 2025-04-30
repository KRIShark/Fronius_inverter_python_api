from solar_panel_controller import SolarPanelController, SolarPanelAPIError

api = SolarPanelController("192.168.0.13")

print("Real-time data:")
print(api.get_realtime_data())

print("\nPower flow data:")
print(api.get_power_flow())

print("\nArchive data:")
print(api.get_archive_data("2023-10-01", "2023-10-02", channels=["EnergyReal_WAC_Sum_Produced", "Temperature_Channel_1"], series_type="Day"))
