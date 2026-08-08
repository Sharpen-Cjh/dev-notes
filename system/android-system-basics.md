# 안드로이드 시스템 기초 (파일/스레드)

## Uri는 파일 경로가 아니다

갤러리 등에서 고른 사진은 실제 파일 경로가 아니라 `Uri`("주소" 같은 것)로 넘어온다. 그 사진이 실제로 어디 있는지(내 폰 안, 클라우드 등)는 시스템만 안다. 앱이 그 내용을 실제로 다루려면, 직접 바이트를 읽어서 앱 전용 저장공간에 복사해둬야 한다 — 원본이 나중에 삭제돼도 앱 안의 복사본은 안전하게 남기 위해서.

비유: 친구 사진첩에서 마음에 드는 사진을 봤다고, 그 사진첩 자체가 내 것이 되는 게 아니다. 나중에 친구가 사진첩을 버리면 나도 그 사진을 잃는다. 그래서 사진을 **복사해서 내 서랍에 따로 보관**해야 한다.

## Context

"지금 앱이 안드로이드 시스템 어디에 있는지"에 대한 정보를 담은 객체. 파일 시스템 접근, 리소스 접근 등에 필요하다.

- `context.filesDir`: 앱 전용 내부 저장 공간(다른 앱은 접근 불가).
- Activity Context를 ViewModel처럼 오래 사는 객체에 주입하면 메모리 누수 위험이 있지만, **Application Context**(`@ApplicationContext`, 앱과 생명주기가 같음)는 안전하게 주입해도 된다.

## ContentResolver — Uri에서 실제 데이터 읽기

```kotlin
context.contentResolver.openInputStream(uri)
```

`contentResolver`는 "사서" 같은 역할 — `Uri`(주소/청구기호)만 주면, 실제 데이터가 어디 있든 찾아서 읽을 수 있는 스트림을 열어준다.

## 파일 복사 흐름 (Uri → 앱 내부 저장소)

```kotlin
private suspend fun copyToInternalStorage(uri: Uri): String = withContext(Dispatchers.IO) {
    val photosDir = File(context.filesDir, "photos").apply { mkdirs() }      // ① 저장할 폴더 준비(없으면 생성)
    val destFile = File(photosDir, "${UUID.randomUUID()}.jpg")               // ② 새 파일 이름 결정
    context.contentResolver.openInputStream(uri)?.use { input ->             // ③ 원본 읽기 스트림 열기
        destFile.outputStream().use { output ->                              // ④ 대상 쓰기 스트림 열기
            input.copyTo(output)                                            // ⑤ 실제 복사
        }
    }
    destFile.absolutePath                                                   // ⑥ 복사본의 실제 경로 리턴
}
```

각 스트림은 `.use { }`로 감싸서, 블록이 끝나면(에러가 나도) 자동으로 닫히게 한다.

## 메인 스레드를 막지 않기: `withContext(Dispatchers.IO)`

`viewModelScope.launch { }`는 기본적으로 메인(화면) 스레드에서 시작된다. 파일 복사 같은 디스크 작업을 메인 스레드에서 직접 하면 화면이 멈출 수 있다. `withContext(Dispatchers.IO)`로 감싸면, 그 블록만 **백그라운드(IO 전용) 스레드로 옮겨서** 실행하고, 끝나면 자동으로 원래 흐름(메인 스레드)으로 돌아온다.

- `Dispatchers.Main`: 화면 그리는 메인 스레드
- `Dispatchers.IO`: 파일/네트워크 등 I/O 작업에 최적화된 백그라운드 스레드 풀

## Photo Picker와 권한

시스템이 제공하는 Photo Picker를 쓰면, 앱이 저장소 전체에 접근할 수 있는 강력한 런타임 권한(`READ_MEDIA_IMAGES` 등)을 요청할 필요가 없다. 사진 선택 UI 자체가 앱이 아니라 **시스템이 별도로 띄우는 신뢰된 화면**이고, 사용자가 고른 사진 하나에 대한 접근 권한만 앱에 넘겨주는 구조이기 때문이다. (자세한 내용은 [frontend/android-jetpack-compose.md](../frontend/android-jetpack-compose.md) 참고)
