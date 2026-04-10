import json

from server.transport.websocket.connection_context import ConnectionContext
from server.transport.websocket.request_parser import parse_ws_message
from server.transport.websocket.response_builder import complete, progress
from server.utils.coords import format_coord_pair, parse_coordinate, round_coord


class WebSocketHandler:
    def __init__(self, geocode_service, route_service, route_matrix_service, http_client_factory):
        self.geocode_service = geocode_service
        self.route_service = route_service
        self.route_matrix_service = route_matrix_service
        self.http_client_factory = http_client_factory

    async def handle_connection(self, websocket):
        async for message in websocket:
            try:
                request = parse_ws_message(message)
            except json.JSONDecodeError:
                await websocket.send(progress({
                    "success": False,
                    "errorType": "parse_error",
                    "request": "websocket",
                    "response": "无法解析请求内容",
                }))
                continue
            if not request:
                continue
            mode = request.get("mode", "geocode")
            route_input_mode = request.get("routeInputMode", "address")
            config = request.get("config", {})
            addresses = request.get("addresses", [])
            routes = request.get("routes", [])
            context = ConnectionContext()

            http_client = self.http_client_factory()
            try:
                if mode == "route" and len(routes) > 100 and (str(config.get("provider", "")).lower() == "custom" or bool(config.get("tokenUrl"))):
                    indexed_routes = []
                    invalid_items = []
                    for index, route in enumerate(routes, start=1):
                        origin_value = route.get("origin")
                        destination_value = route.get("destination")
                        if route_input_mode == "coordinate":
                            origin_coords = parse_coordinate(origin_value)
                            destination_coords = parse_coordinate(destination_value)
                            if not origin_coords or not destination_coords:
                                invalid_items.append({
                                    "index": index,
                                    "origin_coords": None,
                                    "destination_coords": None,
                                    "result": {
                                        "success": False,
                                        "errorType": "invalid",
                                        "request": "coordinate",
                                        "response": "坐标格式错误",
                                    },
                                })
                                continue
                            indexed_routes.append({
                                "index": index,
                                "origin": format_coord_pair(*origin_coords),
                                "destination": format_coord_pair(*destination_coords),
                                "origin_coords": origin_coords,
                                "destination_coords": destination_coords,
                            })
                        else:
                            origin_result = await self.geocode_service.execute(
                                http_client, config, origin_value, context.geocode_cache
                            )
                            destination_result = await self.geocode_service.execute(
                                http_client, config, destination_value, context.geocode_cache
                            )
                            if not origin_result.get("success") or not destination_result.get("success"):
                                failure = origin_result if not origin_result.get("success") else destination_result
                                invalid_items.append({
                                    "index": index,
                                    "origin_coords": None,
                                    "destination_coords": None,
                                    "result": {
                                        "success": False,
                                        "errorType": failure.get("errorType", "no_result"),
                                        "request": failure.get("request", "geocode"),
                                        "response": failure.get("response", "地址无法转换为经纬度"),
                                    },
                                })
                                continue
                            origin_coords = (round_coord(origin_result.get("lat")), round_coord(origin_result.get("lng")))
                            destination_coords = (round_coord(destination_result.get("lat")), round_coord(destination_result.get("lng")))
                            indexed_routes.append({
                                "index": index,
                                "origin": format_coord_pair(*origin_coords),
                                "destination": format_coord_pair(*destination_coords),
                                "origin_coords": origin_coords,
                                "destination_coords": destination_coords,
                            })

                    for item in invalid_items:
                        await websocket.send(progress({
                            "processed": item["index"],
                            "index": item["index"] - 1,
                            "success": False,
                            "errorType": item["result"].get("errorType"),
                            "request": item["result"].get("request"),
                            "response": item["result"].get("response"),
                            "originLat": item["origin_coords"][0] if item["origin_coords"] else None,
                            "originLng": item["origin_coords"][1] if item["origin_coords"] else None,
                            "destinationLat": item["destination_coords"][0] if item["destination_coords"] else None,
                            "destinationLng": item["destination_coords"][1] if item["destination_coords"] else None,
                        }))

                    matrix_result = await self.route_matrix_service.execute(
                        http_client,
                        config,
                        [{
                            "index": item["index"] - 1,
                            "origin": item["origin"],
                            "destination": item["destination"],
                        } for item in indexed_routes],
                    )

                    if not matrix_result.get("success"):
                        for item in indexed_routes:
                            await websocket.send(progress({
                                "processed": item["index"],
                                "index": item["index"] - 1,
                                "success": False,
                                "errorType": matrix_result.get("errorType", "network_error"),
                                "request": matrix_result.get("request", "route_matrix"),
                                "response": matrix_result.get("response", "请求失败"),
                                "originLat": item["origin_coords"][0] if item["origin_coords"] else None,
                                "originLng": item["origin_coords"][1] if item["origin_coords"] else None,
                                "destinationLat": item["destination_coords"][0] if item["destination_coords"] else None,
                                "destinationLng": item["destination_coords"][1] if item["destination_coords"] else None,
                            }))
                    else:
                        for item in matrix_result.get("results", []):
                            await websocket.send(progress({
                                "processed": int(item.get("index", 0)) + 1,
                                "index": item.get("index"),
                                "success": item.get("success"),
                                "distanceKm": item.get("distanceKm"),
                                "durationMin": item.get("durationMin"),
                                "errorType": item.get("errorType"),
                                "request": item.get("request"),
                                "response": item.get("response"),
                                "originLat": item.get("originLat"),
                                "originLng": item.get("originLng"),
                                "destinationLat": item.get("destinationLat"),
                                "destinationLng": item.get("destinationLng"),
                            }))
                elif mode == "route":
                    for index, route in enumerate(routes, start=1):
                        try:
                            origin_value = route.get("origin")
                            destination_value = route.get("destination")
                            origin_coords = None
                            destination_coords = None
                            if route_input_mode == "address":
                                origin_result = await self.geocode_service.execute(
                                    http_client, config, origin_value, context.geocode_cache
                                )
                                destination_result = await self.geocode_service.execute(
                                    http_client, config, destination_value, context.geocode_cache
                                )
                                if not origin_result.get("success") or not destination_result.get("success"):
                                    failure = origin_result if not origin_result.get("success") else destination_result
                                    result = {
                                        "success": False,
                                        "errorType": failure.get("errorType", "no_result"),
                                        "request": failure.get("request", "geocode"),
                                        "response": failure.get("response", "地址无法转换为经纬度"),
                                    }
                                else:
                                    origin_coords = (round_coord(origin_result.get("lat")), round_coord(origin_result.get("lng")))
                                    destination_coords = (round_coord(destination_result.get("lat")), round_coord(destination_result.get("lng")))
                                    result = await self.route_service.execute(
                                        http_client,
                                        config,
                                        format_coord_pair(*origin_coords),
                                        format_coord_pair(*destination_coords),
                                        context.route_cache,
                                    )
                            else:
                                origin_coords = parse_coordinate(origin_value)
                                destination_coords = parse_coordinate(destination_value)
                                if not origin_coords or not destination_coords:
                                    result = {
                                        "success": False,
                                        "errorType": "invalid",
                                        "request": "coordinate",
                                        "response": "坐标格式错误",
                                    }
                                else:
                                    result = await self.route_service.execute(
                                        http_client,
                                        config,
                                        format_coord_pair(*origin_coords),
                                        format_coord_pair(*destination_coords),
                                        context.route_cache,
                                    )
                        except Exception as exc:
                            result = {
                                "success": False,
                                "errorType": "internal_error",
                                "request": "route",
                                "response": f"处理异常: {exc}",
                            }
                            origin_coords = None
                            destination_coords = None
                        await websocket.send(progress({
                            "processed": index,
                            "success": result.get("success"),
                            "distanceKm": result.get("distanceKm"),
                            "durationMin": result.get("durationMin"),
                            "errorType": result.get("errorType"),
                            "request": result.get("request"),
                            "response": result.get("response"),
                            "originLat": origin_coords[0] if origin_coords else None,
                            "originLng": origin_coords[1] if origin_coords else None,
                            "destinationLat": destination_coords[0] if destination_coords else None,
                            "destinationLng": destination_coords[1] if destination_coords else None,
                            "index": index - 1,
                        }))
                else:
                    for index, address in enumerate(addresses, start=1):
                        try:
                            result = await self.geocode_service.execute(
                                http_client, config, address, context.geocode_cache
                            )
                        except Exception as exc:
                            result = {
                                "success": False,
                                "errorType": "internal_error",
                                "request": "geocode",
                                "response": f"处理异常: {exc}",
                            }
                        await websocket.send(progress({
                            "address": address,
                            "processed": index,
                            "success": result.get("success"),
                            "lat": result.get("lat"),
                            "lng": result.get("lng"),
                            "errorType": result.get("errorType"),
                            "request": result.get("request"),
                            "response": result.get("response"),
                        }))
            finally:
                await http_client.close()
            await websocket.send(complete())
