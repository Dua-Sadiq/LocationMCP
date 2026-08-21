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


# ---------------------------------------------------------------------------
# 4. Start the server so it can be reached over the internet.
#    >>> host "0.0.0.0" means "accept connections from outside" (required
#        for hosting). Do NOT use 127.0.0.1 here - that means "me only".
#    >>> The port is read from the slot the host provides. Do NOT hard-code
#        a number - the host assigns it.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
