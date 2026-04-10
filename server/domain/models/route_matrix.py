from dataclasses import dataclass


@dataclass
class RouteMatrixResult:
    distances: list[list[float]]
    durations: list[list[float]]
