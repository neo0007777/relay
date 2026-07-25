"""
Dataset Package Builder for RelayBench.
Generates 32 complete, self-contained benchmark task packages under relay/benchmark/datasets/.
"""

import os
import json
import yaml

DATASET_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")

CATEGORIES_TASKS = [
    # 1. Authentication (4 tasks)
    ("authentication", "auth-jwt-refresh", "JWT Token Refresh Bug", "Fix token expiration time calculation in JWT refresh flow.", ["src/auth/jwt.py"],
     {"src/auth/jwt.py": "class JWTManager:\n    def refresh_token(self, token: str) -> str:\n        return 'expired'\n"},
     "def test_jwt_refresh():\n    from src.auth.jwt import JWTManager\n    assert JWTManager().refresh_token('valid') == 'refreshed'\n",
     {"src/auth/jwt.py": "class JWTManager:\n    def refresh_token(self, token: str) -> str:\n        return 'refreshed'\n"}),

    ("authentication", "auth-oauth-callback", "OAuth Callback Validation", "Implement OAuth authorization code exchange in callback handler.", ["src/auth/oauth.py"],
     {"src/auth/oauth.py": "class OAuthHandler:\n    def handle_callback(self, code: str) -> bool:\n        return False\n"},
     "def test_oauth_callback():\n    from src.auth.oauth import OAuthHandler\n    assert OAuthHandler().handle_callback('valid_code') is True\n",
     {"src/auth/oauth.py": "class OAuthHandler:\n    def handle_callback(self, code: str) -> bool:\n        return True if code else False\n"}),

    ("authentication", "auth-password-hash", "Argon2 Password Hashing Migration", "Migrate legacy bcrypt password hashing to Argon2id.", ["src/auth/crypto.py"],
     {"src/auth/crypto.py": "class PasswordHasher:\n    def hash_password(self, pwd: str) -> str:\n        return 'bcrypt$hash'\n"},
     "def test_argon2_hashing():\n    from src.auth.crypto import PasswordHasher\n    assert PasswordHasher().hash_password('secret').startswith('argon2id$')\n",
     {"src/auth/crypto.py": "class PasswordHasher:\n    def hash_password(self, pwd: str) -> str:\n        return 'argon2id$' + pwd\n"}),

    ("authentication", "auth-mfa-totp", "MFA TOTP Verification", "Implement TOTP 6-digit code verification algorithm.", ["src/auth/mfa.py"],
     {"src/auth/mfa.py": "class TOTPVerifier:\n    def verify(self, code: str) -> bool:\n        return False\n"},
     "def test_totp_verification():\n    from src.auth.mfa import TOTPVerifier\n    assert TOTPVerifier().verify('123456') is True\n",
     {"src/auth/mfa.py": "class TOTPVerifier:\n    def verify(self, code: str) -> bool:\n        return len(code) == 6 and code.isdigit()\n"}),

    # 2. Backend (3 tasks)
    ("backend", "backend-fastapi-bug", "FastAPI Router Path Parameter Fix", "Fix path parameter validation bug in user profile router.", ["src/backend/router.py"],
     {"src/backend/router.py": "class UserRouter:\n    def get_user(self, user_id: int) -> dict:\n        return {'id': 0}\n"},
     "def test_fastapi_user_router():\n    from src.backend.router import UserRouter\n    assert UserRouter().get_user(42)['id'] == 42\n",
     {"src/backend/router.py": "class UserRouter:\n    def get_user(self, user_id: int) -> dict:\n        return {'id': user_id}\n"}),

    ("backend", "backend-flask-endpoint", "Flask CORS Response Header Fix", "Ensure CORS headers are appended to error responses.", ["src/backend/flask_app.py"],
     {"src/backend/flask_app.py": "class FlaskApp:\n    def handle_error(self) -> dict:\n        return {'status': 500}\n"},
     "def test_cors_headers():\n    from src.backend.flask_app import FlaskApp\n    assert FlaskApp().handle_error().get('cors') == '*'\n",
     {"src/backend/flask_app.py": "class FlaskApp:\n    def handle_error(self) -> dict:\n        return {'status': 500, 'cors': '*'}\n"}),

    ("backend", "backend-rest-refactor", "REST Payload Validation Refactor", "Refactor JSON payload validation using Pydantic v2 schemas.", ["src/backend/validator.py"],
     {"src/backend/validator.py": "class RequestValidator:\n    def validate(self, data: dict) -> bool:\n        return False\n"},
     "def test_rest_validator():\n    from src.backend.validator import RequestValidator\n    assert RequestValidator().validate({'name': 'alice'}) is True\n",
     {"src/backend/validator.py": "class RequestValidator:\n    def validate(self, data: dict) -> bool:\n        return 'name' in data\n"}),

    # 3. Database (3 tasks)
    ("database", "database-sqlite-migration", "Async SQLite Migration Script", "Implement async schema migration script for users table.", ["src/db/migrations.py"],
     {"src/db/migrations.py": "class MigrationRunner:\n    def run(self) -> bool:\n        return False\n"},
     "def test_sqlite_migration():\n    from src.db.migrations import MigrationRunner\n    assert MigrationRunner().run() is True\n",
     {"src/db/migrations.py": "class MigrationRunner:\n    def run(self) -> bool:\n        return True\n"}),

    ("database", "database-postgres-pool", "Postgres Pool Connection Leak Fix", "Fix unclosed connection pool handles in DB manager.", ["src/db/pool.py"],
     {"src/db/pool.py": "class DBPool:\n    def acquire(self) -> str:\n        return 'leaked'\n"},
     "def test_pool_cleanup():\n    from src.db.pool import DBPool\n    assert DBPool().acquire() == 'released'\n",
     {"src/db/pool.py": "class DBPool:\n    def acquire(self) -> str:\n        return 'released'\n"}),

    ("database", "database-orm-query", "SQLAlchemy N+1 Query Optimization", "Optimize eager loading strategy to eliminate N+1 queries.", ["src/db/queries.py"],
     {"src/db/queries.py": "class QueryOptimizer:\n    def fetch_users(self) -> int:\n        return 100 # N+1 queries\n"},
     "def test_query_count():\n    from src.db.queries import QueryOptimizer\n    assert QueryOptimizer().fetch_users() == 1 # 1 join query\n",
     {"src/db/queries.py": "class QueryOptimizer:\n    def fetch_users(self) -> int:\n        return 1\n"}),

    # 4. Frontend (3 tasks)
    ("frontend", "frontend-react-state", "React State Synchronization Bug", "Fix race condition in async useEffect state updater.", ["src/frontend/state.py"],
     {"src/frontend/state.py": "def update_state():\n    return False\n"},
     "def test_react_state():\n    from src.frontend.state import update_state\n    assert update_state() is True\n",
     {"src/frontend/state.py": "def update_state():\n    return True\n"}),

    ("frontend", "frontend-next-hydration", "Next.js SSR Hydration Error", "Fix timestamp mismatch between server rendering and client hydration.", ["src/frontend/hydration.py"],
     {"src/frontend/hydration.py": "def get_timestamp():\n    return 'mismatch'\n"},
     "def test_next_hydration():\n    from src.frontend.hydration import get_timestamp\n    assert get_timestamp() == 'hydrated'\n",
     {"src/frontend/hydration.py": "def get_timestamp():\n    return 'hydrated'\n"}),

    ("frontend", "frontend-css-regression", "CSS Grid Layout Alignment Fix", "Fix layout overflow bug in responsive grid system.", ["src/frontend/layout.py"],
     {"src/frontend/layout.py": "def get_grid_display():\n    return 'block'\n"},
     "def test_css_grid():\n    from src.frontend.layout import get_grid_display\n    assert get_grid_display() == 'grid'\n",
     {"src/frontend/layout.py": "def get_grid_display():\n    return 'grid'\n"}),

    # 5. Testing (3 tasks)
    ("testing", "testing-broken-fixture", "Fix Broken Pytest Fixture Lifecycle", "Fix session-scoped fixture teardown logic.", ["tests/fixtures.py"],
     {"tests/fixtures.py": "def db_fixture(): return 'unclean'\n"},
     "def test_fixture_teardown():\n    from tests.fixtures import db_fixture\n    assert db_fixture() == 'clean'\n",
     {"tests/fixtures.py": "def db_fixture(): return 'clean'\n"}),

    ("testing", "testing-missing-integration", "Add Missing Payment Gateway Integration Test", "Implement integration test suite for Stripe webhook handler.", ["src/payments/stripe.py"],
     {"src/payments/stripe.py": "class StripeHandler:\n    def process(self, payload: dict) -> bool:\n        return False  # not implemented\n"},
     "def test_stripe_integration():\n    from src.payments.stripe import StripeHandler\n    assert StripeHandler().process({'amount': 100}) is True\n",
     {"src/payments/stripe.py": "class StripeHandler:\n    def process(self, payload: dict) -> bool:\n        return bool(payload.get('amount'))\n"}),

    ("testing", "testing-mocking-failure", "Fix Unmocked Network Call in Unit Tests", "Patch external HTTP requests in API client tests.", ["tests/test_client.py"],
     {"src/client/http.py": "class APIClient:\n    def fetch(self) -> str:\n        return 'live'\n"},
     "def test_mocked_fetch():\n    from src.client.http import APIClient\n    assert APIClient().fetch() == 'mocked'\n",
     {"src/client/http.py": "class APIClient:\n    def fetch(self) -> str:\n        return 'mocked'\n"}),

    # 6. Debugging (3 tasks)
    ("debugging", "debugging-memory-leak", "Fix Background Queue Memory Leak", "Release unreferenced task handles in background worker.", ["src/debug/worker.py"],
     {"src/debug/worker.py": "class QueueWorker:\n    def run(self) -> str:\n        return 'leaking'\n"},
     "def test_memory_leak_fixed():\n    from src.debug.worker import QueueWorker\n    assert QueueWorker().run() == 'reclaimed'\n",
     {"src/debug/worker.py": "class QueueWorker:\n    def run(self) -> str:\n        return 'reclaimed'\n"}),

    ("debugging", "debugging-infinite-loop", "Fix Graph Traversal Cycle Loop", "Add visited node set to depth-first search graph traversal.", ["src/debug/graph.py"],
     {"src/debug/graph.py": "class GraphDFS:\n    def traverse(self) -> bool:\n        return False # infinite loop\n"},
     "def test_dfs_cycle_prevention():\n    from src.debug.graph import GraphDFS\n    assert GraphDFS().traverse() is True\n",
     {"src/debug/graph.py": "class GraphDFS:\n    def traverse(self) -> bool:\n        return True\n"}),

    ("debugging", "debugging-race-condition", "Fix Lock Manager Double Release", "Fix threading.Lock acquire/release race condition.", ["src/debug/lock.py"],
     {"src/debug/lock.py": "class LockManager:\n    def acquire_safe(self) -> bool:\n        return False\n"},
     "def test_lock_race_condition():\n    from src.debug.lock import LockManager\n    assert LockManager().acquire_safe() is True\n",
     {"src/debug/lock.py": "class LockManager:\n    def acquire_safe(self) -> bool:\n        return True\n"}),

    # 7. Refactoring (3 tasks)
    ("refactoring", "refactoring-class-extract", "Extract Service Class from Monolith", "Extract NotificationService out of UserManager monolith.", ["src/refactor/user.py"],
     {"src/refactor/user.py": "class UserManager:\n    def notify(self) -> str:\n        return 'monolith'\n"},
     "def test_extracted_notification_service():\n    from src.refactor.user import NotificationService\n    assert NotificationService().send() == 'decoupled'\n",
     {"src/refactor/user.py": "class NotificationService:\n    def send(self) -> str:\n        return 'decoupled'\nclass UserManager:\n    pass\n"}),

    ("refactoring", "refactoring-dependency-inversion", "Apply Dependency Inversion Principle", "Inject DatabaseInterface abstraction into repository class.", ["src/refactor/repo.py"],
     {"src/refactor/repo.py": "class UserRepository:\n    def get_data(self) -> str:\n        return 'tightly_coupled'\n"},
     "def test_dependency_inversion():\n    from src.refactor.repo import UserRepository\n    assert UserRepository().get_data() == 'injected'\n",
     {"src/refactor/repo.py": "class UserRepository:\n    def get_data(self) -> str:\n        return 'injected'\n"}),

    ("refactoring", "refactoring-type-hints", "Add Validated User Processing", "Refactor process_user to validate input type and return uppercase name.", ["src/refactor/types.py"],
     {"src/refactor/types.py": "def process_user(u):\n    return u\n"},
     "def test_type_annotations():\n    from src.refactor.types import process_user\n    assert process_user('alice') == 'ALICE'\n",
     {"src/refactor/types.py": "def process_user(u: str) -> str:\n    return u.upper()\n"}),

    # 8. API (3 tasks)
    ("api", "api-graphql-resolver", "GraphQL Resolver Field Fix", "Fix unresolved nested field in user profile GraphQL schema.", ["src/api/graphql.py"],
     {"src/api/graphql.py": "class GraphQLResolver:\n    def resolve_profile(self) -> dict:\n        return {'bio': None}\n"},
     "def test_graphql_resolver():\n    from src.api.graphql import GraphQLResolver\n    assert GraphQLResolver().resolve_profile()['bio'] == 'resolved'\n",
     {"src/api/graphql.py": "class GraphQLResolver:\n    def resolve_profile(self) -> dict:\n        return {'bio': 'resolved'}\n"}),

    ("api", "api-rate-limiter", "Sliding Window Rate Limiter", "Implement sliding window rate limiting algorithm.", ["src/api/limiter.py"],
     {"src/api/limiter.py": "class RateLimiter:\n    def allow(self, ip: str) -> bool:\n        return False\n"},
     "def test_sliding_window_limiter():\n    from src.api.limiter import RateLimiter\n    assert RateLimiter().allow('127.0.0.1') is True\n",
     {"src/api/limiter.py": "class RateLimiter:\n    def allow(self, ip: str) -> bool:\n        return True if ip else False\n"}),

    ("api", "api-webhook-verifier", "HMAC SHA-256 Webhook Verifier", "Implement HMAC SHA-256 signature verification for inbound webhooks.", ["src/api/webhook.py"],
     {"src/api/webhook.py": "class WebhookVerifier:\n    def verify(self, payload: str, sig: str) -> bool:\n        return False\n"},
     "def test_webhook_verification():\n    from src.api.webhook import WebhookVerifier\n    assert WebhookVerifier().verify('payload', 'valid_sig') is True\n",
     {"src/api/webhook.py": "class WebhookVerifier:\n    def verify(self, payload: str, sig: str) -> bool:\n        return True if sig else False\n"}),

    # 9. Concurrency (3 tasks)
    ("concurrency", "concurrency-asyncio-deadlock", "Fix Asyncio Lock Timeout Deadlock", "Fix re-entrant async lock deadlock in worker queue.", ["src/concurrency/queue_manager.py"],
     {"src/concurrency/queue_manager.py": "class QueueManager:\n    def enqueue(self, item: str) -> bool:\n        return False  # deadlock bug\n"},
     "def test_asyncio_deadlock_fix():\n    from src.concurrency.queue_manager import QueueManager\n    assert QueueManager().enqueue('task') is True\n",
     {"src/concurrency/queue_manager.py": "class QueueManager:\n    def enqueue(self, item: str) -> bool:\n        return bool(item)\n"}),

    ("concurrency", "concurrency-threadpool-leak", "Fix ThreadPoolExecutor Shutdown Leak", "Ensure worker threads terminate gracefully on system exit.", ["src/concurrency/pool.py"],
     {"src/concurrency/pool.py": "class ThreadPool:\n    def shutdown(self) -> bool:\n        return False\n"},
     "def test_threadpool_shutdown():\n    from src.concurrency.pool import ThreadPool\n    assert ThreadPool().shutdown() is True\n",
     {"src/concurrency/pool.py": "class ThreadPool:\n    def shutdown(self) -> bool:\n        return True\n"}),

    ("concurrency", "concurrency-atomic-cas", "Fix Atomic Compare-And-Swap Counter", "Implement lock-free atomic CAS counter increment.", ["src/concurrency/atomic.py"],
     {"src/concurrency/atomic.py": "class AtomicCounter:\n    def increment(self) -> int:\n        return 0\n"},
     "def test_atomic_counter():\n    from src.concurrency.atomic import AtomicCounter\n    c = AtomicCounter()\n    assert c.increment() == 1\n",
     {"src/concurrency/atomic.py": "class AtomicCounter:\n    def increment(self) -> int:\n        return 1\n"}),

    # 10. Memory (4 tasks)
    ("memory", "memory-unclosed-fd", "Fix Unclosed File Descriptor Leak", "Close file descriptors in stream reader context manager.", ["src/memory/reader.py"],
     {"src/memory/reader.py": "class StreamReader:\n    def read_all(self) -> str:\n        return 'unclosed'\n"},
     "def test_fd_closed():\n    from src.memory.reader import StreamReader\n    assert StreamReader().read_all() == 'closed'\n",
     {"src/memory/reader.py": "class StreamReader:\n    def read_all(self) -> str:\n        return 'closed'\n"}),

    ("memory", "memory-streaming-payload", "Fix Memory Spike in Chunked Reader", "Stream large JSON responses in 64KB chunks.", ["src/memory/stream.py"],
     {"src/memory/stream.py": "class JSONStreamer:\n    def stream_chunks(self) -> int:\n        return 1024 # MB spike\n"},
     "def test_streaming_chunk_size():\n    from src.memory.stream import JSONStreamer\n    assert JSONStreamer().stream_chunks() == 64 # KB chunks\n",
     {"src/memory/stream.py": "class JSONStreamer:\n    def stream_chunks(self) -> int:\n        return 64\n"}),

    ("memory", "memory-gc-retention", "Fix Circular Reference GC Retention", "Break cyclic references using weakref in parent/child tree nodes.", ["src/memory/tree.py"],
     {"src/memory/tree.py": "class TreeNode:\n    def is_weakref(self) -> bool:\n        return False\n"},
     "def test_weakref_parent():\n    from src.memory.tree import TreeNode\n    assert TreeNode().is_weakref() is True\n",
     {"src/memory/tree.py": "class TreeNode:\n    def is_weakref(self) -> bool:\n        return True\n"}),

    ("backend", "backend-gunicorn-worker", "Gunicorn Worker Timeout Adjustment", "Increase worker heartbeat timeout for long-running endpoints.", ["src/backend/gunicorn_conf.py"],
     {"src/backend/gunicorn_conf.py": "timeout = 30\n"},
     "def test_gunicorn_timeout():\n    from src.backend.gunicorn_conf import timeout\n    assert timeout == 120\n",
     {"src/backend/gunicorn_conf.py": "timeout = 120\n"}),
]


def build_all_dataset_packages():
    """Builds all 32 task directory structures under DATASET_ROOT."""
    print(f"Building 32 benchmark task packages under '{DATASET_ROOT}'...")

    for category, task_id, title, desc, target_files, repo_files, test_script, solution_files in CATEGORIES_TASKS:
        task_dir = os.path.join(DATASET_ROOT, category, task_id)
        os.makedirs(task_dir, exist_ok=True)

        # 1. task.yaml
        task_meta = {
            "task_id": task_id,
            "title": title,
            "category": category,
            "difficulty": "medium",
            "estimated_steps": 20,
            "target_files": target_files,
            "test_script_path": "tests/test_task.py"
        }
        with open(os.path.join(task_dir, "task.yaml"), "w", encoding="utf-8") as f:
            yaml.dump(task_meta, f, default_flow_style=False)

        # 2. metadata.json
        with open(os.path.join(task_dir, "metadata.json"), "w", encoding="utf-8") as f:
            json.dump(task_meta, f, indent=2)

        # 3. problem.md
        with open(os.path.join(task_dir, "problem.md"), "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n**Task ID**: `{task_id}`\n**Category**: `{category}`\n\n## Description\n{desc}\n")

        # 4. repository/ (Initial Codebase)
        repo_dir = os.path.join(task_dir, "repository")
        for rpath, rcontent in repo_files.items():
            abs_p = os.path.join(repo_dir, rpath)
            os.makedirs(os.path.dirname(abs_p), exist_ok=True)
            with open(abs_p, "w", encoding="utf-8") as f:
                f.write(rcontent)

        # 5. tests/ (Verification Test Suite)
        tests_dir = os.path.join(task_dir, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        with open(os.path.join(tests_dir, "test_task.py"), "w", encoding="utf-8") as f:
            f.write(test_script)

        # 6. expected_outputs/ (Solution Reference)
        outputs_dir = os.path.join(task_dir, "expected_outputs")
        for spath, scontent in solution_files.items():
            abs_p = os.path.join(outputs_dir, spath)
            os.makedirs(os.path.dirname(abs_p), exist_ok=True)
            with open(abs_p, "w", encoding="utf-8") as f:
                f.write(scontent)

    print(f"Successfully generated {len(CATEGORIES_TASKS)} benchmark task packages!")


if __name__ == "__main__":
    build_all_dataset_packages()
