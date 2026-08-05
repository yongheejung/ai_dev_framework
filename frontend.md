웹(Web) 표준: Next.js (React 기반)
이유: 글로벌 시장 점유율 1위로 AI가 학습한 소스코드 데이터가 가장 많습니다. SEO(검색 최적화)가 기본 지원되며, 파일 기반 라우팅 시스템 체계가 명확하여 AI가 새로운 페이지(page.tsx)를 생성하고 관리하기 매우 쉽습니다.

앱(Mobile App) 표준: Flutter
이유: 하나의 코드로 iOS와 Android를 동시에 출시할 수 있어 1인 개발자에게 필수적입니다. 리액트 네이티브에 비해 위젯(Widget) 단위의 규격화가 잘 되어 있어, AI 에이전트가 화면 레이아웃을 에러 없이 짜내기에 훨씬 유리합니다.

스타일링(Design): Tailwind CSS + shadcn/ui
이유: 별도의 CSS 파일을 만들지 않고 HTML 태그 안에 클래스명만 적는 구조라 AI가 화면 스타일을 고치기 가장 편합니다. 특히 shadcn/ui나 Radix UI 같은 무스타일(Headless) 컴포넌트를 기본 뼈대로 잡으면, 대기업급 UI/UX와 웹 접근성 표준을 코드 복사만으로 확보할 수 있습니다.

AI 친화적 프론트엔드 폴더 구조 (Architecture)

```
src/
├── app/                  # [1] Next.js 페이지 라우팅 (AI가 페이지 추가하는 곳)
│   ├── layout.tsx        # 전사 공통 레이아웃 (GNB, 푸터)
│   ├── page.tsx          # 메인 화면
│   └── customers/        # 고객 관리 메뉴
│       └── page.tsx      # 고객 리스트 화면
├── components/           # [2] 재사용 가능한 순수 UI 컴포넌트 (공통 부품창고)
│   └── ui/               # Button, Input, Modal, Table (shadcn 기반)
├── features/             # [3] 도메인별 비즈니스 로직 + UI 결합 (AI 작업 핵심 구역)
│   └── customer/         # 고객(Customer) 관련 기능 묶음
│       ├── components/   # CustomerTable.tsx, CustomerForm.tsx
│       ├── hooks/        # useCustomerQuery.ts (API 호출 및 상태 관리)
│       └── types.ts      # 타입 정의
└── shared/               # [4] 공통 유틸리티
    ├── api/              # Axios / Fetch 공통 설정 (인터셉터, 토큰 재발급)
    └── utils/            # 날짜 포맷팅 등 공통 함수
```

① API 통신 및 상태 관리의 표준화 (TanStack Query 활용)

UI 컴포넌트 내부에 useEffect나 fetch를 직접 코딩하지 못하게 막아야 합니다. 모든 데이터 통신은 hooks/ 폴더에 useQuery, useMutation으로 표준화합니다. 효과: AI가 데이터 관리를 단 한 줄의 커스텀 훅으로 처리할 수 있어 코드가 파편화되지 않습니다.

예)
```typescript
// AI가 생성하는 표준 Hooks 예시
export const useCustomers = () => {
  return useQuery({ queryKey: ['customers'], queryFn: customerApi.getAll });
};
```

② 공통 컴포넌트(부품)의 사전 정의

AI에게 "테이블 화면 만들어줘"라고 하면 맨땅에 태그를 짜느라 디자인이 망가집니다. 사전에 components/ui/에 완벽한 디자인의 Button, Input, Table 부품을 밀어 넣어두고, AI에게는 "우리가 미리 만든 ui/Table 부품을 수입(Import)해서 데이터만 바인딩해"라고 제한해야 합니다. (아웃시스템즈의 위젯 시스템을 내 코드로 구현하는 핵심)

③ 디자인 시스템 및 다크모드 표준화

색상 코드를 #FFFFFF, #000000 식으로 하드 코딩하면 유지보수가 불가능합니다. Tailwind Config에 primary, secondary, background 등의 가상 색상 이름을 지정해 두고, AI는 오직 이 테마 이름만 사용하도록 규칙을 줍니다. 나중에 고객사가 "우리 회사 브랜드 색상인 초록색으로 바꿔주세요"라고 하면 설정 파일의 primary 색상 한 줄만 바꾸면 전 시스템이 자동 대응됩니다.
