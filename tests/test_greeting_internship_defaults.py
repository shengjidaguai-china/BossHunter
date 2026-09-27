from unittest.mock import patch
import yaml
from bosshunter.config import load_config, save_config
from bosshunter.ai import greeter
from bosshunter.db import get_db, insert_job, update_job_status


def test_default_generation_skips_review_but_explicit_opt_in_survives(tmp_path):
    config = load_config(tmp_path / 'missing.yaml')
    assert config['ai']['greeting_style_suggestions'] is False
    path = tmp_path / 'jobs.db'
    db = get_db(path)
    insert_job(db, {'id': 'one', 'title': '运营', 'company': '示例', 'salary': '16-25K'})
    update_job_status(db, 'one', 'approved')
    db.close()
    with patch.object(greeter, '_get_resume_summary', return_value='真实简历'), patch.object(greeter, '_call_claude', return_value='您好，我做过内容运营。') as call:
        assert greeter.generate_greetings(config, ['one'], path) == 1
    assert call.call_count == 1
    config['ai']['greeting_style_suggestions'] = True
    save_config(config, tmp_path / 'config.yaml')
    assert load_config(tmp_path / 'config.yaml')['ai']['greeting_style_suggestions'] is True


def test_internship_disables_unknown_salary_filter_on_load_and_save(tmp_path):
    path = tmp_path / 'config.yaml'
    path.write_text('profile:\n  allow_internship: true\n  filter_unparsed_salary: true\n')
    config = load_config(path)
    assert config['profile']['filter_unparsed_salary'] is False
    config['profile']['filter_unparsed_salary'] = True
    save_config(config, path)
    assert yaml.safe_load(path.read_text())['profile']['filter_unparsed_salary'] is False
    assert config['profile']['filter_unparsed_salary'] is True  # save does not mutate caller
    save_config({'profile': {'allow_internship': False, 'filter_unparsed_salary': True}}, path)
    assert load_config(path)['profile']['filter_unparsed_salary'] is True
