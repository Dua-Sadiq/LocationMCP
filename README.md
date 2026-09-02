# Location Toolkit (LocationMCP)

An MCP server that gives a Microsoft Copilot Studio agent real-world location awareness driving times, nearest-location lookups, and address verification powered by the Google Maps API.

Built with [FastMCP](https://github.com/jlowin/fastmcp), containerized with Docker, and designed to be dropped straight into a Copilot Studio agent as a custom tool connector.

## Tools

| Tool | What it does |
|---|---|
| `travel_time` | Live driving time and distance between two places. |
| `find_nearest` | Ranks a list of candidate locations by driving time from a target, returns the closest. |
| `verify_address` | Checks whether an address is real, and returns Google's standardized version plus lat/lng. |
| `nearest_available` | Dispatch-style lookup: given a target and a list of resources (with status), finds the fastest *available* one using live traffic data. |

Typical use cases: dispatching the nearest technician or driver, validating a customer or job-site address during intake, or answering "how far / how long" questions inside an agent conversation.

## Requirements

- Python 3.12+
- A [Google Maps API key](https://developers.google.com/maps/documentation/distance-matrix/get-api-key) with the **Distance Matrix API** and **Geocoding API** enabled

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/Dua-Sadiq/LocationMCP.git
   cd LocationMCP
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your Google Maps API key as an environment variable:
   ```bash
   export GOOGLE_MAPS_KEY=your_key_here
   ```
4. Run the server:
   ```bash
   python main.py
   ```
   The server starts on `0.0.0.0`, using the port from the `PORT` environment variable (defaults to `8000`).

## Running with Docker

```bash
docker build -t location-toolkit .
docker run -p 8000:8000 -e GOOGLE_MAPS_KEY=your_key_here location-toolkit
```

## Connecting to Copilot Studio

Once deployed and reachable over HTTP, register this server as a custom tool/connector in your Copilot Studio agent, pointing it at the server's URL. Each tool's docstring is written as the description Copilot Studio (and the underlying model) uses to decide when to call it — so if you add tools, keep the docstrings clear and specific about when to use them.

## Project structure

```
.
├── main.py             # Server definition and all four tools
├── requirements.txt    # Python dependencies
├── Dockerfile           # Container build for deployment
└── .gitignore
```

## Notes

- No API key is ever hard-coded — `GOOGLE_MAPS_KEY` is read from the environment at runtime.
- Every tool fails gracefully with a descriptive `{"error": ...}` response rather than raising, so a bad address or an unreachable API doesn't take down the agent conversation.
- This is an early-stage project — `travel_time` was the first tool built to prove the end-to-end setup works, with the dispatch-oriented tools added on top.

