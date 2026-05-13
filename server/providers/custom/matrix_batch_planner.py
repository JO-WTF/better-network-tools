import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def _chunk_list(items, size):
    items = list(items)
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _build_pair_maps(od_pairs):
    o_to_d = defaultdict(set)
    d_to_o = defaultdict(set)

    for origin_id, destination_id in od_pairs:
        o_to_d[origin_id].add(destination_id)
        d_to_o[destination_id].add(origin_id)

    return o_to_d, d_to_o


def _calc_block_info(origin_ids, destination_ids, remaining_pairs):
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


def _build_fallback_batches(remaining_pairs, max_size=10):
    o_to_d = defaultdict(list)
    for o, d in remaining_pairs:
        o_to_d[o].append(d)

    batches = []
    for origin_id in sorted(o_to_d):
        destination_ids = sorted(o_to_d[origin_id])
        for destination_chunk in _chunk_list(destination_ids, max_size):
            covered_pairs = {(origin_id, d) for d in destination_chunk}
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


def _mask_bit_count(mask: int) -> int:
    return mask.bit_count()


def _iter_mask_bits(mask: int):
    while mask:
        lowbit = mask & -mask
        yield lowbit.bit_length() - 1
        mask ^= lowbit


def _jaccard_similarity(mask_a: int, mask_b: int) -> float:
    union = mask_a | mask_b
    if union == 0:
        return 0.0
    return (mask_a & mask_b).bit_count() / union.bit_count()


def _build_destination_mask_groups(remaining_pairs):
    o_to_d, d_to_o = _build_pair_maps(remaining_pairs)

    origins_sorted = sorted(o_to_d)
    origin_to_bit = {origin_id: bit_index for bit_index, origin_id in enumerate(origins_sorted)}
    bit_to_origin = {bit_index: origin_id for origin_id, bit_index in origin_to_bit.items()}

    mask_to_destinations = defaultdict(list)
    for destination_id, origin_ids in d_to_o.items():
        mask = 0
        for origin_id in origin_ids:
            mask |= 1 << origin_to_bit[origin_id]
        mask_to_destinations[mask].append(destination_id)

    groups = []
    for mask, destination_ids in mask_to_destinations.items():
        destination_ids = sorted(destination_ids)
        popcount = _mask_bit_count(mask)
        groups.append({"mask": mask, "destinations": destination_ids, "popcount": popcount, "valid": popcount * len(destination_ids)})

    groups.sort(key=lambda g: (-g["popcount"], -len(g["destinations"]), g["mask"]))
    return origins_sorted, origin_to_bit, bit_to_origin, groups


def _mask_to_origin_ids(mask, bit_to_origin):
    return [bit_to_origin[bit_index] for bit_index in _iter_mask_bits(mask)]


def _group_density(mask, groups):
    if not groups:
        return 0, 0, 0.0, 0
    total_valid = sum(g["popcount"] * len(g["destinations"]) for g in groups)
    total_destinations = sum(len(g["destinations"]) for g in groups)
    origin_count = _mask_bit_count(mask)
    matrix_size = origin_count * total_destinations
    if matrix_size <= 0:
        return total_valid, matrix_size, 0.0, 0
    density = total_valid / matrix_size
    waste = matrix_size - total_valid
    return total_valid, matrix_size, density, waste


def _tile_cluster_to_blocks(cluster_groups, bit_to_origin, remaining_pairs, max_size=10, min_density=0.5, min_valid_edges=50, block_type="dense_mask_cluster"):
    if not cluster_groups:
        return []
    union_mask = 0
    destination_ids = []
    for group in cluster_groups:
        union_mask |= group["mask"]
        destination_ids.extend(group["destinations"])

    origin_ids = sorted(_mask_to_origin_ids(union_mask, bit_to_origin))
    destination_ids = sorted(set(destination_ids))
    blocks = []
    for origin_chunk in _chunk_list(origin_ids, max_size):
        for destination_chunk in _chunk_list(destination_ids, max_size):
            block = _calc_block_info(origin_chunk, destination_chunk, remaining_pairs)
            if not block or block["valid"] < min_valid_edges or block["density"] < min_density:
                continue
            blocks.append({**block, "type": block_type, "score": block["valid"] * block["density"]})
    return blocks


def _build_popcount_buckets(groups):
    buckets = defaultdict(list)
    for index, group in enumerate(groups):
        buckets[group["popcount"]].append(index)
    return buckets


def _build_sample_inverted_index(groups, sample_origin_count=32):
    inverted = defaultdict(set)
    for group_index, group in enumerate(groups):
        bits = list(_iter_mask_bits(group["mask"]))
        if not bits:
            continue
        if len(bits) <= sample_origin_count:
            sampled_bits = bits
        else:
            step = len(bits) / sample_origin_count
            sampled_bits = [bits[int(i * step)] for i in range(sample_origin_count)]
        for bit_index in sampled_bits:
            inverted[bit_index].add(group_index)
    return inverted


def _get_candidate_group_indices(current_mask, current_popcount, groups, unused_indices, popcount_buckets, inverted_index, similarity_threshold=0.5, sample_origin_count=32, max_raw_candidates=500):
    if not unused_indices or current_popcount <= 0:
        return []
    s = similarity_threshold
    min_popcount = max(1, int(current_popcount * s))
    max_popcount = int(current_popcount / s) if s > 0 else max(popcount_buckets)
    if popcount_buckets:
        max_popcount = min(max_popcount, max(popcount_buckets))

    bits = list(_iter_mask_bits(current_mask))
    if len(bits) <= sample_origin_count:
        sampled_bits = bits
    else:
        step = len(bits) / sample_origin_count
        sampled_bits = [bits[int(i * step)] for i in range(sample_origin_count)]

    inverted_candidates = set()
    for bit_index in sampled_bits:
        inverted_candidates.update(inverted_index.get(bit_index, set()))

    if not inverted_candidates:
        for popcount in range(min_popcount, max_popcount + 1):
            for group_index in popcount_buckets.get(popcount, []):
                if group_index in unused_indices:
                    inverted_candidates.add(group_index)
                    if len(inverted_candidates) >= max_raw_candidates:
                        break
            if len(inverted_candidates) >= max_raw_candidates:
                break

    candidates = []
    for group_index in inverted_candidates:
        if group_index not in unused_indices:
            continue
        popcount = groups[group_index]["popcount"]
        if min_popcount <= popcount <= max_popcount:
            candidates.append(group_index)
            if len(candidates) >= max_raw_candidates:
                break
    return candidates


def _cluster_remaining_mask_groups(groups, bit_to_origin, remaining_pairs, max_size=10, min_density=0.7, similarity_threshold=0.5, min_valid_edges=50, top_k_candidates=50, sample_origin_count=32, max_expand_steps_per_cluster=10, max_dense_clusters=500):
    if not groups:
        return [], set()

    popcount_buckets = _build_popcount_buckets(groups)
    inverted_index = _build_sample_inverted_index(groups, sample_origin_count=sample_origin_count)

    unused_indices = set(range(len(groups)))
    selected_blocks = []
    covered_pairs = set()
    cluster_count = 0

    while unused_indices and cluster_count < max_dense_clusters:
        seed_index = min(unused_indices, key=lambda idx: (-groups[idx]["popcount"], -len(groups[idx]["destinations"]), groups[idx]["mask"]))
        seed_group = groups[seed_index]

        current_groups = [seed_group]
        current_mask = seed_group["mask"]
        current_valid, current_matrix_size, current_density, current_waste = _group_density(current_mask, current_groups)
        unused_indices.remove(seed_index)

        expand_steps = 0
        while expand_steps < max_expand_steps_per_cluster:
            expand_steps += 1
            current_popcount = _mask_bit_count(current_mask)
            candidate_indices = _get_candidate_group_indices(current_mask, current_popcount, groups, unused_indices, popcount_buckets, inverted_index, similarity_threshold=similarity_threshold, sample_origin_count=sample_origin_count)
            if not candidate_indices:
                break

            scored_candidates = []
            for candidate_index in candidate_indices:
                candidate = groups[candidate_index]
                similarity = _jaccard_similarity(current_mask, candidate["mask"])
                if similarity < similarity_threshold:
                    continue
                merged_mask = current_mask | candidate["mask"]
                merged_groups = current_groups + [candidate]
                valid, matrix_size, density, waste = _group_density(merged_mask, merged_groups)
                if density < min_density:
                    continue
                score = density * 1000 + similarity * 100 + valid - waste
                scored_candidates.append((score, candidate_index, merged_mask, valid, matrix_size, density, waste, similarity))

            if not scored_candidates:
                break
            scored_candidates.sort(reverse=True)
            best = scored_candidates[:top_k_candidates][0]
            _, best_index, merged_mask, valid, matrix_size, density, waste, _ = best
            current_groups.append(groups[best_index])
            current_mask = merged_mask
            current_valid, current_matrix_size, current_density, current_waste = valid, matrix_size, density, waste
            unused_indices.remove(best_index)

        cluster_blocks = _tile_cluster_to_blocks(current_groups, bit_to_origin, remaining_pairs, max_size=max_size, min_density=min_density, min_valid_edges=min_valid_edges, block_type="dense_mask_cluster")
        for block in cluster_blocks:
            new_pairs = block["covered_pairs"] - covered_pairs
            if not new_pairs:
                continue
            refreshed = _calc_block_info(block["origins"], block["destinations"], remaining_pairs - covered_pairs)
            if not refreshed or refreshed["valid"] < min_valid_edges or refreshed["density"] < min_density:
                continue
            selected_blocks.append({**refreshed, "type": "dense_mask_cluster", "score": refreshed["valid"] * refreshed["density"]})
            covered_pairs.update(refreshed["covered_pairs"])

        cluster_count += 1
        logger.info("route_matrix planner: cluster=%d groups=%d valid=%d matrix_size=%d density=%.3f waste=%d blocks=%d covered=%d unused_groups=%d", cluster_count, len(current_groups), current_valid, current_matrix_size, current_density, current_waste, len(cluster_blocks), len(covered_pairs), len(unused_indices))

    return selected_blocks, covered_pairs


def _plan_matrix_batches(missing_pairs, max_size=10, min_density=0.7, similarity_threshold=0.5, min_valid_edges=50, exact_group_min_destinations=10, exact_group_min_valid_edges=50, top_k_candidates=50, sample_origin_count=32, max_expand_steps_per_cluster=10, max_dense_clusters=500):
    remaining_pairs = set(missing_pairs)
    if not remaining_pairs:
        return []

    origins_sorted, origin_to_bit, bit_to_origin, groups = _build_destination_mask_groups(remaining_pairs)
    logger.info("route_matrix planner: start pairs=%d origins=%d mask_groups=%d", len(remaining_pairs), len(origins_sorted), len(groups))

    batches = []
    covered_pairs = set()
    remaining_groups = []
    exact_blocks_count = 0

    for group in groups:
        group_valid = group["popcount"] * len(group["destinations"])
        should_tile_exact = len(group["destinations"]) >= exact_group_min_destinations or group_valid >= exact_group_min_valid_edges
        if not should_tile_exact:
            remaining_groups.append(group)
            continue

        cluster_blocks = _tile_cluster_to_blocks([group], bit_to_origin, remaining_pairs - covered_pairs, max_size=max_size, min_density=min_density, min_valid_edges=min_valid_edges, block_type="dense_exact_signature")
        if not cluster_blocks:
            remaining_groups.append(group)
            continue

        for block in cluster_blocks:
            new_pairs = block["covered_pairs"] - covered_pairs
            if not new_pairs:
                continue
            batches.append(block)
            covered_pairs.update(block["covered_pairs"])
            exact_blocks_count += 1

    logger.info("route_matrix planner: exact signature blocks=%d covered_pairs=%d remaining_groups=%d", exact_blocks_count, len(covered_pairs), len(remaining_groups))

    cluster_blocks, _ = _cluster_remaining_mask_groups(groups=remaining_groups, bit_to_origin=bit_to_origin, remaining_pairs=remaining_pairs - covered_pairs, max_size=max_size, min_density=min_density, similarity_threshold=similarity_threshold, min_valid_edges=min_valid_edges, top_k_candidates=top_k_candidates, sample_origin_count=sample_origin_count, max_expand_steps_per_cluster=max_expand_steps_per_cluster, max_dense_clusters=max_dense_clusters)

    for block in cluster_blocks:
        new_pairs = block["covered_pairs"] - covered_pairs
        if not new_pairs:
            continue
        refreshed = _calc_block_info(block["origins"], block["destinations"], remaining_pairs - covered_pairs)
        if not refreshed or refreshed["valid"] < min_valid_edges or refreshed["density"] < min_density:
            continue
        refreshed_block = {**refreshed, "type": block["type"], "score": refreshed["valid"] * refreshed["density"]}
        batches.append(refreshed_block)
        covered_pairs.update(refreshed_block["covered_pairs"])

    leftover_pairs = remaining_pairs - covered_pairs
    fallback_batches = _build_fallback_batches(leftover_pairs, max_size=max_size)
    batches.extend(fallback_batches)

    dense_count = sum(1 for b in batches if b["type"] in {"dense_exact_signature", "dense_mask_cluster"})
    fallback_count = sum(1 for b in batches if b["type"] == "one_to_many")
    total_matrix_size = sum(b["matrix_size"] for b in batches)
    total_valid = sum(b["valid"] for b in batches)
    total_waste = sum(b["waste"] for b in batches)
    avg_density = total_valid / total_matrix_size if total_matrix_size else 0

    logger.info("route_matrix planner: done batches=%d dense=%d fallback=%d pairs=%d valid=%d matrix_size=%d waste=%d avg_density=%.3f", len(batches), dense_count, fallback_count, len(missing_pairs), total_valid, total_matrix_size, total_waste, avg_density)
    return batches
