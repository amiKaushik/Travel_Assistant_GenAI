from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class EstimatedCost(BaseModel):
    min: float = Field(..., ge=0)
    max: float = Field(..., ge=0)
    currency: str = "INR"

    @model_validator(mode="after")
    def _check_min_max(self):
        if self.min > self.max:
            raise ValueError("estimated_cost.min must be <= estimated_cost.max")
        return self


class TransportOption(BaseModel):
    mode: str
    estimated_travel_time: str
    distance_km: float = Field(..., gt=0)
    available_vehicles: list[str]
    estimated_cost: EstimatedCost
    route_summary: str

    @field_validator("available_vehicles")
    @classmethod
    def _check_vehicles(cls, value):
        if not value:
            raise ValueError("available_vehicles must not be empty")
        return value


class Route(BaseModel):
    leg_name: str
    transport_options: list[TransportOption]

    @field_validator("transport_options")
    @classmethod
    def _check_options(cls, value):
        if not value:
            raise ValueError("transport_options must not be empty")
        return value


class TravelPlan(BaseModel):
    source: str
    destinations: list[str]
    budget: float = Field(..., gt=0)
    routes: list[Route]
    best_route_recommendation: str
    detailed_travel_plan: dict[str, str]

    @field_validator("routes")
    @classmethod
    def _check_routes(cls, value):
        if not value:
            raise ValueError("routes must not be empty")
        return value

    @field_validator("detailed_travel_plan")
    @classmethod
    def _check_plan(cls, value):
        if not value:
            raise ValueError("detailed_travel_plan must not be empty")
        return value

    model_config = {"extra": "ignore"}


def validate_travel_plan(data: dict) -> dict:
    """
    Validate and normalize travel plan data.
    Raises ValidationError on invalid shape.
    """
    # Backward compatibility: convert legacy route schema to new schema
    routes = data.get("routes")
    if isinstance(routes, list):
        normalized_routes = []
        for idx, route in enumerate(routes):
            if "transport_options" in route and "leg_name" in route:
                if isinstance(route.get("transport_options"), list) and route["transport_options"]:
                    if all(isinstance(opt, str) for opt in route["transport_options"]):
                        transport_options = []
                        for opt in route["transport_options"]:
                            transport_options.append({
                                "mode": opt,
                                "estimated_travel_time": "N/A",
                                "distance_km": 1,
                                "available_vehicles": [opt],
                                "estimated_cost": {"min": 0, "max": 0, "currency": "INR"},
                                "route_summary": ""
                            })
                        route["transport_options"] = transport_options
                normalized_routes.append(route)
                continue

            # Legacy single-route format
            mode = route.get("mode") or route.get("route_name") or "Route"
            transport_option = {
                "mode": mode,
                "estimated_travel_time": route.get("estimated_travel_time", "N/A"),
                "distance_km": route.get("distance_km", 1),
                "available_vehicles": route.get("available_vehicles", ["Unknown"]),
                "estimated_cost": route.get("estimated_cost", {"min": 0, "max": 0, "currency": "INR"}),
                "route_summary": route.get("route_summary", "")
            }
            if isinstance(transport_option["estimated_cost"], (int, float)):
                cost_val = float(transport_option["estimated_cost"])
                transport_option["estimated_cost"] = {"min": cost_val, "max": cost_val, "currency": "INR"}
            leg_name = route.get("leg_name")
            if not leg_name:
                from_city = route.get("from")
                to_city = route.get("to")
                if from_city and to_city:
                    leg_name = f"{from_city} -> {to_city}"
                else:
                    leg_name = f"Leg {idx + 1}"
            normalized_routes.append({
                "leg_name": leg_name,
                "transport_options": [transport_option]
            })
        data["routes"] = normalized_routes

    if "destinations" not in data:
        destination = data.get("destination")
        if destination:
            data["destinations"] = [destination]

    plan = TravelPlan.model_validate(data)
    return plan.model_dump()
