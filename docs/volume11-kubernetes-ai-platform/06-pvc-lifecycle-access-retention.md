# PVC: 수명 주기·접근 모드·보존 경계

## 1. 학습 목표

이 장을 마치면 다음을 할 수 있어야 합니다.

- `PersistentVolumeClaim`(PVC)이 워크로드가 요구하는 저장소 계약임을 설명한다.
- `ReadWriteOnce` 접근 모드와 `Filesystem` volume mode가 뜻하는 경계를 읽는다.
- PVC 삭제, PersistentVolume(PV) 재활용 정책, 실제 데이터 보존이 서로 다른 책임임을 구분한다.
- 조직 StorageClass나 실제 데이터를 사용하지 않고 Manifest를 로컬에서 렌더링하고 검사한다.

## 2. 왜 필요한가

AI Platform은 인덱스, 캐시, 체크포인트처럼 Pod 수명보다 오래 남아야 할 수 있는 데이터를 다룹니다. Pod의 임시 파일 시스템에 이런 데이터를 두면 재시작·교체 때 사라질 수 있습니다. PVC는 워크로드가 필요한 용량, 접근 방식, volume mode를 Kubernetes에 요청하는 선언입니다.

그러나 PVC YAML 하나가 데이터 안전을 보장하지는 않습니다. 실제 StorageClass의 프로비저너, PV의 `reclaimPolicy`, 스냅샷·백업, 암호화, 복구 연습, 권한, 비용은 플랫폼 운영 설계에 속합니다. 이 장은 의도적으로 존재하지 않는 `example-storage-class`와 이름만 있는 `ai-platform-index-example`을 사용하며, Deployment에 마운트하지 않고 기본 Kustomize 집합에서도 제외합니다.

> [!WARNING]
> `k8s/volume11/storage/`는 **로컬 렌더링 전용 학습 Manifest**입니다. `kubectl apply`, `kubectl create`, StorageClass 생성, PV/PVC 바인딩, 실제 데이터 기록, 클러스터 연결을 실행하지 마세요. `example-storage-class`는 의도적으로 운영 StorageClass가 아닌 자리표시자입니다.

## 3. 핵심 개념

- **PVC:** Namespace 안에서 워크로드가 요청하는 저장소 용량·접근 모드 계약입니다.
- **PV:** 클러스터 범위의 저장소 공급 단위입니다. 실제 프로비저너와 연결되며 PVC와 별도 객체입니다.
- **StorageClass:** 동적 프로비저닝과 보존 동작을 플랫폼이 정의하는 클래스입니다. 이 예제는 실제 클래스를 가리키지 않습니다.
- **`ReadWriteOnce` (RWO):** 한 노드에서 읽기·쓰기로 마운트할 수 있다는 접근 모드 요청입니다. 여러 Pod가 언제나 동시에 쓸 수 있다는 보장은 아닙니다.
- **`Filesystem`:** 파일 시스템으로 사용하는 volume mode입니다. block 장치 직접 사용과는 다른 계약입니다.
- **보존(reclaim):** PVC 삭제 후 실제 저장소가 유지·삭제·재활용되는지는 PV/StorageClass와 조직 정책이 결정합니다. PVC의 `accessModes`나 이름만으로 결정되지 않습니다.

## 4. 동작 구조

```text
별도 로컬 렌더링 집합: k8s/volume11/storage/

PersistentVolumeClaim: ai-platform-index-example
  storageClassName: example-storage-class ── 비운영용 자리표시자
  accessModes: [ReadWriteOnce] ──────────── 한 노드 읽기·쓰기 요청
  volumeMode: Filesystem ────────────────── 파일 시스템 사용 계약
  requests.storage: 1Gi ─────────────────── 최소 용량 요청 예시

기본 k8s/volume11/kustomization.yaml: PVC 미포함
Deployment volumeMount / 실제 PV / 실제 데이터 / 백업: 이 slice에 없음
```

PVC는 저장소를 "소유"한다고 단정하는 객체가 아니라, Namespace 워크로드가 원하는 계약을 표현합니다. 이 예제의 `storageClassName`은 유효한 공급자를 선택하지 않으므로 적용 대상으로 사용할 수 없습니다. 또한 PVC를 Deployment에 연결하지 않았으므로 API Pod가 이 학습용 claim을 읽거나 쓰지 않습니다.

## 5. 실습 환경

| 경로 | 역할 |
|---|---|
| `k8s/volume11/storage/pvc.yaml` | 예제 StorageClass, 접근 모드, volume mode, 용량 요청을 가진 PVC |
| `k8s/volume11/storage/kustomization.yaml` | PVC만 조합하는 별도 로컬 렌더링 집합 |
| `k8s/volume11/kustomization.yaml` | 안전을 위해 PVC를 포함하지 않는 기본 API 렌더링 집합 |
| `tests/integration/test_volume11_health_artifacts.py` | PVC의 placeholder·접근·분리 경계를 검사하는 오프라인 테스트 |

Python과 `uv`가 필요합니다. 6.1에는 `kubectl` CLI가 필요하지만 kubeconfig, Kubernetes 클러스터, StorageClass 또는 볼륨 프로비저너는 필요하지 않습니다.

## 6. 단계별 실습

### 6.1 PVC Manifest를 로컬에서 렌더링

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11/storage
```

출력에서 `kind: PersistentVolumeClaim`, `storageClassName: example-storage-class`, `ReadWriteOnce`, `Filesystem`, `storage: 1Gi`를 확인합니다. `kubectl kustomize`는 파일을 로컬에서 조합할 뿐 API 서버에 연결하거나 PVC를 생성·바인딩하지 않습니다. **명령을 `apply`나 `create`로 바꾸지 마세요.**

### 6.2 기본 API 집합에서 PVC가 제외됐는지 확인

```bash
# 실행 위치: 저장소 루트
kubectl kustomize k8s/volume11
```

출력에는 Namespace, ConfigMap, Deployment, Service, Ingress만 있고 `kind: PersistentVolumeClaim`은 없어야 합니다. 이 분리는 API 예제를 읽을 때 학습용 저장소 요청이 실수로 적용 집합에 섞이지 않게 합니다.

### 6.3 Volume 11 저장소 경계를 테스트

```bash
# 실행 위치: 저장소 루트
uv run pytest tests/unit/test_volume11_health.py tests/unit/test_volume11_dependencies.py tests/integration/test_volume11_health_artifacts.py -q
```

테스트는 PVC API와 kind, `example-storage-class`, RWO, Filesystem, 1Gi 요청, Secret·토큰·암호·주소의 부재, 기본 Kustomize 집합에서의 제외를 검사합니다. Pod, PV, PVC, 컨테이너, 클러스터 리소스는 만들지 않습니다.

## 7. Manifest 설명

`spec.resources.requests.storage: 1Gi`는 이 학습용 claim이 요구하는 용량 예시일 뿐 실제 사용량 한도나 비용 예측이 아닙니다. 볼륨 확장 가능 여부도 StorageClass의 `allowVolumeExpansion`과 공급자 정책에 달려 있으므로 이 Manifest만으로 판단할 수 없습니다.

`ReadWriteOnce`는 "오직 하나의 Pod"를 의미하지 않습니다. Kubernetes 문서에서 RWO는 단일 **노드**에 읽기·쓰기로 마운트할 수 있다는 접근 모드입니다. 스케줄링, CSI 드라이버, 다중 Pod 사용 가능성 및 애플리케이션 수준 동시 쓰기 안전성은 실제 운영 환경에서 별도로 검증해야 합니다.

이 파일에는 `volumeName`, selector, data source, Secret 참조, CSI driver, 실제 StorageClass, `volumeMounts`가 없습니다. 따라서 정적 PV를 묶거나 기존 데이터를 복제하거나 Pod에 저장소를 연결하지 않습니다. 실제 인덱스 경로와 데이터 마이그레이션은 승인된 설계·백업·복구 검증이 있는 환경에서만 다뤄야 합니다.

## 8. PVC 삭제와 데이터 보존

PVC를 삭제해도 실제 바이트가 즉시 사라진다고 가정하면 안 됩니다. 동적 프로비저닝에서 그 뒤의 동작은 연계된 PV의 reclaim policy와 CSI/StorageClass 구현, 조직의 백업·보존 정책에 좌우됩니다. `Delete`는 backing storage 삭제를 요청할 수 있고, `Retain`은 관리자의 명시적 회수 절차를 요구할 수 있습니다. 이것은 이 Namespace PVC Manifest가 선언하는 값이 아닙니다.

따라서 운영 변경 전에는 다음을 증거와 함께 검토합니다.

1. 승인된 StorageClass와 해당 CSI 드라이버의 영역·암호화·가용성 특성
2. PV reclaim policy, 백업·스냅샷 보존 기간, 복구 책임자
3. 용량 증가와 비용 경보, quota, 데이터 수명 종료 승인
4. 접근 모드와 Pod 배치가 동시 쓰기·장애 조치 요구와 맞는지
5. 삭제·롤백·복구 리허설이 실제 데이터에 손대지 않는 환경에서 검증됐는지

이 학습 slice에는 위의 실제 이름·정책·값·데이터를 기록하지 않습니다.

## 9. 정상 실행 결과

6.1의 렌더링 출력에는 대략 다음 구조가 포함됩니다.

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
spec:
  storageClassName: example-storage-class
  accessModes:
    - ReadWriteOnce
  volumeMode: Filesystem
  resources:
    requests:
      storage: 1Gi
```

6.2 출력에는 `kind: PersistentVolumeClaim`이 없어야 합니다. 두 출력 모두 로컬 YAML 조합 결과이며, `Bound` 상태나 실제 PV 이름은 나타나지 않습니다. 6.3은 설치 버전에 따라 개수와 시간은 달라도 `passed`로 끝나야 합니다.

## 10. 오류 해결

| 증상 | 원인 확인 | 해결 |
|---|---|---|
| `kubectl kustomize`를 찾을 수 없음 | `kubectl` CLI가 설치되지 않았을 수 있습니다. | Python 테스트를 먼저 실행하고, 승인된 CLI 설치 후 6.1의 로컬 렌더링만 다시 실행합니다. |
| 렌더링에서 YAML 오류 | `accessModes` 목록 또는 `resources.requests.storage` 들여쓰기가 바뀌었을 수 있습니다. | `storage/pvc.yaml`의 `spec` 구조를 복원하고 다시 렌더링합니다. |
| 적용하면 StorageClass를 찾을 수 없을 것 같음 | `example-storage-class`는 의도적 자리표시자입니다. | 예상된 보호 동작입니다. 이 slice에서 실제 클래스 이름을 넣거나 적용하지 마세요. |
| PVC 삭제 뒤 데이터가 남을지 불명확함 | reclaim policy, CSI 구현, 백업 정책을 확인하지 않았을 수 있습니다. | 승인된 운영 절차에서 PV·StorageClass·백업 정책을 확인합니다. 이 예제에 운영 값을 저장하지 마세요. |

## 11. 응용 실습

1. RWO 저장소를 사용하는 단일 writer 작업에서 Pod 교체·노드 장애·재시도가 일어날 때 필요한 일관성 검사를 설계합니다.
2. 인덱스의 생성·보존·삭제 수명 주기를 데이터 분류와 비용 관점에서 표로 정리합니다. 실제 저장소 이름이나 데이터는 쓰지 않습니다.
3. 백업 복구 훈련에서 복구 시점 목표(RPO), 복구 시간 목표(RTO), 검증 쿼리, 폐기 기준을 어떤 증거로 남길지 작성합니다.

## 12. 완료 체크리스트

- [ ] PVC와 PV/StorageClass의 책임을 구분할 수 있다.
- [ ] `ReadWriteOnce`, `Filesystem`, `1Gi` 요청이 어떤 계약인지 확인했다.
- [ ] PVC 삭제와 backing storage 보존이 같은 설정이 아님을 설명할 수 있다.
- [ ] `example-storage-class`가 비운영용 자리표시자임을 확인했다.
- [ ] `kubectl kustomize k8s/volume11/storage`로만 PVC 형상을 로컬 렌더링했고 기본 집합에서 PVC가 없음을 확인했다.
- [ ] Volume 11 테스트가 통과했다.
- [ ] 실제 클러스터, StorageClass, PV/PVC 바인딩, 데이터, Secret을 만들거나 저장하지 않았다.

## 13. 핵심 정리

PVC는 워크로드가 원하는 저장소 계약을 표현하지만, 실제 프로비저닝과 데이터 보존은 StorageClass, PV reclaim policy, CSI, 백업·복구 정책의 공동 책임입니다. 이 장은 `example-storage-class`와 RWO·Filesystem·1Gi 요청만 있는 별도 렌더링 집합을 오프라인으로 검증했고, API Deployment나 기본 Kustomize 집합에 저장소를 연결하지 않았습니다. 다음 장에서는 확장 정책과 안전한 업데이트·롤백 경계를 다룹니다.
