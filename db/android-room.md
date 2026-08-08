# Room (Android 로컬 DB)

## Room이 뭔지

안드로이드에 기본 내장된 **SQLite** DB 엔진을 직접 쓰면 SQL 문자열을 손으로 짜고 결과를 수동으로 객체로 변환해야 하는 등 번거로움이 많다. Room은 그 위에 올라가는 라이브러리로:

- 클래스로 테이블을 정의(`@Entity`)하면 실제 테이블을 자동 생성
- 인터페이스에 쿼리를 어노테이션으로 적으면(`@Dao`) 실행 코드를 컴파일 시점에 자동 생성
- SQL 오타를 **컴파일 시점**에 잡아줌
- 쿼리 결과를 자동으로 Kotlin 객체로 변환

## `@Entity` — 테이블 정의

클래스 하나 = 테이블 하나, 필드 하나 = 컬럼 하나.

```kotlin
@Entity(tableName = "photos")
data class PhotoEntity(
    @PrimaryKey val id: String,       // UUID 문자열을 기본키로 (auto-increment 대신)
    val localPath: String,
    val caption: String,
    val createdAt: Long,
    val remoteKey: String? = null,    // 나중에 서버 업로드 시 채워질 필드 (미리 스키마에 자리만 마련)
)
```

UUID를 기본키로 쓰는 이유: 나중에 서버 DB와 동기화할 때 ID 충돌 없이 그대로 재사용 가능.

## `@Dao` — 쿼리 정의

```kotlin
@Dao
interface PhotoDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(photo: PhotoEntity)

    @Query("SELECT * FROM photos ORDER BY createdAt DESC")
    fun getAll(): Flow<List<PhotoEntity>>

    @Query("SELECT * FROM photos WHERE id NOT IN (:excludeIds) ORDER BY RANDOM() LIMIT 1")
    suspend fun getRandomExcluding(excludeIds: List<String>): PhotoEntity?

    @Query("SELECT * FROM photos ORDER BY RANDOM() LIMIT 1")
    suspend fun getRandomAny(): PhotoEntity?   // 제외 검색 결과 없을 때(=아이템이 너무 적을 때) 폴백용
}
```

- `Flow<List<T>>` 리턴: 테이블에 변화가 생길 때마다 Room이 자동으로 최신 목록을 다시 흘려보내줌(반응형).
- `suspend fun`: DB 작업은 I/O라 메인 스레드를 막지 않기 위해 필수.
- **정렬 기준 선택**: 자주 바뀌고 최신이 중요한 데이터(사진 목록)는 `DESC`(최신순), 자리가 고정돼야 하는 목록성 데이터(박스 목록 등)는 `ASC`(생성 순서 유지 — 탭 UI 등에서 순서가 갑자기 바뀌면 혼란스러움).

## 다대다(many-to-many) 관계 — CrossRef 테이블

사진 하나가 여러 박스에, 박스 하나에 여러 사진이 속할 수 있는 관계는 중간(연결) 테이블로 표현한다.

```kotlin
@Entity(
    tableName = "photo_box_cross_ref",
    primaryKeys = ["photoId", "boxId"],   // 두 필드의 조합이 기본키
    foreignKeys = [
        ForeignKey(entity = PhotoEntity::class, parentColumns = ["id"], childColumns = ["photoId"], onDelete = ForeignKey.CASCADE),
        ForeignKey(entity = BoxEntity::class, parentColumns = ["id"], childColumns = ["boxId"], onDelete = ForeignKey.CASCADE),
    ],
    indices = [Index("photoId"), Index("boxId")],
)
data class PhotoBoxCrossRef(val photoId: String, val boxId: String)
```

- **"CrossRef"**: Room에서 다대다 중간 테이블을 부르는 관용적 이름.
- **복합 기본키**: 같은 (사진, 박스) 조합 중복 방지. 사진 하나가 여러 박스와, 박스 하나가 여러 사진과 짝지어질 수 있음 = 다대다.
- **`ForeignKey`**: `childColumns`(지금 이 테이블의 컬럼)가 `parentColumns`(다른 테이블의 컬럼)를 가리켜야 한다는 걸 DB 레벨에서 강제.
- **`onDelete = CASCADE`**: "폭포"라는 뜻(프랑스어 cascade). 부모 행(예: 사진)이 삭제되면, 그걸 참조하던 자식 행(연결 정보)도 자동으로 줄줄이 같이 삭제됨. 없으면 삭제가 막히거나 유령 데이터가 남는다.
- **`Index`**: 책의 찾아보기(색인)와 같은 개념 — 해당 컬럼으로 검색할 때 빠르게 찾게 해줌. Room은 외래키 컬럼에 인덱스가 없으면 경고를 준다.

## JOIN으로 다대다 조회

```kotlin
@Query("""
    SELECT photos.* FROM photos
    INNER JOIN photo_box_cross_ref ON photos.id = photo_box_cross_ref.photoId
    WHERE photo_box_cross_ref.boxId = :boxId
""")
fun getPhotosForBox(boxId: String): Flow<List<PhotoEntity>>
```

실행 순서(작성 순서와 다름):
1. `FROM` + `INNER JOIN ... ON`: 두 테이블을 조건 맞는 것끼리 임시로 이어 붙임(사진 하나가 여러 박스에 속하면 그만큼 행이 늘어남)
2. `WHERE`: 이어 붙인 결과에서 원하는 조건만 필터링
3. `SELECT`: 최종적으로 어떤 컬럼만 뽑아 리턴할지 결정

## `@Database` — DB 정의 묶기

```kotlin
@Database(
    entities = [PhotoEntity::class, BoxEntity::class, PhotoBoxCrossRef::class],
    version = 1,
    exportSchema = false,
)
abstract class PandoraDatabase : RoomDatabase() {
    abstract fun photoDao(): PhotoDao
    abstract fun boxDao(): BoxDao
}
```

- `entities`: 여기 나열된 `@Entity` 클래스들만 실제 테이블로 생성됨.
- `version`: 스키마 버전. 나중에 구조가 바뀌면 올려야 하고, 마이그레이션 경로를 알려줘야 함.
- `exportSchema`: 스키마 변경 이력을 JSON으로 남기는 기능. 초기 개발 단계엔 꺼둬도 무방.
- `abstract class`: 실제 구현은 Room이 컴파일 시점에 자동 생성(KSP).
