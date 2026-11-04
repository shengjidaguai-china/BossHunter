"""Priority cities must be delivered before the rest, score only breaking ties."""

from bosshunter.executor.sender import _order_jobs_by_city_priority


def _job(city, score, job_id):
    return {"id": job_id, "city": city, "score": score, "title": f"岗位{job_id}"}


def test_priority_cities_come_first_and_keep_score_order_inside():
    jobs = [
        _job("合肥", 95, "a"),
        _job("深圳", 70, "b"),
        _job("上海", 71, "c"),
        _job("苏州", 99, "d"),
        _job("广州", 88, "e"),
    ]

    ordered = _order_jobs_by_city_priority(jobs, ["广州", "深圳", "佛山", "上海"])

    assert [job["city"] for job in ordered[:4]] == ["广州", "深圳", "上海", "苏州"]
    assert [job["city"] for job in ordered] == ["广州", "深圳", "上海", "苏州", "合肥"]


def test_unlisted_cities_stay_after_priority_ones_and_sorted_by_score():
    jobs = [_job("合肥", 60, "x"), _job("苏州", 90, "y"), _job("南京", 80, "z")]

    ordered = _order_jobs_by_city_priority(jobs, ["上海"])

    assert [job["city"] for job in ordered] == ["苏州", "南京", "合肥"]


def test_empty_priority_list_leaves_order_untouched():
    jobs = [_job("合肥", 60, "x"), _job("苏州", 90, "y")]

    assert _order_jobs_by_city_priority(jobs, []) == jobs
    assert _order_jobs_by_city_priority(jobs, ["", "  "]) == jobs


def test_priority_city_without_stock_does_not_break_ordering():
    jobs = [_job("合肥", 60, "x"), _job("佛山", 55, "y")]

    ordered = _order_jobs_by_city_priority(jobs, ["广州", "佛山"])

    assert [job["city"] for job in ordered] == ["佛山", "合肥"]


def test_city_names_are_matched_exactly_not_as_substrings():
    """'上海' must not sweep in '上海市' style variants the user did not list."""
    jobs = [_job("上海周边", 90, "p"), _job("上海", 70, "q")]

    ordered = _order_jobs_by_city_priority(jobs, ["上海"])

    assert [job["city"] for job in ordered] == ["上海", "上海周边"]
