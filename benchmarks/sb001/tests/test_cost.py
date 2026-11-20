from decimal import Decimal
from io import StringIO
from uuid import uuid4

import pytest

from benchmarks.sb001.cost import calculate, usd

HEADER = "run_id,outcome,compute_usd,storage_usd,network_usd,snapshot_usd\n"


def test_period_cost_includes_failed_and_abandoned_usage():
    source = StringIO(
        HEADER
        + "".join(
            f"{uuid4()},{status},1.05,0.10,0.02,0.03\n"
            for status in ("completed", "completed", "failed", "abandoned")
        )
    )
    counts, totals = calculate(source, Decimal("2.00"))
    assert counts == {"completed": 2, "failed": 1, "abandoned": 1}
    assert totals["total"] == Decimal("6.80")
    assert totals["per_completed_assessment"] == Decimal("3.40")


def test_no_completions_has_no_unit_cost():
    with pytest.raises(ValueError, match="at least one completed"):
        calculate(StringIO(HEADER), Decimal(0))


def test_duplicate_and_invalid_invoice_rows_fail():
    data = f"{uuid4()},completed,0,0,0,0\n"
    with pytest.raises(ValueError, match="duplicate billed attempt"):
        calculate(StringIO(HEADER + data * 2), Decimal(0))
    for invalid in ("NaN", "-0.01", "1.2USD", "Infinity"):
        with pytest.raises(ValueError):
            usd(invalid)
