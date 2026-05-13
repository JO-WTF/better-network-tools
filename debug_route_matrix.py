import asyncio
import json
import logging
from pathlib import Path

from server.config.settings import get_settings
from server.infrastructure.cache.cache_manager import CacheManager
from server.infrastructure.http.client import HttpClient
from server.services.auth_service import AuthService
from server.services.provider_registry import ProviderRegistry
from server.services.route_matrix_service import RouteMatrixService
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_config(config_file: Path):
    with config_file.open("r", encoding="utf-8") as f:
        return json.load(f)




def _normalize_lonlat_to_latlng(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""

    delimiter = "," if "," in raw else "，" if "，" in raw else None
    if not delimiter:
        return raw

    parts = [item.strip() for item in raw.split(delimiter)]
    if len(parts) < 2:
        return raw

    try:
        lng = float(parts[0])
        lat = float(parts[1])
    except ValueError:
        return raw

    if -180 <= lng <= 180 and -90 <= lat <= 90:
        return f"{lat:.6f},{lng:.6f}"

    return raw


def _load_rows(input_path: Path):
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(input_path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(input_path)
    raise ValueError(f"不支持的输入文件格式: {suffix}")


async def _run(*, input_file: str, output_file: str, start_col: str, end_col: str, input_mode: str, config_file: str):
    settings = get_settings()
    provider_registry = ProviderRegistry()
    auth_service = AuthService()
    cache_manager = CacheManager(settings.cache_dir)
    route_matrix_service = RouteMatrixService(provider_registry, auth_service, cache_manager)
    http_client = HttpClient(settings.request_timeout_s)

    try:
        logger.info("debug_route_matrix: loading input file=%s config=%s", input_file, config_file)
        df = _load_rows(Path(input_file))
        routes = []
        if input_mode not in {"coordinate", "address"}:
            raise ValueError(f"不支持的 input_mode: {input_mode}")

        for idx, row in df.iterrows():
            origin_raw = _normalize_lonlat_to_latlng(row.get(start_col, ""))
            destination_raw = _normalize_lonlat_to_latlng(row.get(end_col, ""))
            if not origin_raw or not destination_raw:
                continue
            routes.append({"index": int(idx), "origin": origin_raw, "destination": destination_raw})

        raw_config = _load_config(Path(config_file))
        data = raw_config.get("data", raw_config)
        config = {
            "provider": "custom",
            "appId": data.get("customAppId", ""),
            "credential": data.get("customCredential", ""),
            "tokenUrl": data.get("customTokenUrl", ""),
            "routeUrl": data.get("customRouteUrl", ""),
            "geocodeUrl": data.get("customGeocodeUrl", ""),
        }

        result = await route_matrix_service.execute(http_client, config, routes)
        logger.info(
            "debug_route_matrix: route_matrix completed success=%s routes=%d results=%d",
            result.get("success", False),
            len(routes),
            len(result.get("results", [])),
        )
        result_lookup = {int(item.get("index")): item for item in result.get("results", [])}

        df["导航距离(km)"] = ""
        df["导航时间(min)"] = ""
        df["错误类型"] = ""
        df["错误详情"] = ""

        for idx in df.index:
            item = result_lookup.get(int(idx))
            if item and item.get("success"):
                df.at[idx, "导航距离(km)"] = item.get("distanceKm", "")
                df.at[idx, "导航时间(min)"] = item.get("durationMin", "")
                df.at[idx, "错误类型"] = ""
                df.at[idx, "错误详情"] = ""
            else:
                df.at[idx, "错误类型"] = item.get("errorType", "") if item else "no_result"
                df.at[idx, "错误详情"] = item.get("response", "") if item else "无结果"

        output_path = Path(output_file) if output_file else Path(input_file).with_name(f"calculated_{Path(input_file).name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        out_suffix = output_path.suffix.lower()
        if out_suffix == ".csv":
            df.to_csv(output_path, index=False, encoding="utf-8-sig")
        elif out_suffix in {".xlsx", ".xls"}:
            df.to_excel(output_path, index=False)
        else:
            raise ValueError(f"不支持的输出文件格式: {out_suffix}")

        print(json.dumps({
            "success": result.get("success", False),
            "input_rows": len(df),
            "calc_routes": len(routes),
            "result_rows": len(result.get("results", [])),
            "output": str(output_path),
        }, ensure_ascii=False))
    finally:
        await http_client.close()


if __name__ == "__main__":
    # ===== 本地调试参数（按需修改） =====
    INPUT_FILE = "./routes.csv"
    OUTPUT_FILE = ""  # 为空时自动输出为 calculated_<输入文件名>
    START_COL = "仓库经纬度"
    END_COL = "站点经纬度"
    INPUT_MODE = "coordinate"  # coordinate | address
    CONFIG_FILE = "config.json"

    asyncio.run(
        _run(
            input_file=INPUT_FILE,
            output_file=OUTPUT_FILE,
            start_col=START_COL,
            end_col=END_COL,
            input_mode=INPUT_MODE,
            config_file=CONFIG_FILE,
        )
    )
