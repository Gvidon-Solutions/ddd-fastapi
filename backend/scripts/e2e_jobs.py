#!/usr/bin/env python3
"""Run an end-to-end job smoke test through HTTP, PostgreSQL, Redis, and ARQ."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any

import httpx

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent


def main() -> int:
    """Run the e2e job flow."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="keep Docker containers")
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()

    postgres_port = free_port()
    redis_port = free_port()
    api_port = free_port()
    suffix = f"{os.getpid()}-{int(time.time())}"
    postgres_name = f"agentops-backend-kit-e2e-postgres-{suffix}"
    redis_name = f"agentops-backend-kit-e2e-redis-{suffix}"

    with tempfile.TemporaryDirectory(prefix="agentops-backend-kit-e2e-") as tmp:
        tmp_path = Path(tmp)
        fake_codex = write_fake_codex(tmp_path)
        env = e2e_env(
            postgres_port=postgres_port,
            redis_port=redis_port,
            fake_codex=fake_codex,
            tmp_path=tmp_path,
        )

        try:
            start_postgres(postgres_name, postgres_port)
            start_redis(redis_name, redis_port)
            wait_for_tcp("127.0.0.1", postgres_port, timeout=args.timeout)
            wait_for_postgres(postgres_name, timeout=args.timeout)
            wait_for_tcp("127.0.0.1", redis_port, timeout=args.timeout)
            init_database(env)

            with managed_process(
                "api",
                [
                    "uv",
                    "run",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                    "--log-level",
                    "warning",
                ],
                env=env,
                log_path=tmp_path / "api.log",
            ) as api:
                base_url = f"http://127.0.0.1:{api_port}/api/v1"
                wait_for_http(f"{base_url}/utils/health-check/", timeout=args.timeout)
                token = login(base_url)
                job_id = launch_codex_auth(base_url, token)
                pending_detail = get_job_detail(base_url, token, job_id)
                assert_status(pending_detail, "pending")

                with managed_process(
                    "worker",
                    ["uv", "run", "arq", "app.infrastructure.arq.worker.WorkerSettings"],
                    env=env,
                    log_path=tmp_path / "worker.log",
                ) as worker:
                    final_detail = wait_for_terminal_job(
                        base_url,
                        token,
                        job_id,
                        timeout=args.timeout,
                    )
                    assert_status(final_detail, "succeeded")
                    assert final_detail["result"] == {
                        "authenticated": True,
                        "error_message": None,
                    }
                    assert [event["type"] for event in final_detail["events"]] == [
                        "CodexAuthStartedV1",
                        "CodexAuthUserLoginRequestedV1",
                        "CodexAuthSucceededV1",
                    ]
                    jobs = list_jobs(base_url, token)
                    assert any(job["id"] == job_id for job in jobs["data"])

                    sys.stdout.write(
                        f"{json.dumps(
                            {
                                'job_id': job_id,
                                'initial_status': pending_detail['status'],
                                'final_status': final_detail['status'],
                                'events': [
                                    event['type'] for event in final_detail['events']
                                ],
                                'listed_jobs': jobs['count'],
                            },
                            indent=2,
                            sort_keys=True,
                        )}\n"
                    )

                    terminate(worker)
                terminate(api)
        except Exception:
            dump_logs(tmp_path)
            raise
        finally:
            if not args.keep:
                docker_rm(postgres_name)
                docker_rm(redis_name)

    return 0


def e2e_env(
    *,
    postgres_port: int,
    redis_port: int,
    fake_codex: Path,
    tmp_path: Path,
) -> dict[str, str]:
    """Return environment variables for all e2e processes."""
    env = os.environ.copy()
    env.update(
        {
            "ENVIRONMENT": "local",
            "SECRET_KEY": "e2e-secret-key",
            "POSTGRES_SERVER": "127.0.0.1",
            "POSTGRES_PORT": str(postgres_port),
            "POSTGRES_USER": "postgres",
            "POSTGRES_PASSWORD": "postgres",
            "POSTGRES_DB": "app",
            "REDIS_URL": f"redis://127.0.0.1:{redis_port}/0",
            "FIRST_SUPERUSER": "admin@example.com",
            "FIRST_SUPERUSER_PASSWORD": "changethis",
            "CODEX_CLI_PATH": str(fake_codex),
            "CODEX_JOB_WORKING_DIRECTORY": str(tmp_path / "codex-home"),
            "JOB_FILE_STORAGE_DIRECTORY": str(tmp_path / "files"),
            "ARQ_QUEUE_NAME": f"agentops-backend-kit-e2e-{os.getpid()}",
        }
    )
    return env


def start_postgres(name: str, port: int) -> None:
    """Start a disposable PostgreSQL container."""
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-e",
            "POSTGRES_PASSWORD=postgres",
            "-e",
            "POSTGRES_DB=app",
            "-p",
            f"{port}:5432",
            "postgres:16-alpine",
        ]
    )


def start_redis(name: str, port: int) -> None:
    """Start a disposable Redis container."""
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-p",
            f"{port}:6379",
            "redis:7-alpine",
        ]
    )


def init_database(env: dict[str, str]) -> None:
    """Create database tables and seed the superuser."""
    code = """
import asyncio
from sqlmodel.ext.asyncio.session import AsyncSession
from app.infrastructure.sqlmodel.database import SQLModel, engine, init_db

async def main():
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine) as session:
        await init_db(session)
        await session.commit()
    await engine.dispose()

asyncio.run(main())
"""
    run(["uv", "run", "python", "-c", code], cwd=BACKEND, env=env)


def login(base_url: str) -> str:
    """Login as the seeded superuser and return an access token."""
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            f"{base_url}/login/access-token",
            data={
                "username": "admin@example.com",
                "password": "changethis",
            },
        )
        response.raise_for_status()
        return str(response.json()["access_token"])


def launch_codex_auth(base_url: str, token: str) -> str:
    """Launch a Codex auth job through HTTP."""
    with httpx.Client(timeout=10.0) as client:
        response = client.post(
            f"{base_url}/codex/auth",
            headers=auth_header(token),
        )
        response.raise_for_status()
        return str(response.json()["job_id"])


def get_job_detail(base_url: str, token: str, job_id: str) -> dict[str, Any]:
    """Read one job through HTTP."""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            f"{base_url}/jobs/{job_id}",
            headers=auth_header(token),
        )
        response.raise_for_status()
        return dict(response.json())


def list_jobs(base_url: str, token: str) -> dict[str, Any]:
    """List current-user jobs through HTTP."""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            f"{base_url}/jobs/",
            headers=auth_header(token),
        )
        response.raise_for_status()
        return dict(response.json())


def wait_for_terminal_job(
    base_url: str,
    token: str,
    job_id: str,
    *,
    timeout: float,
) -> dict[str, Any]:
    """Poll job details until the job reaches a terminal status."""
    deadline = time.monotonic() + timeout
    last_detail: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        last_detail = get_job_detail(base_url, token, job_id)
        if last_detail["status"] in {"succeeded", "failed", "cancelled"}:
            return last_detail
        time.sleep(0.5)
    raise TimeoutError(f"Job did not reach a terminal state: {last_detail}")


def auth_header(token: str) -> dict[str, str]:
    """Return bearer auth headers."""
    return {"Authorization": f"Bearer {token}"}


def assert_status(detail: dict[str, Any], expected: str) -> None:
    """Assert a job status with a readable failure."""
    actual = detail["status"]
    if actual != expected:
        raise AssertionError(f"Expected job status {expected!r}, got {actual!r}: {detail}")


def write_fake_codex(tmp_path: Path) -> Path:
    """Create a fake Codex CLI executable for deterministic e2e auth."""
    path = tmp_path / "codex"
    path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import sys
            import time

            if sys.argv[1:] != ["login", "--device-auth"]:
                raise SystemExit(2)

            print("Open https://example.com/device", flush=True)
            print("code: ABCD-EFGH", flush=True)
            time.sleep(0.2)
            raise SystemExit(0)
            """
        )
    )
    path.chmod(0o755)
    return path


@contextmanager
def managed_process(
    label: str,
    command: list[str],
    *,
    env: dict[str, str],
    log_path: Path,
) -> Iterator[subprocess.Popen]:
    """Start and later stop a subprocess with captured logs."""
    with log_path.open("w") as log_file:
        process = subprocess.Popen(
            command,
            cwd=BACKEND,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )
    try:
        time.sleep(0.2)
        if process.poll() is not None:
            raise RuntimeError(f"{label} exited early with code {process.returncode}")
        yield process
    finally:
        terminate(process)


def terminate(process: subprocess.Popen) -> None:
    """Terminate a subprocess if it is still running."""
    if process.poll() is not None:
        return
    process.terminate()
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=5)
        return
    process.kill()
    process.wait(timeout=5)


def wait_for_http(url: str, *, timeout: float) -> None:
    """Wait until an HTTP endpoint responds successfully."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with suppress(httpx.HTTPError):
            response = httpx.get(url, timeout=2.0)
            if response.status_code < 500:
                return
        time.sleep(0.2)
    raise TimeoutError(f"HTTP endpoint did not become ready: {url}")


def wait_for_tcp(host: str, port: int, *, timeout: float) -> None:
    """Wait until a TCP port accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with suppress(OSError):
            with socket.create_connection((host, port), timeout=1):
                return
        time.sleep(0.2)
    raise TimeoutError(f"TCP endpoint did not become ready: {host}:{port}")


def wait_for_postgres(container_name: str, *, timeout: float) -> None:
    """Wait until PostgreSQL inside the container reports readiness."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            [
                "docker",
                "exec",
                container_name,
                "pg_isready",
                "-U",
                "postgres",
                "-d",
                "app",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(0.2)
    raise TimeoutError("PostgreSQL container did not become ready")


def free_port() -> int:
    """Return an available local port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
) -> None:
    """Run a command and raise on failure."""
    subprocess.run(command, cwd=cwd, env=env, check=True)


def docker_rm(name: str) -> None:
    """Remove a Docker container if it exists."""
    subprocess.run(
        ["docker", "rm", "-f", name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def dump_logs(tmp_path: Path) -> None:
    """Write captured process logs to stderr."""
    for log_path in sorted(tmp_path.glob("*.log")):
        sys.stderr.write(f"\n--- {log_path.name} ---\n")
        sys.stderr.write(f"{log_path.read_text(errors='replace')[-4000:]}\n")


if __name__ == "__main__":
    raise SystemExit(main())
