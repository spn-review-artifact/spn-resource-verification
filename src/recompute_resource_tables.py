#!/usr/bin/env python3
"""Recompute reuse-safe encryption and complete Grover-resource tables.

The program exposes the arithmetic used by the revised paper but does not
contain the proprietary S-box search. Inputs are the verified component costs
and explicit scheduling assumptions in ``data/resource_model.json``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "data" / "resource_model.json"


def ceil_log2(value: int) -> int:
    return 0 if value <= 1 else math.ceil(math.log2(value))


def build_encryption_rows(model: dict[str, Any]) -> list[dict[str, Any]]:
    transition = model["sbox_transition"]
    forward = transition["forward"]
    inverse = transition["inverse"]
    layers = model["linear_and_key_layers"]
    per_sbox_t = int(forward["t_count_4t"]) + int(inverse["t_count_4t"])
    per_sbox_cnot = int(forward["logical_cnot"]) + int(inverse["logical_cnot"])
    transition_depth = int(forward["compiled_full_depth_upper"]) + int(
        inverse["compiled_full_depth_upper"]
    )
    per_sbox_extra_width = max(
        int(forward["clean_width_used"]) - 4,
        int(inverse["clean_width_used"]) - 4,
    )
    rows: list[dict[str, Any]] = []
    for variant, data in model["variants"].items():
        rounds = int(data["rounds"])
        key_bits = int(data["key_bits"])
        state_cnot = (
            int(layers["initial_add_round_key_cnot"])
            + (rounds - 1)
            * (
                32 * per_sbox_cnot
                + int(layers["ordinary_round_mixcolumn_cnot"])
                + int(layers["ordinary_round_add_constant_cnot"])
            )
            + (32 * per_sbox_cnot + int(layers["round_add_key_cnot"]))
        )
        encryption_cnot = state_cnot + int(data["key_schedule_cnot"])
        for schedule, group_size_raw in model["sbox_schedules"].items():
            group_size = int(group_size_raw)
            groups = math.ceil(32 / group_size)
            round_t_depth = groups * (
                int(forward["and_depth"]) + int(inverse["and_depth"])
            )
            ordinary_depth = (
                groups * transition_depth
                + int(layers["mixcolumn_full_depth"])
                + int(layers["add_constant_full_depth_upper"])
                + int(layers["add_round_key_full_depth"])
                + int(data["key_schedule_depth_upper_per_round"])
            )
            final_depth = (
                groups * transition_depth
                + int(layers["add_round_key_full_depth"])
                + int(data["key_schedule_depth_upper_per_round"])
            )
            encryption_depth = 1 + (rounds - 1) * ordinary_depth + final_depth
            tight_width = key_bits + 128 + group_size * per_sbox_extra_width
            fixed_width = key_bits + 128 + max(128, group_size * per_sbox_extra_width)
            rows.append(
                {
                    "variant": variant,
                    "sbox_schedule": schedule,
                    "sboxes_per_group": group_size,
                    "groups_per_round": groups,
                    "rounds": rounds,
                    "t_count": rounds * 32 * per_sbox_t,
                    "t_depth": rounds * round_t_depth,
                    "logical_cnot": encryption_cnot,
                    "compiled_full_depth_upper": encryption_depth,
                    "tight_peak_width": tight_width,
                    "fixed_workspace_width": fixed_width,
                    "round_t_depth": round_t_depth,
                    "ordinary_round_full_depth_upper": ordinary_depth,
                    "final_round_full_depth_upper": final_depth,
                    "full_depth_status": "compiled-upper-bound-not-exact-hardware-depth",
                }
            )
    return rows


def and_tree(controls: int, constant_match: bool) -> dict[str, int]:
    logical_ands = max(0, controls - 1)
    levels = ceil_log2(controls)
    return {
        "controls": controls,
        "logical_ands": logical_ands,
        "clean_ancillas": max(0, 2 * controls - 2),
        "t_count": 4 * logical_ands,
        "cnot": 9 * logical_ands + 1,
        "one_qubit_upper": 7 * logical_ands + (2 * controls if constant_match else 0),
        "measurements": logical_ands,
        "t_depth": levels,
        "full_depth_bound": 12 * levels + (3 if constant_match else 1),
    }


def complete_row(
    variant: str,
    encryption: dict[str, Any],
    parameters: dict[str, Any],
    pair_schedule: str,
) -> dict[str, Any]:
    key = int(parameters["key_bits"])
    block = int(parameters["block_bits"])
    pairs = int(parameters["pairs"])
    compare = and_tree(pairs * block, constant_match=True)
    diffusion = and_tree(key, constant_match=False)
    enc_t = int(encryption["t_count"])
    enc_cnot_logical = int(encryption["logical_cnot"])
    enc_and_pairs = enc_t // 4
    affine_x_upper = int(encryption["rounds"]) * 32 + max(
        0, int(encryption["rounds"]) - 1
    ) * 128
    enc_cnot = enc_cnot_logical + 9 * enc_and_pairs
    enc_one_qubit = 7 * enc_and_pairs + affine_x_upper

    if pair_schedule == "pair-parallel":
        fanout_cnot = 2 * max(0, pairs - 1) * key
        fanout_depth = 2 * ceil_log2(pairs)
        core_t_depth = 2 * int(encryption["t_depth"])
        core_full_depth = 2 * int(encryption["compiled_full_depth_upper"])
        encryption_peak = pairs * int(encryption["fixed_workspace_width"])
        compare_peak = pairs * key + 3 * pairs * block - 1
    elif pair_schedule == "pair-serial":
        fanout_cnot = 0
        fanout_depth = 0
        core_t_depth = 2 * pairs * int(encryption["t_depth"])
        core_full_depth = 2 * pairs * int(encryption["compiled_full_depth_upper"])
        encryption_peak = int(encryption["fixed_workspace_width"]) + (pairs - 1) * block
        compare_peak = key + 3 * pairs * block - 1
    else:
        raise ValueError(pair_schedule)

    width = max(encryption_peak, compare_peak, 3 * key - 1)
    t_count = 2 * pairs * enc_t + compare["t_count"] + diffusion["t_count"]
    cnot = (
        2 * pairs * enc_cnot
        + fanout_cnot
        + compare["cnot"]
        + diffusion["cnot"]
    )
    one_qubit = (
        2 * pairs * enc_one_qubit
        + compare["one_qubit_upper"]
        + diffusion["one_qubit_upper"]
        + 4
        + 4 * key
    )
    measurements = (
        2 * pairs * enc_and_pairs
        + compare["measurements"]
        + diffusion["measurements"]
    )
    t_depth = core_t_depth + compare["t_depth"] + diffusion["t_depth"]
    full_depth = (
        core_full_depth
        + fanout_depth
        + compare["full_depth_bound"]
        + diffusion["full_depth_bound"]
        + 4
    )
    g_upper = t_count + cnot + one_qubit + measurements

    t7 = 2 * pairs * 14 * enc_and_pairs + 14 * (
        compare["logical_ands"] + diffusion["logical_ands"]
    )
    cnot7 = (
        2 * pairs * (enc_cnot_logical + 14 * enc_and_pairs)
        + fanout_cnot
        + 14 * compare["logical_ands"]
        + 1
        + 14 * diffusion["logical_ands"]
        + 1
    )
    one_qubit7 = (
        2 * pairs * (4 * enc_and_pairs + affine_x_upper)
        + 4 * compare["logical_ands"]
        + 2 * compare["controls"]
        + 4 * diffusion["logical_ands"]
        + 4 * key
        + 4
    )
    g_upper7 = t7 + cnot7 + one_qubit7
    if pair_schedule == "pair-parallel":
        t_depth7 = (
            12 * int(encryption["t_depth"])
            + 6 * compare["t_depth"]
            + 6 * diffusion["t_depth"]
        )
    else:
        t_depth7 = (
            12 * pairs * int(encryption["t_depth"])
            + 6 * compare["t_depth"]
            + 6 * diffusion["t_depth"]
        )
    log2_iterations = key / 2 + math.log2(math.pi / 4)
    return {
        "variant": variant,
        "schedule": pair_schedule,
        "key_bits": key,
        "block_bits": block,
        "pairs": pairs,
        "comparator_controls": pairs * block,
        "comparator_t_count": compare["t_count"],
        "diffusion_t_count": diffusion["t_count"],
        "iteration_t_count": t_count,
        "iteration_compiled_cnot_upper": cnot,
        "iteration_one_qubit_upper": one_qubit,
        "iteration_measurements": measurements,
        "iteration_g_upper": g_upper,
        "iteration_t_depth": t_depth,
        "iteration_full_depth_bound": full_depth,
        "iteration_width": width,
        "iteration_dw": full_depth * width,
        "sensitivity_7t_iteration_t_count": t7,
        "sensitivity_7t_iteration_t_depth": t_depth7,
        "sensitivity_7t_iteration_g_upper": g_upper7,
        "log2_iterations_pi_over_4": round(log2_iterations, 6),
        "log2_full_search_g_upper": round(log2_iterations + math.log2(g_upper), 6),
        "sensitivity_7t_log2_full_search_g_upper": round(
            log2_iterations + math.log2(g_upper7), 6
        ),
        "log2_full_search_dw": round(
            log2_iterations + math.log2(full_depth * width), 6
        ),
        "sbox_schedule": encryption["sbox_schedule"],
        "encryption_full_depth_status": encryption["full_depth_status"],
    }


def build_complete_rows(
    model: dict[str, Any], encryption_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for encryption in encryption_rows:
        parameters = model["variants"][encryption["variant"]]
        for pair_schedule in ("pair-parallel", "pair-serial"):
            rows.append(
                complete_row(
                    encryption["variant"], encryption, parameters, pair_schedule
                )
            )
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    with path.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def check_frozen(
    encryption_rows: list[dict[str, Any]], complete_rows: list[dict[str, Any]]
) -> None:
    frozen_encryption = json.loads(
        (
            ROOT
            / "frozen_results"
            / "reuse_safe_ulbc"
            / "reuse_safe_ulbc_schedules.json"
        ).read_text(encoding="utf-8")
    )["rows"]
    frozen_complete = json.loads(
        (
            ROOT
            / "frozen_results"
            / "complete_oracle"
            / "reuse_safe_complete_oracle.json"
        ).read_text(encoding="utf-8")
    )
    if encryption_rows != frozen_encryption:
        raise AssertionError("recomputed encryption rows differ from frozen evidence")
    if complete_rows != frozen_complete:
        raise AssertionError("recomputed complete-oracle rows differ from frozen evidence")
    print("frozen encryption rows: PASS")
    print("frozen complete-oracle rows: PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-frozen", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    encryption_rows = build_encryption_rows(model)
    complete_rows = build_complete_rows(model, encryption_rows)
    if args.check_frozen:
        check_frozen(encryption_rows, complete_rows)
    if args.output_dir:
        output = args.output_dir.resolve()
        write_rows(output / "reuse_safe_ulbc_schedules.json", encryption_rows)
        write_rows(output / "reuse_safe_complete_oracle.json", complete_rows)
        print(f"generated files written under {output}")
    selected = [
        row
        for row in complete_rows
        if row["sbox_schedule"] == "four-group"
        and row["schedule"] == "pair-parallel"
    ]
    for row in selected:
        print(
            f"{row['variant']:11s} T={row['iteration_t_count']} "
            f"Td={row['iteration_t_depth']} D<={row['iteration_full_depth_bound']} "
            f"W={row['iteration_width']} log2G={row['log2_full_search_g_upper']} "
            f"log2DW={row['log2_full_search_dw']}"
        )
    if not args.check_frozen and not args.output_dir:
        print("no files written; use --check-frozen or --output-dir")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
