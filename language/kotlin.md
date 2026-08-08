# Kotlin 언어 개념

## 람다(lambda)와 트레일링 람다

람다는 이름 없는 함수다.

```kotlin
val greet = { name: String -> "안녕, $name" }
```

함수의 **마지막 파라미터가 함수 타입(람다)**이면, 그 부분만 괄호 밖으로 빼서 쓸 수 있고 이름(파라미터명 =)도 생략할 수 있다. 이를 트레일링 람다(trailing lambda)라고 부른다.

```kotlin
fun doTwice(action: () -> Unit) { action(); action() }

doTwice({ println("안녕") })   // 원래 형태
doTwice { println("안녕") }    // 트레일링 람다로 축약
```

파라미터가 여러 개인 함수(예: Compose의 `Scaffold(bottomBar = {...}) { content }`)에서는, **마지막 파라미터만** 괄호 밖으로 뺄 수 있고 나머지는 이름을 붙여 괄호 안에 남아야 한다.

```kotlin
fun build(header: () -> Unit, body: () -> Unit) { ... }

build(
    header = { println("헤더") }   // 마지막이 아니라 이름 필요
) {
    println("본문")                // 마지막이라 이름 생략, 괄호 밖으로
}
```

## Unit 타입

자바의 `void`와 비슷하게 "리턴할 값이 없다"는 뜻이지만, 코틀린의 `Unit`은 **진짜 타입**이다(값이 하나뿐인 타입, 함수형 언어의 Unit 타입 개념에서 옴). 진짜 타입이기 때문에 `() -> Unit`처럼 함수 타입의 리턴 자리에도 쓸 수 있다. `void`는 그렇게 못 쓴다(제네릭 등에서 타입 취급 불가).

## Null 안전성

코틀린은 타입을 **기본적으로 null 불가**로 만들었다. null을 허용하려면 타입 뒤에 `?`를 명시해야 한다.

```kotlin
var caption: String = "위로"      // null 불가
var caption: String? = null       // ?를 붙여야 null 허용
```

- **안전 호출 `?.`**: `photo?.caption` — photo가 null이면 그냥 null 리턴, 아니면 caption 접근
- **엘비스 연산자 `?:`**: `a ?: b` — a가 null이면 b를 대신 사용. `?:`를 눕혀보면 엘비스 프레슬리 헤어스타일처럼 보인다고 붙은 이름.
- **`!!`(non-null assertion)**: "null 아니라고 확신해, 틀리면 크래시 내"라고 강제로 우회하는 것. 가능하면 피해야 한다(자바의 NPE 위험을 다시 불러오는 셈).
- **스마트 캐스트**: `if (x != null) { x.foo() }`처럼 null 체크 이후엔 컴파일러가 자동으로 non-null 타입으로 취급해준다.

**주의 — `by` 델리게이트와 스마트 캐스트**: `by` 델리게이트로 선언한 프로퍼티(예: Compose의 `val x by state`)는 호출할 때마다 다시 계산되는 값이라, 컴파일러가 "두 번 접근해도 같은 값"이라고 보장 못 해서 스마트 캐스트가 안 먹는다. 이럴 땐 일반 `val`에 한 번 담아서 써야 한다.

```kotlin
val revealedPhoto by viewModel.revealedPhoto.collectAsState()
val photo = revealedPhoto   // 일반 val로 한 번 담아야 스마트캐스트 가능
if (photo == null) { ... } else { photo.caption }  // OK
```

null 개념을 만든 토니 호어는 스스로 "10억 달러짜리 실수"라고 부를 만큼, 다른 언어들에선 NullPointerException(NPE)이 흔한 버그였다. 코틀린은 컴파일 시점에 이걸 원천 차단하려고 이 시스템을 만들었다.

## Sealed class

하위 타입이 **같은 파일 안에서 완전히 정해져 있는** 클래스. 일반 `open class`와 달리 어디서나 새로 상속할 수 없다.

```kotlin
sealed class Screen(val route: String) {
    object Home : Screen("home")
    object Archive : Screen("archive")
    object Register : Screen("register")
}
```

`when (screen) { ... }`으로 분기 처리할 때, 컴파일러가 모든 하위 타입을 다 처리했는지 검사해준다(하나 빠뜨리면 컴파일 경고/에러). 화면 종류처럼 "이미 다 정해져 있고 마음대로 안 늘어나는" 값에 적합.

`object`는 "이 타입의 인스턴스가 딱 하나만 존재한다"는 뜻(싱글턴).

## 확장 함수 (Extension Function)

원본 클래스를 건드리지 않고, 마치 그 클래스의 멤버 함수인 것처럼 함수를 밖에서 붙이는 기능.

```kotlin
fun Modifier.fillMaxSize(): Modifier { ... }   // Modifier 타입에 붙는 확장 함수
```

`Modifier` 타입 자체와 `fillMaxSize()` 확장 함수가 서로 다른 패키지에 정의되어 있을 수 있어서, `import`도 따로 해야 하는 경우가 흔하다(Compose에서 `padding`, `size`, `background` 등도 전부 `Modifier`의 확장 함수).

## suspend 함수와 코루틴

안드로이드 앱은 화면을 그리는 메인 스레드가 하나뿐이라, 느린 작업(디스크 I/O, 네트워크)을 메인 스레드에서 직접 하면 화면이 멈춘다(오래 걸리면 ANR로 앱이 강제 종료).

`suspend` 키워드가 붙은 함수는 "실행을 잠깐 멈췄다가, 준비되면 이어서 실행할 수 있는" 함수다. **코루틴(coroutine, "co-"협력 + "routine") 안에서만 호출 가능**하며, 코루틴은 메인 스레드를 막지 않고 백그라운드에서 작업을 처리한 뒤 결과를 갖고 돌아온다.

```kotlin
viewModelScope.launch {           // 코루틴 시작 (kotlinx.coroutines.launch import 필요)
    val result = someSuspendFun() // suspend 함수는 코루틴/다른 suspend 함수 안에서만 호출 가능
}
```

`launch` import를 빠뜨리면, 컴파일러가 "이게 코루틴 시작인지" 인식을 못 해서 안에 있는 suspend 호출을 "코루틴 밖에서 부른다"고 착각해 에러를 낸다.

`suspend` 함수 안에서 라벨 있는 return을 쓸 때: 람다 안에서는 그냥 `return`을 못 쓰고(어디로 돌아갈지 애매해서), `return@launch`처럼 **라벨을 붙여** 어느 람다를 빠져나갈지 명시해야 한다.

## UUID

"Universally Unique Identifier" — 전 세계에서 겹치지 않는 고유 식별자. DB 기본키를 auto-increment 정수 대신 UUID(문자열)로 쓰면, 나중에 서버 DB와 동기화할 때 ID 충돌 걱정이 없다.

```kotlin
val id = UUID.randomUUID().toString()
```

## 리소스 자동 정리: `.use { }`

파일 스트림처럼 다 쓰고 나면 반드시 닫아야(close) 하는 자원을, 블록이 끝나는 순간(에러가 나도) 자동으로 닫아주는 코틀린 관용구. 자바의 try-with-resources와 같은 목적.

```kotlin
inputStream.use { input ->
    // input 사용
}   // 블록 끝나면 자동으로 close() 호출됨
```
