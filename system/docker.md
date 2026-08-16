# Docker

## 컨테이너는 Docker가 발명한 게 아니다

컨테이너는 원래 **리눅스 커널에 있던 기능**이다. 하나의 리눅스 위에서 프로세스를 서로 격리시키는 장치들(namespace — 프로세스가 볼 수 있는 범위를 나눔, cgroup — CPU/메모리 사용량을 제한)이 이미 있었고, Docker는 그걸 **쓰기 쉽게 포장하고 배포 규격을 통일한 도구**다. (커널이 뭔지, 왜 격리는 커널만 할 수 있는지는 [system/operating-system-basics.md](operating-system-basics.md) 참고)

> **어원**: Docker는 **부두 노동자(dock worker)** 에서 왔다. 배에 화물 컨테이너를 싣고 내리는 사람. 컨테이너라는 이름도 실제 **화물 컨테이너**에서 온 것으로, 안에 뭐가 들었든(가전이든 바나나든) 겉 규격이 똑같아서 어느 항구·배·트럭에나 그대로 실을 수 있다는 게 핵심 아이디어다. 소프트웨어도 안에 뭐가 들었든(Java든 PostgreSQL이든) 규격만 맞추면 어느 서버에나 그대로 실을 수 있게 하자는 것.

## Mac에서는 왜 그냥 안 도나

macOS 커널은 리눅스가 아니라서 위의 namespace/cgroup이 없다. 그래서 Mac(과 Windows)에서는 **Docker Desktop이 내부에 아주 작은 리눅스 가상머신(VM)을 띄워두고, 컨테이너는 전부 그 VM 안에서 실행**한다.

터미널에서 `docker ...` 를 치면 그 명령이 Mac에서 직접 실행되는 게 아니라, 숨어 있는 리눅스 VM에게 "이거 해줘"라고 전달되는 구조다. 그래서:

- Docker Desktop 앱을 **실행해둬야** 명령이 동작한다. 앱이 꺼져 있으면 CLI는 설치돼 있어도 "Cannot connect to the Docker daemon" 에러가 난다.
- 반대로 이 구조 덕분에, **어느 OS에서 개발하든 컨테이너 안은 항상 같은 리눅스**다. "Mac은 이렇게, Windows는 저렇게" 하고 갈라지는 설치 문서가 필요 없어지는 이유가 이것이다.

## 설치 (macOS, Homebrew)

```bash
brew install --cask docker-desktop
```

설치 후 Docker Desktop 앱을 한 번 실행 → 메뉴 막대의 고래 아이콘이 멈추면(움직임 = 기동 중) 준비 완료.

동작 확인:

```bash
docker run hello-world
```
