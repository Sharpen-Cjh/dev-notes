# 인증/비밀번호 보안 (Cloudflare Workers)

## 왜 비밀번호를 그대로 저장하면 안 되는가

DB가 해킹당하거나 유출되면, 평문으로 저장된 비밀번호는 그대로 다 털린다. **해싱**은 비밀번호를 "원본으로 되돌릴 수 없는 형태"로 변환해서 저장하는 것 — 로그인할 때는 입력받은 비밀번호를 같은 방식으로 다시 해싱해서, 저장해둔 해시값과 일치하는지만 비교한다(원본을 복원하는 게 아니다).

## Workers 환경에서 bcrypt를 잘 안 쓰는 이유

bcrypt 같은 인기 있는 비밀번호 해싱 라이브러리들은 보통 Node.js의 네이티브(C++) 코드에 의존하는데, Cloudflare Workers는 V8 isolate라는 가벼운 샌드박스 환경이라 이런 네이티브 의존성이 잘 안 돌아간다. 대신 **Web Crypto API**(`crypto.subtle`, 브라우저에도 있는 표준 API)가 Workers에 내장돼있고, 여기 포함된 **PBKDF2** 알고리즘을 쓴다.

## Salt(소금) — 왜 필요한가

같은 비밀번호(`"1234"`)를 여러 사람이 써도, 해싱 결과가 사람마다 다르게 나오도록 각자한테 임의의 랜덤 값(salt)을 하나씩 붙여서 같이 해싱한다. Salt가 없으면, 미리 계산해둔 "흔한 비밀번호 → 해시값" 표(레인보우 테이블)로 원본을 역추적당할 위험이 있다.

## `iterations` — 왜 일부러 느리게 만드는가

PBKDF2는 해싱 연산을 **일부러 수만~수십만 번 반복**한다(`iterations: 100000`). 무차별 대입 공격(가능한 비밀번호를 하나씩 다 시도해보는 것)을 하는 입장에서, 한 번 시도할 때마다 이 반복 연산을 다 거쳐야 하니 전체 공격 시간이 크게 늘어난다. 일반 해시 함수(SHA-256 한 번)는 반대로 "빠른 게 장점"이라 비밀번호 저장용으로는 오히려 취약하다.

## Base64 — 이진 데이터를 텍스트로 안전하게 바꾸는 변환

**핵심 이유는 하나다**: 많은 시스템/프로토콜이 순수 텍스트(사람이 읽을 수 있는 글자)만 안전하게 다룰 수 있고, 임의의 이진 데이터(binary)는 못 다룬다. base64는 "어떤 이진 데이터든 텍스트로 안전하게 바꿔주는 변환 방식"이다.

**왜 이진 데이터를 그대로 못 보내나**: 이미지 파일, 암호화된 토큰 같은 건 내부적으로 아무 숫자 값(바이트)이나 다 들어있다. 근데 URL, JSON 문자열, 이메일, HTTP 헤더 같은 통로들은 원래 "사람이 읽는 텍스트"만 다니라고 설계된 통로라서, 그 안에 이상한 바이트 값이 섞여 들어가면 깨지거나 프로토콜 제어 문자로 오해받을 수 있다.

**base64가 하는 일**: 어떤 이진 데이터든, 딱 64개의 안전한 글자(A-Z, a-z, 0-9, +, /)만 써서 표현하도록 다시 인코딩해준다. 그러면 원래 텍스트만 다니던 통로에 그대로 태울 수 있다.

JWT 토큰(`eyJhbGci...`)이 딱 이 경우다 — JWT 안엔 JSON 데이터가 들어있는데, 이게 URL/헤더에 안전하게 실려가려면 텍스트로 변환돼야 해서 base64로 인코딩된 것. **재밌는 사실**: JSON은 항상 `{"`로 시작하는데, 이걸 base64로 바꾸면 항상 `eyJ`로 시작한다 — 그래서 `eyJ`로 시작하는 문자열을 보면 "아 이거 base64로 인코딩된 JSON이구나"라고 바로 알아채는 경우가 많다.

**중요한 오해 포인트**: base64는 **암호화가 아니다**. 누구나 디코딩하면 원본을 그대로 볼 수 있다(그냥 "표현 방식 변환"일 뿐, "비밀로 만드는 것"이 아니다). JWT가 안전한 이유는 base64 때문이 아니라, 별도의 **서명**이 붙어서 "위조 여부"를 검증할 수 있기 때문이다.

## JWT(JSON Web Token) 구조

점(`.`)으로 구분된 세 조각: `헤더.내용.서명`

- **헤더**: `{"alg":"HS256","typ":"JWT"}` — 어떤 서명 방식을 썼는지
- **내용(payload)**: `{"sub":"유저ID", "exp":만료시각}` — 담고 싶은 정보
- **서명**: 앞의 두 조각을 합친 문자열을, 서버만 아는 비밀 키로 암호화한 값

각 조각을 base64로 인코딩해서 점으로 이어붙인 게 실제 토큰 문자열. **핵심은 서명** — 누군가 `내용` 부분을 몰래 바꿔치기해도(예: 유저ID를 남의 걸로), 비밀 키 없이는 서명을 다시 못 맞추므로, 서버가 검증할 때 서명이 안 맞으면 바로 위조를 잡아낼 수 있다.

## Workers의 Secret — 비밀 키를 코드/설정파일에 안 적는 법

JWT 서명용 비밀 키를 `wrangler.jsonc`에 그냥 텍스트로 적으면, 그 파일이 깃 저장소에 올라갈 때 키도 같이 노출된다. Cloudflare는 이런 민감한 값을 위해 **secret**이라는 별도 저장 방식을 제공한다 — 설정 파일에 안 남고, 암호화된 채로 Cloudflare 쪽에만 저장됨.

```bash
npx wrangler secret put JWT_SECRET --local
```
실행하면 값을 입력하라고 뜨고, 입력한 값은 파일에 안 남는다. (`vars`는 평문 설정값, `secrets`는 암호화된 민감값 — 이 둘을 구분해서 쓴다.)

## 실제 코드

```typescript
async function hashPassword(password: string): Promise<string> {
	const salt = crypto.getRandomValues(new Uint8Array(16));

	const keyMaterial = await crypto.subtle.importKey(
		"raw",
		new TextEncoder().encode(password),
		"PBKDF2",
		false,
		["deriveBits"]
	);

	const derivedBits = await crypto.subtle.deriveBits(
		{ name: "PBKDF2", salt, iterations: 100000, hash: "SHA-256" },
		keyMaterial,
		256
	);

	const toHex = (bytes: Uint8Array) => [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
	return `${toHex(salt)}:${toHex(new Uint8Array(derivedBits))}`;
}
```

## 로그인 시 비밀번호 검증

저장할 때(`hashPassword`)는 salt를 새로 만들지만, 검증할 때(`verifyPassword`)는 **저장해뒀던 salt를 다시 꺼내서 그대로 재사용**한다 — 같은 salt로 같은 계산을 했을 때 같은 결과가 나오면 비밀번호가 맞다는 뜻.

```typescript
async function verifyPassword(password: string, storedHash: string): Promise<boolean> {
	const [saltHex, hashHex] = storedHash.split(":");
	const salt = fromHex(saltHex);
	// ... hashPassword와 동일한 PBKDF2 계산 ...
	return toHex(new Uint8Array(derivedBits)) === hashHex;
}
```

**로그인 실패 메시지는 항상 똑같이**: "이메일이 없어서 실패"인지 "비밀번호가 틀려서 실패"인지 구분해서 알려주면 안 된다. 구분해서 알려주면 공격자가 그걸로 "이 이메일이 가입돼있는지"를 알아낼 수 있다(계정 존재 여부 탐지). 그래서 `!user || !(await verifyPassword(...))` 처럼 두 실패 케이스를 하나의 조건으로 묶어서 같은 에러 메시지를 낸다.

## D1 조회: `.first()` vs `.run()`

- `.run()` — INSERT/UPDATE/DELETE처럼 결과 행이 필요 없는 쓰기 작업에 사용.
- `.first<T>()` — 조건에 맞는 행을 하나만 가져와서 타입 `T`의 객체로 돌려줌 (없으면 `null`). 로그인처럼 "이메일로 유저 한 명 찾기"에 사용.

**단계별 설명**:
1. `crypto.getRandomValues(...)` — 랜덤 salt 16바이트 생성.
2. `crypto.subtle.importKey(...)` — 비밀번호 문자열을 PBKDF2가 다룰 수 있는 "키 재료" 형태로 변환.
3. `crypto.subtle.deriveBits(...)` — 실제 해싱 실행(salt + 10만 번 반복).
4. **salt와 해시값을 `:`로 합쳐서 하나의 문자열로 저장** — 나중에 로그인 검증할 때 "이 사람한테 어떤 salt를 썼었는지" 알아야 다시 계산해서 비교할 수 있으므로, salt 자체도 (비밀은 아니니) 같이 저장해둬야 한다.
