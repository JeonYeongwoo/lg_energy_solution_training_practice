import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from app import create_app
from models import Item, db


class AppTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'test-key', 'SQLALCHEMY_DATABASE_URI': 'sqlite:///' + (root / 'test.db').as_posix(), 'UPLOAD_FOLDER': str(root / 'uploads')})
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp.cleanup()

    def post(self, path, data=None, client=None):
        client = client or self.client
        client.get('/')
        with client.session_transaction() as session:
            token = session['csrf_token']
        return client.post(path, data={**(data or {}), 'csrf_token': token}, follow_redirects=True)

    def test_full_workflow_and_permissions(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/items/new').status_code, 302)
        self.assertEqual(self.client.post('/register').status_code, 400)
        self.post('/register', {'username': 'owner', 'password': 'password123'})
        image = io.BytesIO()
        Image.new('RGB', (20, 20), 'green').save(image, 'PNG')
        image.seek(0)
        response = self.post('/items/new', {'title': '초록 의자', 'description': '원목 의자입니다', 'price': '12000', 'image': (image, 'chair.png')})
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            item = Item.query.one()
            item_id, filename = item.id, item.image_filename
        self.assertTrue((Path(self.app.config['UPLOAD_FOLDER']) / filename).exists())
        self.assertIn('초록 의자', self.client.get('/?q=원목').get_data(as_text=True))
        self.assertNotIn('초록 의자', self.client.get('/?free=1').get_data(as_text=True))
        other = self.app.test_client()
        self.post('/register', {'username': 'other', 'password': 'password123'}, client=other)
        self.assertEqual(other.get(f'/items/{item_id}/edit').status_code, 403)
        self.assertEqual(self.post(f'/items/{item_id}/delete', client=other).status_code, 403)
        self.assertEqual(self.post(f'/items/{item_id}/status', client=other).status_code, 403)
        self.post(f'/items/{item_id}/edit', {'title': '무료 의자', 'description': '나눔합니다', 'price': '500', 'free': 'on'})
        self.assertIn('무료 의자', self.client.get('/?free=1').get_data(as_text=True))
        self.post(f'/items/{item_id}/status')
        with self.app.app_context():
            self.assertEqual(db.session.get(Item, item_id).status, '거래완료')
            self.assertEqual(db.session.get(Item, item_id).price, 0)
        self.post(f'/items/{item_id}/status')
        self.post(f'/items/{item_id}/delete')
        self.assertEqual(self.client.get(f'/items/{item_id}').status_code, 404)
        self.assertFalse((Path(self.app.config['UPLOAD_FOLDER']) / filename).exists())
        self.post('/logout')
        self.assertEqual(self.client.get('/items/new').status_code, 302)
        self.post('/login', {'username': 'owner', 'password': 'password123'})
        self.assertEqual(self.client.get('/items/new').status_code, 200)

    def test_korean_image_filenames(self):
        self.post('/register', {'username': 'tester', 'password': 'password123'})
        for filename in ['아나바다_인형.png', '인형.PNG', '사진.jpg', '사진.webp']:
            with self.subTest(filename=filename):
                image = io.BytesIO()
                Image.new('RGB', (20, 20), 'green').save(image, 'PNG')
                image.seek(0)
                response = self.post('/items/new', {'title': filename, 'description': '사진 테스트', 'price': '0', 'image': (image, filename)})
                self.assertEqual(response.status_code, 200)
                with self.app.app_context():
                    item = Item.query.filter_by(title=filename).one()
                    self.assertTrue((Path(self.app.config['UPLOAD_FOLDER']) / item.image_filename).exists())

    def test_validation(self):
        self.post('/register', {'username': 'tester', 'password': 'password123'})
        response = self.post('/items/new', {'title': 'test', 'description': 'test', 'price': '-1'})
        self.assertIn('가격은', response.get_data(as_text=True))
        response = self.post('/items/new', {'title': 'test', 'description': 'test', 'price': '5', 'image': (io.BytesIO(b'not an image'), 'fake.jpg')})
        self.assertIn('읽을 수 없는', response.get_data(as_text=True))
        with self.app.app_context():
            self.assertEqual(Item.query.count(), 0)


if __name__ == '__main__':
    unittest.main()
