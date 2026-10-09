from concurrent.futures import ThreadPoolExecutor

import pytest

from bosshunter.web.greeting_activity import GreetingActivityRegistry


def test_parallel_edits_cannot_claim_sending_job_but_can_claim_another():
    registry = GreetingActivityRegistry()

    def edit(job_id):
        with registry.claim(job_id, "editing") as acquired:
            return acquired

    with registry.claim("sending", "sending") as acquired:
        assert acquired
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert list(pool.map(edit, ["sending", "other"])) == [False, True]
        # The unsuccessful claimant must not release the sender's reservation.
        assert registry.get("sending") == "sending"
    assert registry.get("sending") is None


def test_exception_releases_activity_for_retry():
    registry = GreetingActivityRegistry()
    with pytest.raises(RuntimeError):
        with registry.claim("job", "generating") as acquired:
            assert acquired
            raise RuntimeError("cancelled or failed")
    with registry.claim("job", "editing") as acquired:
        assert acquired
