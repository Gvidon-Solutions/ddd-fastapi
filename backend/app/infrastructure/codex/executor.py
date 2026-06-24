"""Codex CLI executor implementation."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from app.config import settings
from app.usecase.job.codex import CodexExecResult, CodexExecutor


class CodexCliExecutor(CodexExecutor):
    """Execute Codex CLI commands."""

    def __init__(
        self,
        *,
        codex_cli_path: str = settings.CODEX_CLI_PATH,
        model: str = settings.CODEX_JOB_MODEL,
        sandbox_mode: str = settings.CODEX_JOB_SANDBOX_MODE,
        reasoning_effort: str = settings.CODEX_JOB_REASONING_EFFORT,
        approval_policy: str = settings.CODEX_JOB_APPROVAL_POLICY,
        codex_home: Path | str = settings.CODEX_JOB_WORKING_DIRECTORY,
        process_factory: Any = asyncio.create_subprocess_exec,
    ) -> None:
        """Store Codex process configuration."""
        self.codex_cli_path = codex_cli_path
        self.model = model
        self.sandbox_mode = sandbox_mode
        self.reasoning_effort = reasoning_effort
        self.approval_policy = approval_policy
        self.codex_home = Path(codex_home)
        self.process_factory = process_factory
        self._run_lock = asyncio.Lock()
        self._process: asyncio.subprocess.Process | None = None

    def is_running(self) -> bool:
        """Return whether this executor currently runs Codex exec."""
        process = self._process
        return self._run_lock.locked() and (
            process is None or process.returncode is None
        )

    async def cancel(self) -> bool:
        """Cancel the currently running Codex exec process."""
        process = self._process
        if process is None or process.returncode is not None:
            return False

        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.kill()
            await process.wait()
        return True

    async def codex_exec(
        self,
        *,
        prompt: str | None = None,
        stdin: str | None = None,
        workdir: Path | None = None,
        command: Sequence[str] = (),
        images: Sequence[Path | str] = (),
        model: str | None = None,
        sandbox_mode: str | None = None,
        configs: Sequence[str] = (),
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
        profile: str | None = None,
        oss: bool = False,
        local_provider: str | None = None,
        add_dirs: Sequence[Path | str] = (),
        ephemeral: bool = False,
        ignore_user_config: bool = False,
        ignore_rules: bool = False,
        output_schema: Path | str | None = None,
        color: Literal["always", "never", "auto"] | None = None,
        json_output: bool = True,
        strict_config: bool = True,
        skip_git_repo_check: bool = True,
        dangerously_bypass_approvals_and_sandbox: bool = False,
        dangerously_bypass_hook_trust: bool = False,
        output_last_message_path: Path | str | None = None,
        extra_options: Sequence[str] = (),
    ) -> CodexExecResult:
        """Run `codex exec` non-interactively in a workspace."""
        if self._run_lock.locked():
            raise RuntimeError("Codex exec is already running")

        async with self._run_lock:
            return await self._codex_exec(
                prompt=prompt,
                stdin=stdin,
                workdir=workdir,
                command=command,
                images=images,
                model=model,
                sandbox_mode=sandbox_mode,
                configs=configs,
                enable=enable,
                disable=disable,
                profile=profile,
                oss=oss,
                local_provider=local_provider,
                add_dirs=add_dirs,
                ephemeral=ephemeral,
                ignore_user_config=ignore_user_config,
                ignore_rules=ignore_rules,
                output_schema=output_schema,
                color=color,
                json_output=json_output,
                strict_config=strict_config,
                skip_git_repo_check=skip_git_repo_check,
                dangerously_bypass_approvals_and_sandbox=(
                    dangerously_bypass_approvals_and_sandbox
                ),
                dangerously_bypass_hook_trust=dangerously_bypass_hook_trust,
                output_last_message_path=output_last_message_path,
                extra_options=extra_options,
            )

    async def _codex_exec(
        self,
        *,
        prompt: str | None = None,
        stdin: str | None = None,
        workdir: Path | None = None,
        command: Sequence[str] = (),
        images: Sequence[Path | str] = (),
        model: str | None = None,
        sandbox_mode: str | None = None,
        configs: Sequence[str] = (),
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
        profile: str | None = None,
        oss: bool = False,
        local_provider: str | None = None,
        add_dirs: Sequence[Path | str] = (),
        ephemeral: bool = False,
        ignore_user_config: bool = False,
        ignore_rules: bool = False,
        output_schema: Path | str | None = None,
        color: Literal["always", "never", "auto"] | None = None,
        json_output: bool = True,
        strict_config: bool = True,
        skip_git_repo_check: bool = True,
        dangerously_bypass_approvals_and_sandbox: bool = False,
        dangerously_bypass_hook_trust: bool = False,
        output_last_message_path: Path | str | None = None,
        extra_options: Sequence[str] = (),
    ) -> CodexExecResult:
        """Run `codex exec` while the executor lock is held."""
        exec_workdir = workdir or Path.cwd()
        exec_workdir.mkdir(parents=True, exist_ok=True)
        owns_output_path = output_last_message_path is None
        output_path = (
            Path(output_last_message_path)
            if output_last_message_path is not None
            else exec_workdir / ".codex-output.txt"
        )
        input_text = stdin if stdin is not None else prompt
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        try:
            process = await self.process_factory(
                *self._codex_exec_args(
                    workdir=exec_workdir,
                    output_path=output_path,
                    command=command,
                    use_stdin=input_text is not None and not command,
                    images=images,
                    model=model,
                    sandbox_mode=sandbox_mode,
                    configs=configs,
                    enable=enable,
                    disable=disable,
                    profile=profile,
                    oss=oss,
                    local_provider=local_provider,
                    add_dirs=add_dirs,
                    ephemeral=ephemeral,
                    ignore_user_config=ignore_user_config,
                    ignore_rules=ignore_rules,
                    output_schema=output_schema,
                    color=color,
                    json_output=json_output,
                    strict_config=strict_config,
                    skip_git_repo_check=skip_git_repo_check,
                    dangerously_bypass_approvals_and_sandbox=(
                        dangerously_bypass_approvals_and_sandbox
                    ),
                    dangerously_bypass_hook_trust=dangerously_bypass_hook_trust,
                    extra_options=extra_options,
                ),
                cwd=exec_workdir,
                env=self._codex_env(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._process = process
            assert process.stdin is not None
            assert process.stdout is not None
            assert process.stderr is not None

            stdout_task = asyncio.create_task(
                self._read_lines(process.stdout, stdout_lines),
            )
            stderr_task = asyncio.create_task(
                self._read_lines(process.stderr, stderr_lines),
            )
            if input_text is not None:
                process.stdin.write(input_text.encode())
                await process.stdin.drain()
            process.stdin.close()
            await process.stdin.wait_closed()
            return_code = await process.wait()
            await stdout_task
            await stderr_task

            return CodexExecResult(
                return_code=return_code,
                output=self._read_codex_result(output_path, stdout_lines),
                stdout_lines=stdout_lines,
                stderr_lines=stderr_lines,
            )
        finally:
            self._process = None
            if owns_output_path:
                output_path.unlink(missing_ok=True)

    def _codex_exec_args(
        self,
        *,
        workdir: Path,
        output_path: Path,
        command: Sequence[str] = (),
        use_stdin: bool = True,
        images: Sequence[Path | str] = (),
        model: str | None = None,
        sandbox_mode: str | None = None,
        configs: Sequence[str] = (),
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
        profile: str | None = None,
        oss: bool = False,
        local_provider: str | None = None,
        add_dirs: Sequence[Path | str] = (),
        ephemeral: bool = False,
        ignore_user_config: bool = False,
        ignore_rules: bool = False,
        output_schema: Path | str | None = None,
        color: Literal["always", "never", "auto"] | None = None,
        json_output: bool = True,
        strict_config: bool = True,
        skip_git_repo_check: bool = True,
        dangerously_bypass_approvals_and_sandbox: bool = False,
        dangerously_bypass_hook_trust: bool = False,
        extra_options: Sequence[str] = (),
    ) -> list[str]:
        """Build `codex exec` args from the installed CLI help."""
        args = [self.codex_cli_path, "exec"]
        if json_output:
            args.append("--json")
        if strict_config:
            args.append("--strict-config")
        if skip_git_repo_check:
            args.append("--skip-git-repo-check")
        args.extend(["--cd", str(workdir)])

        for image in images:
            args.extend(["--image", str(image)])

        selected_model = model or self.model
        if selected_model:
            args.extend(["--model", selected_model])

        if oss:
            args.append("--oss")
        if local_provider is not None:
            args.extend(["--local-provider", local_provider])
        if profile is not None:
            args.extend(["--profile", profile])

        selected_sandbox_mode = sandbox_mode or self.sandbox_mode
        if selected_sandbox_mode:
            args.extend(["--sandbox", selected_sandbox_mode])

        if dangerously_bypass_approvals_and_sandbox:
            args.append("--dangerously-bypass-approvals-and-sandbox")
        if dangerously_bypass_hook_trust:
            args.append("--dangerously-bypass-hook-trust")

        for add_dir in add_dirs:
            args.extend(["--add-dir", str(add_dir)])
        if ephemeral:
            args.append("--ephemeral")
        if ignore_user_config:
            args.append("--ignore-user-config")
        if ignore_rules:
            args.append("--ignore-rules")
        if output_schema is not None:
            args.extend(["--output-schema", str(output_schema)])
        if color is not None:
            args.extend(["--color", color])

        args.extend(["--config", f'model_reasoning_effort="{self.reasoning_effort}"'])
        args.extend(["--config", f'approval_policy="{self.approval_policy}"'])
        for config in configs:
            args.extend(["--config", config])
        for feature in enable:
            args.extend(["--enable", feature])
        for feature in disable:
            args.extend(["--disable", feature])

        args.extend(["--output-last-message", str(output_path)])
        args.extend(extra_options)
        args.extend(command or (["-"] if use_stdin else []))
        return args

    def _codex_env(self) -> dict[str, str]:
        """Return environment variables for Codex subprocesses."""
        self.codex_home.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = str(self.codex_home)
        return env

    async def _read_lines(
        self,
        stream: asyncio.StreamReader,
        lines: list[str],
    ) -> None:
        """Read stream lines into a list."""
        while line := await stream.readline():
            decoded_line = line.decode(errors="replace").strip()
            if decoded_line:
                lines.append(decoded_line)

    def _read_codex_result(
        self,
        output_path: Path,
        stdout_lines: Sequence[str],
    ) -> str:
        """Read Codex output file with a stdout fallback."""
        if output_path.is_file():
            return output_path.read_text(encoding="utf-8").strip()
        return self._fallback_result(stdout_lines)

    def _fallback_result(self, stdout_lines: Sequence[str]) -> str:
        """Return a best-effort result from streamed stdout events."""
        for line in reversed(stdout_lines):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                if line:
                    return line
                continue
            if not isinstance(event, dict):
                continue
            for key in ("message", "text", "content"):
                value = event.get(key)
                if isinstance(value, str) and value:
                    return value
            item = event.get("item")
            if isinstance(item, dict):
                for key in ("message", "text", "content"):
                    value = item.get(key)
                    if isinstance(value, str) and value:
                        return value
        return ""


def new_codex_executor() -> CodexExecutor:
    """Create a Codex CLI executor."""
    return CodexCliExecutor()
