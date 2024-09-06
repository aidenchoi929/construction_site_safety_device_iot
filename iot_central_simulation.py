import time
import random
import json
import threading
from datetime import datetime, timedelta
from azure.iot.device import IoTHubDeviceClient, Message, ProvisioningDeviceClient
import math

# Device credentials
ID_SCOPE = "0ne00D0DE57"
DEVICE_ID = "1slr81n1tnn"
PRIMARY_KEY = "fN1ZgJYWciyfHdmheE2hhXDWBKZgDkDWQetC0Vm7ynQ=="

# Fixed central point (latitude and longitude) for Singapore
# Prevents the GPS coordinates being fluctuated
CENTER_LAT = 1.3521  # Singapore Latitude
CENTER_LON = 103.8198  # Singapore Longitude

# 1 km radius(The GPS stays within 1km range)
RADIUS = 1000  # meter(=1km)
EARTH_RADIUS = 6371000  # Radius of the earth in meters

# Create provisioning client
def create_provisioning_client(id_scope, device_id, primary_key):
    provisioning_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host="global.azure-devices-provisioning.net",
        registration_id=device_id,
        id_scope=id_scope,
        symmetric_key=primary_key
    )
    return provisioning_client

# Provision the device and get the connection string
def provision_device():
    provisioning_client = create_provisioning_client(ID_SCOPE, DEVICE_ID, PRIMARY_KEY)
    registration_result = provisioning_client.register()

    if registration_result.status == "assigned":
        print("Device successfully provisioned!")
        return registration_result.registration_state.assigned_hub, registration_result.registration_state.device_id
    else:
        raise RuntimeError("Failed to provision device. Status: {}".format(registration_result.status))

# Send reported properties
def send_reported_properties(device_client):
    properties = {
        "DeviceID": 929,  # Reported Device ID
        "WorkerName": "Aiden Choi"  # Reported Worker Name
    }
    print(f"Sending reported properties: {properties}")
    device_client.patch_twin_reported_properties(properties)
    print("Reported properties sent successfully!")

# Handle desired properties
def desired_property_callback(desired_properties):
    if "DeviceID" in desired_properties:
        new_device_id = desired_properties["DeviceID"]
        print(f"Received new desired DeviceID: {new_device_id}")

    if "WorkerName" in desired_properties:
        new_worker_name = desired_properties["WorkerName"]
        print(f"Received new desired WorkerName: {new_worker_name}")

# Function to generate random GPS coordinates within preferred range
def generate_random_gps_within_radius(center_lat, center_lon, radius):
    # Convert radius from meters to degrees
    radius_in_degrees = radius / EARTH_RADIUS

    # Generate random angle and distance
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius_in_degrees)

    # Calculate new latitude and longitude
    delta_lat = distance * math.cos(angle)
    delta_lon = distance * math.sin(angle) / math.cos(math.radians(center_lat))

    new_lat = center_lat + math.degrees(delta_lat)
    new_lon = center_lon + math.degrees(delta_lon)

    return round(new_lat, 5), round(new_lon, 5)

# Function to send a notification message to IoT Central
def send_notification(device_client, notification_name, message):
    try:
        payload = {notification_name: message}
        message_obj = Message(json.dumps(payload))
        message_obj.content_type = "application/json"
        message_obj.content_encoding = "utf-8"
        device_client.send_message(message_obj)
        print(f"Sent {notification_name}: {message}")
    except Exception as e:
        print(f"Error sending {notification_name}: {e}")

# Scheduled notifications with one-time triggers per day
def schedule_notifications(device_client):
    sent_notifications = {
        "ShiftStartNotification": False,
        "ShiftEndNotification": False,
        "LunchNotification": False,
        "BreakNotificationAM": False,
        "BreakNotificationPM": False,
        "WaterNotification": False
    }

    while True:
        current_time = datetime.now()

        # Reset daily notifications at midnight
        if current_time.hour == 0 and current_time.minute == 0:
            sent_notifications = {key: False for key in sent_notifications}

        # Shift start notification at 8 AM
        if current_time.hour == 8 and current_time.minute == 0 and not sent_notifications["ShiftStartNotification"]:
            send_notification(device_client, "ShiftStartNotification", "Shift start notification")
            sent_notifications["ShiftStartNotification"] = True

        # Shift end notification at 6 PM
        if current_time.hour == 18 and current_time.minute == 0 and not sent_notifications["ShiftEndNotification"]:
            send_notification(device_client, "ShiftEndNotification", "Shift end notification")
            sent_notifications["ShiftEndNotification"] = True

        # Lunch time notification at 12 PM
        if current_time.hour == 12 and current_time.minute == 00 and not sent_notifications["LunchNotification"]:
            send_notification(device_client, "LunchNotification", "Lunch time notification")
            sent_notifications["LunchNotification"] = True

        # Break time notification at 10 AM and 4 PM
        if current_time.hour == 10 and current_time.minute == 0 and not sent_notifications["BreakNotificationAM"]:
            send_notification(device_client, "BreakNotification", "Break time notification")
            sent_notifications["BreakNotificationAM"] = True

        if current_time.hour == 16 and current_time.minute == 0 and not sent_notifications["BreakNotificationPM"]:
            send_notification(device_client, "BreakNotification", "Break time notification")
            sent_notifications["BreakNotificationPM"] = True

        # Water time notification every 30 minutes between 8 AM and 6 PM
        if current_time.hour >= 8 and current_time.hour < 18 and current_time.minute % 30 == 0:
            send_notification(device_client, "WaterNotification", "Water time notification")
            time.sleep(60)  # Avoid sending multiple water notifications within the same minute

        # Sleep for 1 minute before checking again
        time.sleep(60)

# Send simulated telemetry data
def send_data(device_client):
    try:
        print("Connecting to IoT Central...")
        device_client.connect()

        # Send reported properties once at the beginning
        send_reported_properties(device_client)

        device_client.on_twin_desired_properties_patch_received = desired_property_callback

        # Define shift start time (8:00 AM)
        shift_start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        standing_hours = 0

        while True:
            #Current time
            current_time = datetime.now()

            # Check if it's 6 PM and reset the standing hours
            if current_time.hour == 18 and current_time.minute == 0:
                standing_hours = 0
                shift_start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=1)
                print("Standing hours reset to 0 at 6 PM")

            # Calculate standing hours based on shift start time
            if current_time >= shift_start_time:
                standing_hours = (current_time - shift_start_time).total_seconds() // 3600
            else:
                standing_hours = 0

            # Simulate other sensor data
            heart_rate = random.randint(40, 150)  # BPM
            body_temp = round(random.uniform(35.0, 42.0), 1)  # Rounded to 1 decimal places
            weather_temp = round(random.uniform(20.0, 42.0), 1)  # Rounded to 1 decimal places

            # Simulate rain detection with 10% probability of True and 90% probability of False
            # Prevent the data being fluctuated and too random
            rain_detected = random.choices([True, False], weights=[0.1, 0.9])[0]

            # Simulate fall detection with 10% probability of True and 90% probability of False
            # Prevent the data being fluctuated and too random
            fall_detected = random.choices([True, False], weights=[0.1, 0.9])[0]

            # Generate random GPS coordinates within preferred designated location
            # Prevent the gps location fluctuated and too random
            gps_latitude, gps_longitude = generate_random_gps_within_radius(CENTER_LAT, CENTER_LON, RADIUS)
            gps_altitude = round(random.uniform(0, 1000), 5)

            # Message payload matching the IoT Central template
            message = {
                "HeartRate": heart_rate,
                "BodyTemperature": body_temp,
                "StandHours": int(standing_hours),
                "WeatherTemperature": weather_temp,
                "RainDetection": rain_detected,
                "GPSLocation": {
                    "lat": gps_latitude,
                    "lon": gps_longitude,
                    "alt": gps_altitude 
                },
                "FallDetection": fall_detected  # As boolean
            }

            # Convert the message to JSON and send it
            message_obj = Message(json.dumps(message))
            message_obj.content_type = "application/json"
            message_obj.content_encoding = "utf-8"
            message_obj.custom_properties["priority"] = "high"

            # Print the timestamp and send the message
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"Sending telemetry message: {message}")
            device_client.send_message(message_obj)
            print(f"Message successfully sent at {timestamp}!")

            # Interval between messages
            time.sleep(3)

    except KeyboardInterrupt:
        print("Execution interrupted by the user. Stopping...")

    finally:
        print("Shutting down the device client...")
        device_client.shutdown()

if __name__ == "__main__":
    try:
        hub_hostname, provisioned_device_id = provision_device()

        device_client = IoTHubDeviceClient.create_from_symmetric_key(
            symmetric_key=PRIMARY_KEY,
            hostname=hub_hostname,
            device_id=provisioned_device_id
        )

        notification_thread = threading.Thread(target=schedule_notifications, args=(device_client,))
        notification_thread.start()

        send_data(device_client)

        notification_thread.join()

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        print("Program has been terminated.")
