# R2 파일 저장 (Cloudflare Workers)

## 버킷(bucket)이란

R2 안에서 파일들을 모아두는 저장 공간 하나. D1에서 데이터베이스 하나를 만들듯, 프로젝트 하나에 R2 버킷 하나를 만든다. 버킷 안 파일 이름에 `/`를 넣으면 폴더처럼 보이지만(예: `photos/uuid.jpg`) 실제 폴더 구조는 아니고 그냥 이름 규칙이다.

```bash
npx wrangler r2 bucket create pandorabox-photos
```

**활성화 필요**: R2는 계정에서 별도 활성화(결제 수단 등록, 무료 한도 안에서는 청구 안 됨)가 먼저 필요하다 — Cloudflare 대시보드 → R2 → "Get started" 화면에서 처리. "R2 Data Catalog"는 대용량 분석용 별개 기능이라 혼동 주의.

## R2 요금 구조

3가지 항목으로 나뉜다:

- **Storage(저장 용량)**: 10GB/월 무료, 초과분 GB당 $0.015/월. 쌓여있는 총 데이터양.
- **Class A operations**: 월 100만 건 무료, 초과분 100만 건당 $4.50. **상태를 바꾸는 작업**(업로드/쓰기, 목록 조회 등).
- **Class B operations**: 월 1000만 건 무료, 초과분 100만 건당 $0.36. **읽는 작업**(파일 조회/다운로드).
- **DeleteObject는 아예 무료** — 두 클래스 어디에도 안 잡힘.

**규모별 대략적인 계산** (1인당 사진 15장, 평균 4MB 기준):
- 1000명: 저장용량만 10GB 초과분 발생 → 월 약 $0.75~1. 조회/업로드는 여전히 무료 한도 안.
- 10,000명: 저장용량 약 600GB(초과분 약 $8.85) + 하루 50회 조회 기준 Class B 살짝 초과(약 $1.80) → **합쳐서 월 $10~15 수준**.

**AWS S3였다면 어땠을까**: 다운로드(egress) 요금이 있는 S3라면, 만 명이 하루 50번씩 사진을 조회하는 트래픽(한 달에 약 60TB)만으로 **월 $4,000 이상**이 egress 요금으로 나갔을 것 — R2를 고른 이유(egress 무료)가 사용자 수가 늘어날수록 격차가 커지는 지점.

## Presigned URL 대신 Worker가 직접 중계하는 방식을 선택한 이유

원래 계획은 "클라이언트가 R2에 직접 업로드/다운로드"(presigned URL, AWS S3 서명 방식 SigV4 필요)였는데, 이건 대규모 트래픽에서 서버 부담을 줄이려는 최적화다. 개인 프로젝트(사용자 소수, 1인당 15장 제한) 규모에서는 이 최적화가 사실상 무의미하고, SigV4를 직접 구현하는 복잡도만 늘어난다. 그래서 **Worker가 R2 바인딩(`env.버킷.put/get/delete`)으로 직접 파일을 중계**하는 단순한 방식을 택함.

## `request.formData()` — 파일과 텍스트를 한 요청에 담아 받기

이미지 파일 같은 바이너리와 `caption` 같은 텍스트를 같이 보낼 때 쓰는 표준 방식(`multipart/form-data`).

```typescript
const formData = await request.formData();
const caption = formData.get("caption");       // string
const file = formData.get("photo");             // File 인스턴스
if (!(file instanceof File)) { /* 파일 아님 처리 */ }
await env.pandorabox_photos.put(r2Key, await file.arrayBuffer());
```

## R2 바인딩 기본 동작

```typescript
await env.버킷.put(key, bytes);   // 저장
const object = await env.버킷.get(key);   // 조회, object.body가 실제 데이터 스트림
await env.버킷.delete(key);   // 삭제 (R2 Class 과금에도 안 잡히는 무료 작업)

return new Response(object.body, { headers: { "Content-Type": "image/jpeg" } });
```

## 접근 권한(authorization) — 로그인 여부와는 다른 체크

**인증(authentication)**은 "이 요청 보낸 사람이 누군지"만 확인한다(`getUserId`). **접근 권한(authorization)**은 "그 사람이 이 특정 자원을 볼 자격이 있는지"를 추가로 확인하는 것 — 로그인만 됐다고 아무 사진이나 다 보여주면 안 된다.

```typescript
if (photo.owner_id !== myId) {
	const share = await env.pandorabox_db
		.prepare(`SELECT 1 FROM box_shares WHERE owner_id = ? AND viewer_id = ? AND status = 'accepted'`)
		.bind(photo.owner_id, myId)
		.first();
	if (!share) return new Response("Forbidden", { status: 403 });
}
```

내 사진이 아니면, `box_shares`에 accepted 상태로 연결돼있는지 다시 확인한다. 클라이언트가 보내는 값(`ownerIds` 쿼리 파라미터 등)은 절대 그대로 믿지 않고, 항상 서버가 DB를 다시 조회해서 검증한다.

## 동적 개수의 `IN (...)` 조건 만들기

`ownerIds`가 몇 개 올지 미리 모를 때, 개수만큼 `?`를 만들어 SQL을 조립한다.

```typescript
const placeholders = ownerIds.map(() => "?").join(",");  // "?,?,?"
const { results } = await env.pandorabox_db
	.prepare(`SELECT * FROM photos WHERE owner_id IN (${placeholders})`)
	.bind(...ownerIds)
	.all();
```

## `result.meta.changes` — UPDATE/DELETE가 실제로 몇 행을 건드렸는지

```typescript
const result = await env.pandorabox_db
	.prepare(`UPDATE photos SET caption = ? WHERE id = ? AND owner_id = ?`)
	.bind(caption, photoId, myId)
	.run();

if (result.meta.changes === 0) {
	// owner_id 조건 때문에 남의 사진이면 조용히 0행 변경됨 — 에러가 안 나므로 이렇게 직접 확인해야 함
}
```

`WHERE owner_id = ?` 조건이 안 맞으면 SQL 자체는 에러 없이 그냥 "해당 없음"으로 0행 처리된다. 권한 없는 시도를 잡아내려면 `changes` 값을 직접 확인해야 한다.
