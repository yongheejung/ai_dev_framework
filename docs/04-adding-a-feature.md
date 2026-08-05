# 4. 새 기능(도메인) 추가하기

이 프레임워크에는 이미 끝까지 연결된 실제 예시 도메인이 하나 있다 — **`agent-task`**
(bff-service 백엔드 + 웹 `features/agent-task` + 모바일 `features/agent_task`). 막힐 때마다 그
코드를 그대로 열어서 비교하면 된다. 이 문서는 그 패턴을 그대로 따라 **`note`**(제목+내용을 저장하는
아주 단순한 메모)라는 새 도메인을 처음부터 끝까지 추가하는 실습이다.

## 4.1 먼저 정할 것: core-service냐 bff-service냐

- **인증/트랜잭션/정합성이 중요한 데이터** → core-service. (사용자별 소유권, 결제, 재고처럼 "틀리면
  안 되는" 데이터)
- **가볍게 조회/기록하면 되는 데이터, AI 에이전트가 다루는 데이터** → bff-service.

`note`는 지금은 인증 없이 붙여서(agent-task와 동일한 난이도로) 패턴을 익히는 게 목적이다. 4.6절에서
"만약 core-service에 붙였다면 뭐가 달라지는지"를 정리한다.

## 4.2 백엔드 (bff-service)

**모델** — `bff-service/app/models.py`에 추가:

```python
class Note(Base):
    __tablename__ = "note"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(String(4000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**마이그레이션** 생성 (3.6절 참고):

```bash
cd bff-service
alembic revision --autogenerate -m "add note table"
alembic upgrade head
```

**라우터** — `bff-service/app/api/v1/notes.py` 새로 작성 (`agent_tasks.py`와 완전히 동일한 구조):

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.core.db import get_db
from app.core.responses import ApiResponse
from app.models import Note

router = APIRouter()


class CreateNoteRequest(BaseModel):
    title: str
    content: str


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    content: str
    created_at: datetime


@router.post("/notes", response_model=ApiResponse[NoteResponse])
async def create_note(request: CreateNoteRequest, db: AsyncSession = Depends(get_db)) -> ApiResponse[NoteResponse]:
    note = Note(title=request.title, content=request.content)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return ApiResponse.ok(NoteResponse.model_validate(note))


@router.get("/notes", response_model=ApiResponse[list[NoteResponse]])
async def list_notes(db: AsyncSession = Depends(get_db)) -> ApiResponse[list[NoteResponse]]:
    result = await db.execute(select(Note).order_by(Note.created_at.desc()))
    return ApiResponse.ok([NoteResponse.model_validate(n) for n in result.scalars().all()])
```

**등록** — `bff-service/app/main.py`에 한 줄 추가:

```python
from app.api.v1 import agent_tasks, notes, ping
...
app.include_router(notes.router, prefix="/api/v1", tags=["notes"])
```

확인:

```bash
docker compose up -d --build bff-service-migrate bff-service
curl -X POST http://localhost:8000/api/v1/notes -H "Content-Type: application/json" \
  -d '{"title":"첫 메모","content":"테스트"}'
curl http://localhost:8000/api/v1/notes
```

## 4.3 웹 프론트엔드

폴더 구조는 항상 `features/<domain>/{hooks,components,types.ts}` — `features/agent-task`를 그대로
복사해서 이름만 바꾸는 게 제일 빠르다.

**`frontend/src/features/note/types.ts`**:

```ts
export interface Note {
  id: string;
  title: string;
  content: string;
  created_at: string;
}

export interface CreateNoteInput {
  title: string;
  content: string;
}
```

**`frontend/src/features/note/hooks/useNotes.ts`**:

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { bffClient } from "@/shared/api/client";
import type { Note, CreateNoteInput } from "../types";

const NOTES_KEY = ["notes"];

export function useNotes() {
  return useQuery({
    queryKey: NOTES_KEY,
    queryFn: () => bffClient.get<Note[]>("/notes"),
  });
}

export function useCreateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateNoteInput) => bffClient.post<Note>("/notes", input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: NOTES_KEY }),
  });
}
```

**규칙 세 가지, 절대 어기지 말 것**:

1. 컴포넌트에서 `fetch`나 `axios`를 직접 쓰지 않는다 — 항상 `bffClient`/`coreClient`
   (`shared/api/client.ts`)를 거친다. 인증 필요한 도메인이면 `coreClient`.
2. 서버 상태(목록/생성 등)는 항상 TanStack Query 훅(`useQuery`/`useMutation`)으로만 다룬다.
   컴포넌트에서 직접 `useState` + `useEffect`로 fetch하지 않는다.
3. UI 요소는 `components/ui/`의 공용 파츠(`Button`, `Input`, `Card`, `Table`, `Dialog`)만 쓰고,
   색상은 절대 하드코딩하지 않는다(`bg-[#ffffff]` 같은 거 금지) — Tailwind 테마 토큰
   (`bg-background`, `text-foreground`, `text-destructive` 등, `globals.css`의 `@theme inline`)만
   쓴다. 새 색이 필요하면 컴포넌트에서 임의로 넣지 말고 `globals.css`에 토큰을 추가한다.

**컴포넌트/페이지**는 `features/agent-task/components/AgentTaskForm.tsx`,
`AgentTaskTable.tsx`와 `app/agent-tasks/page.tsx`를 그대로 본떠서 `features/note/components/`,
`app/notes/page.tsx`를 만들면 된다 — 구조가 완전히 동일해서 이름만 바꾸는 수준이다.

## 4.4 모바일 (Flutter)

역시 `features/agent_task`를 복제하는 게 제일 빠르다. `mobile/lib/features/note/`:

**`models/note.dart`**:

```dart
class Note {
  final String id;
  final String title;
  final String content;

  Note({required this.id, required this.title, required this.content});

  factory Note.fromJson(Map<String, dynamic> json) => Note(
        id: json['id'] as String,
        title: json['title'] as String,
        content: json['content'] as String,
      );
}
```

**`data/note_repository.dart`** (`agent_task_repository.dart`와 동일한 형태):

```dart
import '../../../core/api_client.dart';
import '../models/note.dart';

class NoteRepository {
  Future<List<Note>> list() => bffClient.get(
        '/notes',
        (json) => (json as List).map((e) => Note.fromJson(e as Map<String, dynamic>)).toList(),
      );

  Future<Note> create({required String title, required String content}) => bffClient.post(
        '/notes',
        {'title': title, 'content': content},
        (json) => Note.fromJson(json as Map<String, dynamic>),
      );
}

final noteRepository = NoteRepository();
```

**`providers/note_provider.dart`** (`agent_task_provider.dart`와 동일한 형태 — Riverpod
`AsyncNotifier`가 TanStack Query 훅 역할):

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/note_repository.dart';
import '../models/note.dart';

class NoteListNotifier extends AsyncNotifier<List<Note>> {
  @override
  Future<List<Note>> build() => noteRepository.list();

  Future<void> create({required String title, required String content}) async {
    await noteRepository.create(title: title, content: content);
    ref.invalidateSelf();
    await future;
  }
}

final noteListProvider = AsyncNotifierProvider<NoteListNotifier, List<Note>>(NoteListNotifier.new);
```

화면(`screens/note_screen.dart`)은 `ref.watch(noteListProvider)`로 구독하면 되고,
`features/agent_task/screens/agent_task_screen.dart`를 그대로 참고하면 된다. 색상은 여기서도
`Theme.of(context).colorScheme`만 쓴다 (`core/theme.dart`의 `_seedColor` 한 줄로 브랜드 색 전체가
바뀌는 구조를 깨지 말 것).

## 4.5 체크리스트 (새 도메인 추가할 때마다)

- [ ] 백엔드: 모델 → 마이그레이션 → 라우터/컨트롤러 → (필요하면) `main.py`/컨트롤러 등록
- [ ] 응답이 표준 `ApiResponse` 포맷(`{success, data, error}`)을 따르는가
- [ ] 인증이 필요한 도메인이면 core-service에 만들었는가, 또는 2.4절의 방식 중 하나로 보호했는가
- [ ] 웹: `features/<domain>/{types.ts, hooks/, components/}` + `app/<domain>/page.tsx`
- [ ] 웹: API 호출은 `bffClient`/`coreClient`만, 서버 상태는 TanStack Query만, 색상은 테마 토큰만
- [ ] 모바일: `features/<domain>/{models/, data/, providers/, screens/}`
- [ ] 모바일: API 호출은 `bffClient`/`coreClient`만, 서버 상태는 Riverpod `AsyncNotifier`만, 색상은 `ColorScheme`만
- [ ] `docker compose up -d --build`로 전체 스택에서 실제로 눌러서 확인

## 4.6 만약 core-service(인증 필요한 도메인)에 붙인다면

`note`를 core-service에 붙였다면 위 4.2와 다른 점:

- **엔티티**: JPA `@Entity` (`auth/User.java`처럼), **마이그레이션**: Flyway SQL (3.5절), 벤더
  폴더마다 SQL을 따로 관리해야 함.
- **컨트롤러**에서 `Authentication authentication` 파라미터로 현재 로그인한 사용자를 받을 수 있다
  (`authentication.getName()`이 username). 본인 데이터만 보게 하려면 리포지토리 쿼리에
  `WHERE user_id = :username` 조건을 추가.
- 관리자만 삭제 가능하게 하려면 `@PreAuthorize("hasRole('ADMIN')")` (2.4절 예시 그대로).
- 프론트/모바일에서는 `bffClient` 대신 **`coreClient`**를 쓴다 — 자동으로 `Authorization`,
  `X-Tenant-Id` 헤더가 붙는다.
