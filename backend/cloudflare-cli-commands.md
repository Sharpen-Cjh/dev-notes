# Cloudflare CLI 명령어 모음

Workers/D1/R2 관련해서 실제로 쓴 명령어들을 나올 때마다 여기 누적 기록. 개념 설명은 [serverless-cloudflare-workers.md](serverless-cloudflare-workers.md) 참고.

## 프로젝트 생성

```bash
npm create cloudflare@latest pandorabox-api
```
새 Workers 프로젝트 폴더를 스캐폴딩(초기 생성)한다. 대화형으로 템플릿("Hello World example" 등), Worker 종류("Worker only"), 언어(TypeScript)를 물어본다. `git init`까지 자동으로 해준다.

## 계정/로그인

```bash
npx wrangler login
npx wrangler logout
```
로컬 컴퓨터를 Cloudflare 계정과 연결/해제. 브라우저가 열리며 승인 절차를 거친다. **계정 상태(이메일 인증 등)가 바뀌었는데 CLI가 옛날 상태를 들고 있어서 에러가 날 때, logout 후 login으로 세션을 새로고침하면 해결되는 경우가 많다.**

## 로컬 개발/배포

```bash
npx wrangler dev       # 로컬에서 미리 실행/테스트 (http://localhost:8787)
npx wrangler deploy    # 실제 Cloudflare 서버에 배포 → 진짜 인터넷 주소 생김
```
**반드시 프로젝트 폴더(`wrangler.jsonc`가 있는 곳) 안에서 실행해야 한다.** 바깥에서 실행하면 설정 파일을 못 찾아서 엉뚱한 에러(정적 사이트 배포 시도 등)가 난다.

## D1 (데이터베이스)

```bash
npx wrangler d1 create pandorabox-db
```
D1 데이터베이스를 새로 만든다. 실행 결과로 나오는 `database_id`를 `wrangler.jsonc`의 `d1_databases` 설정에 넣어야 Worker 코드에서 그 DB에 접근할 수 있다.

```bash
npx wrangler d1 execute pandorabox-db --file=./schema.sql
```
SQL 파일(CREATE TABLE 등)을 D1에 실제로 적용한다. `--local` 옵션을 붙이면 로컬 테스트용 D1에만 적용되고, 안 붙이면 실제 원격(production) D1에 적용된다.

## D1은 사실 SQLite다

Cloudflare가 DB 엔진을 새로 만든 게 아니라, **SQLite 엔진을 그대로 가져다가 서버에서 호스팅/복제해서 안전하게 여러 곳에서 접근 가능하게 만든 서비스**다. Android Room이 내부적으로 쓰는 그 SQLite와 완전히 같은 엔진 — 차이는 Room의 SQLite는 폰 안에, D1의 SQLite는 Cloudflare 서버에 있다는 것뿐. `CREATE TABLE`, `PRIMARY KEY` 같은 문법도 Room의 `@Query`에 쓰던 것과 같은 SQL 방언이다.

(Docker가 컨테이너를 발명한 게 아니라 리눅스 커널 기능을 포장한 것과 같은 패턴 — [system/docker.md](../system/docker.md) 참고)

### `CREATE TABLE`에 세미콜론(`;`) 빠뜨리면 생기는 일

문장을 여러 개 이어 쓸 때 세미콜론으로 끝을 안 표시하면, 파서가 다음 문장이 시작되는 줄 몰라서 그 경계에서 에러가 난다. **문제는, 에러가 나기 전까지 앞쪽 문장은 이미 정상 실행/저장됐을 수 있다는 것** — "전체가 실패했으니 아무것도 안 만들어졌겠지"라고 생각하면 안 된다. 스키마를 고친 뒤 재실행해도 "이미 존재하는 테이블"은 조용히 건너뛰어질 수 있어서, 옛날 버전이 남아있는 채로 다음 단계에서 뜬금없는 에러(예: 없는 컬럼 이름)를 만날 수 있다. 스키마를 고쳤으면 `DROP TABLE`로 지우고 처음부터 다시 만드는 게 안전하다.

## R2 (파일 저장소)

```bash
npx wrangler r2 bucket create pandorabox-photos
```
사진 파일을 저장할 R2 버킷(저장 공간)을 생성한다.

## 로그/디버깅

```bash
npx wrangler tail
```
배포된 Worker에 지금 들어오는 요청과 로그를 실시간으로 스트리밍해서 보여준다. 디버깅용.
