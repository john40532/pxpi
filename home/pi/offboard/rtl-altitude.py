#!/usr/bin/env python3

'''
Adjust RTL height based on the max elevation of the RTL path.
Install:
pip3 install googlemaps
pip3 install mavsdk
'''

import os
import asyncio
import googlemaps
from pandas import DataFrame
from mavsdk import System, telemetry
from googlemaps_apikey import apikey

home_elevation = 0
default_return_alt = 0
return_alt = 0
max_alt = 500

# additional altitude above the max elevation
above_alt = 50

# Google Maps APi client
gmaps = googlemaps.Client(key=apikey)

async def run():
    # Init the drone
    drone = System()
    await drone.connect(system_address="udp://:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print(f"Drone discovered with UUID: {state.uuid}")            
            break

    # Get RTL altitude
    default_return_alt = await drone.action.get_return_to_launch_altitude()
    print("Default RTL altitude", default_return_alt)

    # Get home position
    async for h in drone.telemetry.home():
        home_position = (h.latitude_deg, h.longitude_deg)
        print("Home position:", home_position)
        break

    # Get home elevation
    home_elevation =  gmaps.elevation(home_position)[0]["elevation"]
    print("Home elevation:", home_elevation)

    # Monitoring drone position and update the Return to Home altitude
    async for flight_mode in drone.telemetry.flight_mode():
        # http://mavsdk-python-docs.s3-website.eu-central-1.amazonaws.com/plugins/telemetry.html#mavsdk.telemetry.FlightMode
        if flight_mode == telemetry.FlightMode.POSCTL:
            async for p in drone.telemetry.position():
                drone_position = (p.latitude_deg, p.longitude_deg)
                print("Drone position:", drone_position)

                # Get a list of elevations from the RTL path
                path = [home_position, drone_position]
                result = gmaps.elevation_along_path(path, 100)
                df = DataFrame(result, columns=['elevation', 'location', 'resolution'])
                max_elevation = df["elevation"].max()
                print("Max elevation:", max_elevation)

                # Update the return to home alt
                return_alt = max_elevation - home_elevation + above_alt
                if return_alt < default_return_alt:
                    return_alt = default_return_alt

                if return_alt > max_alt:
                    return_alt = max_alt

                await drone.action.set_return_to_launch_altitude(return_alt)
                print("Update RTL alt:", return_alt)

                await asyncio.sleep(5)
                break

    # Reset the default return alt when quit
    await drone.action.set_return_to_launch_altitude(default_return_alt)
    print("Reset Return to Home alt:", default_return_alt)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run())