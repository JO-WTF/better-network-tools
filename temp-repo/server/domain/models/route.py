from dataclasses import dataclass


@dataclass
class RouteResult:
    distance_km: float
    duration_min: int
