# Hilt / 의존성 주입(Dependency Injection)

## 의존성 주입(DI)이 뭔지

어떤 클래스가 동작하려면 다른 객체가 필요한 경우(= 의존성), 그 객체를 직접 만들지 않고 **외부에서 넣어(주입해)받는** 설계 방식.

- DI 없이: 클래스가 스스로 필요한 객체를 생성 → 재사용/테스트 어려움, 화면마다 생성 코드 반복
- DI로: 클래스는 "이런 타입이 필요하다"고 선언만 하면, 프레임워크(Hilt)가 알맞은 걸 자동으로 찾아 넣어줌

## Hilt 이름의 유래

안드로이드엔 원래 **Dagger**(단검)라는 DI 라이브러리가 있었고, Hilt는 그걸 더 쓰기 쉽게 감싼 것. "Hilt"는 칼자루/손잡이라는 뜻 — 단검(Dagger)을 편하게 쥘 수 있게 하는 손잡이라는 네이밍 말장난.

## `@HiltAndroidApp`

앱 전체의 Hilt 의존성 저장소(컨테이너)를 만드는 시작점. `Application` 클래스에 붙여야 한다.

```kotlin
@HiltAndroidApp
class PandoraBoxApplication : Application()
```

## `@Module` + `@InstallIn` + `@Provides`

생성자만으로는 못 만드는 타입(예: Room DB — 빌더 패턴 필요)을 "이렇게 만들어라"고 직접 알려주는 방법.

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): PandoraDatabase {
        return Room.databaseBuilder(context, PandoraDatabase::class.java, "db_name").build()
    }
}
```

- `@InstallIn(SingletonComponent::class)`: 여기서 만든 것들이 앱이 켜져있는 동안 계속 살아있는 범위에 속함.
- `@Singleton`: 딱 하나만 만들고 계속 재사용(DB처럼 여러 개 생기면 안 되는 것에 필수).
- `@ApplicationContext context: Context`: 앱 전체 Context를 Hilt가 자동으로 넣어줌. (Activity Context를 ViewModel 등에 주입하면 메모리 누수 위험이 있지만, Application Context는 앱과 생명주기가 같아 안전)

## `@Inject constructor` — 생성자 주입

내가 직접 만든 클래스는, 생성자 앞에 `@Inject`만 붙이면 Hilt가 필요한 인자를 자동으로 찾아 넣어준다. `@Module`에 일일이 만드는 법을 안 적어도 되는, 더 간단하고 선호되는 방식.

```kotlin
class LocalPhotoRepositoryImpl @Inject constructor(
    private val photoDao: PhotoDao,   // PhotoDao는 이미 DatabaseModule이 만드는 법을 알고 있어서 자동 연결됨
) : PhotoRepository
```

## `@Binds` — 인터페이스 ↔ 구현체 연결

이미 `@Inject constructor`로 만들 줄 아는 구현체가 있을 때, "인터페이스 A가 필요하면 구현체 B를 써라"고 **타입 매칭만** 선언하는 더 가벼운 방법. 함수 본문이 필요 없어서 `abstract` 함수로 선언한다.

```kotlin
@Module
@InstallIn(SingletonComponent::class)
abstract class RepositoryModule {
    @Binds
    abstract fun bindPhotoRepository(impl: LocalPhotoRepositoryImpl): PhotoRepository
}
```

`@Provides`(직접 만드는 코드 필요할 때) vs `@Binds`(단순 인터페이스-구현체 매칭일 때)로 구분해서 쓴다.

## Repository 패턴

화면(ViewModel)이 데이터가 로컬(Room)에서 오는지, 나중에 서버에서 오는지 전혀 몰라도 되게 만드는 설계.

```kotlin
interface PhotoRepository {
    fun getAllPhotos(): Flow<List<PhotoEntity>>
    suspend fun getRandomPhoto(excludeIds: List<String>): PhotoEntity?
    // ...
}

class LocalPhotoRepositoryImpl @Inject constructor(
    private val photoDao: PhotoDao,
) : PhotoRepository {
    override fun getAllPhotos() = photoDao.getAll()
    override suspend fun getRandomPhoto(excludeIds: List<String>) =
        photoDao.getRandomExcluding(excludeIds) ?: photoDao.getRandomAny()  // 폴백 로직은 여기서 판단
}
```

Dao는 "이런 쿼리를 실행할 수 있다"는 능력만 제공하고, "언제 어떤 쿼리를 쓸지" 같은 판단(비즈니스 로직)은 Repository 계층 몫. 화면은 오직 인터페이스(`PhotoRepository`)만 보고 개발하며, 나중에 서버 연동 버전(`RemotePhotoRepositoryImpl`)으로 바꿔도 화면 코드는 안 건드려도 된다.

### 인터페이스와 구현체, 왜 파일을 두 개로 나누는가

- **인터페이스(`PhotoRepository`)**: "이런 기능이 있다"는 **약속(계약서)**만 적는다. 어떻게 동작하는지는 없다.
- **구현체(`LocalPhotoRepositoryImpl`)**: 그 약속을 실제로 지키는 진짜 코드.

비유: 인터페이스는 **채용 공고**("코틀린 할 줄 알아야 함"), 구현체는 **그 조건을 실제로 갖춘 직원**. 공고에 적힌 조건은 뽑힌 사람이 반드시 실제로 만족해야 하듯, 인터페이스에 함수를 선언하면 구현체는 반드시 그 함수를 구현해야 한다(안 하면 컴파일 에러).

인터페이스 없이 구현체 하나만 있었다면, 모든 ViewModel이 "로컬 Room 기반"이라는 사실에 직접 묶인다. 나중에 서버 버전을 추가할 때 그걸 쓰던 ViewModel 코드를 전부 찾아 고쳐야 한다. 인터페이스로 분리해두면, `RemotePhotoRepositoryImpl`을 새로 만들고 `RepositoryModule`의 `@Binds` 연결 대상만 바꾸면 끝 — ViewModel은 한 글자도 안 건드린다.

**함수를 추가할 때는 인터페이스와 구현체 두 곳 다 손대야 한다** — 계약서에 조건을 추가하고, 그 조건을 실제로 만족시키는 코드를 채워 넣는 것이므로 당연히 한 세트다.

## `@HiltViewModel`

ViewModel을 Hilt가 관리하게 만드는 어노테이션. Compose 화면에서 `hiltViewModel()`로 가져다 쓴다. (자세한 사용은 [frontend/android-jetpack-compose.md](../frontend/android-jetpack-compose.md) 참고)
