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
    def _normalize_option(opt: dict) -> dict:
        mode = opt.get("mode") or opt.get("type") or "Route"
        if "estimated_travel_time" in opt:
            est_time = opt.get("estimated_travel_time")
        elif "duration_hours" in opt:
            est_time = f"{opt.get('duration_hours')} hr"
        else:
            est_time = "N/A"

        distance = opt.get("distance_km")
        if distance is None:
            distance = opt.get("estimated_distance_km") or opt.get("distance") or 1

        vehicles = opt.get("available_vehicles")
        if vehicles is None:
            vehicles = [mode.title()]

        est_cost = opt.get("estimated_cost", {"min": 0, "max": 0, "currency": "INR"})
        if isinstance(est_cost, (int, float)):
            cost_val = float(est_cost)
            est_cost = {"min": cost_val, "max": cost_val, "currency": "INR"}

        summary = opt.get("route_summary", "")
        return {
            "mode": mode,
            "estimated_travel_time": est_time,
            "distance_km": distance,
            "available_vehicles": vehicles,
            "estimated_cost": est_cost,
            "route_summary": summary
        }

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
                    elif all(isinstance(opt, dict) for opt in route["transport_options"]):
                        route["transport_options"] = [_normalize_option(opt) for opt in route["transport_options"]]
                normalized_routes.append(route)
                continue

            # Legacy single-route format
            mode = route.get("mode") or route.get("route_name") or "Route"
            transport_option = _normalize_option(route)
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
