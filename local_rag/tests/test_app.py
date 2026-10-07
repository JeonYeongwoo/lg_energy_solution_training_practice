import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module


class FakeRagService:
    instances = {}

    def __init__(self, session_id):
        self.session_id = session_id
        self.questions = []
        self.deleted = False
        self.__class__.instances[session_id] = self

    def add_pdfs(self, files):
        return len(files) * 3

    def stream_answer(self, question, history):
        self.questions.append((question, list(history)))
        return iter(("문서 ", f"답변: {question}")), []

    def delete_collection(self):
        self.deleted = True


class AppTestCase(unittest.TestCase):
    def setUp(self):
        FakeRagService.instances.clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.root = root
        self.patches = [
            patch.object(app_module, "RagService", FakeRagService),
            patch.object(app_module, "UPLOAD_DIR", root / "uploads"),
            patch.object(app_module, "CHROMA_DIR", root / "chroma"),
        ]
        for item in self.patches:
            item.start()
        flask_app = app_module.create_app({"TESTING": True, "SECRET_KEY": "test"})
        self.client = flask_app.test_client()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp_dir.cleanup()

    def test_rejects_non_pdf(self):
        response = self.client.post(
            "/api/upload",
            data={"files": (io.BytesIO(b"hello"), "notes.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "PDF 파일만 업로드할 수 있습니다.")

    def test_rejects_fake_pdf(self):
        response = self.client.post(
            "/api/upload",
            data={"files": (io.BytesIO(b"not-a-pdf"), "fake.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("올바른 PDF", response.get_json()["error"])
        self.assertEqual(list((self.root / "uploads").rglob("*.pdf")), [])

    def test_failed_batch_removes_all_uploaded_files(self):
        response = self.client.post(
            "/api/upload",
            data={"files": [
                (io.BytesIO(b"%PDF-valid"), "valid.pdf"),
                (io.BytesIO(b"invalid"), "invalid.pdf"),
            ]},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(list((self.root / "uploads").rglob("*.pdf")), [])
        self.assertFalse(FakeRagService.instances)

    def test_rejects_invalid_chat_payloads(self):
        for payload in (["question"], "question", 1, {"message": None}, {"message": []}):
            with self.subTest(payload=payload):
                response = self.client.post("/api/chat", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
        self.assertFalse(FakeRagService.instances)

    def test_upload_limit_returns_json(self):
        self.client.application.config["MAX_CONTENT_LENGTH"] = 100
        response = self.client.post(
            "/api/upload",
            data={"files": (io.BytesIO(b"%PDF-" + b"x" * 200), "large.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 413)
        self.assertIn("허용 용량", response.get_json()["error"])

    def test_multiple_uploads_and_conversation_history(self):
        response = self.client.post(
            "/api/upload",
            data={
                "files": [
                    (io.BytesIO(b"%PDF-one"), "one.pdf"),
                    (io.BytesIO(b"%PDF-two"), "two.PDF"),
                ]
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["chunks"], 6)
        first = self.client.post("/api/chat", json={"message": "첫 질문"})
        first_events = self.stream_events(first)
        self.assertEqual([event["event"] for event in first_events], ["token", "token", "done"])
        self.assertEqual("".join(event.get("text", "") for event in first_events), "문서 답변: 첫 질문")
        response = self.client.post("/api/chat", json={"message": "그 내용은?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/x-ndjson")
        self.stream_events(response)
        instance = next(iter(FakeRagService.instances.values()))
        _, history = instance.questions[-1]
        self.assertEqual(history[0]["content"], "첫 질문")
        self.assertEqual(history[1]["content"], "문서 답변: 첫 질문")

    def test_empty_question_and_reset(self):
        self.assertEqual(self.client.post("/api/chat", json={"message": "  "}).status_code, 400)
        self.client.post("/api/chat", json={"message": "질문"})
        instance = next(iter(FakeRagService.instances.values()))
        self.assertEqual(self.client.post("/api/reset").status_code, 200)
        self.assertTrue(instance.deleted)

    @staticmethod
    def stream_events(response):
        return [json.loads(line) for line in response.get_data(as_text=True).splitlines()]


if __name__ == "__main__":
    unittest.main()
