import importlib.util
import os
import pathlib
import tempfile
import unittest


class TestAPIRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        cls.temp_db.close()
        os.environ['Astravox_DB_PATH'] = cls.temp_db.name

        backend_root = pathlib.Path(__file__).resolve().parents[1]
        app_path = backend_root / 'server' / 'app.py'
        spec = importlib.util.spec_from_file_location('Astravox_app', str(app_path))
        module = importlib.util.module_from_spec(spec)
        assert spec.loader, 'Import loader not found'
        spec.loader.exec_module(module)
        cls.app = module.create_app()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        try:
            os.unlink(cls.temp_db.name)
        except OSError:
            pass

    def test_status_endpoint(self):
        response = self.client.get('/api/status')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get('status'), 'OK')
        self.assertIn('service', data)

    def test_register_login_usage_and_metrics(self):
        register_response = self.client.post(
            '/auth/register',
            json={
                'username': 'testuser',
                'email': 'testuser@example.com',
                'password': 'StrongPass123!'
            }
        )
        self.assertEqual(register_response.status_code, 201)
        register_data = register_response.get_json()
        self.assertEqual(register_data.get('status'), 'OK')
        self.assertIn('user', register_data)
        self.assertEqual(register_data['user']['username'], 'testuser')

        status_response = self.client.get('/auth/status')
        self.assertEqual(status_response.status_code, 200)
        status_data = status_response.get_json()
        self.assertTrue(status_data.get('authenticated'))

        usage_response = self.client.get('/api/usage')
        self.assertEqual(usage_response.status_code, 200)
        usage_data = usage_response.get_json()
        self.assertEqual(usage_data.get('status'), 'OK')
        self.assertIn('usage', usage_data)
        self.assertIn('summary', usage_data)

        metrics_response = self.client.get('/api/metrics')
        self.assertEqual(metrics_response.status_code, 200)
        metrics_data = metrics_response.get_json()
        self.assertEqual(metrics_data.get('status'), 'OK')
        self.assertIn('metrics', metrics_data)
        self.assertGreaterEqual(metrics_data['metrics'].get('total_users', 0), 1)
        self.assertGreaterEqual(metrics_data['metrics'].get('total_messages', 0), 0)
        self.assertGreaterEqual(metrics_data['metrics'].get('total_conversations', 0), 0)
        self.assertGreaterEqual(metrics_data['metrics'].get('active_users', 0), 1)


if __name__ == '__main__':
    unittest.main()
