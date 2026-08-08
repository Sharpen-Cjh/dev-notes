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
