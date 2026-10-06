import io
import os
import threading
from types import SimpleNamespace
from unittest.mock import patch
from pypdf import PdfWriter
import app

client = app.app.test_client()
assert client.get('/').status_code == 200
assert client.post('/translate').status_code == 400
pdf = io.BytesIO()
writer = PdfWriter()
writer.add_blank_page(width=300, height=300)
writer.write(pdf)
raw = pdf.getvalue()

def upload(name='보고서.pdf', direction='en-ko'):
    return client.post('/translate', data={'pdf': (io.BytesIO(raw), name), 'direction': direction})

with patch.dict(os.environ, {}, clear=True):
    assert upload().status_code == 503
with patch.dict(os.environ, {'OPENAI_API_KEY': 'mock-key'}):
    assert upload().status_code == 400
    assert upload(direction='invalid').status_code == 400

class FakeClient:
    def __init__(self, **kwargs): self.responses = self
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def create(self, **kwargs):
        assert kwargs['store'] is False
        return SimpleNamespace(status='completed', output_text='번역 결과')

with patch.dict(os.environ, {'OPENAI_API_KEY': 'mock-key'}), patch.object(app, 'OpenAI', FakeClient), patch('pypdf._page.PageObject.extract_text', return_value='hello ' * 1100):
    response = upload()
    assert response.status_code == 202, response.json
    job_id = response.json['job_id']
    events = client.get('/events/' + job_id).data.decode()
    assert events.count('event: translation') == 3
    assert 'event: complete' in events and '"progress": 100' in events
    resumed = client.get('/events/' + job_id, headers={'Last-Event-ID':'3'}).data.decode()
    assert 'event: translation' not in resumed and 'event: complete' in resumed
    download = client.get('/download/' + job_id)
    assert download.status_code == 200
    assert download.data.decode('utf-8-sig').count('번역 결과') == 3
    assert '%EB%B3%B4%EA%B3%A0%EC%84%9C.txt' in download.headers['Content-Disposition']

pending = dict(condition=threading.Condition(), events=[], finished=False, result=None)
app.jobs['pending'] = pending
assert client.get('/download/pending').status_code == 409
assert client.get('/download/unknown').status_code == 404
with patch.object(app, 'OpenAI', side_effect=RuntimeError('mock failure')), patch.object(app.app.logger, 'exception'):
    app.translate(dict(pending, direction='ko-en', chunks=['hello']), 'mock-key')
assert pending['events'][-1][0] == 'failure'
assert ''.join(app.chunks('a' * 10000)) == 'a' * 10000
print('PASS: upload validation, PDF extraction, 3-chunk SSE, resume, UTF-8 Korean filename download, unfinished/unknown jobs, API failure, chunk preservation')
