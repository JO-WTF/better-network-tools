from enum import Enum


class ProviderType(str, Enum):
    CUSTOM = "custom"
    MAPBOX = "mapbox"
    HERE = "here"
    UNKNOWN = "unknown"


class CapabilityType(str, Enum):
    GEOCODE = "geocode"
    REVERSE_GEOCODE = "reverse_geocode"
    ROUTE = "route"
    ROUTE_MATRIX = "route_matrix"
    ISOCHRONE = "isochrone"
    AUTOCOMPLETE = "autocomplete"
    MAP_MATCH = "map_match"


class InputMode(str, Enum):
    ADDRESS = "address"
    COORDINATE = "coordinate"
