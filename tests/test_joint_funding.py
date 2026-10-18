from copy import deepcopy

import pytest

from app.services.joint_funding import (
    _digest,
    analyze,
    apply_evidence,
    rank_evidence,
    verify,
)
from scripts.joint_funding_cases import (
    enumerate_bounds,
    query_case,
    split_case,
    tiny_case,
)


def test_joint_bounds_do_not_sum_marginal_upper_bounds():
    ledger = split_case()
    joint = analyze(ledger, 1)["result"]
    assert (joint["lower"], joint["upper"]) == (1_000_000, 1_000_000)
    for target in ("B", "C"):
        ledger["targets"] = [target]
        marginal = analyze(ledger, 1)["result"]
        assert (marginal["lower"], marginal["upper"]) == (0, 1_000_000)
    for target in ("B", "C"):
        ledger["movements"].append(
            {
                "id": f"merge-{target}",
                "source": target,
                "destination": "D",
                "amount": 1_000_000,
            }
        )
    ledger["targets"] = ["B", "C", "D"]
    assert analyze(ledger, 1)["result"] == joint


@pytest.mark.parametrize("seed", range(250))
def test_exact_bounds_against_independent_exhaustive_oracle(seed):
    ledger = tiny_case(seed)
    result = analyze(ledger, 1)["result"]
    assert (result["lower"], result["upper"]) == enumerate_bounds(ledger)


def test_certificate_verifier_detects_nonoptimal_feasible_endpoint_even_with_rehashed_payload():
    ledger = split_case()
    ledger["targets"] = ["B"]
    certificate = analyze(ledger, 1)
    assert verify(certificate)
    certificate["lower_witness"] = certificate["upper_witness"]
    certificate["result"]["lower"] = certificate["result"]["upper"]
    certificate["result"]["condition"] = "MET"
    certificate["digest"] = _digest(
        {k: v for k, v in certificate.items() if k != "digest"}
    )
    assert not verify(certificate)


def test_certificate_tamper_and_deterministic_replay():
    certificate = analyze(split_case(), 1)
    assert certificate == analyze(split_case(), 1)
    certificate["ledger"]["cohort_id"] = "changed"
    assert not verify(certificate)


def test_query_selection_and_actual_evidence_application():
    ledger, threshold, queries = query_case()
    before = deepcopy(ledger)
    report = rank_evidence(ledger, threshold, queries)
    assert report["selected_query"] == "relevant-query"
    assert report["ranking"][0]["all_outcomes_resolve"]
    assert report["ranking"][1]["guaranteed_ambiguity_reduction"] == 0
    for index, expected in enumerate(("NOT_MET", "MET")):
        updated = apply_evidence(ledger, queries[0], index)
        assert analyze(updated, threshold)["result"]["condition"] == expected
    assert ledger == before


def test_irreducible_fungibility_does_not_trigger_useless_query():
    ledger = split_case()
    ledger["targets"] = ["B"]
    query = {
        "id": "already-known",
        "record_id": "receipt",
        "cost": 1,
        "evidence_reference": "synthetic",
        "outcomes": [[1_000_000, 1_000_000]],
    }
    report = rank_evidence(ledger, 1, [query])
    assert report["selected_query"] is None


@pytest.mark.parametrize(
    "outcomes", ([[0, 1]], [[0, 1], [1, 20]], [[0, 1], [3, 20]], [[-1, 2]], [])
)
def test_nonexhaustive_or_invalid_queries_rejected(outcomes):
    ledger, threshold, queries = query_case()
    queries[0]["outcomes"] = outcomes
    with pytest.raises(ValueError):
        rank_evidence(ledger, threshold, queries)


def test_internal_allocation_cannot_be_queried_as_fact():
    ledger, threshold, queries = query_case()
    queries[0]["record_id"] = "forward"
    with pytest.raises(ValueError, match="external boundary"):
        rank_evidence(ledger, threshold, queries)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(complete=False),
        lambda d: d.update(targets=["B", "B"]),
        lambda d: d.update(targets=["unknown"]),
        lambda d: d["movements"][1].update(amount=9_000_000),
        lambda d: d["movements"][1].update(amount=1.5),
        lambda d: d["movements"][1].update(amount=True),
        lambda d: d["movements"][1].update(lower=0),
        lambda d: d["movements"][1].update(id="receipt"),
        lambda d: d["movements"][1].update(destination=None),
    ],
)
def test_invalid_or_incomplete_inputs_fail_closed(mutation):
    ledger = split_case()
    mutation(ledger)
    with pytest.raises(ValueError):
        analyze(ledger, 1)


def test_large_integer_minor_units_remain_exact():
    ledger = split_case()
    scale = 10**12 + 7
    for record in ledger["opening"] + ledger["movements"]:
        for key in ("amount", "lower", "upper"):
            if key in record:
                record[key] *= scale
    result = analyze(ledger, 1)["result"]
    assert result["lower"] == result["upper"] == 1_000_000 * scale


def test_all_zero_cohort_is_valid_and_below_threshold():
    ledger = split_case()
    ledger["movements"][0].update(lower=0, upper=0)
    assert analyze(ledger, 1)["result"] == {
        "lower": 0,
        "upper": 0,
        "condition": "NOT_MET",
    }
