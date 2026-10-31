from copy import deepcopy

import pytest

from bosshunter.config import DEFAULTS, validate_platform_safety


@pytest.mark.parametrize('platform', ['zhilian', '51job', 'liepin'])
def test_native_defaults_are_bounded_and_independent(platform):
    config = deepcopy(DEFAULTS)
    validate_platform_safety(config)
    assert config['platforms'][platform]['safety'] == {
        'daily_search_page_limit': 20,
        'daily_detail_page_limit': 50,
        'daily_platform_page_limit': 80,
        'daily_delivery_limit': 10,
    }


@pytest.mark.parametrize('value', [0, -1, True, 1.5, '20', None, float('inf')])
def test_invalid_daily_limit_is_rejected(value):
    with pytest.raises(ValueError, match='正整数'):
        validate_platform_safety({'platforms': {'liepin': {'safety': {'daily_platform_page_limit': value}}}})


@pytest.mark.parametrize('value', [None, [], 'unlimited'])
def test_invalid_safety_section_is_rejected(value):
    with pytest.raises(ValueError, match='配置对象'):
        validate_platform_safety({'platforms': {'51job': {'safety': value}}})
