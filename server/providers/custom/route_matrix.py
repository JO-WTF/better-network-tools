import logging
from collections import defaultdict
from itertools import combinations

from server.providers.common.request_builder import auth_headers
from server.providers.common.result_builder import error_result
from server.utils.json_utils import safe_json_dumps

logger = logging.getLogger(__name__)


# =========================
# 基础坐标工具
# =========================

def _normalize_coord(value: str):
    raw = str(value or "").strip()
    if not raw:
        return None

    delimiter = "," if "," in raw else "，" if "，" in raw else None
    if not delimiter:
        return None

    parts = [item.strip() for item in raw.split(delimiter)]
    if len(parts) < 2:
        return None

    try:
        first = round(float(parts[0]), 6)
        second = round(float(parts[1]), 6)
    except ValueError:
        return None

    # 仅支持 lat,lng 输入
    if -90 <= first <= 90 and -180 <= second <= 180:
        return first, second

    return None


def _fmt_latlng(lat: float, lng: float) -> str:
    return f"{float(lat):.6f},{float(lng):.6f}"


def _chunk_list(items, size):
    """
    将列表按 size 切块。

    例如：
        [1,2,3,4,5], size=2

    得到：
        [1,2], [3,4], [5]

    这里主要用于兜底的 1 x n 请求。
    """
    items = list(items)
    for i in range(0, len(items), size):
        yield items[i:i + size]


# =========================
# 矩阵响应解析
# =========================

def _parse_matrix_response(data, origins, destinations):
    """
    解析矩阵接口返回结果。

    origins / destinations 是本次请求时传入的点列表，格式类似：

        [
            {"id": 1, "lat": 1.23, "lng": 4.56},
            ...
        ]

    返回：
        {
            (origin_id, destination_id): {
                "distanceKm": xx,
                "durationMin": xx,
            }
        }
    """
    parsed = {}

    if isinstance(data, str) or not isinstance(data, dict):
        return parsed

    ori_lookup = {
        _fmt_latlng(item["lat"], item["lng"]): item["id"]
        for item in origins
    }

    dst_lookup = {
        _fmt_latlng(item["lat"], item["lng"]): item["id"]
        for item in destinations
    }

    payload_data = data.get("data")
    matrix_results = payload_data.get("matrixResults") if isinstance(payload_data, dict) else None
    result_items = matrix_results or data.get("results") or []

    for idx, item in enumerate(result_items):
        origin = item.get("origin", "")
        destination = item.get("destination", "")

        origin_id = ori_lookup.get(origin)
        destination_id = dst_lookup.get(destination)

        # 有些服务返回的坐标格式可能不是完全一致的小数字符串，
        # 所以再做一次 normalize。
        if origin_id is None or destination_id is None:
            normalized_origin = _normalize_coord(origin)
            normalized_destination = _normalize_coord(destination)

            if normalized_origin:
                origin_id = ori_lookup.get(
                    _fmt_latlng(normalized_origin[0], normalized_origin[1])
                )

            if normalized_destination:
                destination_id = dst_lookup.get(
                    _fmt_latlng(normalized_destination[0], normalized_destination[1])
                )

        # 某些矩阵接口在 1 x n 的情况下，返回结果里可能没有可靠的 origin/destination 字段。
        # 这种情况下按照顺序兜底匹配。
        if (origin_id is None or destination_id is None) and len(origins) == 1 and idx < len(destinations):
            origin_id = origins[0].get("id")
            destination_id = destinations[idx].get("id")

        if origin_id is None or destination_id is None:
            continue

        distance = item.get("distance")
        duration = item.get("duration")

        if distance is None or duration is None:
            continue

        parsed[(origin_id, destination_id)] = {
            "distanceKm": round(float(distance) / 1000.0, 2),
            "durationMin": round(float(duration) / 60.0),
        }

    return parsed


async def _call_matrix_batch(http_client, route_url, headers, origins, destinations):
    """
    发起一次矩阵请求。

    origins / destinations 可以是：
        1 x n
        m x n
        最大建议 10 x 10

    注意：
        这里不关心哪些 OD 是真实需要的。
        它只负责请求完整的 origins x destinations 矩阵。
    """
    payload = {
        "origin": "|".join(_fmt_latlng(p["lat"], p["lng"]) for p in origins),
        "destination": "|".join(_fmt_latlng(p["lat"], p["lng"]) for p in destinations),
        "matrix": "true",
        "language": "en",
        "coordType": "wgs84",
    }

    status, data = await http_client.post_json(
        route_url,
        json_body=payload,
        headers=headers,
    )

    if status != 200:
        return status, data, {}

    return status, data, _parse_matrix_response(data, origins, destinations)


# =========================
# 贪心算法：候选 block 规划
# =========================

def _build_pair_maps(od_pairs):
    """
    基于当前还没有被覆盖的 OD 构建索引。

    参数：
        od_pairs:
            set[(origin_id, destination_id)]

    返回：
        o_to_d:
            origin_id -> set(destination_id)

        d_to_o:
            destination_id -> set(origin_id)

    这两个索引用于快速找稠密块。
    """
    o_to_d = defaultdict(set)
    d_to_o = defaultdict(set)

    for origin_id, destination_id in od_pairs:
        o_to_d[origin_id].add(destination_id)
        d_to_o[destination_id].add(origin_id)

    return o_to_d, d_to_o


def _calc_block_info(origin_ids, destination_ids, remaining_pairs):
    """
    计算一个候选 block 的信息。

    一个 block 表示一次请求：

        origin_ids x destination_ids

    例如：
        origins = [1, 2, 3]
        destinations = [10, 11, 12, 13]

    那么实际请求大小是：
        3 * 4 = 12 个格子

    但其中只有存在于 remaining_pairs 的 OD 才是有效格子。

    返回：
        {
            "origins": [...],
            "destinations": [...],
            "covered_pairs": set(...),
            "valid": 有效 OD 数量,
            "matrix_size": m * n,
            "density": valid / matrix_size,
            "waste": matrix_size - valid,
        }
    """
    origin_ids = list(dict.fromkeys(origin_ids))
    destination_ids = list(dict.fromkeys(destination_ids))

    if not origin_ids or not destination_ids:
        return None

    covered_pairs = {
        (o, d)
        for o in origin_ids
        for d in destination_ids
        if (o, d) in remaining_pairs
    }

    matrix_size = len(origin_ids) * len(destination_ids)
    if matrix_size <= 0:
        return None

    valid = len(covered_pairs)
    density = valid / matrix_size
    waste = matrix_size - valid

    return {
        "origins": origin_ids,
        "destinations": destination_ids,
        "covered_pairs": covered_pairs,
        "valid": valid,
        "matrix_size": matrix_size,
        "density": density,
        "waste": waste,
    }


def _shrink_to_dense_block(
    origin_ids,
    destination_ids,
    remaining_pairs,
    max_size=10,
    min_density=0.5,
):
    """
    把一个初始候选 block 收缩成满足密度要求的 block。

    初始候选通常是通过 seed 扩展得到的，可能比较稀疏。

    例如初始 block：

              d1  d2  d3  d4
        o1    ✅  ✅  ✅  ✅
        o2    ✅  ✅  ❌  ❌
        o3    ❌  ❌  ❌  ❌

    如果密度不达标，就不断删除贡献最低的行或列。

    删除规则：
        1. 计算每个 origin 行命中的有效 OD 数量
        2. 计算每个 destination 列命中的有效 OD 数量
        3. 删除命中数更低的一侧

    返回：
        block dict 或 None
    """
    origins = set(list(dict.fromkeys(origin_ids))[:max_size])
    destinations = set(list(dict.fromkeys(destination_ids))[:max_size])

    while origins and destinations:
        block = _calc_block_info(
            sorted(origins),
            sorted(destinations),
            remaining_pairs,
        )

        if not block:
            return None

        if block["density"] >= min_density:
            return block

        row_hit = {
            o: sum((o, d) in remaining_pairs for d in destinations)
            for o in origins
        }

        col_hit = {
            d: sum((o, d) in remaining_pairs for o in origins)
            for d in destinations
        }

        min_o, min_o_hit = min(row_hit.items(), key=lambda x: x[1])
        min_d, min_d_hit = min(col_hit.items(), key=lambda x: x[1])

        if min_o_hit <= min_d_hit:
            origins.remove(min_o)
        else:
            destinations.remove(min_d)

    return None


def _generate_origin_seed_candidates(
    remaining_pairs,
    max_size=10,
    min_density=0.5,
    top_origin_seed_count=None,
):
    """
    从 origin 作为 seed 生成候选 block。

    思路：
        1. 选一个 origin seed_o
        2. 找 seed_o 连接的 destinations
        3. destinations 按热门程度排序
        4. 再反向找这些 destinations 连接的 origins
        5. 形成一个 m x n 候选
        6. shrink 成满足密度要求的 block

    适合发现这种结构：

              d1  d2  d3  d4
        o1    ✅  ✅  ✅  ✅
        o2    ✅  ✅  ✅  ❌
        o3    ✅  ✅  ❌  ❌
    """
    o_to_d, d_to_o = _build_pair_maps(remaining_pairs)

    origin_seeds = sorted(
        o_to_d,
        key=lambda o: len(o_to_d[o]),
        reverse=True,
    )

    if top_origin_seed_count is not None:
        origin_seeds = origin_seeds[:top_origin_seed_count]

    candidates = []

    for seed_o in origin_seeds:
        candidate_destinations = sorted(
            o_to_d[seed_o],
            key=lambda d: len(d_to_o[d]),
            reverse=True,
        )[:max_size]

        origin_score = defaultdict(int)

        for d in candidate_destinations:
            for o in d_to_o[d]:
                origin_score[o] += 1

        candidate_origins = sorted(
            origin_score,
            key=lambda o: origin_score[o],
            reverse=True,
        )[:max_size]

        block = _shrink_to_dense_block(
            candidate_origins,
            candidate_destinations,
            remaining_pairs,
            max_size=max_size,
            min_density=min_density,
        )

        if block:
            candidates.append(block)

    return candidates


def _generate_destination_seed_candidates(
    remaining_pairs,
    max_size=10,
    min_density=0.5,
    top_destination_seed_count=300,
):
    """
    从 destination 作为 seed 生成候选 block。

    你的场景通常是：
        origins 少，比如 30
        destinations 多，比如 1000

    所以从 destination 出发很有价值。

    思路：
        1. 选一个 destination seed_d
        2. 找需要 seed_d 的 origins
        3. origins 按剩余连接数排序
        4. 再找这些 origins 连接的 destinations
        5. destinations 按命中次数排序
        6. shrink 成满足密度要求的 block
    """
    o_to_d, d_to_o = _build_pair_maps(remaining_pairs)

    destination_seeds = sorted(
        d_to_o,
        key=lambda d: len(d_to_o[d]),
        reverse=True,
    )

    if top_destination_seed_count is not None:
        destination_seeds = destination_seeds[:top_destination_seed_count]

    candidates = []

    for seed_d in destination_seeds:
        candidate_origins = sorted(
            d_to_o[seed_d],
            key=lambda o: len(o_to_d[o]),
            reverse=True,
        )[:max_size]

        destination_score = defaultdict(int)

        for o in candidate_origins:
            for d in o_to_d[o]:
                destination_score[d] += 1

        candidate_destinations = sorted(
            destination_score,
            key=lambda d: destination_score[d],
            reverse=True,
        )[:max_size]

        block = _shrink_to_dense_block(
            candidate_origins,
            candidate_destinations,
            remaining_pairs,
            max_size=max_size,
            min_density=min_density,
        )

        if block:
            candidates.append(block)

    return candidates


def _generate_signature_candidates(
    remaining_pairs,
    max_size=10,
    min_density=0.5,
    enable_signature_merge=True,
    max_signature_merge_groups=2,
    top_signature_count=120,
):
    """
    基于 destination 的 origin signature 生成候选 block。

    signature 的含义：

        某个 destination 被哪些 origins 需要。

    例如：
        d1 -> {o1, o2, o3}
        d2 -> {o1, o2, o3}
        d3 -> {o1, o2}

    那么：
        d1 和 d2 的 signature 相同，天然适合放到同一个 block：

            origins = [o1, o2, o3]
            destinations = [d1, d2]

        density = 1.0

    这个方法特别适合：
        origins 少，destinations 多。
    """
    _, d_to_o = _build_pair_maps(remaining_pairs)

    signature_to_destinations = defaultdict(list)

    for d, origins in d_to_o.items():
        signature = tuple(sorted(origins))
        signature_to_destinations[signature].append(d)

    signatures = sorted(
        signature_to_destinations,
        key=lambda sig: len(signature_to_destinations[sig]),
        reverse=True,
    )

    if top_signature_count is not None:
        signatures_for_merge = signatures[:top_signature_count]
    else:
        signatures_for_merge = signatures

    candidates = []

    for signature in signatures:
        origin_ids = list(signature)
        destination_ids = sorted(signature_to_destinations[signature])

        for origin_chunk in _chunk_list(origin_ids, max_size):
            for destination_chunk in _chunk_list(destination_ids, max_size):
                block = _calc_block_info(
                    origin_chunk,
                    destination_chunk,
                    remaining_pairs,
                )

                if block and block["density"] >= min_density:
                    candidates.append(block)

    if enable_signature_merge:
        for merge_count in range(2, max_signature_merge_groups + 1):
            for signature_group in combinations(signatures_for_merge, merge_count):
                merged_origins = sorted(
                    set().union(*[set(sig) for sig in signature_group])
                )

                if len(merged_origins) > max_size:
                    continue

                merged_destinations = []

                for sig in signature_group:
                    merged_destinations.extend(signature_to_destinations[sig])

                merged_destinations = sorted(set(merged_destinations))

                for destination_chunk in _chunk_list(merged_destinations, max_size):
                    block = _calc_block_info(
                        merged_origins,
                        destination_chunk,
                        remaining_pairs,
                    )

                    if block and block["density"] >= min_density:
                        candidates.append(block)

    return candidates


def _deduplicate_blocks(blocks):
    unique = {}

    for block in blocks:
        key = (
            tuple(sorted(block["origins"])),
            tuple(sorted(block["destinations"])),
        )

        old = unique.get(key)

        if old is None:
            unique[key] = block
            continue

        old_rank = (
            old["valid"],
            old["density"],
            -old["matrix_size"],
        )

        new_rank = (
            block["valid"],
            block["density"],
            -block["matrix_size"],
        )

        if new_rank > old_rank:
            unique[key] = block

    return list(unique.values())


def _score_block(block, score_mode="valid_x_density", request_overhead=0):
    valid = block["valid"]
    density = block["density"]
    waste = block["waste"]
    matrix_size = block["matrix_size"]

    if score_mode == "valid_x_density":
        return valid * density

    if score_mode == "valid_minus_waste":
        return valid - waste

    if score_mode == "cost_efficiency":
        return valid / (matrix_size + request_overhead)

    if score_mode == "valid":
        return valid

    raise ValueError(f"unknown score_mode: {score_mode}")


def _pick_best_block(
    candidates,
    min_valid_edges=6,
    score_mode="valid_x_density",
    request_overhead=0,
):
    best_block = None
    best_score = None

    for block in candidates:
        if block["valid"] < min_valid_edges:
            continue

        score = _score_block(
            block,
            score_mode=score_mode,
            request_overhead=request_overhead,
        )

        if best_score is None or score > best_score:
            best_block = block
            best_score = score

    return best_block, best_score


def _build_fallback_batches(remaining_pairs, max_size=10):
    o_to_d = defaultdict(list)

    for o, d in remaining_pairs:
        o_to_d[o].append(d)

    batches = []

    for origin_id in sorted(o_to_d):
        destination_ids = sorted(o_to_d[origin_id])

        for destination_chunk in _chunk_list(destination_ids, max_size):
            covered_pairs = {
                (origin_id, d)
                for d in destination_chunk
            }

            batches.append({
                "type": "one_to_many",
                "origins": [origin_id],
                "destinations": destination_chunk,
                "covered_pairs": covered_pairs,
                "valid": len(covered_pairs),
                "matrix_size": len(destination_chunk),
                "density": 1.0,
                "waste": 0,
                "score": None,
            })

    return batches


def _plan_matrix_batches_by_greedy(
    missing_pairs,
    max_size=10,
    min_density=0.5,
    min_valid_edges=6,
    score_mode="valid_x_density",
    request_overhead=0,
    top_origin_seed_count=None,
    top_destination_seed_count=300,
    enable_signature_candidates=True,
    enable_signature_merge=True,
    max_signature_merge_groups=2,
    top_signature_count=120,
):
    remaining_pairs = set(missing_pairs)
    batches = []
    round_index = 0

    while remaining_pairs:
        round_index += 1

        candidates = []

        candidates.extend(
            _generate_origin_seed_candidates(
                remaining_pairs=remaining_pairs,
                max_size=max_size,
                min_density=min_density,
                top_origin_seed_count=top_origin_seed_count,
            )
        )

        candidates.extend(
            _generate_destination_seed_candidates(
                remaining_pairs=remaining_pairs,
                max_size=max_size,
                min_density=min_density,
                top_destination_seed_count=top_destination_seed_count,
            )
        )

        if enable_signature_candidates:
            candidates.extend(
                _generate_signature_candidates(
                    remaining_pairs=remaining_pairs,
                    max_size=max_size,
                    min_density=min_density,
                    enable_signature_merge=enable_signature_merge,
                    max_signature_merge_groups=max_signature_merge_groups,
                    top_signature_count=top_signature_count,
                )
            )

        candidates = _deduplicate_blocks(candidates)

        best_block, best_score = _pick_best_block(
            candidates=candidates,
            min_valid_edges=min_valid_edges,
            score_mode=score_mode,
            request_overhead=request_overhead,
        )

        if best_block is None:
            logger.info(
                "route_matrix greedy: no dense block found, remaining_pairs=%d",
                len(remaining_pairs),
            )
            break

        batch = {
            "type": "dense",
            "origins": best_block["origins"],
            "destinations": best_block["destinations"],
            "covered_pairs": best_block["covered_pairs"],
            "valid": best_block["valid"],
            "matrix_size": best_block["matrix_size"],
            "density": best_block["density"],
            "waste": best_block["waste"],
            "score": best_score,
        }

        batches.append(batch)
        remaining_pairs -= best_block["covered_pairs"]

        logger.info(
            "route_matrix greedy: round=%d select block type=dense origins=%d destinations=%d "
            "valid=%d matrix_size=%d density=%.3f waste=%d score=%.3f remaining=%d",
            round_index,
            len(batch["origins"]),
            len(batch["destinations"]),
            batch["valid"],
            batch["matrix_size"],
            batch["density"],
            batch["waste"],
            batch["score"],
            len(remaining_pairs),
        )

    fallback_batches = _build_fallback_batches(
        remaining_pairs=remaining_pairs,
        max_size=max_size,
    )

    batches.extend(fallback_batches)

    dense_count = sum(1 for b in batches if b["type"] == "dense")
    fallback_count = sum(1 for b in batches if b["type"] == "one_to_many")
    total_matrix_size = sum(b["matrix_size"] for b in batches)
    total_valid = sum(b["valid"] for b in batches)
    total_waste = sum(b["waste"] for b in batches)
    avg_density = total_valid / total_matrix_size if total_matrix_size else 0

    logger.info(
        "route_matrix greedy: planned batches=%d dense=%d fallback=%d valid=%d matrix_size=%d "
        "waste=%d avg_density=%.3f",
        len(batches),
        dense_count,
        fallback_count,
        total_valid,
        total_matrix_size,
        total_waste,
        avg_density,
    )

    return batches


# =========================
# 结果构造
# =========================

def _build_result_item_success(row_index, origin, destination, result_item):
    return {
        "index": row_index,
        "success": True,
        "distanceKm": result_item["distanceKm"],
        "durationMin": result_item["durationMin"],
        "originLat": origin[0],
        "originLng": origin[1],
        "destinationLat": destination[0],
        "destinationLng": destination[1],
    }


def _build_result_item_failure(row_index, origin, destination, route_url, data, status):
    return {
        "index": row_index,
        "success": False,
        "errorType": "no_result" if status == 200 else "network_error",
        "request": route_url,
        "response": safe_json_dumps(data) if status != 200 else "无可用路径结果",
        "originLat": origin[0],
        "originLng": origin[1],
        "destinationLat": destination[0],
        "destinationLng": destination[1],
    }


# =========================
# 主入口
# =========================

async def route_matrix(http_client, auth, config, routes, progress_callback=None):
    route_url = config.get("routeUrl")
    if not route_url:
        return error_result("config_error", "routeUrl", "缺少导航接口地址")

    matrix_max_size = int(config.get("matrixMaxSize", 10))
    matrix_min_density = float(config.get("matrixMinDensity", 0.5))
    matrix_min_valid_edges = int(config.get("matrixMinValidEdges", 6))
    matrix_score_mode = config.get("matrixScoreMode", "valid_x_density")
    matrix_request_overhead = float(config.get("matrixRequestOverhead", 0))

    matrix_top_destination_seed_count = config.get("matrixTopDestinationSeedCount", 300)
    if matrix_top_destination_seed_count is not None:
        matrix_top_destination_seed_count = int(matrix_top_destination_seed_count)

    matrix_top_signature_count = config.get("matrixTopSignatureCount", 120)
    if matrix_top_signature_count is not None:
        matrix_top_signature_count = int(matrix_top_signature_count)

    enable_signature_candidates = bool(config.get("matrixEnableSignatureCandidates", True))
    enable_signature_merge = bool(config.get("matrixEnableSignatureMerge", True))
    max_signature_merge_groups = int(config.get("matrixMaxSignatureMergeGroups", 2))


    point_lookup = {}
    route_pairs = []

    for item in routes:
        origin = _normalize_coord(item.get("origin"))
        destination = _normalize_coord(item.get("destination"))

        if not origin or not destination:
            continue

        point_lookup.setdefault(_fmt_latlng(*origin), origin)
        point_lookup.setdefault(_fmt_latlng(*destination), destination)

        route_pairs.append((item.get("index"), origin, destination))

    if not route_pairs:
        logger.info("route_matrix: no valid route pairs after normalization")
        return {"success": True, "results": []}

    points = list(point_lookup.values())

    point_id_lookup = {
        _fmt_latlng(lat, lng): idx
        for idx, (lat, lng) in enumerate(points)
    }

    points_with_id = [
        {
            "id": idx,
            "lat": lat,
            "lng": lng,
        }
        for idx, (lat, lng) in enumerate(points)
    ]

    missing_pairs = set()
    pair_to_rows = defaultdict(list)

    for row_index, origin, destination in route_pairs:
        origin_key = _fmt_latlng(*origin)
        destination_key = _fmt_latlng(*destination)

        origin_id = point_id_lookup.get(origin_key)
        destination_id = point_id_lookup.get(destination_key)

        if origin_id is None or destination_id is None:
            continue

        pair_key = (origin_id, destination_id)

        missing_pairs.add(pair_key)
        pair_to_rows[pair_key].append((row_index, origin, destination))

    if not missing_pairs:
        logger.info("route_matrix: no valid missing pairs")
        return {"success": True, "results": []}

    headers = auth_headers(auth)
    parsed = {}
    last_error = None
    streamed_batches = []

    request_batches = _plan_matrix_batches_by_greedy(
        missing_pairs=missing_pairs,
        max_size=matrix_max_size,
        min_density=matrix_min_density,
        min_valid_edges=matrix_min_valid_edges,
        score_mode=matrix_score_mode,
        request_overhead=matrix_request_overhead,
        top_origin_seed_count=None,
        top_destination_seed_count=matrix_top_destination_seed_count,
        enable_signature_candidates=enable_signature_candidates,
        enable_signature_merge=enable_signature_merge,
        max_signature_merge_groups=max_signature_merge_groups,
        top_signature_count=matrix_top_signature_count,
    )

    logger.info(
        "route_matrix: start planned batches, routes=%d unique_pairs=%d batches=%d",
        len(route_pairs),
        len(missing_pairs),
        len(request_batches),
    )

    worker_count = max(1, int(config.get("matrixWorkerCount", 1)))

    logger.info(
        "route_matrix: execute planned batches with workers=%d total_batches=%d",
        worker_count,
        len(request_batches),
    )

    headers_state = {"headers": headers}
    state_lock = __import__("asyncio").Lock()
    refresh_lock = __import__("asyncio").Lock()
    callback_lock = __import__("asyncio").Lock()
    batch_queue = __import__("asyncio").Queue()

    for batch_index, batch in enumerate(request_batches, start=1):
        batch_queue.put_nowait((batch_index, batch))

    async def _run_worker(worker_id: int):
        nonlocal last_error

        while True:
            try:
                batch_index, batch = batch_queue.get_nowait()
            except __import__("asyncio").QueueEmpty:
                return

            try:
                origin_ids = batch["origins"]
                destination_ids = batch["destinations"]
                covered_pairs = batch["covered_pairs"]

                origin_points = [
                    points_with_id[o_id]
                    for o_id in origin_ids
                ]

                destination_points = [
                    points_with_id[d_id]
                    for d_id in destination_ids
                ]

                current_headers = headers_state["headers"]

                status, data, batch_parsed = await _call_matrix_batch(
                    http_client,
                    route_url,
                    current_headers,
                    origin_points,
                    destination_points,
                )

                logger.debug(
                    "route_matrix: worker=%d request batch index=%d type=%s origins=%d destinations=%d "
                    "valid=%d matrix_size=%d density=%.3f status=%s",
                    worker_id,
                    batch_index,
                    batch["type"],
                    len(origin_ids),
                    len(destination_ids),
                    batch["valid"],
                    batch["matrix_size"],
                    batch["density"],
                    status,
                )

                if status == 401:
                    async with refresh_lock:
                        refreshed_auth = config.get("token")

                        if not refreshed_auth:
                            from server.providers.custom.token import fetch_token
                            refreshed_auth = await fetch_token(http_client, config)

                        if refreshed_auth:
                            headers_state["headers"] = auth_headers(refreshed_auth)

                    status, data, batch_parsed = await _call_matrix_batch(
                        http_client,
                        route_url,
                        headers_state["headers"],
                        origin_points,
                        destination_points,
                    )

                batch_payload = []

                for origin_id, destination_id in sorted(covered_pairs):
                    rows = pair_to_rows.get((origin_id, destination_id), [])

                    for row_index, origin, destination in rows:
                        result_item = batch_parsed.get((origin_id, destination_id)) if status == 200 else None

                        if result_item:
                            batch_payload.append(
                                _build_result_item_success(
                                    row_index=row_index,
                                    origin=origin,
                                    destination=destination,
                                    result_item=result_item,
                                )
                            )
                        else:
                            batch_payload.append(
                                _build_result_item_failure(
                                    row_index=row_index,
                                    origin=origin,
                                    destination=destination,
                                    route_url=route_url,
                                    data=data,
                                    status=status,
                                )
                            )

                if batch_payload:
                    success_count = sum(1 for x in batch_payload if x.get("success"))

                    logger.info(
                        "route_matrix: worker=%d batch ready index=%d type=%s rows=%d success=%d fail=%d "
                        "origins=%d destinations=%d valid=%d matrix_size=%d density=%.3f waste=%d",
                        worker_id,
                        batch_index,
                        batch["type"],
                        len(batch_payload),
                        success_count,
                        len(batch_payload) - success_count,
                        len(origin_ids),
                        len(destination_ids),
                        batch["valid"],
                        batch["matrix_size"],
                        batch["density"],
                        batch["waste"],
                    )

                    async with state_lock:
                        streamed_batches.append(batch_payload)

                    if progress_callback:
                        async with callback_lock:
                            maybe = progress_callback(batch_payload)
                            if hasattr(maybe, "__await__"):
                                await maybe

                if status != 200:
                    async with state_lock:
                        last_error = (status, data)
                    continue

                async with state_lock:
                    parsed.update(batch_parsed)
            finally:
                batch_queue.task_done()

    worker_tasks = [
        __import__("asyncio").create_task(_run_worker(worker_id=i + 1))
        for i in range(worker_count)
    ]
    await __import__("asyncio").gather(*worker_tasks)

    results = []

    for row_index, origin, destination in route_pairs:
        origin_id = point_id_lookup.get(_fmt_latlng(*origin))
        destination_id = point_id_lookup.get(_fmt_latlng(*destination))

        item = None

        if origin_id is not None and destination_id is not None:
            item = parsed.get((origin_id, destination_id))

        if item:
            results.append(
                _build_result_item_success(
                    row_index=row_index,
                    origin=origin,
                    destination=destination,
                    result_item=item,
                )
            )
        else:
            results.append({
                "index": row_index,
                "success": False,
                "errorType": "no_result",
                "request": route_url,
                "response": safe_json_dumps(last_error[1]) if last_error else "无可用路径结果",
                "originLat": origin[0],
                "originLng": origin[1],
                "destinationLat": destination[0],
                "destinationLng": destination[1],
            })

    total_matrix_cells = sum(b["matrix_size"] for b in request_batches)
    total_valid_cells = sum(b["valid"] for b in request_batches)
    total_waste_cells = sum(b["waste"] for b in request_batches)

    logger.info(
        "route_matrix: completed results=%d batches=%d unique_pairs=%d matrix_cells=%d "
        "valid_cells=%d waste_cells=%d",
        len(results),
        len(streamed_batches),
        len(missing_pairs),
        total_matrix_cells,
        total_valid_cells,
        total_waste_cells,
    )

    return {
        "success": True,
        "results": results,
        "batches": streamed_batches,
    }
