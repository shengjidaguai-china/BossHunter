import builtins
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from bosshunter import config as config_module
from bosshunter.web import server


class WebConfigApiTests(unittest.TestCase):
	def test_redacted_config_does_not_return_raw_api_key(self):
		config = {"ai": {"api_key": "test-api-key-12345678", "model": "claude"}}

		redacted = server._redact_config_for_response(config)

		self.assertNotIn("api_key", redacted["ai"])
		self.assertEqual(redacted["ai"]["api_key_masked"], "test***5678")
		self.assertEqual(config["ai"]["api_key"], "test-api-key-12345678")

	def test_config_download_payload_does_not_include_raw_credentials(self):
		payload = server._config_download_payload({
			"ai": {
				"api_key": "test-api-key-12345678",
				"auth_token": "auth-token-12345678",
				"model": "claude",
			}
		})

		self.assertNotIn("test-api-key-12345678", payload)
		self.assertNotIn("auth-token-12345678", payload)
		self.assertNotIn("api_key_masked", payload)
		self.assertNotIn("auth_token_masked", payload)

	def test_write_config_separates_credentials_without_leaving_temp_files(self):
		with tempfile.TemporaryDirectory() as tmp:
			config_path = Path(tmp) / "config.yaml"
			config_path.write_text("ai:\n  model: old\n", encoding="utf-8")
			api_key = "web-api-key-that-must-not-enter-config"

			with patch.object(server, "CONFIG_PATH", config_path):
				server._write_config({"ai": {"model": "new", "api_key": api_key}})

			public_text = config_path.read_text(encoding="utf-8")
			self.assertEqual(yaml.safe_load(public_text)["ai"]["model"], "new")
			self.assertNotIn(api_key, public_text)
			self.assertTrue((Path(tmp) / ".config.credentials.yaml").exists())
			self.assertEqual(list(Path(tmp).glob(".config.*.tmp")), [])

	def test_atomic_config_write_retries_windows_access_denied(self):
		with tempfile.TemporaryDirectory() as tmp:
			target = Path(tmp) / "config.yaml"
			real_replace = config_module.os.replace
			calls = []

			def flaky_replace(source, destination):
				calls.append((source, destination))
				if len(calls) == 1:
					exc = PermissionError(5, "access denied")
					exc.winerror = 5
					raise exc
				return real_replace(source, destination)

			with patch.object(config_module.os, "replace", side_effect=flaky_replace):
				with patch.object(config_module.time, "sleep") as sleep:
					config_module._write_yaml_atomic(target, {"ai": {"model": "new"}})

			self.assertEqual(len(calls), 2)
			self.assertEqual(yaml.safe_load(target.read_text(encoding="utf-8")), {"ai": {"model": "new"}})
			sleep.assert_called_once_with(0.05)

	def test_config_read_and_write_are_serialized(self):
		with tempfile.TemporaryDirectory() as tmp:
			target = Path(tmp) / "config.yaml"
			target.write_text("ai:\n  model: old\n", encoding="utf-8")
			reader_started = threading.Event()
			release_reader = threading.Event()
			writer_done = threading.Event()
			writer_errors = []

			def blocking_open(file, *args, **kwargs):
				if Path(file) == target:
					reader_started.set()
					release_reader.wait(timeout=2)
				return builtins.open(file, *args, **kwargs)

			def read_config():
				config_module._load_yaml_mapping(target)

			def write_config():
				try:
					config_module._write_yaml_atomic(target, {"ai": {"model": "new"}})
				except BaseException as exc:
					writer_errors.append(exc)
				finally:
					writer_done.set()

			with patch.object(config_module, "open", blocking_open, create=True):
				reader = threading.Thread(target=read_config)
				reader.start()
				self.assertTrue(reader_started.wait(timeout=2))
				writer = threading.Thread(target=write_config)
				writer.start()
				self.assertFalse(writer_done.wait(timeout=0.1))
				release_reader.set()
				reader.join(timeout=2)
				writer.join(timeout=2)

			self.assertFalse(reader.is_alive())
			self.assertFalse(writer.is_alive())
			self.assertEqual(writer_errors, [])
			self.assertEqual(yaml.safe_load(target.read_text(encoding="utf-8")), {"ai": {"model": "new"}})

	def test_sanitize_config_strips_display_fields_and_preserves_blank_key(self):
		with tempfile.TemporaryDirectory() as tmp:
			config_path = Path(tmp) / "config.yaml"
			config_path.write_text(
				yaml.dump({"ai": {"api_key": "test-api-key-12345678", "model": "old"}}, sort_keys=False),
				encoding="utf-8",
			)

			with patch.object(server, "CONFIG_PATH", config_path):
				cleaned = server._sanitize_config_for_write({
					"ai": {
						"api_key": "",
						"api_key_masked": "test***5678",
						"model": "new",
					}
				})

		self.assertEqual(cleaned["ai"]["api_key"], "test-api-key-12345678")
		self.assertEqual(cleaned["ai"]["model"], "new")
		self.assertNotIn("api_key_masked", cleaned["ai"])

	def test_sanitize_config_discards_retired_collection_count_fields_without_ai_section(self):
		cleaned = server._sanitize_config_for_write({
			"search": {"target_count": 9},
			"collection": {"default_target_count": 8, "daily_new_jobs_limit": 100},
			"platforms": {
				"boss": {"search": {"target_count": 7}},
				"zhilian": {"search": {"target_count": 6}},
				"51job": {"search": {"target_count": 5}},
			},
		})

		self.assertEqual(cleaned["search"], {})
		self.assertEqual(cleaned["collection"], {})
		for platform in ("boss", "zhilian", "51job"):
			self.assertEqual(cleaned["platforms"][platform]["search"], {})

	def test_sanitize_config_preserves_omitted_api_key(self):
		with tempfile.TemporaryDirectory() as tmp:
			config_path = Path(tmp) / "config.yaml"
			config_path.write_text(
				yaml.dump({"ai": {"api_key": "test-api-key-12345678", "model": "old"}}, sort_keys=False),
				encoding="utf-8",
			)

			with patch.object(server, "CONFIG_PATH", config_path):
				cleaned = server._sanitize_config_for_write({
					"ai": {
						"api_key_masked": "test***5678",
						"model": "new",
					}
				})

		self.assertEqual(cleaned["ai"]["api_key"], "test-api-key-12345678")
		self.assertEqual(cleaned["ai"]["model"], "new")
		self.assertNotIn("api_key_masked", cleaned["ai"])

	def test_sanitize_config_accepts_new_api_key(self):
		with tempfile.TemporaryDirectory() as tmp:
			config_path = Path(tmp) / "config.yaml"
			config_path.write_text(
				yaml.dump({"ai": {"api_key": "test-api-key-old", "model": "old"}}, sort_keys=False),
				encoding="utf-8",
			)

			with patch.object(server, "CONFIG_PATH", config_path):
				cleaned = server._sanitize_config_for_write({
					"ai": {
						"api_key": "test-api-key-new",
						"api_key_masked": "test***-old",
					}
				})

		self.assertEqual(cleaned["ai"]["api_key"], "test-api-key-new")
		self.assertNotIn("api_key_masked", cleaned["ai"])

	def test_sanitize_config_forces_fixed_anthropic_provider(self):
		# Arrange
		with tempfile.TemporaryDirectory() as tmp:
			config_path = Path(tmp) / "config.yaml"
			config_path.write_text(yaml.dump({"ai": {"provider": "anthropic"}}, sort_keys=False), encoding="utf-8")

			# Act
			with patch.object(server, "CONFIG_PATH", config_path):
				cleaned = server._sanitize_config_for_write({"ai": {"provider": "openai", "model": "claude-sonnet-4-6"}})

		# Assert
		self.assertEqual(cleaned["ai"]["provider"], "anthropic")
		self.assertEqual(cleaned["ai"]["model"], "claude-sonnet-4-6")

	def test_sanitize_config_maps_deepseek_service_and_clears_old_credentials(self):
		with tempfile.TemporaryDirectory() as tmp:
			config_path = Path(tmp) / "config.yaml"
			config_path.write_text(
				yaml.dump(
					{
						"ai": {
							"service": "anthropic",
							"provider": "anthropic",
							"api_key": "old-secret",
						}
					},
					sort_keys=False,
				),
				encoding="utf-8",
			)

			with patch.object(server, "CONFIG_PATH", config_path):
				cleaned = server._sanitize_config_for_write({
					"ai": {
						"service": "deepseek",
						"provider": "anthropic",
						"clear_credentials": True,
						"model": "provider-current-model",
					}
				})

		self.assertEqual(cleaned["ai"]["service"], "deepseek")
		self.assertEqual(cleaned["ai"]["provider"], "openai_compatible")
		self.assertNotIn("api_key", cleaned["ai"])
		self.assertNotIn("clear_credentials", cleaned["ai"])

	def test_sanitize_config_keeps_new_key_while_clearing_old_auth_token(self):
		with tempfile.TemporaryDirectory() as tmp:
			config_path = Path(tmp) / "config.yaml"
			config_path.write_text(
				yaml.dump(
					{
						"ai": {
							"service": "anthropic",
							"provider": "anthropic",
							"api_key": "old-secret",
							"auth_token": "old-auth-token",
						}
					},
					sort_keys=False,
				),
				encoding="utf-8",
			)

			with patch.object(server, "CONFIG_PATH", config_path):
				cleaned = server._sanitize_config_for_write({
					"ai": {
						"service": "deepseek",
						"clear_credentials": True,
						"api_key": "new-deepseek-secret",
					}
				})

		self.assertEqual(cleaned["ai"]["api_key"], "new-deepseek-secret")
		self.assertNotIn("auth_token", cleaned["ai"])

	def test_redacted_config_does_not_return_raw_auth_token(self):
		config = {"ai": {"auth_token": "auth-token-12345678", "model": "claude"}}

		redacted = server._redact_config_for_response(config)

		self.assertNotIn("auth_token", redacted["ai"])
		self.assertEqual(redacted["ai"]["auth_token_masked"], "auth***5678")
		self.assertEqual(config["ai"]["auth_token"], "auth-token-12345678")

	def test_sanitize_config_strips_auth_token_display_fields_and_preserves_blank_token(self):
		with tempfile.TemporaryDirectory() as tmp:
			config_path = Path(tmp) / "config.yaml"
			config_path.write_text(
				yaml.dump({"ai": {"auth_token": "auth-token-12345678", "model": "old"}}, sort_keys=False),
				encoding="utf-8",
			)

			with patch.object(server, "CONFIG_PATH", config_path):
				cleaned = server._sanitize_config_for_write({
					"ai": {
						"auth_token": "",
						"auth_token_masked": "auth***5678",
						"has_auth_token": True,
						"model": "new",
					}
				})

		self.assertEqual(cleaned["ai"]["auth_token"], "auth-token-12345678")
		self.assertEqual(cleaned["ai"]["model"], "new")
		self.assertNotIn("auth_token_masked", cleaned["ai"])
		self.assertNotIn("has_auth_token", cleaned["ai"])


if __name__ == "__main__":
	unittest.main()
