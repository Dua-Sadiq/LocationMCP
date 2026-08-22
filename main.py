"""
Location Toolkit - an MCP server for Microsoft Copilot Studio.

This file is the heart of the project. It defines the tools that a
Copilot Studio agent can call. Right now it has ONE working tool
(travel_time) so you can prove everything works end-to-end before
adding the rest.

You do NOT need to understand every line. The parts you care about
are marked with  # >>>  comments.
"""

import os
import httpx
from fastmcp import FastMCP

# ---------------------------------------------------------------------------
# 1. Create the server
# ---------------------------------------------------------------------------
mcp = FastMCP("Location Toolkit")

# ---------------------------------------------------------------------------
# 2. Read the Google Maps API key from the "slot" (environment variable).
#    >>> The key is NEVER written here. It lives in a setting called
#        GOOGLE_MAPS_KEY that you fill in during setup. This line just
#        reads whatever is in that slot.
# ---------------------------------------------------------------------------
GOOGLE_MAPS_KEY = os.environ.get("GOOGLE_MAPS_KEY", "")


# ---------------------------------------------------------------------------
# 3. Define your first tool.
#    The @mcp.tool line tells FastMCP "this is a tool the agent can call."
#    The words in quotes below (the docstring) tell the agent WHAT the
#    tool does and WHEN to use it - so write them clearly.
# ---------------------------------------------------------------------------
@mcp.tool
def travel_time(origin: str, destination: str) -> dict:
    """Get the live driving time and distance between two places.

    Use this when someone asks how long it takes to drive from one
    location to another, or how far apart two places are.

    origin: the starting place (an address or place name).
    destination: the ending place (an address or place name).
    """
    # Safety check: make sure the key was actually set up.
    if not GOOGLE_MAPS_KEY:
        return {"error": "No Google Maps API key is configured on this server."}

    # Ask Google for the driving distance and time.
    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "mode": "driving",
        "key": GOOGLE_MAPS_KEY,
    }

    try:
        response = httpx.get(url, params=params, timeout=15)
        data = response.json()
    except Exception as e:
        return {"error": f"Could not reach Google Maps: {e}"}

    # Dig the useful numbers out of Google's answer.
    try:
        element = data["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            return {"error": f"No route found ({element.get('status')})."}
        return {
            "origin": origin,
            "destination": destination,
            "distance": element["distance"]["text"],   # e.g. "12.4 km"
            "drive_time": element["duration"]["text"],  # e.g. "18 mins"
        }
    except (KeyError, IndexError):
        return {"error": "Google's response was not in the expected shape."}


@mcp.tool
def find_nearest(target: str, candidates: list[str]) -> dict:
    """Find the closest candidate to a target by driving time.

    Use this when finding the nearest driver, branch, or technician to a
    pickup location or job site. The target is the place being served, and
    candidates are the places that could serve it.

    target: the pickup location or job site (an address or place name).
    candidates: a list of possible locations (addresses or place names).
    """
    if not GOOGLE_MAPS_KEY:
        return {"error": "No Google Maps API key is configured on this server."}

    if not candidates:
        return {"error": "At least one candidate location is required."}

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": target,
        "destinations": "|".join(candidates),
        "mode": "driving",
        "key": GOOGLE_MAPS_KEY,
    }

    try:
        response = httpx.get(url, params=params, timeout=15)
        data = response.json()
    except Exception as e:
        return {"error": f"Could not reach Google Maps: {e}"}

    try:
        elements = data["rows"][0]["elements"]
        ranked = []
        for candidate, element in zip(candidates, elements):
            if element.get("status") != "OK":
                continue
            ranked.append({
                "candidate": candidate,
                "distance": element["distance"]["text"],
                "drive_time": element["duration"]["text"],
                "drive_time_seconds": element["duration"]["value"],
            })

        if not ranked:
            return {"error": "None of the candidate locations are reachable."}

        ranked.sort(key=lambda result: result["drive_time_seconds"])
        for result in ranked:
            result.pop("drive_time_seconds")

        return {
            "target": target,
            "nearest": ranked[0],
            "ranked_candidates": ranked,
        }
    except (KeyError, IndexError, TypeError):
        return {"error": "Google's response was not in the expected shape."}


@mcp.tool
def verify_address(address: str) -> dict:
    """Verify an address and return Google's cleaned, standardized version.

    Use this to check whether an address is real and findable, which is
    useful for checking delivery addresses, cleaning customer data during
    onboarding, or confirming a job site before dispatch.

    address: the address to verify.
    """
    if not address or not address.strip():
        return {"error": "An address is required."}

    if not GOOGLE_MAPS_KEY:
        return {"error": "No Google Maps API key is configured on this server."}

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": GOOGLE_MAPS_KEY,
    }

    try:
        response = httpx.get(url, params=params, timeout=15)
        data = response.json()
    except Exception as e:
        return {"error": f"Could not reach Google Maps: {e}"}

    try:
        if data.get("status") == "ZERO_RESULTS" or not data["results"]:
            return {
                "valid": False,
                "message": "The address could not be found.",
            }

        result = data["results"][0]
        location = result["geometry"]["location"]
        return {
            "valid": True,
            "formatted_address": result["formatted_address"],
            "latitude": location["lat"],
            "longitude": location["lng"],
        }
    except (KeyError, IndexError, TypeError):
        return {"error": "Google's response was not in the expected shape."}


@mcp.tool
def route_with_traffic(origin: str, destination: str) -> dict:
    """Get the live, traffic-aware driving time between two places.

    This reflects current road conditions right now, unlike a normal
    driving estimate. Use it for realistic dispatch and delivery timing.

    origin: the starting place (an address or place name).
    destination: the ending place (an address or place name).
    """
    if not origin or not origin.strip() or not destination or not destination.strip():
        return {"error": "Both origin and destination are required."}

    if not GOOGLE_MAPS_KEY:
        return {"error": "No Google Maps API key is configured on this server."}

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "mode": "driving",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "key": GOOGLE_MAPS_KEY,
    }

    try:
        response = httpx.get(url, params=params, timeout=15)
        data = response.json()
    except Exception as e:
        return {"error": f"Could not reach Google Maps: {e}"}

    try:
        if data["status"] != "OK" or not data["routes"]:
            return {"error": f"No route found ({data['status']})."}

        leg = data["routes"][0]["legs"][0]
        traffic_duration = leg.get("duration_in_traffic")
        return {
            "origin": origin,
            "destination": destination,
            "distance": leg["distance"]["text"],
            "normal_duration": leg["duration"]["text"],
            "traffic_aware_duration": (
                traffic_duration["text"] if traffic_duration else None
            ),
        }
    except (KeyError, IndexError, TypeError):
        return {"error": "Google's response was not in the expected shape."}


# ---------------------------------------------------------------------------
# 4. Start the server so it can be reached over the internet.
#    >>> host "0.0.0.0" means "accept connections from outside" (required
#        for hosting). Do NOT use 127.0.0.1 here - that means "me only".
#    >>> The port is read from the slot the host provides. Do NOT hard-code
#        a number - the host assigns it.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="http", host="0.0.0.0", port=port)
