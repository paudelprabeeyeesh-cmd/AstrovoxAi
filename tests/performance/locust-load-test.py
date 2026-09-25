from locust import HttpUser, task, between
from locust import events
import json
import time


class AstrovoxUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        login_response = self.client.post('/api/auth/login', json={
            'email': 'loadtest@example.com',
            'password': 'test-password'
        })
        if login_response.status_code == 200:
            self.token = login_response.json().get('access_token')

    @task(3)
    def send_message(self):
        if not self.token:
            return
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        self.client.post('/api/chat/message', json={
            'conversation_id': f'load-test-{self.user_id}',
            'message': 'Load test message from Locust',
            'model': 'gpt-4'
        }, headers=headers)

    @task(1)
    def list_conversations(self):
        if not self.token:
            return
        headers = {'Authorization': f'Bearer {self.token}'}
        self.client.get('/api/conversations', headers=headers)

    @task(1)
    def health_check(self):
        self.client.get('/health')


class StressUser(HttpUser):
    wait_time = between(0.1, 0.5)
    token = None

    def on_start(self):
        login_response = self.client.post('/api/auth/login', json={
            'email': 'stresstest@example.com',
            'password': 'test-password'
        })
        if login_response.status_code == 200:
            self.token = login_response.json().get('access_token')

    @task(5)
    def spike_send_message(self):
        if not self.token:
            return
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        self.client.post('/api/chat/message', json={
            'conversation_id': f'stress-{self.user_id}',
            'message': 'Stress test message',
            'model': 'gpt-4'
        }, headers=headers)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    if exception:
        print(f'Request failed: {name} - {exception}')


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    print(f'Total requests: {environment.stats.total.num_requests}')
    print(f'Total failures: {environment.stats.total.num_failures}')
    print(f'Avg response time: {environment.stats.total.avg_response_time}ms')
