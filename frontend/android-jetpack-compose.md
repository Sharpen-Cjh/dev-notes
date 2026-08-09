# Android Jetpack Compose

## Composable 함수

`@Composable` 어노테이션이 붙은 함수는 "화면의 일부를 그리는 방법"을 선언하는 함수다. 리액트의 함수형 컴포넌트와 개념적으로 유사하다.

## Scaffold와 슬롯(slot) 기반 레이아웃

`Scaffold`는 화면의 기본 뼈대(상단바/하단바/본문 위치)를 잡아주는 컴포저블. 실제 내용은 각 슬롯에 람다(콜백)로 넘겨받는다 — "레이아웃 배치는 내가 할게, 실제 내용은 네가 람다로 줘"라는 설계.

```kotlin
Scaffold(
    bottomBar = { NavigationBar { ... } }
) { innerPadding ->
    // content 파라미터: 이름 생략, 트레일링 람다로 옴
    NavHost(..., modifier = Modifier.padding(innerPadding))
}
```

- `bottomBar`는 마지막 파라미터가 아니라서 이름 붙여 괄호 안에
- `content`는 마지막 파라미터라서 이름 생략하고 괄호 밖 트레일링 람다로
- `innerPadding: PaddingValues`는 Scaffold가 "하단바가 이만큼 공간을 차지하니, 본문은 이만큼 여백을 줘야 안 가려진다"고 계산해서 넘겨주는 값. 파라미터 이름(`innerPadding`)은 개발자 마음대로 지어도 된다.

## State와 리컴포지션

Compose는 `State`로 감싼 값이 바뀔 때만 화면을 다시 그린다(recompose). 그냥 일반 변수는 값이 바뀌어도 화면에 반영 안 된다.

### `remember { mutableStateOf(...) }`

화면 로컬 상태. 리컴포지션 돼도 값이 유지된다.

```kotlin
var caption by remember { mutableStateOf("") }
```

`by` 델리게이트를 쓰면 `.value`를 매번 안 붙이고 바로 값처럼 읽고 쓸 수 있다. `mutableStateOf`는 읽기/쓰기(get/set)가 다 되는 `MutableState`를 만들기 때문에, `by`를 쓰려면 `getValue`뿐 아니라 `setValue`도 import해야 한다(반면 읽기 전용 `State`는 `getValue`만 있으면 됨).

### `collectAsState()`

Room의 `Flow`(구독해야 값이 오는 스트림)를 Compose가 감시할 수 있는 `State`로 바꿔주는 함수. StateFlow/Flow가 바뀔 때마다 자동으로 리컴포지션을 트리거한다.

```kotlin
val photos by viewModel.photos.collectAsState(initial = emptyList())
```

## ViewModel과 hiltViewModel()

`ViewModel`은 화면(Activity/화면 이동)보다 오래 살아남는 상태 보관 객체. `@HiltViewModel` + `@Inject constructor`로 선언하면, Compose 화면에서 `hiltViewModel()`을 호출해 Hilt가 자동으로 인스턴스를 만들고(또는 재사용하고) 연결해준다.

```kotlin
@Composable
fun HomeScreen(viewModel: HomeViewModel = hiltViewModel()) { ... }
```

ViewModel 안에서는 보통 상태를 두 버전으로 나눠서 관리한다: 내부에서만 수정 가능한 `MutableStateFlow`(비공개, `_` 접두사 관례)와 화면이 읽기만 하는 `StateFlow`(공개). 화면이 직접 상태를 변경 못 하게 강제하는 관례다.

```kotlin
private val _revealedPhoto = MutableStateFlow<PhotoEntity?>(null)
val revealedPhoto: StateFlow<PhotoEntity?> = _revealedPhoto.asStateFlow()
```

## Navigation Compose

```kotlin
val navController = rememberNavController()
val currentRoute = navController.currentBackStackEntryAsState().value?.destination?.route

NavHost(navController = navController, startDestination = Screen.Home.route) {
    composable(Screen.Home.route) { HomeScreen() }
}
```

- `rememberNavController()`: 화면 전환/뒤로가기 스택을 관리하는 컨트롤러. `remember`로 리컴포지션 돼도 유지.
- 화면 컴포저블(`ArchiveScreen`, `RegisterScreen` 등)은 `navController`를 직접 몰라도 되게, "버튼 눌렸을 때 할 일"을 `onAddClick: () -> Unit` 같은 람다 파라미터로 밖에서 주입받는 패턴을 쓴다. 재사용성/테스트 용이성 때문.
- `popBackStack()`: 뒤로가기와 같은 동작.

## 사진 선택: Photo Picker API

```kotlin
val pickImageLauncher = rememberLauncherForActivityResult(
    contract = ActivityResultContracts.PickVisualMedia(),
) { uri -> selectedImageUri = uri }

// 버튼 클릭 시
pickImageLauncher.launch(
    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
)
```

- 안드로이드 13(API 33)에서 생긴 시스템 Photo Picker의 호환 라이브러리 버전. **API 21까지 자동으로 하위 호환**됨(구버전 기기는 라이브러리가 알아서 예전 방식 선택창으로 폴백, 코드는 안 바뀜).
- **저장소 접근 권한(READ_MEDIA_IMAGES 등)을 요청할 필요가 없다** — 사진 선택 UI 자체가 앱이 아니라 시스템이 별도로 띄우는 신뢰된 화면이고, 사용자가 고른 사진 딱 하나에 대한 접근 권한(`Uri`)만 앱에 넘겨주는 구조라서. "집 열쇠 전체"가 아니라 "고른 방 하나"만 보여주는 방식.
- 선택 결과는 실제 파일 경로가 아니라 `Uri`(주소)로 온다 — 왜 파일로 바로 못 쓰는지는 [system/android-system-basics.md](../system/android-system-basics.md) 참고.

## 이미지 표시: Coil `AsyncImage`

```kotlin
AsyncImage(model = uri, contentDescription = "설명", modifier = Modifier.height(200.dp))
```

`Uri`나 URL만 주면 알아서 비동기로 이미지를 불러와서 그려주는 컴포넌트(Coil 라이브러리).

## `?.let { }` 패턴

"값이 null이 아닐 때만 이 블록을 실행해라"는 뜻의 안전 호출 + let 조합.

```kotlin
selectedImageUri?.let { uri -> AsyncImage(model = uri, ...) }
```

## 테마 만들기 (Material3)

`Color.kt`(색 상수) / `Type.kt`(글꼴) / `Theme.kt`(둘을 묶는 테마)로 나누는 게 관례.

```kotlin
private val LightColors = lightColorScheme(
    primary = RetroAmber,      // 강조색(버튼 등)
    onPrimary = RetroBrown,    // primary 위에 올라가는 글자색
    background = RetroBackground,
    onBackground = RetroBrown,
    surface = RetroCream,
    onSurface = RetroBrown,
)

@Composable
fun PandoraBoxTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),   // 기기 다크모드 자동 감지
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = PixelTypography,
        content = content,
    )
}
```

`onXxx` 색은 "Xxx 위에 올라가는 요소의 색"이라는 뜻(예: `onBackground`는 배경 위 글자색).

### 커스텀 폰트 적용 — 15개 스타일 전부 바꿔야 한다

`Typography`는 displayLarge ~ labelSmall까지 **15개 스타일**을 갖는다. 일부만 지정하면 나머지는 기본 폰트로 남아서 "폰트가 부분만 적용된" 상태가 된다. 기본값을 가져와 일괄 변환하는 방식이 안전하다.

```kotlin
val PixelFontFamily = FontFamily(Font(R.font.galmuri9))   // res/font/ 안의 파일명

private val defaultTypography = Typography()   // Material3 기본 15종
private const val PIXEL_SCALE = 0.8f

private fun TextStyle.asPixel(): TextStyle = copy(
    fontFamily = PixelFontFamily,
    fontSize = fontSize * PIXEL_SCALE,
    lineHeight = lineHeight * PIXEL_SCALE,
)

val PixelTypography = Typography(
    displayLarge = defaultTypography.displayLarge.asPixel(),
    // ... 15개 전부
)
```

**주의점**
- `res/font/` 안의 폰트 파일명과 font-family XML 파일명이 같으면 리소스 ID가 겹쳐 `Duplicate resources` 빌드 에러가 난다. 이름을 다르게 하거나 XML 없이 ttf만 쓴다.
- Compose의 `Font()`는 font-family XML이 아니라 **실제 폰트 파일**을 가리켜야 한다. XML을 가리키면 빌드는 되지만 폰트가 적용되지 않는다.
- **한글 글리프가 없는 폰트**(예: Press Start 2P)를 쓰면 한글은 시스템 기본 폰트로 대체된다. 크기만 바뀌고 모양이 안 바뀌면 이걸 의심할 것. 한글 도트 폰트로는 Galmuri(OFL)가 있다.

## 애니메이션

### `Animatable` — 값 하나를 부드럽게 변화시키기

```kotlin
val progress = remember { Animatable(0f) }

LaunchedEffect(key) {
    progress.animateTo(1f, animationSpec = tween(1600, easing = FastOutSlowInEasing))
}
```

- `animateTo`는 suspend 함수라 코루틴(`LaunchedEffect`, `rememberCoroutineScope`) 안에서만 호출한다.
- 연속 호출하면 순차 실행되므로, 흔들림 같은 다단계 동작을 자연스럽게 표현할 수 있다.
  ```kotlin
  wiggle.animateTo(1f, tween(80)); wiggle.animateTo(-1f, tween(130)); wiggle.animateTo(0f, tween(80))
  ```
- `snapTo(v)`는 애니메이션 없이 즉시 값을 바꾼다(초기화용).
- `LaunchedEffect` 안의 `while(true)` 반복은 key가 바뀌면 자동으로 취소된다 → 반복 애니메이션에 유용.

### `graphicsLayer` — 변형(회전/확대/투명도)

```kotlin
Modifier.graphicsLayer {
    rotationZ = wiggle.value * 20f
    scaleX = zoom; scaleY = zoom
    alpha = 1f - fade
    translationX = ...
    transformOrigin = TransformOrigin(0.5f, 0.33f)   // 확대 기준점
}
```

레이아웃을 다시 계산하지 않고 그리기 단계에서만 변형하므로 성능이 좋다. `transformOrigin`을 바꾸면 "특정 지점을 향해 확대"(카메라가 그쪽으로 들어가는 느낌) 연출이 가능하다.

### 단계가 있는 연출: 상태 머신 + LaunchedEffect

```kotlin
private enum class Phase { IDLE, OPENING, ESCAPING, DIVING, SPARKLE, REVEALING, REVEALED }

var phase by remember { mutableStateOf(Phase.IDLE) }

LaunchedEffect(phase) {
    when (phase) {
        Phase.OPENING -> { lidOpen.animateTo(1f, tween(1600)); phase = Phase.ESCAPING }
        Phase.ESCAPING -> { spirits.animateTo(1f, tween(4400)); phase = Phase.DIVING }
        // ...
        else -> Unit
    }
}
```

각 단계가 끝나면 다음 단계로 상태를 바꾸고, `LaunchedEffect(phase)`가 다시 실행되며 이어진다. 긴 시네마틱 연출을 단계별로 쪼개 관리할 수 있다.

### `Crossfade`

두 상태 사이를 부드럽게 교차 페이드한다.

```kotlin
Crossfade(targetState = page, label = "story-text") { index -> Text(storyPages[index]) }
```

## Canvas로 직접 그리기

`Canvas`는 좌표를 직접 계산해 도형을 그리는 컴포저블. 사각형만으로 표현 못 하는 기울어진 면은 `Path`로 다각형을 만든다.

```kotlin
Canvas(modifier = modifier.aspectRatio(224f / 204f)) {
    val path = Path().apply {
        moveTo(p0.x, p0.y); lineTo(p1.x, p1.y); lineTo(p2.x, p2.y); close()
    }
    drawPath(path, color)
    drawPath(path, outlineColor, style = Stroke(width = 3f, join = StrokeJoin.Round, cap = StrokeCap.Round))
}
```

- **외곽선이 모서리에서 삐져나오는 현상**: `Stroke`의 기본 모서리 처리(miter join)는 예각에서 선이 뾰족하게 튀어나온다. `join = StrokeJoin.Round`로 해결. 또 선은 경계선 중앙에 그려지므로 캔버스 가장자리에서는 절반이 잘린다 → 여백(margin)을 두어야 한다.
- `Modifier.size()` 대신 `Modifier.aspectRatio()`를 쓰면 부모 크기에 맞춰 비율을 유지하며 확대/축소된다.

### 아이소메트릭(3/4 시점) 렌더링 직접 만들기

정면 뷰 대신 입체감을 주려면 오블리크 투영을 쓴다. 뒤쪽으로 갈수록 화면상 `(+d, -d)`만큼 밀리게 한다.

```kotlin
// 3차원 점: x=좌우, dep=앞뒤 깊이, hei=높이
fun project(p: P3) = Offset(
    x = left + p.x + (p.dep / physDepth) * d,
    y = baseY - p.hei - (p.dep / physDepth) * d,
)
```

**면별 명암 차등**이 입체감의 핵심: 윗면 가장 밝게 / 앞면 중간 / 옆면 가장 어둡게.

**깊이 정렬(painter's algorithm)**: 먼 면부터 그린다. 회전하는 부품(뚜껑)이 있으면 회전 후 좌표로 매번 다시 정렬해야 한다.

**뒷면 제거(backface culling)**: 뒤를 향한 면을 그리지 않는 처리. 이게 없으면 뚜껑이 열려도 원래 안 보여야 할 윗면과 그 장식이 계속 보인다.

각 면에 법선 벡터(그 면이 향하는 방향)를 부여하고, 시선 방향과 내적해서 판정한다.

```kotlin
val k = d / physDepth
// 투영식에서 화면상 변위가 0이 되는 방향 = 시선 방향 (-k, 1, -k)
fun isVisible(n: P3) = (n.x * -k + n.dep * 1f + n.hei * -k) < 0f
```

회전하는 부품은 **법선도 함께 회전**시켜야 한다.

```kotlin
fun rotNormal(n: P3) = P3(n.x, n.dep * cos + n.hei * sin, -n.dep * sin + n.hei * cos)
```

**축을 기준으로 한 회전**: 뚜껑을 뒤쪽 경첩(dep=physDepth, hei=0) 기준으로 열려면, 그 축을 원점으로 옮겨 2차원 회전 후 되돌린다.

```kotlin
fun rot(p: P3): P3 {
    val u = p.dep - physDepth   // 축을 원점으로
    val v = p.hei
    return P3(p.x, u * cos + v * sin + physDepth, -u * sin + v * cos)
}
```

### 파티클 연출

입자마다 시작 위치·속도·크기·등장 지연·흔들림을 랜덤으로 정해 `remember`로 고정해두고, 진행도(0~1)만 애니메이션한다.

```kotlin
val spirits = remember { List(110) { Spirit(startX = Random.nextFloat() * 2f - 1f, delay = ..., ...) } }

// 그릴 때: 개별 진행도 = 전체 진행도에서 지연을 뺀 값
val local = ((progress - s.delay) / (1f - s.delay)).coerceIn(0f, 1f)
val eased = 1f - (1f - local) * (1f - local)   // 처음 빠르고 점점 느리게
val alpha = if (local < 0.18f) local / 0.18f else (1f - local) / 0.82f   // 페이드 인 → 아웃
```

## 상태 끌어올리기(state hoisting) — 자식이 부모 UI를 제어해야 할 때

Scaffold의 하단 탭바는 부모가 그리므로, 자식 화면(HomeScreen)이 직접 숨길 수 없다. 콜백을 내려주고 부모가 상태를 갖는다.

```kotlin
// 부모
var immersive by remember { mutableStateOf(false) }
Scaffold(bottomBar = { if (!immersive) NavigationBar { ... } }) { ... }
composable(Screen.Home.route) { HomeScreen(onImmersiveChange = { immersive = it }) }

// 자식
LaunchedEffect(immersive) { onImmersiveChange(immersive) }
DisposableEffect(Unit) { onDispose { onImmersiveChange(false) } }   // 화면 벗어나면 원상복구
```

전체 화면을 덮는 오버레이를 만들 때는 부모의 padding도 주의해야 한다. 바깥 컨테이너에 padding이 있으면 오버레이가 화면 끝까지 닿지 않는다 → padding을 안쪽 콘텐츠에만 준다.

## 조건부 첫 화면 (온보딩)

`NavHost`의 `startDestination`을 저장된 설정값으로 결정한다.

```kotlin
@HiltViewModel
class RootViewModel @Inject constructor(preferences: AppPreferences) : ViewModel() {
    val startDestination =
        if (preferences.isOnboardingDone) Screen.Home.route else Screen.Onboarding.route
}
```

온보딩을 마치면 뒤로가기로 돌아오지 않도록 백스택에서 제거한다.

```kotlin
navController.navigate(Screen.Home.route) {
    popUpTo(Screen.Onboarding.route) { inclusive = true }
}
```

## 클릭 효과(ripple) 없애기

화면 전체를 탭 영역으로 쓸 때는 물결 효과가 어색하다.

```kotlin
Modifier.clickable(
    interactionSource = remember { MutableInteractionSource() },
    indication = null,
    onClick = { advance() },
)
```

## 확장 아이콘

`Icons.Default.Home` 같은 기본 아이콘 외의 것(`Inventory2`, `PhotoLibrary` 등)은 별도 의존성이 필요하다.

```kotlin
implementation("androidx.compose.material:material-icons-extended")
```
