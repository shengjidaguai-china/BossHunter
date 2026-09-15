import tempfile
import unittest
from pathlib import Path


class JobOkResumeMigrationTests(unittest.TestCase):
    def test_recruiter_target_does_not_invent_client_company(self):
        from bosshunter.ai.resume import _resume_target_context

        company_line, instruction, direction = _resume_target_context(
            {
                "title": "AI 产品经理",
                "company": "某知名互联网公司",
                "jd": "猎头推荐至客户岗位",
            }
        )

        self.assertIn("客户公司未作为候选人事实提供", company_line)
        self.assertIn("不得出现", instruction)
        self.assertEqual(direction, "AI 产品经理")

    def test_job_ok_evidence_map_marks_unsupported_requirements(self):
        from bosshunter.ai.resume import _job_ok_evidence_map

        job = {
            "jd": "负责用户调研与需求分析；必须具备法语商务谈判经验。",
        }
        base_resume = "- 通过用户访谈完成需求调研，并协同研发推进产品迭代。\n"

        mapped = _job_ok_evidence_map(job, base_resume, base_resume)

        self.assertTrue(any(item["label"] != "needs_proof" for item in mapped))
        self.assertTrue(any(item["label"] == "needs_proof" for item in mapped))

    def test_job_ok_structure_normalizes_known_sections_without_deleting_content(self):
        from bosshunter.ai.resume import _normalize_job_ok_resume_structure

        original = """# 候选人

联系方式

## 相关技能

- Python

## 教育经历

- 某大学

## 项目经历

### Agent 项目

- 本地验证
"""

        normalized = _normalize_job_ok_resume_structure(original)

        self.assertLess(normalized.index("## 教育背景"), normalized.index("## 项目经历"))
        self.assertLess(normalized.index("## 项目经历"), normalized.index("## 技能"))
        self.assertIn("Agent 项目", normalized)
        self.assertIn("本地验证", normalized)

    def test_job_ok_currency_tracks_jd_and_master_resume(self):
        from bosshunter.ai.resume import _write_resume_metadata, is_job_ok_resume_current

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base_path = root / "base.md"
            output_path = root / "tailored.pdf"
            base_path.write_text("# 候选人\n\n真实经历。\n", encoding="utf-8")
            output_path.write_bytes(b"%PDF-test")
            job = {
                "id": "job-current",
                "status": "needs_resume",
                "jd": "负责产品设计",
                "resume_path": str(output_path),
            }
            config = {"profile": {"resume_path": str(base_path)}}

            self.assertFalse(is_job_ok_resume_current(job, config))
            _write_resume_metadata(output_path, job, base_path.read_text(encoding="utf-8"))
            self.assertTrue(is_job_ok_resume_current(job, config))
            job["jd"] = "负责不同的产品设计"
            self.assertFalse(is_job_ok_resume_current(job, config))


if __name__ == "__main__":
    unittest.main()
