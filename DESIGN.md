# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-09-15
- Primary product surfaces: 회원가입, 로그인, 메모 목록·작성·상세·수정, 관리자 회원 목록
- Evidence reviewed: `app.py`, `README.md`; 별도 디자인 문서, 이미지, 로고, 컴포넌트 자산은 없음

## Brand
- Personality: 차분하고 개발자 친화적이며 기능에 집중하는 메모 도구
- Trust signals: 명확한 로그인 상태, 예측 가능한 피드백, 과장 없는 인터페이스
- Avoid: 밝은 배경, 화려한 그라데이션, 과도한 그림자와 애니메이션, 장식 위주의 요소

## Product goals
- Goals: 계정 진입 과정을 빠르고 명확하게 만들고 향후 메모 기능에 일관된 UI 기반 제공
- Non-goals: GitHub 화면의 픽셀 단위 복제, 복잡한 브랜딩, 마케팅 랜딩 페이지
- Success signals: 각 인증 작업과 현재 로그인 상태를 사용자가 즉시 이해함

## Personas and jobs
- Primary personas: 개인 메모를 간단히 관리하려는 사용자
- User jobs: 계정을 만들고, 로그인 상태를 유지하고, 안전하게 로그아웃하기
- Key contexts of use: 데스크톱 및 모바일 브라우저의 짧은 개인 작업

## Information architecture
- Primary navigation: 브랜드 홈 링크, 내 메모, 관리자(관리자 전용), 로그아웃
- Core routes/screens: `/signup`, `/login`, `/`, `/notes/new`, `/notes/<id>`, `/notes/<id>/edit`, `/admin/users`
- Content hierarchy: 브랜드 → 화면 제목 → 상태 메시지 → 핵심 폼 또는 로그인 상태 → 보조 행동

## Design principles
- Clarity first: 한 화면에는 하나의 주요 행동만 강조한다.
- GitHub-dark familiarity: 중성 다크 캔버스, 얇은 테두리, 파란 링크, 초록 주요 버튼을 일관되게 사용한다.
- Tradeoffs: 장식보다 가독성과 구현 단순성을 우선한다.

## Visual language
- Color: 캔버스 `#0d1117`, 표면 `#161b22`, 테두리 `#30363d`, 본문 `#f0f6fc`, 보조 텍스트 `#8b949e`, 강조 `#2f81f7`, 성공 행동 `#238636`
- Typography: 운영체제 기본 sans-serif, 작은 본문과 명확한 600 굵기 제목
- Spacing/layout rhythm: 4px 기반, 주요 간격은 16px/24px, 인증 카드 최대 너비 440px
- Shape/radius/elevation: 6–8px 모서리, 1px 테두리, 낮은 단일 그림자
- Motion: 120ms 이하의 상태 전환만 사용하며 reduced-motion을 존중
- Imagery/iconography: 이미지 없이 문자형 브랜드 마크와 최소한의 기호 사용

## Components
- Existing components to reuse: 공통 페이지 셸, 카드, 플래시 메시지, 필드, 버튼, 인증 전환 링크
- New/changed components: 메모 목록·편집기·상세 행동 영역, 빈 상태, 관리자 회원 테이블과 권한 배지
- Variants and states: 주요/보조 버튼, 기본/hover/focus 입력, 오류·상태 메시지
- Token/component ownership: 현재는 `app.py`의 `:root` CSS 변수가 단일 소스

## Accessibility
- Target standard: WCAG 2.1 AA 수준을 지향
- Keyboard/focus behavior: 모든 링크·입력·버튼에 명확한 `:focus-visible` 제공
- Contrast/readability: GitHub 다크 계열의 고대비 본문과 보조 텍스트 사용
- Screen-reader semantics: 연결된 label, heading 구조, 상태 메시지 `role="status"` 사용
- Reduced motion and sensory considerations: `prefers-reduced-motion`에서 전환 제거

## Responsive behavior
- Supported breakpoints/devices: 최신 데스크톱·모바일 브라우저, 320px 이상
- Layout adaptations: 520px 이하에서 외부 및 카드 내부 여백 축소
- Touch/hover differences: 주요 컨트롤 최소 높이 38px, hover 없이도 상태와 행동을 구분 가능

## Interaction states
- Loading: 현재 동기식 요청이므로 별도 상태 없음
- Empty: 메모가 없을 때 목록 영역에 명확한 빈 상태 표시
- Error: 카드 내부 붉은 톤의 상태 메시지
- Success: 회원가입·로그아웃 결과를 다음 화면의 상태 메시지로 표시
- Disabled: 현재 사용하지 않음
- Offline/slow network, if applicable: 현재 별도 처리 없음

## Content voice
- Tone: 간결하고 정중한 한국어
- Terminology: “계정 만들기”, “로그인”, “로그아웃”, “메모”를 일관되게 사용
- Microcopy rules: 행동 결과와 다음 단계를 한 문장으로 안내

## Implementation constraints
- Framework/styling system: Flask 단일 `app.py`, 템플릿과 CSS도 파일 내부 유지
- Security constraints: 사용자별 객체 권한, CSRF 토큰, 출력 이스케이프, CSP와 보안 헤더를 모든 신규 화면에 유지
- Resource constraints: 사용자당 메모 100개, 제목·본문 합계 1 MiB로 제한하고 목록에 현재 사용량 표시
- Design-token constraints: 색상은 `:root` 사용자 정의 속성을 우선 사용
- Performance constraints: 외부 폰트·이미지·CSS 의존성 없이 렌더링
- Compatibility constraints: CSS Grid/Flex 및 사용자 정의 속성을 지원하는 최신 브라우저
- Test/screenshot expectations: 인증 흐름 테스트와 각 핵심 화면의 모바일·데스크톱 육안 확인

## Open questions
- [ ] 실제 배포 환경의 HTTPS 종료 지점과 `SESSION_COOKIE_SECURE` 설정 / 운영 담당 / 세션 쿠키 보호에 영향
