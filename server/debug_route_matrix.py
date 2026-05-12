import argparse
import asyncio
import csv
import json
from pathlib import Path

from server.config.settings import get_settings
from server.infrastructure.cache.cache_manager import CacheManager
from server.infrastructure.http.client import HttpClient
from server.services.auth_service import AuthService
from server.services.provider_registry import ProviderRegistry
from server.services.route_matrix_service import RouteMatrixService


def _parse_args():
    parser = argparse.ArgumentParser(description="本地调试 custom route matrix（CSV 文件）")
    parser.add_argument("--input", required=True, help="输入 CSV 文件路径")
    parser.add_argument("--output", default="", help="输出 CSV 文件路径，可为空")
    parser.add_argument("--start-col", required=True, help="起点列名")
    parser.add_argument("--end-col", required=True, help="终点列名")
    parser.add_argument("--config-file", default="config.json", help="前端配置文件（默认 config.json）")
    parser.add_argument("--input-mode", choices=["coordinate", "address"], default="coordinate")
    return parser.parse_args()




def _load_config(config_file: Path):
    with config_file.open("r", encoding="utf-8") as f:
        return json.load(f)
def _load_rows(input_path: Path):
    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


async def _run(args):
    settings = get_settings()
    provider_registry = ProviderRegistry()
    auth_service = AuthService()
    cache_manager = CacheManager(settings.cache_dir)
    route_matrix_service = RouteMatrixService(provider_registry, auth_service, cache_manager)
    http_client = HttpClient(settings.request_timeout_s)

    try:
        rows = _load_rows(Path(args.input))
        routes = []
        for idx, row in enumerate(rows):
            origin_raw = str(row.get(args.start_col, "")).strip()
            destination_raw = str(row.get(args.end_col, "")).strip()
            if not origin_raw or not destination_raw:
                continue
            if args.input_mode == "coordinate":
                origin = origin_raw
                destination = destination_raw
            else:
                origin = origin_raw
                destination = destination_raw
            routes.append({"index": idx, "origin": origin, "destination": destination})

        raw_config = _load_config(Path(args.config_file))
        config = {
            "provider": "custom",
            "appId": raw_config.get("appId", ""),
            "credential": raw_config.get("credential", ""),
            "tokenUrl": raw_config.get("tokenUrl", ""),
            "routeUrl": raw_config.get("routeUrl", ""),
            "geocodeUrl": raw_config.get("geocodeUrl", ""),
        }

        result = await route_matrix_service.execute(http_client, config, routes)
        result_lookup = {int(item.get("index")): item for item in result.get("results", [])}

        for idx, row in enumerate(rows):
            item = result_lookup.get(idx)
            if item and item.get("success"):
                row["导航距离(km)"] = item.get("distanceKm", "")
                row["导航时间(min)"] = item.get("durationMin", "")
            else:
                row["导航距离(km)"] = ""
                row["导航时间(min)"] = ""
                row["错误类型"] = item.get("errorType", "") if item else "no_result"
                row["错误详情"] = item.get("response", "") if item else "无结果"

        output_path = Path(args.output) if args.output else Path(args.input).with_name(f"calculated_{Path(args.input).name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(rows[0].keys()) if rows else [args.start_col, args.end_col, "导航距离(km)", "导航时间(min)"]
        with output_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(json.dumps({
            "success": result.get("success", False),
            "input_rows": len(rows),
            "calc_routes": len(routes),
            "result_rows": len(result.get("results", [])),
            "output": str(output_path),
        }, ensure_ascii=False))
    finally:
        await http_client.close()


if __name__ == "__main__":
    asyncio.run(_run(_parse_args()))
