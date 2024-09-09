# construction_site_safety_device_iot
A python script sends simulated customized data with patterns and complexity to Azure IoT central for implementation of construction site safety device for workers to prevent injury and deadly accidents
  - The script requires IoT central device credentials for connectivity(Line 10~12)
  - Message payload needs to be matched the IoT central device template to avoid data being classified as unmodeled
  - The script includes properties and telemetry
      - Property represents the intrinsic data such as Device ID and Worker Name(Function send_reported_properties)
      - Telemetry represents the data is being received(Heart rate, Body Temperature, Standhours, WeatherTemperature, RainDetection, GPSLocation, and FallDetection)
  -The script includes schedule notification that trrigers the device(Function send_notification & schedule_notification)


Data patterns with probability and complexity
  - Telemetry "Fall detection" and "Rain detection"(Both are Boolean) are given probability to prevent the data being fluctuated and random which mimics real-life situation(10% True and 90% False in script, Line 183~187)
  - Telemetry "GPSLocation" will be created within a preferred range to give stability to the GPS coordinate
      - Designated Central point and Radius(Range) is implemented in the script(Line 16~21)
      - GPS coordinates will be generated within radius(Function generate_random_gps_within_radius)
