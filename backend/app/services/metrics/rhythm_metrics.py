"""节奏与效率指标（D 组）。

- stroke_cycle_duration_sec：单侧 hand_entry 相邻间隔 / fps
- stroke_rate_spm：60 / 单侧周期（用 event.side 过滤出单侧）
- stroke_count：单侧 hand_entry 计数
- stroke_length_m：优先级1 = distance_markers 距离增量 / stroke_count；否则 speed/(rate/60) 估算
- average_speed_mps：基于 distance_markers 推导
- swolf：time_sec + stroke_count，保留 distance_m 上下文
- cycles[]：单侧划水周期明细
"""

from statistics import mean


def _hand_entries_by_side(events: list[dict]) -> dict[str, list[dict]]:
    """按 side 把 hand_entry 事件分组；side 未知/缺失时归为 'unknown'。"""
    groups: dict[str, list[dict]] = {}
    for e in events:
        if not isinstance(e, dict) or e.get("name") != "hand_entry":
            continue
        side = e.get("side") or "unknown"
        groups.setdefault(side, []).append(e)
    return groups


def calculate_rhythm_efficiency_metrics(annotation: dict, ppm: float | None) -> tuple[dict, list[dict]]:
    events = annotation.get("events") or []
    fps = annotation.get("fps") or 0
    distance_markers = annotation.get("distance_markers") or []

    summary: dict = {}
    cycles: list[dict] = []

    groups = _hand_entries_by_side(events)
    # 若全部 unknown，则把 unknown 当作单侧处理；否则取任一侧（优先非 unknown）
    sides = [s for s in groups if s != "unknown"] or (["unknown"] if "unknown" in groups else [])

    all_entries: list[dict] = []
    for side in sides:
        entries = sorted(groups[side], key=lambda e: e.get("frame", 0))
        if len(entries) < 1:
            continue
        all_entries.extend(entries)

        # 单侧完整周期（相邻同侧 hand_entry 间隔）
        intervals: list[float] = []
        for i in range(1, len(entries)):
            f0 = entries[i - 1].get("frame", 0)
            f1 = entries[i].get("frame", 0)
            if fps:
                intervals.append((f1 - f0) / fps)
            cycle = {
                "cycle_index": len(cycles) + 1,
                "start_frame": f0,
                "end_frame": f1,
                "duration_sec": round((f1 - f0) / fps, 3) if fps else None,
                "events": {
                    "hand_entry": f0,
                    "next_hand_entry": f1,
                },
            }
            cycles.append(cycle)

        if intervals:
            avg_cycle = mean(intervals)
            summary[f"stroke_cycle_duration_sec_{side}"] = round(avg_cycle, 3)
            summary[f"stroke_rate_spm_{side}"] = round(60.0 / avg_cycle, 2) if avg_cycle > 0 else None

    # 汇总（优先单侧；多侧时以首个非 unknown 侧为准，并记录总数）
    stroke_count = len(all_entries)
    summary["stroke_count"] = stroke_count

    if cycles:
        cycle_durations = [c["duration_sec"] for c in cycles if c["duration_sec"]]
        if cycle_durations:
            avg_cycle = mean(cycle_durations)
            summary["stroke_cycle_duration_sec_avg"] = round(avg_cycle, 3)
            if avg_cycle > 0:
                summary["stroke_rate_spm_avg"] = round(60.0 / avg_cycle, 2)

    # 平均速度和划幅（distance_markers）
    if distance_markers and len(distance_markers) >= 2 and fps:
        dm = sorted(distance_markers, key=lambda m: m.get("frame", 0))
        d0, d1 = dm[0], dm[-1]
        dist_delta = d1.get("distance_m", 0) - d0.get("distance_m", 0)
        time_delta = (d1.get("frame", 0) - d0.get("frame", 0)) / fps
        if time_delta > 0:
            avg_speed = dist_delta / time_delta
            summary["average_speed_mps"] = round(avg_speed, 3)
            if stroke_count > 0 and "stroke_cycle_duration_sec_avg" in summary:
                summary["stroke_length_m_avg"] = round(dist_delta / stroke_count, 3)

    # SWOLF：覆盖周期的时间跨度 + 划水次数
    if cycles:
        first_frame = cycles[0]["start_frame"]
        last_frame = cycles[-1]["end_frame"]
        if fps:
            time_span = (last_frame - first_frame) / fps
            swolf = time_span + stroke_count
            swolf_obj = {
                "value": round(swolf, 2),
                "time_sec": round(time_span, 3),
                "stroke_count": stroke_count,
            }
            if distance_markers and len(distance_markers) >= 2:
                dm = sorted(distance_markers, key=lambda m: m.get("frame", 0))
                swolf_obj["distance_m"] = round(
                    dm[-1].get("distance_m", 0) - dm[0].get("distance_m", 0), 3
                )
            summary["swolf"] = swolf_obj

    return summary, cycles
