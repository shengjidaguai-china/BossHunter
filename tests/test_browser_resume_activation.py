from unittest.mock import patch

from bosshunter.browser.client import RuntimeClient


def test_activate_uses_runtime_and_never_navigates():
    client = RuntimeClient()
    target = 'A' * 32
    with patch.object(client, '_get_ok', return_value=True) as call:
        assert client.activate_tab(target)
    call.assert_called_once_with('/activate', params={'target': target}, timeout=5)


def test_invalid_target_cannot_reach_browser():
    client = RuntimeClient()
    with patch.object(client, '_get_ok') as call:
        assert not client.activate_tab('../other')
    call.assert_not_called()
