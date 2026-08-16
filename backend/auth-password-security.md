# 인증/비밀번호 보안 (Cloudflare Workers)

## 왜 비밀번호를 그대로 저장하면 안 되는가

DB가 해킹당하거나 유출되면, 평문으로 저장된 비밀번호는 그대로 다 털린다. **해싱**은 비밀번호를 "원본으로 되돌릴 수 없는 형태"로 변환해서 저장하는 것 — 로그인할 때는 입력받은 비밀번호를 같은 방식으로 다시 해싱해서, 저장해둔 해시값과 일치하는지만 비교한다(원본을 복원하는 게 아니다).

## Workers 환경에서 bcrypt를 잘 안 쓰는 이유

bcrypt 같은 인기 있는 비밀번호 해싱 라이브러리들은 보통 Node.js의 네이티브(C++) 코드에 의존하는데, Cloudflare Workers는 V8 isolate라는 가벼운 샌드박스 환경이라 이런 네이티브 의존성이 잘 안 돌아간다. 대신 **Web Crypto API**(`crypto.subtle`, 브라우저에도 있는 표준 API)가 Workers에 내장돼있고, 여기 포함된 **PBKDF2** 알고리즘을 쓴다.

## Salt(소금) — 왜 필요한가

같은 비밀번호(`"1234"`)를 여러 사람이 써도, 해싱 결과가 사람마다 다르게 나오도록 각자한테 임의의 랜덤 값(salt)을 하나씩 붙여서 같이 해싱한다. Salt가 없으면, 미리 계산해둔 "흔한 비밀번호 → 해시값" 표(레인보우 테이블)로 원본을 역추적당할 위험이 있다.

## `iterations` — 왜 일부러 느리게 만드는가

PBKDF2는 해싱 연산을 **일부러 수만~수십만 번 반복**한다(`iterations: 100000`). 무차별 대입 공격(가능한 비밀번호를 하나씩 다 시도해보는 것)을 하는 입장에서, 한 번 시도할 때마다 이 반복 연산을 다 거쳐야 하니 전체 공격 시간이 크게 늘어난다. 일반 해시 함수(SHA-256 한 번)는 반대로 "빠른 게 장점"이라 비밀번호 저장용으로는 오히려 취약하다.

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

**단계별 설명**:
1. `crypto.getRandomValues(...)` — 랜덤 salt 16바이트 생성.
2. `crypto.subtle.importKey(...)` — 비밀번호 문자열을 PBKDF2가 다룰 수 있는 "키 재료" 형태로 변환.
3. `crypto.subtle.deriveBits(...)` — 실제 해싱 실행(salt + 10만 번 반복).
4. **salt와 해시값을 `:`로 합쳐서 하나의 문자열로 저장** — 나중에 로그인 검증할 때 "이 사람한테 어떤 salt를 썼었는지" 알아야 다시 계산해서 비교할 수 있으므로, salt 자체도 (비밀은 아니니) 같이 저장해둬야 한다.
