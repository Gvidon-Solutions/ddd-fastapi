"""Codex executor tests."""

import asyncio
from pathlib import Path

import pytest

from app.infrastructure.codex import CodexCliExecutor

pytestmark = pytest.mark.anyio


class FakeStream:
    """Async stream backed by lines."""

    def __init__(self, lines: list[bytes]):
        self.lines = lines

    async def readline(self) -> bytes:
        """Return the next stream line."""
        if not self.lines:
            return b""
        return self.lines.pop(0)


class FakeStdin:
    """Writable fake process stdin."""

    def __init__(self) -> None:
        self.content = b""

    def write(self, content: bytes) -> None:
        """Write content."""
        self.content += content

    async def drain(self) -> None:
        """Drain content."""

    def close(self) -> None:
        """Close stdin."""

    async def wait_closed(self) -> None:
        """Wait until stdin is closed."""


class FakeProcess:
    """Fake subprocess."""

    def __init__(
        self,
        stdout_lines: list[bytes],
        stderr_lines: list[bytes] | None = None,
        return_code: int = 0,
        on_wait=None,
    ):
        self.stdout = FakeStream(stdout_lines)
        self.stderr = FakeStream(stderr_lines or [])
        self.stdin = FakeStdin()
        self.return_code = return_code
        self.returncode: int | None = None
        self.on_wait = on_wait

    async def wait(self) -> int:
        """Finish the process."""
        if self.on_wait is not None:
            self.on_wait()
        self.returncode = self.return_code
        return self.return_code


async def test_codex_executor_runs_codex_exec_with_help_documented_flags(
    tmp_path: Path,
) -> None:
    # Arrange
    captured: dict = {}

    async def process_factory(*args, **kwargs):
        output_path = Path(args[args.index("--output-last-message") + 1])

        def write_output() -> None:
            output_path.write_text("Codex result", encoding="utf-8")

        process = FakeProcess(
            stdout_lines=[b'{"type":"message","message":"running"}\n'],
            stderr_lines=[b"warning\n"],
            on_wait=write_output,
        )
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["process"] = process
        return process

    executor = CodexCliExecutor(
        codex_cli_path="codex",
        model="gpt-5.5",
        sandbox_mode="workspace-write",
        reasoning_effort="low",
        approval_policy="never",
        codex_home=tmp_path / ".codex_work_dir",
        process_factory=process_factory,
    )
    workdir = tmp_path / "workdir"

    # Act
    result = await executor.codex_exec(prompt="Review repository", workdir=workdir)

    # Assert
    assert result.return_code == 0
    assert result.output == "Codex result"
    assert result.stdout_lines == ['{"type":"message","message":"running"}']
    assert result.stderr_lines == ["warning"]
    assert captured["args"] == (
        "codex",
        "exec",
        "--json",
        "--strict-config",
        "--skip-git-repo-check",
        "--cd",
        str(workdir),
        "--model",
        "gpt-5.5",
        "--sandbox",
        "workspace-write",
        "--config",
        'model_reasoning_effort="low"',
        "--config",
        'approval_policy="never"',
        "--output-last-message",
        str(workdir / ".codex-output.txt"),
        "-",
    )
    assert captured["kwargs"]["cwd"] == workdir
    assert captured["kwargs"]["env"]["HOME"] == str(tmp_path / ".codex_work_dir")
    assert captured["process"].stdin.content == b"Review repository"


async def test_codex_executor_accepts_full_codex_exec_options(tmp_path: Path) -> None:
    # Arrange
    captured: dict = {}
    output_path = tmp_path / "last-message.txt"

    async def process_factory(*args, **kwargs):
        output_path.write_text("Review result", encoding="utf-8")
        process = FakeProcess(stdout_lines=[], stderr_lines=[])
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["process"] = process
        return process

    executor = CodexCliExecutor(
        codex_cli_path="codex",
        codex_home=tmp_path / ".codex_work_dir",
        process_factory=process_factory,
    )
    workdir = tmp_path / "repo"

    # Act
    result = await executor.codex_exec(
        workdir=workdir,
        command=["review"],
        images=[tmp_path / "screen.png"],
        model="gpt-5.4",
        sandbox_mode="danger-full-access",
        configs=["foo.bar=true"],
        enable=["experimental"],
        disable=["legacy"],
        profile="ci",
        oss=True,
        local_provider="ollama",
        add_dirs=[tmp_path / "extra"],
        ephemeral=True,
        ignore_user_config=True,
        ignore_rules=True,
        output_schema=tmp_path / "schema.json",
        color="never",
        dangerously_bypass_approvals_and_sandbox=True,
        dangerously_bypass_hook_trust=True,
        output_last_message_path=output_path,
        extra_options=["--unknown-future-flag"],
    )

    # Assert
    assert result.output == "Review result"
    assert output_path.read_text(encoding="utf-8") == "Review result"
    assert captured["args"] == (
        "codex",
        "exec",
        "--json",
        "--strict-config",
        "--skip-git-repo-check",
        "--cd",
        str(workdir),
        "--image",
        str(tmp_path / "screen.png"),
        "--model",
        "gpt-5.4",
        "--oss",
        "--local-provider",
        "ollama",
        "--profile",
        "ci",
        "--sandbox",
        "danger-full-access",
        "--dangerously-bypass-approvals-and-sandbox",
        "--dangerously-bypass-hook-trust",
        "--add-dir",
        str(tmp_path / "extra"),
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--output-schema",
        str(tmp_path / "schema.json"),
        "--color",
        "never",
        "--config",
        'model_reasoning_effort="low"',
        "--config",
        'approval_policy="never"',
        "--config",
        "foo.bar=true",
        "--enable",
        "experimental",
        "--disable",
        "legacy",
        "--output-last-message",
        str(output_path),
        "--unknown-future-flag",
        "review",
    )
    assert captured["process"].stdin.content == b""


async def test_codex_executor_streams_output_lines_to_handler(tmp_path: Path) -> None:
    # Arrange
    captured_lines = []

    async def process_factory(*_args, **_kwargs):
        return FakeProcess(
            stdout_lines=[b"stdout one\n", b"stdout two\n"],
            stderr_lines=[b"stderr one\n"],
        )

    async def output_handler(line) -> None:
        captured_lines.append(line)

    executor = CodexCliExecutor(
        codex_home=tmp_path / ".codex_work_dir",
        process_factory=process_factory,
    )

    # Act
    result = await executor.codex_exec(
        prompt="Review repository",
        workdir=tmp_path / "workdir",
        output_handler=output_handler,
    )

    # Assert
    assert result.stdout_lines == ["stdout one", "stdout two"]
    assert result.stderr_lines == ["stderr one"]
    assert [(line.channel, line.line_number, line.line) for line in captured_lines] == [
        ("stdout", 1, "stdout one"),
        ("stdout", 2, "stdout two"),
        ("stderr", 1, "stderr one"),
    ]


class BlockingFakeProcess(FakeProcess):
    """Fake subprocess that waits until released."""

    def __init__(self) -> None:
        super().__init__(stdout_lines=[], stderr_lines=[])
        self.wait_started = asyncio.Event()
        self.wait_finished = asyncio.Event()
        self.terminated = False
        self.killed = False

    async def wait(self) -> int:
        """Wait until the test releases the process."""
        self.wait_started.set()
        await self.wait_finished.wait()
        self.returncode = self.return_code
        return self.return_code

    def terminate(self) -> None:
        """Terminate the fake process."""
        self.terminated = True
        self.return_code = -15
        self.wait_finished.set()

    def kill(self) -> None:
        """Kill the fake process."""
        self.killed = True
        self.return_code = -9
        self.wait_finished.set()


async def test_codex_executor_rejects_parallel_execs(tmp_path: Path) -> None:
    # Arrange
    process = BlockingFakeProcess()

    async def process_factory(*_args, **_kwargs):
        return process

    executor = CodexCliExecutor(
        codex_home=tmp_path / ".codex_work_dir",
        process_factory=process_factory,
    )
    assert executor.is_running() is False
    running_task = asyncio.create_task(
        executor.codex_exec(prompt="first", workdir=tmp_path / "first"),
    )
    await process.wait_started.wait()
    assert executor.is_running() is True

    # Act / Assert
    with pytest.raises(RuntimeError, match="Codex exec is already running"):
        await executor.codex_exec(prompt="second", workdir=tmp_path / "second")

    process.wait_finished.set()
    await running_task
    assert executor.is_running() is False


async def test_codex_executor_cancel_terminates_running_process(tmp_path: Path) -> None:
    # Arrange
    process = BlockingFakeProcess()

    async def process_factory(*_args, **_kwargs):
        return process

    executor = CodexCliExecutor(
        codex_home=tmp_path / ".codex_work_dir",
        process_factory=process_factory,
    )
    assert executor.is_running() is False
    running_task = asyncio.create_task(
        executor.codex_exec(prompt="cancel me", workdir=tmp_path / "workdir"),
    )
    await process.wait_started.wait()
    assert executor.is_running() is True

    # Act
    cancelled = await executor.cancel()
    result = await running_task

    # Assert
    assert cancelled is True
    assert process.terminated is True
    assert process.killed is False
    assert result.return_code == -15
    assert executor.is_running() is False


async def test_codex_executor_cancel_returns_false_when_idle(tmp_path: Path) -> None:
    # Arrange
    executor = CodexCliExecutor(codex_home=tmp_path / ".codex_work_dir")

    # Act / Assert
    assert executor.is_running() is False
    assert await executor.cancel() is False
