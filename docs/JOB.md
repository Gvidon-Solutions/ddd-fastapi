# Job Model

## Что есть сейчас

Сейчас джоба хранится как универсальная запись выполнения в таблице `job` и
мапится в доменную сущность `Job`.

Текущие поля `Job`:

- `job_id`: уникальный ID конкретного запуска.
- `job_type`: строка, которая одновременно играет роль типа джобы и фактически
  имени ARQ-функции при вызове `redis.enqueue_job(...)`.
- `job_name`: отображаемое имя.
- `job_description`: опциональное описание.
- `job_input`: сырой JSON/dict.
- `job_status`: общий статус жизненного цикла: `queued`, `running`,
  `succeeded`, `failed`, `cancelled`.
- `job_stage`: JSON-объект с текущей стадией, прогрессом или промежуточными
  данными.
- `result_summary`: сырой JSON/dict с итогом выполнения.
- `root_initiator`: JSON-объект инициатора.
- `parent_job_id`: опциональная связь с родительской джобой.
- `requested_at`, `updated_at`, `started_at`, `finished_at`: timestamps.
- `job_error`: JSON-объект ошибки для failed/cancelled состояний.

Текущий ARQ flow:

1. `LaunchJobUseCase` создает запись `Job` в БД.
2. `ArqJobQueue.enqueue(job_type, job_id)` отправляет задачу в ARQ.
3. В ARQ в качестве имени функции передается `job_type`.
4. В `WorkerSettings.functions` вручную перечислены функции воркера, например
   `execute_codex_auth_job_use_case` и `codex_run`.
5. ARQ-функция получает `job_id`, загружает джобу из БД и вызывает нужный use
   case.

Текущие контракты частично типизированы:

- Для `codex_auth` уже есть `CodexAuthJobResult` как dataclass, но в БД итог все
  равно сохраняется как `result_summary: dict`.
- `codex_run` читает `job.job_input` как свободный dict и возвращает dict.
- Для Codex-джоб есть dataclass-стадии, но они сохраняются в универсальное поле
  `job_stage`.

Главная проблема текущей модели: доменный тип джобы, имя ARQ-функции, input,
result, progress и initiator смешаны в слишком слабых JSON/string контрактах.

## Целевая модель

Джоба - это запуск версионированного контракта.

В доменной сущности `Job` должны быть:

- `id`: уникальный ID конкретного запуска.
- `type`: стабильный уникальный идентификатор типа джобы.
- `version`: версия контракта джобы.
- `name`: опциональное отображаемое имя конкретного запуска.
- `description`: опциональное описание конкретного запуска.
- `input`: экземпляр input dataclass для этого типа джобы.
- `result`: экземпляр result dataclass для этого типа джобы.
  Заполняется только при успешном выполнении.
- `status`: общий статус жизненного цикла.
- `initiator`: typed dataclass/value object инициатора.
- `parent_job_id`: опциональная связь с родительской джобой.
- timestamps.
- `error`: детали ошибки/отмены для неуспешных терминальных состояний.

`stage` в целевой модели не нужен и должен быть удален из `Job`.

`Job` является generic domain entity:

```python
InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")


@dataclass
class Job(Generic[InputT, ResultT]):
    id: UUID
    type: str
    version: str
    name: str | None
    description: str | None
    input: InputT
    result: ResultT | None
    status: JobStatus
    initiator: Initiator
    parent_job_id: UUID | None
    requested_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: JobError | None


AnyJob = Job[object, object]
```

Для заранее известного contract class код может работать с конкретным типом,
например `Job[CodexRunInputV1, CodexRunResultV1]`. Для generic read paths, где
contract заранее неизвестен, используется `AnyJob`.

## Implementation Strategy

Миграция к целевой модели выполняется как clean-break.

Перед применением новой модели система не сохраняет совместимость со старыми
`queued` / `running` jobs. Все non-terminal jobs старой схемы должны быть явно
завершены, отменены или удалены до миграции.

Исторические terminal jobs старой схемы на первом этапе удаляются вместе со
связанными job artifacts/events. Текущие job contracts пока не считаются
публичным durable API, поэтому best-effort migration старых rows не требуется.

Реализация делится на фазы:

1. Implementation Slice 1: typed executable jobs.
2. Typed event contracts, `event_registry` и `job_event` link-table.
3. `File` / `JobFile` extraction.
4. `Initiator` table extraction.

Implementation Slice 1 включает:

- `Job[InputT, ResultT]`;
- `JobContract`;
- первые контракты `codex.auth v1` и `codex.run v1`;
- strict dataclass JSON codec;
- domain `job_registry`;
- worker binding registry/decorator;
- новую `job` schema без `stage`;
- typed `Initiator` в домене; SQL extraction в отдельную `initiator` table
  остается follow-up миграцией;
- один `JobRepository` со strict typed `get(...)` и execution-specific lifecycle
  methods;
- `job_dispatch_outbox`;
- outbox dispatcher через `FOR UPDATE SKIP LOCKED`;
- atomic lifecycle transitions;
- `JobLauncher`;
- `JobCancellationBackend`;
- `CodexAuthSession` в Redis вместо `job_stage`;
- read-only projection/query repository для UI/history.

Следующие части являются отдельными follow-up миграциями:

- typed event contracts, `event_registry` и `job_event` link-table;
- `File` / `JobFile` extraction;
- `Initiator` table extraction;
- full deletion semantics with orphan cleanup;
- user deletion cleanup.

Follow-up миграции не должны блокировать первый шаг typed executable jobs. Они
накладываются поверх уже стабилизированной модели `Job`.

## Type

`type` - это уникальный идентификатор логического контракта джобы.

Требования:

- стабильный при рефакторинге Python-кода;
- однозначно описывает use case, который имплементирует эту job;
- содержит имя, по которому понятно, какой domain/application use case ее
  исполняет;
- не зависит от имени ARQ-функции.

Формат:

```text
<bounded-context>.<use-case-name>
```

Примеры:

```text
codex.auth
codex.run
```

`type` задается через стабильное имя use case, а не через физическое имя
Python-функции, class import path или ARQ handler. Use case может быть
переименован/перенесен в коде без смены `type`, если его доменный смысл и
input/result contract остаются теми же.

Для каждой executable job должен быть один application/domain use case, который
имплементирует выполнение этой job contract version.

Версия хранится отдельно:

```text
type = "codex.run"
version = "v1"
```

Если меняется input/result контракт несовместимым образом, `type` остается тем
же, если доменный смысл джобы не изменился, а `version` увеличивается.

Полная идентичность контракта - это пара `(type, version)`.

## Version

`version` описывает версию контракта конкретного запуска.

Формат version: строка вида `v<N>`, например `v1`, `v2`.

Версия определяет:

- как десериализуется `job_input`;
- какой result dataclass ожидается;
- как читать старые сохраненные джобы;
- какой worker-handler имеет право исполнять эту джобу.

## Контракты Джоб

Для каждого типа джобы нужно определять отдельный контракт.

Для каждой пары `(type, version)` должны быть:

- contract class джобы;
- frozen dataclass для input;
- frozen dataclass для result успешного выполнения;
- handler/use case, который принимает input dataclass и возвращает result
  dataclass;
- зарегистрированная сериализация/десериализация для хранения в БД.

Пример:

```python
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Generic, Literal, TypeVar
from uuid import UUID, uuid4


InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")


class JobContract(Generic[InputT, ResultT]):
    type: str
    version: str
    input: type[InputT]
    result: type[ResultT]

    @classmethod
    def new(
        cls,
        *,
        initiator: Initiator,
        input: InputT,
        name: str | None = None,
        description: str | None = None,
        parent_job_id: UUID | None = None,
    ) -> Job[InputT, ResultT]:
        if not isinstance(input, cls.input):
            raise TypeError(
                f"{cls.type} {cls.version} requires {cls.input.__name__}"
            )

        now = datetime.now(UTC)
        return Job(
            id=uuid4(),
            type=cls.type,
            version=cls.version,
            name=name,
            description=description,
            input=input,
            result=None,
            status=JobStatus.QUEUED,
            initiator=initiator,
            parent_job_id=parent_job_id,
            requested_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
            error=None,
        )


@dataclass(frozen=True)
class CodexRunInputV1:
    prompt: str
    workdir: str | None = None


@dataclass(frozen=True)
class CodexRunResultV1:
    log_artifacts: int
    generated_artifacts: int


class CodexRunJobV1(JobContract[CodexRunInputV1, CodexRunResultV1]):
    type: Literal["codex.run"] = "codex.run"
    version: Literal["v1"] = "v1"
    input = CodexRunInputV1
    result = CodexRunResultV1
```

`job_input` не должен использоваться в домене/use case как ad hoc dict. В БД он
может храниться как JSON, но через границу persistence должен проходить как
типизированный dataclass.

`input` не nullable. Даже если job не требует параметров, для нее определяется
пустой frozen dataclass input contract:

```python
@dataclass(frozen=True)
class CodexAuthInputV1:
    pass
```

В доменной модели `Job.input` всегда содержит typed object. Use case не должен
получать `None` и не должен интерпретировать отсутствие input как особый режим.

`job_result` содержит только результат успешного выполнения. В него не должны
попадать:

- ошибка;
- причина отмены;
- текущий прогресс;
- промежуточные данные;
- stage/state конкретной реализации.

Ошибки и отмены хранятся в `job_error`, а не в `job_result`.

## Job Error

`job_error` должен быть typed value object, а не ad hoc dict.

На первом этапе error contract общий для всех job types и не версионируется на
уровне `(type, version)`.

Рекомендуемая форма:

```python
@dataclass(frozen=True)
class JobError:
    code: str
    message: str
    details: dict[str, JSONValue]
    retryable: bool = False
```

`JobError` используется для:

- `failed`;
- `cancelled`;
- infrastructure failures вроде `queue_enqueue_failed`;
- worker binding failures вроде `worker_binding_missing`;
- validation/serialization failures вроде `invalid_job_input`.

`result` остается typed successful result contract. Error не является частью
result contract.

Если конкретной job позже понадобится rich domain failure model, она должна
публиковаться typed event-ом или помещаться в structured `details`, но terminal
lifecycle по-прежнему использует общий `JobError`.

## Job Contract Serialization

Input/result contracts остаются frozen dataclasses.

Для перехода через persistence boundary нужен единый strict dataclass JSON
codec. Нельзя полагаться на обычный dataclass constructor как на validation:
он не проверяет runtime-типы.

Codec responsibilities:

- сериализовать dataclass input/result в JSON-compatible dict;
- десериализовать JSON-compatible dict обратно в registered dataclass type;
- поддерживать nested dataclasses;
- поддерживать enums;
- поддерживать `UUID`;
- поддерживать `datetime`;
- поддерживать `list`, `dict`, `tuple` если они явно указаны в type hints;
- поддерживать `T | None` / optional fields;
- уважать dataclass defaults и `default_factory`;
- запрещать unknown fields;
- запрещать missing required fields;
- запрещать wrong runtime types.

Ошибки:

- если persisted `input` не десериализуется при execution, worker переводит job в
  `failed` с `JobError(code="invalid_job_input")`;
- если handler вернул object не того result dataclass type, worker переводит job
  в `failed` с `JobError(code="invalid_job_result")`;
- если result не сериализуется перед сохранением, worker переводит job в
  `failed` с `JobError(code="job_result_serialization_failed")`;
- если persisted `result` не десериализуется при read, repository бросает
  `JobSerializationError`, потому что durable data corrupted.

Pydantic models для job contracts на первом этапе не используются, чтобы не
смешивать domain dataclasses с presentation/infrastructure validation models.

## Job Registry

`job_registry` должен жить на уровне domain layer.

Он хранит соответствие `(type, version) -> JobContract class` и является
единственным источником знания о том, какой typed input/result соответствует
сохраненной job.

Registry responsibilities:

- зарегистрировать все `JobContract` classes;
- запретить duplicate registration для одной пары `(type, version)`;
- вернуть contract class по `(type, version)`;
- дать infrastructure слою input/result dataclass types для восстановления
  доменного `Job`;
- дать ARQ/decorator слою возможность связать contract class с worker function.

Пример:

```python
job_registry.register(CodexRunJobV1)

contract = job_registry.get(
    type="codex.run",
    version="v1",
)

assert contract.input is CodexRunInputV1
assert contract.result is CodexRunResultV1
```

`JobRepository` при чтении из БД должен возвращать уже готовый доменный `Job`, а
не `Job` с raw dict input/result.

Flow восстановления job из persistence:

1. Repository читает row из `job`.
2. Repository берет `type` и `version` из row.
3. Repository запрашивает contract в domain `job_registry`.
4. Repository десериализует `input` в `contract.input`.
5. Если `result` не `null`, repository десериализует `result` в
   `contract.result`.
6. Repository возвращает доменный `Job` с typed `input` и typed `result`.

Концептуально:

```python
contract = job_registry.get(type=record.type, version=record.version)

input_obj = deserialize(record.input, contract.input)
result_obj = (
    deserialize(record.result, contract.result)
    if record.result is not None
    else None
)

return Job(
    id=record.job_id,
    type=record.type,
    version=record.version,
    input=input_obj,
    result=result_obj,
    ...
)
```

Repository не должен знать про `CodexRunInputV1` или другие конкретные job
contracts напрямую. Он знает только `job_registry`.

Сам registry не обязан хранить JSON-specific логику. JSON serialization может
оставаться infrastructure detail. Важно, что mapping `(type, version) ->
input/result dataclass types` живет в domain registry.

`JobRepository` остается одним domain port. Он содержит и strict typed read
methods, и execution-specific methods. Worker execution path не должен начинаться
с `JobRepository.get(job_id)`, потому что `get(...)` десериализует input/result и
может упасть до lifecycle transition.

Worker execution path использует методы того же `JobRepository`, которые не
десериализуют input/result до atomic status transition:

```python
@dataclass(frozen=True)
class JobExecutionRecord:
    job_id: UUID
    type: str
    version: str
    input: dict
    status: JobStatus


class JobRepository:
    async def get(self, job_id: UUID) -> AnyJob: ...

    async def try_mark_running(
        self,
        job_id: UUID,
        *,
        started_at: datetime,
    ) -> bool: ...

    async def get_execution_record(
        self,
        job_id: UUID,
    ) -> JobExecutionRecord: ...

    async def try_mark_succeeded(...): ...
    async def try_mark_failed(...): ...
    async def try_mark_cancelled(...): ...
```

Worker flow:

1. Получить `job_id` из queue message.
2. Выполнить atomic `queued -> running` через `try_mark_running(...)`.
3. Если transition не прошел, завершиться no-op.
4. Прочитать raw `JobExecutionRecord`.
5. Resolve `(type, version)` через `job_registry`.
6. Десериализовать `input` в registered input dataclass.
7. Если input invalid, записать `running -> failed` с
   `JobError(code="invalid_job_input")`.
8. Выполнить handler/use case.
9. Проверить и сериализовать result.
10. Записать terminal status через atomic terminal transition.

### Unknown Job Contracts

`JobRepository.get(job_id)` и другие методы, которые возвращают полноценный
доменный `Job`, должны быть строгими.

Если в БД лежит job с `(type, version)`, которого нет в `job_registry`,
repository не должен возвращать raw fallback с dict input/result и не должен
угадывать контракт. В этом случае repository бросает доменное исключение,
например `UnknownJobContractError`.

Причины:

- typed boundary остается настоящей границей, а не best-effort mapping;
- неизвестный контракт нельзя безопасно выполнить worker-ом;
- caller явно видит несовместимость сохраненных данных и текущего кода.

User-facing read APIs, которым нужно показать список исторических jobs, не
должны использовать strict `JobRepository`, если им не нужен полноценный typed
`Job`. Для этого вводится отдельный read/query repository.

`JobRepository`:

- используется execution/use cases, которым нужен полноценный typed `Job`;
- strict;
- unknown contract -> `UnknownJobContractError`;
- corrupted input/result -> `JobSerializationError`.

`JobQueryRepository` / `JobProjectionRepository`:

- используется user-facing read APIs, history/list/admin screens;
- не десериализует input/result в typed contracts;
- возвращает lightweight projection из SQL columns;
- может показывать unknown `(type, version)` как данные, а не как ошибку.

Пример projection:

```python
@dataclass(frozen=True)
class JobSummary:
    job_id: UUID
    type: str
    version: str
    name: str | None
    status: JobStatus
    initiator: InitiatorSummary
    requested_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error: JobError | None
```

Для detail screen можно иметь raw-safe projection:

```python
@dataclass(frozen=True)
class JobDetailProjection:
    summary: JobSummary
    input: dict | None
    result: dict | None
    contract_known: bool
    serialization_error: str | None
```

Execution paths must not use projections. Read-only user-facing APIs must not
use strict `JobRepository` unless they really need typed input/result.

`JobRepository.delete(job_id)` не должен требовать registered contract и не
должен десериализовать typed input/result. Delete path работает по SQL rows,
`job_file`, `job_event`, orphan file/event checks и physical file cleanup. Это
позволяет удалить job даже тогда, когда ее `(type, version)` больше не
поддерживается текущим кодом.

## Status

Статусы остаются общими и не зависят от типа джобы:

- `queued`: джоба создана и ожидает выполнения.
- `running`: handler начал выполнение.
- `succeeded`: handler завершился успешно, `job_result` заполнен.
- `failed`: выполнение завершилось ошибкой, `job_error` заполнен.
- `cancelled`: выполнение отменено, `job_error` содержит детали отмены.

Инварианты:

- `status == succeeded`: `job_result is not None`, `job_error is None`.
- `status in {failed, cancelled}`: `job_result is None`,
  `job_error is not None`.
- `status in {queued, running}`: `job_result is None`.

Допустимые переходы:

```text
queued -> running       worker начал выполнение
queued -> failed        launch/enqueue failure после commit или worker binding missing
queued -> cancelled     job отменена до старта worker-а

running -> succeeded    handler завершился и вернул valid result
running -> failed       handler/infrastructure/serialization failure
running -> cancelled    worker обработал cancel
```

Terminal statuses immutable:

```text
succeeded -> terminal
failed -> terminal
cancelled -> terminal
```

Запрещенные переходы:

```text
queued -> succeeded
running -> queued
succeeded -> failed
succeeded -> running
failed -> running
cancelled -> running
cancelled -> succeeded
```

`running -> running` не используется как progress update. Progress,
checkpoint-ы и intermediate state пишутся в events или read models.

Отдельный статус `cancelling` / `cancel_requested` на первом этапе не вводится.
Для running job durable status становится `cancelled` только после того, как
worker реально обработал отмену. Timeout `wait(...)` не является отменой job.

Execution boundary должен проверять текущий status перед изменениями. Если ARQ
retry или duplicate execution пришел для terminal job, worker не должен
перезаписывать terminal status/result/error.

### Retry And Duplicate Execution

Job execution должен быть guarded by atomic status transition.

Worker не должен начинать handler обычным `get -> mutate -> save`. Перед
выполнением handler-а он должен атомарно перевести job:

```text
queued -> running
```

только если текущий status все еще `queued`.

SQL-level shape:

```sql
update job
set status = 'running', started_at = now(), updated_at = now()
where job_id = :job_id
  and status = 'queued'
returning job_id;
```

Если updated row count равен `1`, этот worker получил право выполнять handler.

Если updated row count равен `0`, worker не выполняет handler:

- `running`: другой worker уже выполняет эту job;
- `succeeded`: job уже успешно завершена;
- `failed`: job уже завершена ошибкой;
- `cancelled`: job уже отменена.

Такой duplicate execution должен завершиться как no-op и не должен создавать
новые files/events/result.

Terminal transitions тоже должны быть guarded. First terminal write wins
реализуется не через обычный `get -> mutate -> save`, а через atomic repository
methods:

```python
class JobRepository:
    async def try_mark_running(
        self,
        job_id: UUID,
        *,
        started_at: datetime,
    ) -> bool: ...

    async def try_mark_succeeded(
        self,
        job_id: UUID,
        *,
        result: object,
        finished_at: datetime,
    ) -> bool: ...

    async def try_mark_failed(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool: ...

    async def try_mark_cancelled(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool: ...
```

SQL-level shape для terminal updates:

```sql
update job
set status = 'succeeded',
    result = :result,
    error = null,
    finished_at = :now,
    updated_at = :now
where job_id = :job_id
  and status = 'running'
returning job_id;

update job
set status = 'failed',
    result = null,
    error = :error,
    finished_at = :now,
    updated_at = :now
where job_id = :job_id
  and status = 'running'
returning job_id;

update job
set status = 'cancelled',
    result = null,
    error = :error,
    finished_at = :now,
    updated_at = :now
where job_id = :job_id
  and status = 'running'
returning job_id;
```

Если terminal update вернул `0` rows, worker не переписывает job и завершает
обработку как no-op / late result. Обычный `save(job)` не используется для
lifecycle transitions worker-а; его можно оставить только для metadata-only
операций вне execution path.

ARQ retries не используются как доменный retry mechanism для execution jobs.
Если handler упал, worker переводит job:

```text
running -> failed
```

и сохраняет `job.error`. Повторная доставка той же ARQ task увидит terminal
`failed` и выйдет без повторного выполнения handler-а.

Автоматический перезапуск terminal `failed` job запрещен. Если позже понадобится
user-visible retry, он должен быть отдельным use case, который создает новую job
с тем же input или явно связанную retry job через `parent_job_id`.

### Cancellation Semantics

`cancelled` означает, что job больше не должна выполняться и завершилась
отменой. Причина отмены хранится в `job.error`, а не в `job.result`.

Отмена queued job:

- выполняется как `queued -> cancelled`;
- system best-effort вызывает queue backend cancel/abort, если task уже была
  поставлена в очередь;
- если ARQ позже доставит эту task worker-у, atomic `queued -> running` не
  пройдет, потому что job уже `cancelled`, и worker выйдет no-op.

Отмена running job:

- отдельный durable статус `cancelling` не вводится;
- cancel use case не меняет SQL `job.status`;
- cancel use case пишет cancel request через `JobCancellationBackend`;
- worker/handler периодически проверяет cancel request;
- worker отвечает за фактическую остановку handler-а;
- durable transition `running -> cancelled` выполняет worker после того, как
  handler действительно остановлен или cancellation exception обработан.

Cancellation backend contract:

```python
class JobCancellationBackend:
    async def request_cancel(self, job_id: UUID) -> None: ...
    async def is_cancel_requested(self, job_id: UUID) -> bool: ...
    async def clear_cancel_request(self, job_id: UUID) -> None: ...
```

Первая implementation uses Redis:

```text
job_cancel_requested:{job_id}
```

Redis key получает TTL, например 24 часа или до terminal cleanup. Worker очищает
cancel request best-effort после terminal transition.

Timeout `wait(...)` не является отменой. Если caller перестал ждать, running job
может продолжать выполняться.

Если cancel пришел одновременно с success/failure, применяется first terminal
write wins:

- если worker уже записал `succeeded` или `failed`, cancel не переписывает
  terminal status;
- если cancel успел записать `cancelled`, worker не переписывает status/result.

## Job Dispatch Outbox

SQL transaction и Redis/ARQ enqueue не атомарны между собой. Поэтому launch не
должен напрямую вызывать `JobQueue.enqueue(...)` после создания job.

Постановка в очередь выполняется через durable `job_dispatch_outbox`.

Launch flow:

1. В одной SQL transaction создать `job` со `status = queued`.
2. В той же transaction создать `job_dispatch_outbox` row:
   `job_id`, `type`, `version`, `status = pending`, `attempts = 0`.
3. Commit.
4. Outbox dispatcher/reconciler читает `pending` rows.
5. Dispatcher резолвит worker binding и вызывает ARQ enqueue.
6. Если enqueue успешен:
   - `outbox.status = dispatched`;
   - `outbox.dispatched_at = now`.
7. Если binding отсутствует:
   - `job` atomically updates `queued -> failed`;
   - `JobError(code="worker_binding_missing")`;
   - `outbox.status = failed`.
8. Если Redis/ARQ временно недоступен:
   - `attempts += 1`;
   - `last_error = ...`;
   - `next_attempt_at = backoff time`.

Dispatcher сам является reconciler-ом: он периодически читает `pending` rows с
`next_attempt_at <= now`. Дополнительный maintenance repair path может искать
`queued` jobs без non-terminal outbox row и создавать missing outbox row, но это
не основной launch flow.

Несколько dispatcher процессов могут работать параллельно. Pending rows должны
claim-иться через SQL transaction с `FOR UPDATE SKIP LOCKED`:

```sql
select *
from job_dispatch_outbox
where status = 'pending'
  and next_attempt_at <= now()
order by next_attempt_at, created_at
for update skip locked
limit :batch_size;
```

В первой версии отдельные `locked_at` / `locked_by` columns не нужны. Row остается
locked до тех пор, пока dispatcher не запишет `dispatched`, `failed` или pending
backoff metadata и не commit-нет transaction. Если dispatcher process упал,
database transaction rollback освобождает row для следующего dispatcher-а.

ARQ idempotency:

```text
ARQ _job_id = job_id
```

Если `enqueue_job(...)` возвращает `None` из-за duplicate `_job_id`, dispatcher
проверяет текущую job:

- если job `queued` или `running`, outbox считается `dispatched`;
- если job terminal, outbox тоже можно пометить `dispatched`, потому что durable
  delivery intent больше не нужен.

`JobQueue.enqueue(...)` не вызывается из API launch use case. Launch пишет только
`job + outbox` в одной transaction.

## Progress И Промежуточные Данные

`stage` удаляется из модели джобы.

Прогресс, промежуточные данные и чекпоинты, которые нужно показать наружу,
должны жить в событиях или в отдельных read models.

Примеры:

- Codex auth `user_code` не хранится в `job_stage`, `job.result` или durable
  event payload. Он хранится только в transient `CodexAuthSession`.
- Если UI должен polling-ом получить текущий `user_code`, API читает SQL `Job`
  только для existence/access/status, а сам код получает из Redis read model.
- Codex run file creation остается явно определенным `JobEvent` плюс связью
  джобы с файлом.

Строка `job` должна описывать жизненный цикл и финальный успешный результат, а
не текущую доменно-специфичную стадию.

## Codex Auth Session

Для `codex.auth` текущий auth flow не должен использовать `job_stage`.

Текущее состояние выдачи пользовательского кода хранится в отдельной
transient read model `CodexAuthSession`, backed by Redis.

`CodexAuthSession` не является durable SQL state и не является source of truth
для terminal lifecycle джобы. Source of truth остается строка `job`:

- `job.status`;
- `job.result`;
- `job.error`.

Redis session нужна только для polling/API состояния auth-кода.

Публичный код, который пользователь вводит в браузере, во всей новой модели
называется `user_code`. Старое имя `device_code` не сохраняется и не
поддерживается как backward-compatible alias. Если будущий provider вернет
отдельный backend-only OAuth `device_code`, он должен оставаться внутренним
секретом и не использоваться как имя публичного пользовательского кода.

Рекомендуемый Redis key:

```text
codex_auth_session:{job_id}
```

Поля session:

- `job_id`;
- `verification_url`;
- `user_code`;
- `expires_at`;
- `status`: `pending`, `authenticated`, `failed`, `cancelled`, `expired`;
- `error`;
- `created_at`;
- `updated_at`.

`user_code` и `verification_url` не хранятся в durable SQL `job`, `result` или
durable event payload. Они живут только в Redis `CodexAuthSession` до истечения
TTL или terminal cleanup.

TTL rules:

- для `pending` session TTL выставляется до `expires_at`;
- после `authenticated`, `cancelled` или `failed` sensitive fields
  (`user_code`, `verification_url`) очищаются;
- terminal snapshot остается в Redis на короткий TTL, например 5 минут, чтобы UI
  мог получить понятный terminal status вместо `not found`;
- если Redis session истекла или удалена, API fallback-ится на SQL `Job`.

API read flow:

1. API получает `job_id`.
2. Загружает `Job` из SQL.
3. Проверяет доступ текущего пользователя к job через `initiator`.
4. Только после успешной проверки доступа читает Redis `CodexAuthSession`.
5. Если Redis session найдена, возвращает ее текущее состояние.
6. Если Redis session не найдена:
   - `queued` / `running` job возвращается как `pending` без кода;
   - `succeeded` job возвращается как `authenticated` без кода;
   - `failed` job возвращается как `failed` с `job.error`;
   - `cancelled` job возвращается как `cancelled` с `job.error`.

Redis session может пережить SQL job deletion до истечения TTL. Это допустимо,
потому что API не читает Redis session до проверки существования job и access
check в SQL.

`JobRepository.delete(job_id)` не обязан чистить Redis `CodexAuthSession`.
Cleanup Redis session выполняется TTL-ом и terminal transition-ами auth flow.

## Files

`JobArtifact` всегда является файлом. Все не-файловые итоги выполнения должны
жить в typed `Job.result`, typed events или read models, но не в `JobArtifact`.

`JobArtifact` не должен оставаться базовой доменной сущностью job-домена.

Файл должен быть отдельной доменной сущностью, например `File`, которая
описывает файл сам по себе:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class File:
    file_id: UUID
    name: str
    kind: FileKind
    location: FileLocation
    metadata: dict
    status: FileStatus
    delete_requested_at: datetime | None
    delete_attempts: int
    last_delete_error: str | None
    created_at: datetime
```

Связь "этот файл относится к этой джобе" не должна быть частью самого `File`.
Для этого в домене может быть отдельная association entity `JobFile`.

`JobFile` описывает файл в контексте конкретной джобы и должен содержать ссылку
на джобу, с которой файл ассоциирован:

```python
@dataclass(frozen=True)
class JobFile:
    job_id: UUID
    file: File
    role: JobFileRole
    description: str | None
    created_at: datetime
```

В infrastructure это моделируется отдельной link-таблицей, которая связывает
`job` и `file` и хранит атрибуты этой связи:

```text
job_file
---
job_id uuid not null references job(job_id)
file_id uuid not null references file(file_id)
role varchar not null
description varchar null
created_at timestamptz not null
```

`role` (`output`, `log`, `input` и т.п.) появляется в контексте связи с джобой,
а не внутри файла как универсальное свойство.

Job result не должен дублировать связи с файлами.

Например `CodexRunResultV1` хранит summary/counts успешного выполнения, а не
`output_file_id` или `job_file_id`. Связанные файлы получаются через
`JobFileRepository.list_by_job(job_id)`.

Если caller-у нужно найти primary output, это моделируется на уровне `JobFile`
role/metadata, например `role = "primary_output"` или отдельным typed
`JobFileRole.PRIMARY_OUTPUT`, а не полем в `result`.

То есть:

- `File` - самостоятельная доменная сущность файла;
- `JobFile` - доменная association entity "файл, связанный с конкретной
  джобой";
- `job_file` - infrastructure link-table для persistence реализации
  `JobFile`.

## File Repository And Storage

`FileRepository` и `FileStorage` отвечают за разные вещи.

`FileRepository` хранит только metadata и ссылку на файл:

- `file_id`;
- `name`;
- `kind`;
- `location`;
- `metadata`;
- `status`;
- `delete_requested_at`;
- `delete_attempts`;
- `last_delete_error`;
- `created_at`.

Он не читает и не пишет содержимое файла. Его ответственность - сохранить и
вернуть доменную сущность `File` как мета-ссылку:

```python
await file_repository.create(file)
file = await file_repository.get(file_id)
```

`FileStorage` хранит сами bytes/files и умеет работать с содержимым по
`FileLocation`.

Его ответственность:

- сохранить содержимое файла и вернуть `FileLocation`;
- прочитать содержимое по `FileLocation`;
- при необходимости удалить физический файл по `FileLocation`.

```python
location = await file_storage.save(content)
content = await file_storage.read(location)
```

Типовой flow записи:

1. `FileStorage` сохраняет реальные bytes/path и возвращает `location`.
2. Use case создает `File(location=location, ...)`.
3. `FileRepository` сохраняет только metadata и `location`.
4. Если файл относится к джобе, создается `JobFile`, который связывает `Job` и
   `File`.

Типовой flow чтения:

1. `FileRepository` возвращает `File`.
2. `FileStorage` по `file.location` достает реальные bytes/content.

Repository не является storage. Repository хранит указатель и метаданные,
storage хранит сам файл.

При удалении связи джобы с файлом нужно учитывать shared files:

1. link `job_file` для удаляемой джобы удаляется всегда.
2. После удаления link-а проверяется, остались ли другие ссылки на этот
   `file_id`.
3. Если ссылки остались, file metadata и physical content остаются.
4. Если ссылок больше нет, file metadata не удаляется сразу, а помечается
   `status = pending_delete`, `delete_requested_at = now`.
5. Physical content удаляет отдельный cleanup worker.

То есть content файла нельзя удалять просто потому, что удаляется одна джоба.
Physical content удаляется только когда файл больше не связан ни с одной
джобой.

### File Physical Delete Failures

PostgreSQL transaction и `FileStorage` delete не атомарны. Нельзя надежно
удалить SQL metadata и physical content одним commit-ом.

Поэтому используется mark-and-sweep cleanup:

1. `JobRepository.delete(job_id)` удаляет `job_file` links.
2. Orphan files помечаются как `status = pending_delete`,
   `delete_requested_at = now`.
3. SQL transaction commit-ится.
4. Отдельный `FileCleanupWorker` читает `pending_delete` files.
5. Worker вызывает `FileStorage.delete(file.location)`.
6. Если physical delete успешен, worker удаляет file metadata.
7. Если physical delete упал, worker оставляет metadata в `pending_delete`,
   увеличивает `delete_attempts`, записывает `last_delete_error` и пробует позже.

Статусы файла:

```text
active
pending_delete
```

`pending_delete` file не должен быть доступен пользователям как обычный файл.
Он остается в БД только как durable cleanup task, чтобы storage failure не
оставил неотслеживаемый orphan blob/path.

## Job Events

`JobEvent` остается доменной сущностью, и все job events должны быть явно
определены типами.

Event identity:

```text
(event.type, event.version)
```

Для каждого durable event contract должны быть:

- event class;
- frozen/typed payload dataclass;
- `type`;
- `version`;
- `source`;
- registered serializer/deserializer.

То есть для доменных событий джоб продолжаем определять отдельные contracts:

```python
@dataclass(kw_only=True)
class CodexRunStartedV1(JobEvent):
    ...


@dataclass(kw_only=True)
class CodexRunSucceededV1(JobEvent):
    ...
```

`event_registry` хранит mapping `(type, version) -> event class / payload type`.
Duplicate registration запрещен. Typed `EventRepository` при чтении использует
`event_registry`.

Unknown events:

- typed `EventRepository.get(...)` / `list_typed(...)` strict;
- если event contract неизвестен, repository бросает
  `UnknownEventContractError`;
- user-facing audit/history APIs могут использовать raw projection, которая
  показывает event metadata без typed payload deserialization.

Versioning:

- breaking payload change -> новая `version`;
- non-breaking additive changes допустимы только если codec поддерживает
  defaults и старые events продолжают десериализоваться.

Но базовое хранение событий не должно зашивать связь с job прямо в event row.
Событие хранится "как есть", а связь с джобой моделируется отдельной
infrastructure таблицей:

```text
job_event
---
job_id uuid not null references job(job_id)
event_id uuid not null references event(event_id)
relation varchar not null
sequence bigint not null
created_at timestamptz not null
```

Это такая же идея, как с `initiator`: доменная сущность остается typed object,
а SQL-связь моделируется отдельно. Поэтому `job_id_issuer` не должен быть
частью базовой event persistence model или payload. Связь с job должна
восстанавливаться через `job_event`.

`event.created_at` не является единственным ordering guarantee. Для per-job
истории порядок задается `job_event.sequence`, monotonically increasing внутри
одной job.

На первом этапе `job_event.relation` поддерживает только:

```text
emitted_by
```

`job_event` должен иметь уникальность:

```text
(job_id, event_id, relation)
(job_id, sequence)
```

Auth-specific security rule: `CodexAuthUserLoginRequestedV1` может фиксировать
факт запроса логина и `expires_at`, но не должен хранить `user_code` или
`verification_url` в durable payload. Эти поля остаются только в Redis
`CodexAuthSession`.

## Initiators

В доменной модели инициатор остается typed dataclass/value object, а не
`initiator_id`.

Пример доменного объекта:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Initiator:
    type: InitiatorType
    external_id: str | None = None
    display_name: str | None = None
    metadata: dict | None = None
```

Отдельная таблица `initiator` - это persistence detail для PostgreSQL: в БД не
нужно хранить инициатора JSON-ом внутри `job`, но домен не обязан оперировать
foreign key вместо объекта.

Целевые поля:

- `initiator_id`: primary key.
- `type`: `user`, `system`, `schedule`, `api`.
- `external_id`: опциональный ID во внешней системе, например user ID.
- `display_name`: опциональное человекочитаемое имя.
- `metadata`: опциональный JSON для source-specific данных.
- `created_at`.

В таблице `job` хранится `initiator_id` как foreign key.

Зачем:

- инициатор становится нормально queryable/indexable;
- много джоб могут ссылаться на одного инициатора;
- access checks не зависят от JSON extraction;
- расширение данных инициатора не меняет core schema джобы.

Deduplication rules:

- если `external_id` известен, initiator дедуплицируется по `(type,
  external_id)`;
- если `external_id is None`, initiator не дедуплицируется по SQL `NULL` и по
  умолчанию создается отдельная запись;
- для `system`, `schedule` и `api` initiators, которым нужна дедупликация,
  caller должен передавать stable `external_id`, например `system:codex`,
  `schedule:nightly` или `api:<client_id>`.

Так мы не смешиваем разные anonymous/system источники в одну запись только
потому, что у них нет external ID.

Deduplication должен быть database invariant, а не только repository convention.
Для PostgreSQL используется partial unique index:

```sql
create unique index uq_initiator_type_external_id
on initiator (type, external_id)
where external_id is not null;
```

Repository flow:

1. Если `external_id is not null`, `InitiatorRepository.get_or_create(...)`
   делает `insert ... on conflict` по `(type, external_id)` или retry/select
   existing row.
2. Если `external_id is null`, repository всегда создает новую initiator row.

В domain используется имя `external_id`, а не `Actor.id`, чтобы не смешивать
внешний ID источника с SQL primary key `initiator_id`.

## Привязка ARQ Worker

ARQ worker нужно линковать с job contract через явный декоратор.

Декоратор принимает contract class и регистрирует маппинг
`(contract.type, contract.version) -> ARQ function`. Тип джобы не должен
выводиться из имени Python-функции.

Концептуальный пример:

```python
@job_worker(contract=CodexRunJobV1)
async def run_codex_job(ctx: dict, job_id: str) -> dict:
    ...
```

Контракт, а не декоратор, является единственным источником:

- `type`;
- `version`;
- input dataclass;
- result dataclass;

Декоратор должен регистрировать:

- contract class;
- ARQ-функцию;
- опциональные display/public metadata.

Новый flow постановки в очередь:

1. Caller создает валидную доменную `Job` напрямую или через дополнительный
   конструктор на `Job`.
2. `JobLauncher` принимает готовую `Job` и в одной SQL transaction сохраняет
   `job + job_dispatch_outbox`.
3. Outbox dispatcher резолвит `(job.type, job.version)` через domain
   `job_registry` и worker binding registry.
4. Если binding существует, dispatcher передает ARQ физическое имя
   зарегистрированной worker-функции и `job_id`.
5. Если binding отсутствует, dispatcher переводит job `queued -> failed` с
   `JobError(code="worker_binding_missing")`.
6. Worker загружает джобу, десериализует typed input, выполняет use case,
   сохраняет typed successful result и обновляет status.

Worker binding проверяется на двух уровнях:

- primary validation выполняет outbox dispatcher перед enqueue;
- worker-side validation остается defensive fallback для stale queue messages,
  deploy races и ручных ошибок.

Если worker получил queued job, но binding для `(type, version)` отсутствует,
job переводится в `failed` с `JobError(code="worker_binding_missing")`, а не
остается вечной `queued`.

`WorkerSettings.functions` должен собираться из worker binding registry, который
ссылается на domain `job_registry`, чтобы список зарегистрированных контрактов и
список реально доступных ARQ-функций не расходились.

### Worker Binding Version Lifecycle

Для clean-break миграции старые worker handlers сохранять не нужно, потому что
старые queued/running jobs удаляются и не перезапускаются.

После перехода на новую модель действует правило:

```text
Нельзя удалять worker binding для (type, version), пока существуют
non-terminal jobs этой пары.
```

Non-terminal statuses:

- `queued`;
- `running`.

Перед удалением worker binding старой версии нужно:

1. дождаться, пока все jobs этой `(type, version)` станут terminal;
2. или явно отменить/удалить non-terminal jobs через обычный cancellation/delete
   flow;
3. только после этого удалить worker binding/handler.

## Persistence Shape

Целевая таблица `job`:

```text
job
---
job_id uuid primary key
type varchar not null
version varchar not null
name varchar null
description varchar null
input json not null default '{}'
result json null
status varchar not null
initiator_id uuid not null references initiator(initiator_id)
parent_job_id uuid null references job(job_id)
requested_at timestamptz not null
updated_at timestamptz not null
started_at timestamptz null
finished_at timestamptz null
error json null
```

Рекомендуемые индексы:

- `(type, version)`
- `status`
- `initiator_id`
- `parent_job_id`
- `requested_at`

Required constraints:

```sql
check (type <> '');
check (version ~ '^v[0-9]+$');

check (
  (
    status = 'succeeded'
    and result is not null
    and error is null
    and finished_at is not null
  )
  or (
    status in ('failed', 'cancelled')
    and result is null
    and error is not null
    and finished_at is not null
  )
  or (
    status in ('queued', 'running')
    and result is null
    and error is null
    and finished_at is null
  )
);

check (
  (status = 'queued' and started_at is null)
  or (status in ('running', 'succeeded') and started_at is not null)
  or (status in ('failed', 'cancelled'))
);

check (started_at is null or started_at >= requested_at);
check (finished_at is null or started_at is null or finished_at >= started_at);
```

`failed` и `cancelled` допускают `started_at is null`, потому terminal failure
может случиться до старта worker-а: enqueue failure, missing binding, validation
failure перед execution.

Целевая таблица `job_dispatch_outbox`:

```text
job_dispatch_outbox
---
outbox_id uuid primary key
job_id uuid not null references job(job_id)
type varchar not null
version varchar not null
status varchar not null
attempts integer not null default 0
next_attempt_at timestamptz not null
last_error text null
created_at timestamptz not null
updated_at timestamptz not null
dispatched_at timestamptz null
```

Outbox statuses:

```text
pending
dispatched
failed
```

Рекомендуемые индексы:

- `(status, next_attempt_at)`
- `job_id`

Целевая таблица `initiator`:

```text
initiator
---
initiator_id uuid primary key
type varchar not null
external_id varchar null
display_name varchar null
metadata json not null default '{}'
created_at timestamptz not null
```

Рекомендуемые индексы:

- `(type, external_id)`
- unique `(type, external_id) where external_id is not null`

Целевая таблица `file`:

```text
file
---
file_id uuid primary key
name varchar not null
kind varchar not null
location json not null
metadata json not null default '{}'
status varchar not null
delete_requested_at timestamptz null
delete_attempts integer not null default 0
last_delete_error varchar null
created_at timestamptz not null
```

Рекомендуемые индексы:

- `status`
- `delete_requested_at`

`event` хранит события как самостоятельные записи. Связь event с job хранится в
link-таблице `job_event`:

```text
job_event
---
job_id uuid not null references job(job_id)
event_id uuid not null references event(event_id)
relation varchar not null
sequence bigint not null
created_at timestamptz not null
```

Рекомендуемые constraints/indexes:

- unique `(job_id, event_id, relation)`
- unique `(job_id, sequence)`
- `(job_id, sequence)`

`file` хранит файлы как самостоятельные записи. Связь file с job хранится в
link-таблице `job_file`:

```text
job_file
---
job_id uuid not null references job(job_id)
file_id uuid not null references file(file_id)
role varchar not null
description varchar null
created_at timestamptz not null
```

Рекомендуемые constraints/indexes:

- unique `(job_id, file_id, role)`
- `job_id`
- `file_id`

## Deletion Semantics

Удаление джоб и связанных объектов должно быть responsibility
repository/infrastructure слоя.

Не нужен отдельный `DeleteJobUseCase` только ради cleanup-а. Любой путь, который
вызывает `JobRepository.delete(job_id)`, должен получать одинаковую семантику
удаления связанных rows и physical content.

### User Deletion

Когда удаляется user, нужно вручную удалить все джобы, где инициатор - этот
user.

Правило:

- найти initiator с `type = "user"` и `external_id = user.id`;
- найти все jobs, связанные с этим initiator;
- для non-terminal jobs сначала запросить cancel и дождаться terminal status;
- удалить каждую terminal job через `JobRepository.delete(job_id)`;
- после этого удалить самого user.

Это не должно быть raw DB cascade, который молча удаляет только строки. Удаление
джобы должно пройти через repository path, потому что у job есть files/events и
physical file content.

### Job Deletion

`JobRepository.delete(job_id)` разрешен только для terminal jobs:

- `succeeded`;
- `failed`;
- `cancelled`.

Прямое удаление `queued` или `running` job запрещено.

Для `queued` job caller должен сначала отменить job (`queued -> cancelled`) и
только потом вызвать delete.

Для `running` job caller должен сначала запросить cancel, дождаться terminal
`cancelled` от worker-а и только потом вызвать delete.

Причина: non-terminal job может параллельно выполняться worker-ом и писать
`result`, `error`, events или files. Cleanup не должен гоняться с active
execution.

Parent/child deletion:

- по умолчанию delete работает в restrict mode;
- если у job есть children, `JobRepository.delete(job_id)` бросает
  `JobHasChildrenError`;
- caller может явно запросить cascade deletion, например
  `delete(job_id, cascade_children=True)`;
- cascade deletion строит descendants tree и удаляет jobs post-order: сначала
  children, потом parent;
- каждая job в cascade tree должна быть terminal;
- если в tree есть `queued` или `running` job, cascade delete падает; caller
  должен сначала отменить non-terminal jobs и дождаться terminal status.

`JobRepository.delete(job_id)` должен удалять:

- links `job_file` для этой job;
- для files, на которые после удаления links больше нет ссылок, выставлять
  `status = pending_delete` и `delete_requested_at = now`;
- links `job_event` для этой job;
- events, которые после удаления links больше не связаны ни с одной job;
- саму job.

Удаление job должно быть reference-aware.

Файл нельзя удалять физически только потому, что удаляется одна job. Physical
content удаляется только когда `file_id` больше не связан ни с одной job.

Событие аналогично: если event связан с несколькими jobs, удаление одной job
удаляет только link. Сам event удаляется только когда на него больше нет
`job_event` ссылок.

Job events в этой модели не являются вечным immutable audit log. Для privacy и
user deletion cleanup orphan job events должен удалять event rows, если после
удаления `job_event` links они больше не связаны ни с одной job.

### Repository Responsibilities

`JobRepository` на уровне domain contract должен иметь `delete(job_id)`.

Infrastructure implementation `JobRepositoryImpl` отвечает за orchestration
cleanup-а:

- читает `job_file` links;
- проверяет orphan files;
- помечает orphan files как `pending_delete`;
- читает `job_event` links;
- проверяет orphan events;
- удаляет event rows;
- удаляет job row.

`UserRepository.delete(user_id)` должен либо иметь доступ к `JobRepository`, либо
использовать общий infrastructure helper, но итоговое правило остается тем же:
jobs пользователя удаляются через тот же cleanup path, что и прямое удаление
job.

## Domain API

Запуск джобы не должен принимать сырой dict и не должен собирать `Job` из
набора primitive-параметров.

`JobLauncher` принимает уже сформированную доменную `Job`. Создание `Job`
остается на стороне конкретного contract class через `new(...)`.

Целевая форма:

```python
job = CodexRunJobV1.new(
    initiator=initiator,
    input=CodexRunInputV1(prompt="Inspect this repo", workdir="/tmp/work"),
    name="Codex run",
    description="Run Codex against a workspace",
)

await job_launcher.launch(job)

completed_job = await job_launcher.launch_and_wait(job, timeout=120)
```

`CodexRunJobV1.new(...)` или аналогичный `new(...)` на contract class должен:

- проверить, что `input` соответствует input dataclass этого контракта;
- создать `Job` в статусе `queued`;
- заполнить `type`, `version`, `input`, `initiator`, timestamps, optional
  `name`, optional `description` и optional `parent_job_id`.

`name` и `description` не обязательны. Если caller их не передал, они остаются
`None`.

`JobLauncher` должен:

- принять готовую доменную `Job`;
- проверить, что `(job.type, job.version)` зарегистрирован;
- сохранить `job + job_dispatch_outbox` в одной SQL transaction;
- передать persistence-слою typed `initiator`; после follow-up extraction
  persistence маппит его в `initiator_id`;
- не вызывать queue backend напрямую;
- уметь дождаться завершения джобы, если caller-у нужен synchronous boundary.

### Launch Transaction Boundary

Launch использует durable `job_dispatch_outbox`. Прямой enqueue из API launch
use case запрещен.

`JobLauncher.launch(job)` должен делать одну SQL transaction:

1. сохранить `Job` в SQL в статусе `queued`;
2. сохранить `job_dispatch_outbox` row со `status = pending`;
3. commit-нуть SQL transaction;
4. вернуть `job_id` caller-у.

Outbox dispatcher после commit-а:

- читает `pending` outbox rows;
- резолвит worker binding;
- вызывает `JobQueue.enqueue(job)`;
- помечает outbox row как `dispatched` при успешном enqueue;
- переводит job `queued -> failed` с `worker_binding_missing`, если binding
  отсутствует;
- оставляет outbox row `pending` с backoff metadata, если queue backend временно
  недоступен.

Такой порядок нужен, чтобы worker не мог получить `job_id` раньше, чем строка
`job` закоммичена и видна другим DB sessions, и чтобы process crash после SQL
commit-а не оставлял job без durable dispatch intent.

Проверка successful enqueue зависит от конкретного queue backend. Для ARQ
минимальное правило: `redis.enqueue_job(...)` должен вернуть non-null queued job
handle. `None` из-за duplicate `_job_id` обрабатывается dispatcher-ом
idempotently через проверку текущего job status.

Ожидание выполнения должно быть явным API, а не неявным поведением `launch`.
Например:

```python
job_id = await job_launcher.launch(job)
completed_job = await job_launcher.wait(job_id, timeout=120)

# или shortcut:
completed_job = await job_launcher.launch_and_wait(job, timeout=120)
```

`wait(...)` / `launch_and_wait(...)` не выполняют джобу в текущем процессе.
Они создают durable dispatch intent и ждут, пока worker переведет job в
terminal status:

- `succeeded`;
- `failed`;
- `cancelled`.

`wait(...)` всегда возвращает terminal `Job`, если дождался terminal status.
`failed` и `cancelled` не являются ошибкой `wait(...)`; это нормальные terminal
statuses job. Если джоба завершилась успешно, caller получает `Job` с
заполненным `job.result`. Если джоба завершилась ошибкой или отменой, caller
получает `Job` с terminal status и `job.error`.

`wait(...)` бросает исключение только для ошибок самого ожидания:

- `JobNotFoundError`;
- `JobWaitTimeoutError`;
- persistence/system errors.

Если caller-у нужен API, который считает `failed`/`cancelled` исключительными
состояниями, поверх `wait(...)` можно добавить отдельный helper, например
`wait_succeeded(...)`.

`wait(...)` должен поддерживать timeout. Timeout ожидания не равен отмене джобы:
если caller перестал ждать, сама джоба может продолжить выполняться в worker-е.

Execution boundary должен:

- выполнить atomic `queued -> running`;
- если transition не прошел, выйти no-op;
- загрузить raw execution record по ID;
- десериализовать input в зарегистрированный dataclass;
- если input invalid, записать `running -> failed` с
  `JobError(code="invalid_job_input")`;
- выполнить handler/use case;
- проверить, что результат соответствует зарегистрированному result dataclass;
- сохранить сериализованный result только через atomic terminal transition.

## Миграция

Полный target checklist:

1. Переименовать/заменить `job_type` на `type`.
2. Добавить `version`.
3. Заменить `result_summary` на `result`.
4. Удалить `job_stage`.
5. Заменить `root_initiator` JSON на доменный `initiator` dataclass/value
   object.
6. Добавить таблицу `initiator`.
7. Ввести dataclass contracts для input/result каждой джобы.
8. Ввести domain `job_registry` и ARQ worker binding decorator.
9. Добавить `job_dispatch_outbox` и outbox dispatcher/reconciler.
10. Переделать enqueue так, чтобы ARQ function name резолвился через worker
   binding registry, связанный с domain `job_registry`.
11. Ввести atomic lifecycle repository methods для `queued -> running` и
    terminal transitions.
12. Перенести progress/intermediate state из `job_stage` в events или typed read
    models.
13. Для `codex.auth` заменить публичное имя `device_code` на `user_code` без
    backward compatibility и хранить `user_code` только в Redis
    `CodexAuthSession`.
14. Ввести `event_registry`, typed event codec, `job_event.sequence` и
    `relation = emitted_by`.
15. Оставить один strict `JobRepository` для typed domain reads и
    execution-specific lifecycle methods; read-only projection/query repositories
    используются отдельно для UI/history.
16. Заменить `JobArtifact` на отдельный домен `File` плюс infrastructure
    link-таблицу `job_file`.
17. Хранить events отдельно и вынести связь events с jobs в infrastructure
    link-таблицу `job_event`.
18. Добавить `JobRepository.delete(job_id)` с cleanup-ом `job_file`,
    orphan files, physical file content, `job_event`, orphan events и самой job.
19. Добавить partial unique index для initiator dedup:
    `(type, external_id) where external_id is not null`.
20. Изменить удаление user так, чтобы все jobs этого user удалялись через
    `JobRepository.delete(job_id)` до удаления user row.

Первые контракты:

```text
codex.auth v1
input: CodexAuthInputV1
result: CodexAuthResultV1

codex.run v1
input: CodexRunInputV1
result: CodexRunResultV1
```

Совместимость с текущими данными не поддерживается.

Миграция выполняется как чистый разрыв:

- старые `job`, `job_artifact` и job-related event данные удаляются;
- backfill `job_type`, `job_input`, `result_summary`, `root_initiator` и
  `job_stage` не выполняется;
- legacy field names и compatibility adapters в коде не сохраняются;
- новая схема, domain model, repositories, API и worker flow используют только
  целевые поля и typed contracts.

Zero-downtime migration для этого среза не требуется.

Deployment flow:

1. остановить API и workers, которые используют старую job модель;
2. очистить старые `job`, `job_artifact` и job-related event данные;
3. применить новую SQL schema;
4. задеплоить новый код domain/usecase/infrastructure/API/worker;
5. запустить API и workers.

Старые queued/running jobs не сохраняются и не перезапускаются.
