"""Calculate sandbox cost per completed assessment from reconciled USD billing records."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TextIO
from uuid import UUID

COST_FIELDS = ("compute_usd", "storage_usd", "network_usd", "snapshot_usd")
OUTCOMES = ("completed", "failed", "abandoned")


def usd(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except (TypeError, InvalidOperation) as exc:
        raise ValueError("invalid USD amount") from exc
    if not amount.is_finite() or amount < 0:
        raise ValueError("expected a finite nonnegative USD amount")
    return amount


def calculate(stream: TextIO, period_fees: Decimal) -> tuple[dict[str, int], dict[str, Decimal]]:
    reader = csv.DictReader(stream)
    required = {"run_id", "outcome", *COST_FIELDS}
    if (
        not reader.fieldnames
        or len(reader.fieldnames) != len(required)
        or set(reader.fieldnames) != required
    ):
        raise ValueError("expected run_id, outcome and the four USD usage columns")
    seen: set[UUID] = set()
    counts = dict.fromkeys(OUTCOMES, 0)
    totals = dict.fromkeys(OUTCOMES, Decimal(0))
    for row in reader:
        try:
            if None in row:
                raise ValueError("extra columns in billing row")
            run_id = UUID(row["run_id"])
            if run_id in seen:
                raise ValueError(f"duplicate billed attempt {run_id}")
            seen.add(run_id)
            outcome = row["outcome"]
            if outcome not in counts:
                raise ValueError("unknown outcome")
            totals[outcome] += sum(usd(row[key]) for key in COST_FIELDS)
            counts[outcome] += 1
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError(f"billing CSV line {reader.line_num}: {exc}") from exc
    if not counts["completed"]:
        raise ValueError("a unit cost requires at least one completed assessment")
    totals["allocated_period_fees"] = period_fees
    totals["total"] = sum(totals.values(), Decimal(0))
    totals["per_completed_assessment"] = totals["total"] / counts["completed"]
    return counts, totals


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("invoice_rows", type=Path)
    parser.add_argument(
        "--allocated-period-fees-usd",
        required=True,
        type=usd,
        help="billed base fees attributable to this cohort, entered once",
    )
    args = parser.parse_args()
    try:
        with args.invoice_rows.open(encoding="utf-8", newline="") as stream:
            counts, totals = calculate(stream, args.allocated_period_fees_usd)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"{exc}\n")
    for outcome, count in counts.items():
        print(f"{outcome}: {count} attempts, USD {totals[outcome]:.4f} usage")
    print(f"Total including allocated fees: USD {totals['total']:.4f}")
    print(f"Per completed assessment: USD {totals['per_completed_assessment']:.4f}")


if __name__ == "__main__":
    main()
