import os
from functools import lru_cache
import requests


class ProviderError(RuntimeError):
    pass


def _format_duration(seconds: float) -> str:
    minutes = int(round(seconds / 60))
    hours = minutes // 60
    rem_minutes = minutes % 60
    if hours == 0:
        return f"{rem_minutes} min"
    if rem_minutes == 0:
        return f"{hours} hr"
    return f"{hours} hr {rem_minutes} min"


def _estimate_cost(distance_km: float, mode: str) -> dict:
    if mode == "transit":
        rate_min, rate_max = 2.0, 6.0
    else:
        rate_min, rate_max = 10.0, 16.0
    return {
        "min": int(round(distance_km * rate_min)),
        "max": int(round(distance_km * rate_max)),
        "currency": "INR"
    }


class GeoapifyProvider:
    def __init__(self, api_key: str | None = None, session: requests.Session | None = None):
        self.api_key = api_key or os.getenv("GEOAPIFY_API_KEY")
        if not self.api_key:
            raise ProviderError("GEOAPIFY_API_KEY is not set")
        self.session = session or requests.Session()

    @lru_cache(maxsize=128)
    def _geocode(self, place: str) -> dict:
        url = "https://api.geoapify.com/v1/geocode/search"
        params = {
            "text": place,
            "limit": 1,
            "format": "json",
            "apiKey": self.api_key
        }
        response = self.session.get(url, params=params, timeout=20)
        if response.status_code != 200:
            raise ProviderError(f"Geoapify geocoding failed ({response.status_code})")
        data = response.json()
        results = data.get("results", [])
        if not results:
            raise ProviderError(f"Location not found: {place}")
        return {
            "lat": results[0]["lat"],
            "lon": results[0]["lon"],
            "formatted": results[0].get("formatted", place)
        }

    @lru_cache(maxsize=256)
    def _route(self, source_key: str, dest_key: str, mode: str) -> dict:
        url = "https://api.geoapify.com/v1/routing"
        waypoints = f"{source_key}|{dest_key}"
        params = {
            "waypoints": waypoints,
            "mode": mode,
            "apiKey": self.api_key
        }
        response = self.session.get(url, params=params, timeout=30)
        if response.status_code != 200:
            raise ProviderError(f"Geoapify routing failed ({response.status_code})")
        data = response.json()
        features = data.get("features", [])
        if not features:
            raise ProviderError("No route returned")
        properties = features[0].get("properties", {})
        return {
            "distance_m": properties.get("distance"),
            "time_s": properties.get("time")
        }

    def get_transport_options(self, source: str, destination: str) -> list[dict]:
        src = self._geocode(source)
        dst = self._geocode(destination)

        modes = [
            ("drive", "Driving", ["Car", "Taxi"]),
            ("transit", "Transit", ["Bus", "Train"])
        ]

        options = []
        for mode, label, vehicles in modes:
            src_key = f"{src['lat']},{src['lon']}"
            dst_key = f"{dst['lat']},{dst['lon']}"
            try:
                route = self._route(src_key, dst_key, mode)
            except ProviderError:
                continue

            distance_m = route.get("distance_m") or 0
            time_s = route.get("time_s") or 0
            if distance_m <= 0 or time_s <= 0:
                continue

            distance_km = round(distance_m / 1000.0, 1)
            cost = _estimate_cost(distance_km, mode)
            summary = (
                f"Distance/time from Geoapify routing. Cost estimated at INR "
                f"{cost['min']}-{cost['max']} based on distance."
            )

            options.append({
                "mode": label,
                "estimated_travel_time": _format_duration(time_s),
                "distance_km": distance_km,
                "available_vehicles": vehicles,
                "estimated_cost": cost,
                "route_summary": summary
            })

        if not options:
            raise ProviderError("Insufficient route data from provider")
        return options
