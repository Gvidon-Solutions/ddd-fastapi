# TODO

## Job Domain Follow-Ups

- Разобраться, зачем нужен `backend/app/domain/job/base/serialization.py`, и зафиксировать его роль:
  - строгая сериализация typed job input/result в JSON для БД и очередей;
  - строгая десериализация из persisted JSON обратно в dataclass contracts;
  - раннее обнаружение schema drift, лишних полей и несовместимых типов;
  - граница между domain contract и infrastructure persistence.
- Сделать `File` отдельным доменным item, а не только частью job domain:
  - определить ownership и lifecycle;
  - описать связи `JobFile` как link/association model;
  - отделить storage metadata от доменной сущности файла.
- Разобраться с контрактом use case/job handler output:
  - вместо голых `dict` возвращать typed `JobOutput`/`JobResult`;
  - описать, кто и где переводит output в public API schema;
  - запретить неструктурированные result payloads.
- Пересмотреть `JobProjection`, `JobSummary`, `JobDetailProjection`:
  - решить, где они должны жить: domain, read model, application query layer;
  - отделить executable domain entity от read-side projection;
  - описать правила, когда projection может не десериализовать typed job contract.

## Project Conventions

- Сделать нормальный skill и `AGENTS.md`, которые фиксируют DDD-структуру проекта:
  - `domain`, `usecase`, `infrastructure`, `presentation`;
  - один dataclass на файл;
  - один exception на файл или явно описанная exception group convention;
  - контракт exception: base exception, semantic subclasses, payload/metadata policy;
  - что можно импортировать между слоями и что нельзя.
- Зафиксировать API convention:
  - route только валидирует transport input, вызывает use case и переводит результат;
  - domain/usecase exceptions мапятся в HTTP exceptions на presentation layer;
  - route не содержит бизнес-логики и не ходит напрямую в infrastructure, кроме DI.
- Описать контракт каждой job:
  - `type`, `version`, input dataclass, result dataclass;
  - как создается job через `JobContract.new(...)`;
  - где живет worker binding;
  - как сохраняются result/error/events/files;
  - naming conventions для job type, event type, logger name, queue name.

## Tooling

- Написать DDD linter:
  - проверяет расположение файлов по слоям;
  - ловит запрещенные импорты между слоями;
  - проверяет один dataclass/exception на файл;
  - проверяет naming conventions для use cases, repositories, DTOs, events, jobs;
  - выдает actionable report с file/line.
- Сделать reviewer skill:
  - умеет спаунить агента для DDD/codebase review;
  - проверяет текущий diff и весь affected surface;
  - возвращает подробный отчет по нарушениям convention, рискам и missing tests.
- Написать test convention:
  - тесты в формате Arrange / Act / Assert;
  - явные fake repositories/ports;
  - отдельные проверки на структуру тестов;
  - reviewer/agent, который проверяет тесты на соответствие convention.

## Job Runtime

- Полностью описать и проверить flow создания job:
  - API создает typed contract job;
  - `JobLauncher` сохраняет job и dispatch outbox row в одной транзакции;
  - dispatcher резолвит worker по `(type, version)`;
  - worker atomically claims job, исполняет use case, пишет result/error/events/files.
- Прокидывать под каждую job отдельный logger:
  - logger name содержит job type/version/job id;
  - логировать started/claimed/succeeded/failed/cancelled;
  - логировать полезные параметры без secrets;
  - связать logger с job events или trace/correlation id.
- Спроектировать websocket/async event API:
  - endpoint подписки на job timeline;
  - stream typed events и read model updates;
  - backpressure/reconnect contract;
  - authorization per initiator/user;
  - правила реакции frontend/backend consumers на events.
