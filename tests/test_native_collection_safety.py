from threading import Event

import pytest

from bosshunter.collection.base import CollectionBlockedError
from bosshunter.collection.safety import CollectionSafety
from bosshunter.db import add_platform_access, get_active_platform_safety_lock, get_db
from bosshunter.platform_safety import PlatformSafetyStop


@pytest.fixture
def db(tmp_path):
    conn = get_db(tmp_path / 'safety.db')
    yield conn
    conn.close()


@pytest.mark.parametrize('platform', ['zhilian', '51job', 'liepin'])
def test_search_limit_survives_new_guard_without_debiting_boss(db, platform):
    config = {'platforms': {platform: {'safety': {'daily_search_page_limit': 1}}}}
    CollectionSafety(config, db, platform).reserve('search_page')
    with pytest.raises(PlatformSafetyStop, match='daily_search_page_limit'):
        CollectionSafety(config, db, platform).reserve('search_page')
    assert db.execute("SELECT COUNT(*) FROM platform_access_events WHERE platform='boss'").fetchone()[0] == 0


def test_total_budget_includes_delivery_pages(db):
    add_platform_access(db, 'send', 'job_page', platform='51job')
    safety = CollectionSafety({'platforms': {'51job': {'safety': {'daily_platform_page_limit': 1}}}}, db, '51job')
    with pytest.raises(PlatformSafetyStop, match='daily_platform_page_limit'):
        safety.reserve('search_page')


@pytest.mark.parametrize('status', [403, 429])
def test_api_risk_cannot_fall_back_to_dom(db, status):
    safety = CollectionSafety({}, db, 'zhilian')
    with pytest.raises(CollectionBlockedError, match='停止采集'):
        safety.check_api_response({'http_status': status})


def test_three_errors_set_shared_persistent_lock(db):
    safety = CollectionSafety({}, db, 'liepin')
    safety.failure()
    safety.failure()
    with pytest.raises(PlatformSafetyStop, match='consecutive_page_failures'):
        safety.failure()
    assert get_active_platform_safety_lock(db)['reason'] == 'consecutive_page_failures'
    with pytest.raises(PlatformSafetyStop, match='persistent_risk_lock'):
        CollectionSafety({}, db, 'zhilian').reserve('search_page')


def test_missing_db_and_user_stop_never_open_page(db):
    with pytest.raises(PlatformSafetyStop, match='safety_db_unavailable'):
        CollectionSafety({}, None, '51job').reserve('search_page')
    safety = CollectionSafety({}, db, '51job')
    safety.stop_event = Event()
    safety.stop_event.set()
    with pytest.raises(PlatformSafetyStop, match='user_stopped'):
        safety.reserve('search_page')
    assert db.execute('SELECT COUNT(*) FROM platform_access_events').fetchone()[0] == 0
