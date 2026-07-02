# TODO

## Raw Intent To Preserve

Эти заметки надо сохранить как исходный смысл, а не превращать в слишком
общие пункты:

- Зачем вообще нужен `serialization.py`, и не является ли он симптомом
  неправильного контракта job.
- `File` надо сделать отдельным доменным item, а не деталью job domain.
- Контракт job/use case должен возвращать `JobOutput` или другой typed output,
  а не голые `dict`.
- Надо разобраться с `JobProjection`, `JobSummary`, `JobDetailProjection`:
  кажется, это должно быть оформлено как отдельная domain/read-model
  концепция, а не случайные классы рядом с repository port.
- Нужен нормальный skill и `AGENTS.md`, которые будут регулировать структуру
  проекта и ревью.
- Нужен DDD linter и отдельный reviewer skill, который сможет спаунить агента
  и выдавать подробный отчет по текущим проблемам.
- Нужна конвенция для тестов в формате Arrange / Act / Assert и проверки,
  которые будут ловить отклонения.
- Надо полностью описать и проверить логику создания job.
- Под каждую job надо прокидывать своего logger, который пишет ценную
  информацию.
- Нужен websocket/async event API, который стримит события, и контракт того,
  как мы работаем с событиями и реагируем на них.

## Job Domain Follow-Ups

- Разобраться, зачем нужен `backend/app/domain/job/base/serialization.py`, и зафиксировать его роль:
  - строгая сериализация typed job input/result в JSON для БД и очередей;
  - строгая десериализация из persisted JSON обратно в dataclass contracts;
  - раннее обнаружение schema drift, лишних полей и несовместимых типов;
  - граница между domain contract и infrastructure persistence.
  - проверить, не должен ли этот слой быть частью общего contract codec, а не
    лежать в `domain/job/base`;
  - решить, допускаем ли поддержку nested dataclass, enum, UUID, datetime,
    collection types и version migration;
  - описать, кто отвечает за ошибку сериализации: job contract, repository,
    worker boundary или отдельный codec service;
  - проверить, не надо ли заменить public `serialize_json`/`deserialize_json`
    на более явный `JobContractCodec`.
- Сделать `File` отдельным доменным item, а не только частью job domain:
  - определить ownership и lifecycle;
  - описать связи `JobFile` как link/association model;
  - отделить storage metadata от доменной сущности файла.
  - решить, где должен жить file domain: `domain/file`, shared kernel или
    bounded context вокруг assets/storage;
  - описать repository ports для `File`, `FileStorage`, delete lifecycle,
    orphan cleanup и permissions;
  - решить, может ли один `File` быть связан с несколькими jobs и другими
    доменами;
  - отделить immutable file content identity от mutable metadata/status;
  - описать, что такое `FileKind.TEXT` vs `FileKind.FILE` и не является ли это
    storage/detail, а не доменной моделью.
- Разобраться с контрактом use case/job handler output:
  - вместо голых `dict` возвращать typed `JobOutput`/`JobResult`;
  - описать, кто и где переводит output в public API schema;
  - запретить неструктурированные result payloads.
  - проверить все `execute(...) -> dict` и заменить на typed response;
  - разделить durable `Job.result`, immediate handler return value и public
    HTTP response;
  - решить, должен ли worker возвращать `JobOutput` в ARQ result или только
    писать durable state;
  - описать error output: typed failure result запрещен или вся ошибка только
    через `JobError`;
  - добавить тесты, которые ломаются при возврате raw dict из job use case.
- Пересмотреть `JobProjection`, `JobSummary`, `JobDetailProjection`:
  - решить, где они должны жить: domain, read model, application query layer;
  - отделить executable domain entity от read-side projection;
  - описать правила, когда projection может не десериализовать typed job contract.
  - проверить, не должны ли projection классы лежать в `domain/job/base/read_models`
    или `usecase/job/queries`, а repository port только ссылаться на них;
  - договориться о naming: `Projection`, `ReadModel`, `View`, `Summary`;
  - описать, какие поля projection обязаны иметь для UI/API;
  - добавить projection для list screen, detail screen и timeline/events;
  - решить, должны ли projections включать `files`, `events`, `output`,
    `serialization_error` и raw payload.

## Project Conventions

- Сделать нормальный skill и `AGENTS.md`, которые фиксируют DDD-структуру проекта:
  - `domain`, `usecase`, `infrastructure`, `presentation`;
  - один dataclass на файл;
  - один exception на файл или явно описанная exception group convention;
  - контракт exception: base exception, semantic subclasses, payload/metadata policy;
  - что можно импортировать между слоями и что нельзя.
  - описать правило: domain не импортирует infrastructure/presentation;
  - usecase зависит от domain и ports, но не от SQLModel/FastAPI/Redis;
  - infrastructure реализует ports и содержит DTO/adapters;
  - presentation содержит FastAPI routes/schemas/exception mapping;
  - DTO не является domain entity;
  - value object/entity/event/exception/repository port/use case должны иметь
    понятные suffix/name conventions;
  - один dataclass на файл: когда можно нарушить, кто approve-ит исключение;
  - один exception на файл или строгая exception group convention: base class,
    subclasses, поля, message policy, retryable/metadata policy;
  - описать contract для domain exception: не зависит от HTTP, не содержит
    transport status code, может иметь machine-readable code/details;
  - добавить checklist для review: layering, naming, ownership, DTO leakage.
- Зафиксировать API convention:
  - route только валидирует transport input, вызывает use case и переводит результат;
  - domain/usecase exceptions мапятся в HTTP exceptions на presentation layer;
  - route не содержит бизнес-логики и не ходит напрямую в infrastructure, кроме DI.
  - описать стандартный route skeleton;
  - описать, где живут public request/response schemas;
  - описать mapping exceptions -> HTTP codes;
  - запретить route-level repository orchestration, кроме простого access
    check через отдельный use case/query;
  - решить, можно ли route вызывать два use case подряд или нужен facade use case;
  - описать transaction/session boundary и кто делает commit/rollback;
  - добавить тесты route-level: happy path, exception mapping, access denied.
- Описать контракт каждой job:
  - `type`, `version`, input dataclass, result dataclass;
  - как создается job через `JobContract.new(...)`;
  - где живет worker binding;
  - как сохраняются result/error/events/files;
  - naming conventions для job type, event type, logger name, queue name.
  - required файлы для новой job: contract, use case, ports, worker binding,
    tests, API launch schema/route if needed;
  - `type` format: dot-separated stable string, например `codex.run`;
  - `version` format: `v1`, `v2`, без silent mutation старых payloads;
  - input/result dataclasses immutable или mutable: принять решение;
  - запрещены raw dict input/result, кроме projection/raw persistence layer;
  - events должны быть typed, versioned, без secrets в durable payload;
  - files должны сохраняться через `File`/`JobFile`, не через result dict;
  - cancellation semantics: queued/running, cancellation backend, cleanup;
  - retry semantics: новая job с тем же input или linked retry job;
  - logging semantics: отдельный job logger и correlation id.

## Tooling

- Написать DDD linter:
  - проверяет расположение файлов по слоям;
  - ловит запрещенные импорты между слоями;
  - проверяет один dataclass/exception на файл;
  - проверяет naming conventions для use cases, repositories, DTOs, events, jobs;
  - выдает actionable report с file/line.
  - отдельные rules:
    - domain imports infrastructure/presentation запрещены;
    - usecase imports SQLModel/FastAPI запрещены;
    - routes не импортируют SQLModel DTO;
    - `dict` в job input/result сигнатурах запрещен;
    - dataclass/entity/event не должен жить в `__init__.py`;
    - repository implementation не должен жить в domain;
    - migration/DTO naming соответствует table/entity naming;
    - tests содержат Arrange / Act / Assert comments или секции;
    - old legacy names вроде `Artifact`, `Stage`, `Actor`, `result_summary`
      запрещены после миграции.
  - определить формат вывода: text, JSON, GitHub annotations;
  - добавить режим `--changed` для проверки diff и `--all` для всего repo.
- Сделать reviewer skill:
  - умеет спаунить агента для DDD/codebase review;
  - проверяет текущий diff и весь affected surface;
  - возвращает подробный отчет по нарушениям convention, рискам и missing tests.
  - reviewer должен читать `AGENTS.md`, DDD convention docs и linter report;
  - должен уметь разделять findings по severity;
  - должен проверять не только changed files, но и call sites/contracts;
  - должен явно писать residual risk и какие тесты надо добавить;
  - должен уметь спаунить explorer/worker агента для независимой проверки,
    когда это разрешено пользователем.
- Написать test convention:
  - тесты в формате Arrange / Act / Assert;
  - явные fake repositories/ports;
  - отдельные проверки на структуру тестов;
  - reviewer/agent, который проверяет тесты на соответствие convention.
  - описать naming: `test_<behavior>_<expected_result>`;
  - тест должен проверять behavior, а не implementation detail;
  - fake должен быть минимальным и typed, без лишней логики;
  - каждый bug fix должен иметь regression test;
  - для repository тестов проверять round-trip, ordering, filters,
    cleanup/delete semantics;
  - для API тестов проверять exception mapping и auth/access rules;
  - добавить linter/reviewer checks на AAA structure.

## Job Runtime

- Полностью описать и проверить flow создания job:
  - API создает typed contract job;
  - `JobLauncher` сохраняет job и dispatch outbox row в одной транзакции;
  - dispatcher резолвит worker по `(type, version)`;
  - worker atomically claims job, исполняет use case, пишет result/error/events/files.
  - проверить, что API не может создать job через raw `dict`;
  - проверить, что unknown contract не попадает в очередь;
  - проверить, что duplicate enqueue не запускает job дважды;
  - проверить, что worker не получает `job_id` раньше commit job row;
  - проверить, что `try_mark_running/succeeded/failed/cancelled` атомарны;
  - проверить, что failed serialization переводит job в failed с понятным
    `JobError`;
  - проверить deletion cleanup для terminal jobs, files, events, outbox rows;
  - добавить end-to-end тест с outbox dispatcher и fake queue.
- Прокидывать под каждую job отдельный logger:
  - logger name содержит job type/version/job id;
  - логировать started/claimed/succeeded/failed/cancelled;
  - логировать полезные параметры без secrets;
  - связать logger с job events или trace/correlation id.
  - определить logger injection contract: use case получает `JobLogger` port
    или worker создает scoped logger;
  - structured fields: `job_id`, `job_type`, `job_version`, `initiator_id`,
    `attempt`, `worker`, `correlation_id`;
  - redact policy для secrets/auth codes/tokens/path-sensitive данных;
  - решить, какие события идут только в logs, а какие в durable `JobEvent`;
  - добавить tests на то, что секреты не попадают в durable events/log payload.
- Спроектировать websocket/async event API:
  - endpoint подписки на job timeline;
  - stream typed events и read model updates;
  - backpressure/reconnect contract;
  - authorization per initiator/user;
  - правила реакции frontend/backend consumers на events.
  - описать protocol: websocket или SSE, event envelope, `last_event_id`;
  - автоматический async API для подписки на job/user events;
  - contract событий: `type`, `version`, `sequence`, `created_at`, `payload`;
  - replay missed events после reconnect;
  - heartbeat/ping и timeout policy;
  - access control: пользователь видит только свои jobs/admin видит все;
  - consumer reaction policy: какие events обновляют status, timeline, files,
    notifications;
  - добавить integration tests на connect, reconnect, auth denied, ordering.
