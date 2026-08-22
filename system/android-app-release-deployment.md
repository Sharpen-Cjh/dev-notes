# 안드로이드 앱 배포 매뉴얼 (판도라의 상자 기준)

앱을 만들고 나서 "실제로 다른 사람 폰에 설치되게 하는" 단계에서 필요한 것들을 순서대로 정리한다. 처음 보는 사람도 이 문서만 보고 따라할 수 있게, 각 단계마다 "왜 이게 필요한지" 개념부터 설명하고 실제로 실행한 명령어를 그대로 남긴다. 배포 관련 작업을 새로 할 때마다 이 문서에 이어서 추가한다.

---

## 1단계 — 릴리즈 서명(Release Signing)

### 왜 필요한가

안드로이드는 APK 파일 하나하나가 **반드시 디지털 서명**이 돼 있어야 설치가 허용된다(예외 없음). 서명이 증명하는 것: "이 앱, 나중에 업데이트 버전이 나왔을 때 진짜 원래 만든 사람이 낸 게 맞다."

개발 중 `./gradlew installDebug`로 기기에 설치할 때는 안드로이드가 자동으로 **디버그 키**(모든 개발자 컴퓨터에 똑같이 자동 생성되는, 테스트 전용의 사실상 의미 없는 열쇠, 비밀번호도 `android`로 고정)로 서명해준다. 그래서 지금까지는 서명에 대해 신경 쓸 일이 없었다.

**왜 디버그 키로 배포하면 안 되는가**:
1. 디버그 키는 진짜 신원 증명이 아니다 — 아무 개발자 컴퓨터에나 똑같이 있는 열쇠라서.
2. 더 실질적인 문제: **한 번 배포한 앱은 이후 업데이트도 반드시 같은 열쇠로 서명해야 한다.** 다른 열쇠로 서명된 새 버전을 주면 안드로이드가 "이건 다른 앱이잖아"라며 설치를 거부한다(설치돼 있던 걸 지우고 새로 깔아야 하고, 그러면 로컬 데이터가 다 날아간다).

그래서 **개발자 본인만의 진짜 열쇠(keystore)**를 한 번 만들어서, 앞으로 나가는 모든 릴리즈 빌드가 항상 이 열쇠로 서명되도록 프로젝트에 연결해둔다.

**이름 유래**: "keystore"는 말 그대로 암호화 키(key)들을 담아두는 저장소(store)라는 뜻의 파일 포맷/컨테이너 이름이다.

### 실제로 한 작업

**1) keystore 파일 생성** — JDK에 기본 포함된 `keytool` 사용:

```bash
keytool -genkeypair \
  -v \
  -keystore keystore/pandorabox-release.jks \
  -alias pandorabox \
  -keyalg RSA \
  -keysize 2048 \
  -validity 10000 \
  -storepass "<임의의 강력한 비밀번호>" \
  -keypass "<임의의 강력한 비밀번호>" \
  -dname "CN=PandoraBox, OU=Personal, O=PandoraBox, L=Seoul, ST=Seoul, C=KR"
```

- `-keyalg RSA -keysize 2048`: 이전 FCM 정리 문서에서 다룬 것과 같은 비대칭키(RSA) 암호. 서명(구글이 검증)과 원리가 같다.
- `-validity 10000`: 유효기간을 일(day) 단위로, 10000일(약 27년)로 아주 길게 잡는다 — Play Store 같은 곳은 서명 인증서가 앱 수명 내내 유효해야 한다고 강력히 권장하기 때문에, 짧게 잡을 이유가 없다.
- `-dname`: 인증서에 들어가는 "누가 만들었는지" 메타데이터. 개인 프로젝트라 내용 자체는 크게 중요하지 않다.
- **참고**: 최신 `keytool`은 기본으로 PKCS12 포맷을 쓰는데, 이 포맷은 스펙상 store 비밀번호와 key 비밀번호가 같아야 한다 — 그래서 `-keypass`를 다르게 줘도 무시되고 `-storepass`로 통일된다는 경고가 뜬다. 정상 동작이다.

**2) `keystore.properties` 작성** — 위에서 만든 keystore 파일의 위치/비밀번호를 코드에 하드코딩하지 않고, 카카오 네이티브 앱 키를 다뤘던 것과 같은 패턴(`local.properties`처럼 **git에 올라가지 않는 별도 파일**)으로 관리한다:

```properties
storeFile=keystore/pandorabox-release.jks
storePassword=<위에서 만든 비밀번호>
keyAlias=pandorabox
keyPassword=<위에서 만든 비밀번호>
```

프로젝트 루트(`PandoraBox/keystore.properties`)에 저장.

**3) `.gitignore`에 추가**:
```gitignore
/keystore.properties
/keystore/
```
keystore 파일과 비밀번호 파일 둘 다 절대 git에 올라가면 안 된다 — 이 둘 중 하나라도 유출되면 남이 내 앱 명의로 서명된 가짜 업데이트를 만들 수 있다.

**4) `app/build.gradle.kts`에 연결**:

```kotlin
// keystore.properties에서 값을 읽어온다. 파일이 없으면(예: 이 저장소를 처음 받은 사람,
// 혹은 릴리즈 빌드가 필요 없는 CI) 릴리즈 서명 없이도 디버그 빌드는 그대로 되게 한다.
val keystoreProperties = Properties().apply {
    val file = rootProject.file("keystore.properties")
    if (file.exists()) load(FileInputStream(file))
}
val hasReleaseSigning = keystoreProperties.getProperty("storeFile") != null

android {
    signingConfigs {
        if (hasReleaseSigning) {
            create("release") {
                storeFile = rootProject.file(keystoreProperties.getProperty("storeFile"))
                storePassword = keystoreProperties.getProperty("storePassword")
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            if (hasReleaseSigning) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
}
```

`hasReleaseSigning` 체크를 넣은 이유: `keystore.properties`가 아예 없는 환경(예: 이 프로젝트를 새로 클론한 다른 컴퓨터)에서도 빌드 자체는 깨지지 않게 하기 위해서다 — 릴리즈 서명이 없으면 그냥 서명 안 된 release 빌드가 나올 뿐, gradle 설정 자체가 에러나진 않는다.

**5) 실제로 서명된 릴리즈 빌드 만들기**:
```bash
./gradlew assembleRelease
```
결과물: `app/build/outputs/apk/release/app-release.apk` — 이 파일을 친구에게 직접 보내서 설치하게 하거나, Play Store에 업로드할 수 있다.

### 겪은 문제 — 카카오 SDK 클래스 때문에 릴리즈 빌드만 실패

`./gradlew assembleRelease`를 처음 돌렸을 때 이런 에러로 실패했다:

```
AndroidManifest.xml:33: Error: AuthCodeHandlerActivity must extend android.app.Activity [Instantiatable]
```

`installDebug`로는 한 번도 안 걸리던 에러였는데, **릴리즈 빌드에만 있는 `lintVitalRelease`라는 검사 단계**가 원인이다 — 디버그 빌드는 이 전수 lint 검사를 안 돌리지만, 릴리즈 빌드는 기본적으로 돌리고 에러가 하나라도 있으면 빌드 자체를 막는다.

실제로는 카카오 SDK가 제공하는 `AuthCodeHandlerActivity`는 당연히 `Activity`를 상속하고 있다 — Lint가 외부 라이브러리 클래스의 바이트코드를 완전히 분석 못 해서 생기는 **오탐(false positive)**이다. 그래서 이 검사 하나만 매니페스트에서 명시적으로 끄는 방식으로 해결했다:

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:tools="http://schemas.android.com/tools">
    ...
    <activity
        android:name="com.kakao.sdk.auth.AuthCodeHandlerActivity"
        android:exported="true"
        tools:ignore="Instantiatable">
```

`tools:ignore`는 "이 특정 태그에서만 이 Lint 규칙 무시해줘"라는 뜻 — 전체 프로젝트의 Lint 설정을 건드리지 않고 딱 오탐 난 부분만 조용히 시킨다.

### 실제 서명 확인

빌드된 APK가 진짜 우리 release 키로 서명됐는지는 안드로이드 SDK의 `apksigner` 도구로 확인할 수 있다:

```bash
apksigner verify --print-certs app/build/outputs/apk/release/app-release.apk
```

출력된 인증서 지문(SHA-256 등)이 `keytool -list -v -keystore ...`로 확인한 keystore의 지문과 똑같으면, 의도한 키로 서명된 게 맞다는 뜻이다.

### 디버그 → 릴리즈로 처음 전환할 때 겪는 필연적인 문제

같은 기기에 이미 **디버그 서명**으로 설치돼 있는 상태에서 **릴리즈 서명** APK를 설치하려고 하면:

```
adb: failed to install ...: Failure [INSTALL_FAILED_UPDATE_INCOMPATIBLE:
Existing package com.pandorabox.app signatures do not match newer version; ignoring!]
```

이 에러가 뜬다 — 바로 위에서 설명한 "서명이 다르면 안드로이드가 다른 앱 취급한다"는 원리가 실제로 발동한 것이다(오류가 아니라 의도된 안전장치). 처음 한 번은 기존 걸 지우고(`adb uninstall <패키지명>`) 새로 설치해야 하고, 그 이후부터는 계속 같은 릴리즈 키로만 서명하면 업데이트가 정상적으로 인식된다. 지우면 그 기기의 로컬 데이터(로그인 세션, 캐시)는 날아간다.

### ⚠️ 절대 잃어버리면 안 되는 것

`keystore/pandorabox-release.jks` 파일과 `keystore.properties` 안의 비밀번호. **이 둘을 잃어버리면, 이미 배포한 앱을 다시는 업데이트할 방법이 없다**(친구들이 전부 삭제 후 재설치해야 함, 그러면 그 폰의 로컬 데이터도 날아감). git에는 못 올리니, 비밀번호 관리자나 별도 백업 위치에 안전하게 복사해두는 것을 권장.

---

*(앞으로 배포 관련 작업 — 예: Play Store 등록, APK 직접 배포 방식, 버전 관리 정책 등 — 이 이어서 여기 추가될 예정)*
