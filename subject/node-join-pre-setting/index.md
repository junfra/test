# DSPAAS VM Pre-setting Node Join Procedure — 학습 자료

## 1. 탄생배경

Kubernetes 클러스터 관리에서 새로운 노드를 기존 클러스터에 추가하는 작업, 즉 "노드 조인(node join)"은 인프라 확장 시 가장 빈번하게 발생하는 운영 행위 중 하나입니다. 특히 DSPAAS(삼성 SDS 클라우드 플랫폼) 환경에서는 Kubespray라는 오픈소스 도구를 활용하여 Kubernetes 클러스터를 배포하고 관리하는데, 이 과정에서 신규 노드를 조인하기 위해 사전에 VM을 설정하는 작업이 필수적으로 요구됩니다.

DSPAAS VM Pre-setting Node Join Procedure가 필요한 근본적인 이유는 여러 가지입니다. 먼저, 새로운 VM이 Kubernetes를 실행할 수 있도록 충분한 시스템 구성이 선행되어야 합니다. OS 레벨에서 SELinux 비활성화, firewalld 중지, swap 메모리 설정 변경, chrony 시간 동기화, resolv.conf 네임서버 설정 등 최소한 20개 이상의 개별 구성 작업이 필요합니다. 이러한 작업 중 하나라도 누락되면 노드 조인 실패로 이어지며, 클러스터의 안정성에도 영향을 미칠 수 있습니다.

또 다른 중요한 이유는 보안입니다. DSPAAS 환경에서는 SECDS-ROOTCA 및 SECDS-T2RootCA라는 삼성 SDS 내부 CA 인증서를 모든 노드에 배포해야 합니다. 이 인증서가 없으면 containerd가 SSL/TLS 통신을 수행할 때 인증 에러가 발생하여 CSI 볼륨 마운트가 실패합니다. 실제로 2024년 이후 여러 사례에서 CA 인증서 누락으로 인해 PVC 생성이 실패한 사건들이 보고되었습니다.

마지막으로, DSPAAS 환경의 VM은 초기 상태가 표준 Kubernetes 요구사항과 완전히 일치하지 않습니다. 예를 들어 디스크 구성(LVM)이 Kubespray가 기대하는 경로와 다르고, swap 기능이 활성화되어 있으며, SELinux 정책이 enforced 모드로 설정되어 있습니다. 이러한 불일치를 해결하기 위해 사전 조정이 필수적입니다.

노드 조인 절차는 크게 세 단계로 구분됩니다: VM Pre-setting(1-1~1-11), Ansible Playbook 실행(2-1~2-2), Post-deployment 검증(3-1~4-2)입니다. 이 중에서 1-1부터 1-11까지의 VM Pre-setting 단계가 전체 조인 절차의 성패를 좌우하는 가장 중요한 부분이며, 이 단계를 완성해야만 노드가 클러스터에 성공적으로 합류할 수 있습니다.

노드 조인의 역사적 배경을 살펴보면, Kubernetes의 초기 버전에서는 노드를 추가하는 방식이 매우 수동적이었습니다. 각 노드에 Docker를 직접 설치하고, kubeadm 명령어를 하나씩 실행하며, certificates를 수동으로 복사해야 했습니다. 그러나 Kubespray가 등장하면서 이러한 복잡성이 크게 줄어들었고, Ansible Playbook을 통해 대량의 노드를 일괄적으로 조인할 수 있게 되었습니다.

DSPAAS는 삼성 SDS의 PaaS 플랫폼으로서 Kubernetes 클러스터를 다중 가용영역(AZ)에 걸쳐 운영하며, 수백 개 이상의 VM이 하나의 클러스터로 묶여 있습니다. 이러한 대규모 환경에서 신규 VM을 조인할 때 수동으로 한 노드씩 설정하는 것은 현실적으로 불가능하므로, DSPAAS VM Pre-setting Procedure는 자동화된 스크립트와 Ansible Playbook의 조합으로 설계되었습니다.

**[RETRIEVE: 왜 DSPAAS VM Pre-setting이 필요한가?]**
**[RETRIEVE: CSPSAS 환경에서 CA 인증서가 중요한 이유는?]**
**[RETRIEVE: 노드 조인 절차는 어떤 단계로 구분되는가?]**

### Chapter 1 Recall Questions

- **사실 기반:** DSPAAS VM Pre-setting의 총 단계 수와 각 단계 번호를 나열하시오.
- **비교:** 기존 Kubernetes manual node join 방식과 Kubespray Ansible Playbook 방식을 비교하시오.
- **이해:** SECDS-ROOTCA CA 인증서가 누락될 경우 어떤 문제가 발생하는가?

---

## 2. 정의

DSPAAS VM Pre-setting Node Join Procedure는 신규 VM을 기존 Kubernetes 클러스터에 조인하기 위해 수행해야 하는 사전 설정 작업의 전체 프로세스를 지칭합니다. 이 절차는 "기존 DSPAAS VM Pre-setting Node Join Procedure — Scale-out Reference"라는 원본 문건에서 유래하였으며, 주로 Bastion 서버에서 ansible-playbook 명령어를 직접 실행하는 기존 방식(Kubespray Ansible Playbook)에 따라 수행됩니다.

이 절차의 핵심 구성 요소는 다음과 같습니다:
1. **DSPAAS 계정:** sudo 권한을 가진 dspaas 사용자가 모든 노드에 생성되어야 합니다.
2. **SSH Key:** Bastion 서버와 각 노드 간 암호 없는 SSH 연결을 위한 공개키 배포.
3. **System Configuration:** resolv.conf, chrony.conf, NetworkManager.conf, swap 설정 등 OS 레벨의 필수 서비스 구성.
4. **Filesystem Reconfiguration:** containerd 및 etcd를 위한 디스크(LV) 재구성.
5. **CA Certificate Distribution:** SECDS-ROOTCA 및 SECDS-T2RootCA 인증서의 배포 및 신뢰 저장소 등록.
6. **Package Installation:** Kubernetes 실행에 필요한 필수 패키지 목록의 일괄 설치.

이러한 구성 요소들은 순차적으로 수행되어야 하며, 각 단계가 완료되어야 다음 단계로 진행할 수 있습니다. 예를 들어, SSH key가 배포되기 전에는 dspaas 계정 생성을 원격으로 수행할 수 없고, dspaas 계정이 설정되기 전에는 ansible 명령어를 사용하여 다른 노드에 접근할 수 없습니다.

DSPAAS VM Pre-setting Procedure의 목표는 신규 노드가 "기존 클러스터와 동일한 상태"가 되도록 만드는 것입니다. 기존 노드들이 이미 완료한 시스템 구성을 새로운 노드에도 동일하게 적용해야 하며, containerd 버전, kernel 버전, SELinux 상태 등이 일관되게 유지되어야 합니다.

**[RETRIEVE: DSPAAS VM Pre-setting의 핵심 구성 요소는 무엇인가?]**
**[RETRIEVE: 왜 각 단계가 순차적으로 수행되어야 하는가?]**
**[RETRIEVE: 기존 노드와 신규 노드의 상태를 동일하게 유지해야 하는 이유는?]**

### Chapter 2 Recall Questions

- **사실 기반:** DSPAAS VM Pre-setting의 6가지 핵심 구성 요소를 나열하시오.
- **비교:** Bastion 서버를 통한 노드 조인과 직접 SSH 접속을 통한 조인 방식을 비교하시오.
- **이해:** 왜 기존 노드의 containerd 버전과 신규 노드의 containerd 버전을 일치시켜야 하는가?

---

## 3. 하위개념

DSPAAS VM Pre-setting Node Join Procedure는 총 11개의 주요 단계(1-1부터 1-11)로 구성되어 있으며, 각 단계는 다시 여러 하부 단계로 세분화됩니다. 아래에서 각 단계의 상세 내용을 다룹니다.

### DSPAAS 1-1: 작업 대상 목록 준비
새로운 노드를 위한 작업 디렉토리를 생성합니다. `mkdir /app/dspaas/$(date +'%Y%m%d')_scale-out` 명령어로 날짜를 포함하여 고유한 디렉토리를 만듭니다. 이 디렉토리에는 모든 관련 파일(인벤토리 스크립트, SSH key script, 설정 파일 등)이 저장됩니다.

### DSPAAS 1-2: /etc/hosts 업데이트
Bastion 서버에서 `/etc/hosts` 파일을 수정하여 신규 노드의 IP 주소와 호스트명을 등록합니다. 예를 들어 `10.166.113.185 khk8cspb1wpw04 wk04`와 같은 형식으로, 각 노드에 대해 IP, FQDN, 단축 이름을 한 줄에 기록합니다.

### DSPAAS 1-3: KubeSpray 설정 스크립트 작성
Kubespray 인벤토리 파일과 `hosts.yaml`을 생성하기 위한 두 개의 스크립트를 작성하고 실행합니다:
- **make_list.sh**: 신규 노드의 IP와 호스트명을 Kubespray 형식으로 변환하여 출력
- **make_list2.sh**: 호스트명만 추출하여 추가 인벤토리 파일 생성

### DSPAAS 1-4: dspaas 계정 생성 및 sudoers 설정 (ROOT 단계)
네 가지 하부 단계로 구성됩니다.

**ROOT 1-4-1:** `cat /etc/passwd | grep dspaas` 명령어로 기존 계정을 확인한 후, 없으면 신규 계정 생성.
**ROOT 1-4-2:** `useradd -d /app/dspaas -m -G wheel dspaas`로 계정 생성 및 wheel 그룹 추가.
**ROOT 1-4-3:** `/etc/sudoers` 파일에서 `%wheel` 줄의 주석 처리를 해제하여 NOPASSWD: ALL 권한 부여. 이 단계는 매우 중요한데, sudoers 파일을 잘못 수정하면 루트 비밀번호 변경이 불가능해지므로 반드시 백업 후 작업해야 합니다.
**ROOT 1-4-4:** `passwd --stdin dspaas`로 dspaas 계정 비밀번호 설정 (예: #######!).

### DSPAAS 1-5: SSH key script 생성 및 실행
sshpass를 사용하여 모든 신규 노드에 dspaas 계정으로 암호 없는 SSH 연결을 위한 공개키를 배포합니다. `ssh_copy.sh` 스크립트를 생성하고 실행하며, 기본 비밀번호는 "test"입니다.

### DSPAAS 1-6: 노드 SPEC 확인
노드의 CPU, 메모리, 디스크, OS 버전을 확인합니다. `nproc`, `free -h`, `df -h`, `cat /etc/os-release` 명령어를 사용하여 사양을 검증하고, 스펙이 부족하면 조인 전에 VM 사양을 수정해야 합니다.

### DSPAAS 1-7: System Config (ROOT 단계) — DNS 및 시간 동기화
다섯 가지 하부 단계로 구성됩니다.
**ROOT 1-7-1:** `/etc/resolv.conf` 파일의 nameserver 설정 확인 후 Bastion에서 복사 적용.
**ROOT 1-7-2:** `chrony.conf` 파일 복사 및 chronyd 서비스 재시작. `chronyc sources -v`로 NTP 동기화 상태 확인.
**ROOT 1-7-3:** `/etc/NetworkManager/NetworkManager.conf`의 `[main]` 섹션에 `dns=none` 라인 추가하여 DNS 관리를 NetworkManager가 아닌 resolv.conf에서 수행하도록 설정.
**ROOT 1-7-4:** Memory swap 기능을 off (`swapoff -a`) 합니다. Kubernetes는 swap을 권장하지 않으므로 반드시 비활성화해야 합니다.
**ROOT 1-7-5:** logrotate의 compress 옵션 활성화 및 rsyslog 재시작.
**ROOT 1-7-6:** YUM 저장소 업데이트 — Appstream, BaseOS, Artifactory-docker, EPEL 등 4개 저장소 설정.

### DSPAAS 1-8: SELinux 및 firewalld 비활성화 (ROOT 단계)
**ROOT 1-8-1:** `selinux -a "policy=targeted state=disabled"`로 SELinux를 disabled 모드로 변경.
**ROOT 1-8-2:** nftables와 firewalld 서비스를 stopped 상태로 설정하고 부팅 시 자동 시작을 비활성화합니다.

### DSPAAS 1-9: Filesystem 재구성 (ROOT 단계) — 컨테이너 데이터 디스크
네 가지 하부 단계로 구성됩니다.
**ROOT 1-9-1:** 기존 fstab 파일을 백업 (`cp /etc/fstab /etc/fstab_bak`)하고 퍼미션을 600으로 변경.
**ROOT 1-9-2:** containerd 및 etcd를 위한 디스크(LV) 재구성 — 기존 `/appdata` 마운트를 해제한 후, LV 명을 `containerd_lv`(for `/var/lib/containerd`)와 `etcd_lv`(for `/var/lib/etcd`)로 변경하여 적절한 경로에 마운트합니다.
**ROOT 1-9-3:** fstab에서 swap 설정 주석 처리 (`sed -i 's|/dev/mapper/rhel-swap|#/dev/mapper/rhel-swap|g' /etc/fstab`).
**ROOT 1-9-4:** 재부팅 (reboot)을 통해 모든 변경 사항을 적용.

### DSPAAS 1-10: 필수 패키지 설치
Kubernetes 실행에 필요한 16개 패키지를 일괄 설치합니다: `net-tools`, `yum-utils`, `bind-utils`, `device-mapper-persistent-data`, `lvm2`, `nmap`, `bash`, `bash-completion`, `openssh`, `openssl`, `nfs-utils`, `wget`, `tcpdump`, `tree`, `cloud-utils-growpart`, `sg3_utils`, `ncurses-compat-libs.x86_64`, `git`.

### DSPAAS 1-11: SECDS-ROOTCA / SECDS-T2RootCA CA Cert 다운로드 및 배포
SECDS-ROOTCA.crt와 SECDS-T2RootCA.crt를 Nexus 레포지토리에서 다운로드한 후, 각 노드의 `/etc/containerd/certs.d/` 디렉토리와 `/etc/pki/ca-trust/source/anchors`에 복사합니다. 마지막으로 `update-ca-trust` 명령어로 CA 저장소를 업데이트하여 모든 인증서가 신뢰되도록 합니다.

**[RETRIEVE: DSPAAS 1-4의 ROOT 하부 단계는 몇 개인가?]**
**[RETRIEVE: 왜 swap을 비활성화해야 하는가?]**
**[RETRIEVE: SECDS-T2RootCA를 저장하는 두 가지 경로는 무엇인가?]**

### Chapter 3 Recall Questions

- **사실 기반:** DSPAAS 1-7에서 수행하는 5가지 하부 단계(1-7-1~1-7-6)의 순서대로 나열하시오.
- **비교:** make_list.sh와 make_list2.sh 스크립트의 역할 차이를 설명하시오.
- **이해:** 왜 ROOT 1-9-3에서 fstab의 swap 설정을 주석 처리하는 것이 중요한가?

---

## 4. 관계도

DSPAAS VM Pre-setting Node Join Procedure의 각 단계는 서로 밀접하게 연결되어 있으며, 한 단계의 실패가 다음 단계에 영향을 미칩니다. 이 섹션에서는 각 구성 요소 간의 관계를 설명합니다.

### 순차적 의존성
```
1-1 (디렉토리 생성) → 1-2 (/etc/hosts 업데이트) → 1-3 (스크립트 작성) → 1-4 (dspaas 계정)
        ↓
    1-5 (SSH key 배포) → 1-6 (노드 SPEC 확인) → 1-7 (System Config)
        ↓
    1-8 (SELinux/firewalld 비활성화) → 1-9 (Filesystem 재구성) → 1-10 (패키지 설치)
        ↓
    1-11 (CA Cert 배포) → 2-1~2-2 (Ansible Playbook 실행)
```

### 단계 간 의존성 분석
1. **1-4와 1-5의 관계:** dspaas 계정(1-4)이 생성되지 않으면 SSH key 배포(1-5)가 불가능합니다. 또한 sudoers 파일 수정이 잘못되면 SSH 연결은 되지만 ansible 명령어 실행 시 권한 에러가 발생합니다.
2. **1-7과 1-8의 관계:** DNS 및 시간 동기화 설정(1-7)이 완료되어야 SELinux/firewalld 비활성화(1-8)를 수행할 수 있습니다. 이는 시간 동기화가 없으면 certificate 검증에 실패할 수 있기 때문입니다.
3. **1-9와 1-10의 관계:** Filesystem 재구성(1-9)이 완료되어야 패키지 설치(1-10)를 수행할 수 있습니다. 컨테이너 데이터 디스크가 제대로 마운트되지 않으면 containerd 관련 패키지가 오류를 발생시킬 수 있습니다.
4. **1-11과 2-1~2-2의 관계:** CA Cert 배포(1-11)가 완료되어야 Ansible Playbook 실행(2-1~2-2)에서 SSL/TLS 통신이 성공합니다. 인증서가 없으면 kubelet과 API 서버 간 통신이 차단됩니다.

### 역할 분담
- **Bastion 서버:** 모든 설정 작업의 시작점이며, ansible 명령어를 직접 실행하는 위치입니다.
- **신규 노드(VM):** 설정 대상이며, 최종적으로 Kubernetes를 실행할 머신입니다.
- **Nexus 레포지토리:** CA 인증서와 RPM 패키지가 저장되는 중앙 저장소입니다.

**[RETRIEVE: 1-4와 1-5의 의존성 관계는?]**
**[RETRIEVE: Bastion 서버, 신규 노드, Nexus 레포지토리의 역할은 각각 무엇인가?]**
**[RETRIEVE: CA Cert 배포가 완료되지 않으면 어떤 문제가 발생하는가?]**

### Chapter 4 Recall Questions

- **사실 기반:** VM Pre-setting 절차의 전체 순서를 단계별로 나열하시오.
- **비교:** Bastion 서버에서의 작업과 신규 노드에서의 작업을 비교하여 설명하시오.
- **이해:** 왜 각 단계 사이에 의존성이 존재하는가?

---

## 5. 사례

실제 DSPAAS VM Pre-setting Node Join Procedure 수행 시 발생할 수 있는 다양한 상황과 해결 방법을 다룹니다. 아래는 실제 운영 환경에서 겪었던 사례들입니다.

### 사례 1: ssh_copy.sh 스크립트 실행 중 비밀번호 에러
sshpass를 사용하여 SSH key 배포 시, 일부 노드에서 "Permission denied (publickey)" 오류가 발생한 경우. 원인은 기존 노드에 이미 다른 공개키가 등록되어 있었기 때문입니다. 해결 방법: `~/.ssh/known_hosts` 파일을 먼저 제거하고 재실행했습니다.

```bash
# ssh_copy.sh 스크립트 생성 예시
cat scale-out.list | awk '{print $2}' > ssh_copy.sh
sed -i 's/^/sshpass -p "test" ssh-copy-id -o StrictHostKeyChecking=no dspaas\@/g' ssh_copy.sh

# 실행 전 known_hosts 정리
for i in khk8cspb1wpw04 khk8cspb1wpw05 khk8cspb1wpw06; do 
  sed -i "/$i/d" ~/.ssh/known_hosts
done

./ssh_copy.sh
```

### 사례 2: sudoers 파일 수정 후 루트 권한 손실
sudoers 파일을 잘못 수정하여 루트 비밀번호 변경이 불가능해진 경우. 이 문제는 매우 심각한데, root 계정 자체가 잠기면 해당 노드는 완전히 사용 불가 상태가 됩니다. 해결 방법: KVM 콘솔에 직접 접속하거나 BMC(IPMI)를 통해 수동으로 /etc/sudoers 파일을 복구해야 했습니다.

```bash
# 올바른 sudoers 파일 수정 순서
1. 백업 생성: cp /etc/sudoers ./sudoers.bak
2. 주석 해제: sed -i 's/# %wheel\tALL=(ALL)\tNOPASSWD: ALL/%wheel ALL=(ALL) NOPASSWD: ALL/g' ./sudoers
3. 검증: cat /etc/group | grep wheel && cat /etc/sudoers | grep "%wheel"
4. 적용: ansible all -i inventory_$(date +'%Y%m%d') -m copy -a "src=./sudoers dest=/etc/sudoers" -k -u root
5. 확인: ansible all -i inventory_$(date +'%Y%m%d') -m shell -a "cat /etc/sudoers | grep %wheel" -k -u root
```

### 사례 3: chrony 동기화 실패로 인한 kubelet 에러
chronyd가 제대로 시작되지 않아 kubelet이 API 서버와 통신할 때 time drift 오류를 발생시킨 경우. 해결 방법: `chronyc sources -v` 명령어로 NTP 소스 연결 상태를 확인하고, 문제 있는 source는 제거한 후 다시 설정했습니다.

```bash
# chrony 상태 확인 및 문제 해결
chronyc sources -v  # NTP 소스 목록 표시
date                 # 현재 시간 확인
systemctl restart chronyd  # 서비스 재시작
chronyc tracking      # 추적 정보 확인
```

### 사례 4: CA Cert 미배포로 인한 PVC 마운트 실패
1-11 단계를 건너뛰고 Ansible Playbook을 실행한 결과, PVC(PersistentVolumeClaim) 생성 시 CSI 드라이버가 API 서버와 통신할 때 SSL handshake에 실패하는 경우. 이 문제는 PVC가 Bound 상태가 되지 않고 Pending 상태로 남아 있는 것으로 나타났습니다.

```bash
# CA Cert 배포 명령어
wget http://nexus.adpaas.cloud.samsungds.net/repository/paas-filerepo/SECDS-ROOTCA.crt
ansible all -i inventory_$(date +'%Y%m%d') -m copy \
  -a "src=./SECDS-ROOTCA.crt dest=/etc/containerd/certs.d/ mode=0644 owner=root group=root" -b

wget http://nexus.adpaas.cloud.samsungds.net/repository/paas-filerepo/SECDS-T2RootCA.crt
ansible all -i inventory_$(date +'%Y%m%d') -m copy \
  -a "src=./SECDS-T2RootCA.crt dest=/etc/pki/ca-trust/source/anchors mode=0644 owner=root group=root" -b

ansible all -i inventory_$(date +'%Y%m%d') -m shell -a "update-ca-trust" -b
```

### 사례 5: swap 비활성화 후 재부팅 후에도 swap이 활성화된 경우
fstab 파일의 swap 설정을 주석 처리하지 않고 swapoff만 실행한 경우. 이 문제는 부팅 시 자동으로 다시 swap이 마운트되는 것이었습니다. 해결 방법: fstab 파일을 직접 수정하고 reboot을 수행하여 영구적으로 비활성화했습니다.

```bash
# swap 영구 비활성화 확인
cat /etc/fstab | grep -i "swap"   # 주석 처리된 swap 라인 확인
free -h                           # 현재 swap 상태 확인
```

**[RETRIEVE: ssh_copy.sh 스크립트 실행 중 Permission denied 에러의 원인은?]**
**[RETRIEVE: sudoers 파일 수정 후 루트 권한이 손실될 경우 어떻게 복구하는가?]**
**[RETRIEVE: chrony 동기화 실패 시 kubelet에서 어떤 오류가 발생하는가?]**

### Chapter 5 Recall Questions

- **사실 기반:** 사례 2에서 sudoers 파일 수정 후 루트 권한을 복구하기 위해 사용하는 두 가지 방법은?
- **비교:** chronyc sources -v와 chronyc tracking 명령어의 차이점을 설명하시오.
- **이해:** 왜 사례 4에서 CA Cert 미배포가 PVC 마운트 실패로 이어지는지 설명하시오.

---

## 6. 오해

DSPAAS VM Pre-setting Node Join Procedure를 수행하는 과정에서 흔히 발생하는 오해와 잘못된 인식을 바로잡습니다.

### 오해 1: SSH key 배포 시 passwordless 연결이 필요 없다는 생각
일부 운영자는 sshpass를 사용한 비밀번호 기반 연결만으로도 충분하다고 생각하는 경향이 있습니다. 그러나 sshpass는 임시 용도로만 사용되어야 하며, 실제 운영 환경에서는 공개키 기반 인증을 반드시 사용해야 합니다. sshpass가 설치되어 있지 않은 노드에서 scp 명령어가 실패하는 경우가 발생합니다.

### 오해 2: SELinux 설정은 테스트용 VM에서만 필요하다는 생각
SELinux를 disabled로 설정하지 않으면 kubelet이 컨테이너 런타임과 통신할 때 권한 에러가 발생하고, Pod가 정상적으로 시작되지 않습니다. 특히 RHEL/CentOS 기반 노드에서는 SELinux policy가 enforced 모드로 기본값으로 설정되어 있어 반드시 비활성화해야 합니다.

### 오해 3: swap 메모리 사용은 성능에 도움이 된다는 생각
Kubernetes는 swap을 사용하지 않도록 권장하며, kubelet은 `--fail-swap-on` 플래그를 통해 swap이 활성화된 노드에서 실행되지 않도록 설계되어 있습니다. swap을 활성화한 상태로 kubespray scale.yml을 실행하면 Pod가 해당 노드에 스케줄링되지 않습니다.

### 오해 4: DNS 설정은 resolv.conf만 수정하면 된다는 생각
NetworkManager의 DNS 관리를 비활성화하지 않으면 resolv.conf 변경이 무시됩니다. `/etc/NetworkManager/NetworkManager.conf`의 `[main]` 섹션에 `dns=none` 라인을 추가해야 NetworkManager가 resolv.conf를 덮어쓰지 않습니다.

### 오해 5: CA Cert 배포는 한 번만 해도 된다는 생각
신규 노드에만 CA Cert를 배포하면 기존 노드와 신규 노드의 인증서 불일치로 인해 API 서버 간 통신에 문제가 발생할 수 있습니다. 따라서 모든 노드에 CA Cert를 배포하고 `update-ca-trust` 명령어로 각 노드의 CA 저장소를 개별적으로 업데이트해야 합니다.

### 오해 6: Ansible Playbook 실행 시 --limit 옵션이 필요 없다는 생각
신규 노드만 조인하려면 반드시 `--limit "new_worker_node"` 옵션을 사용해야 합니다. 이 옵션을 사용하지 않으면 모든 노드에 대한 재구성이 수행되어 기존에 작동하던 서비스에도 영향을 미칠 수 있습니다.

**[RETRIEVE: sshpass를 사용할 때 주의사항은?]**
**[RETRIEVE: kubelet의 --fail-swap-on 플래그는 어떤 역할을 하는가?]**
**[RETRIEVE: 왜 NetworkManager의 dns=none 설정이 필요한가?]**

### Chapter 6 Recall Questions

- **사실 기반:** 오해 4에서 `/etc/NetworkManager/NetworkManager.conf`에 추가해야 할 라인은?
- **비교:** sshpass 기반 인증과 공개키 기반 인증의 차이점을 설명하시오.
- **이해:** --limit 옵션 없이 scale.yml을 실행했을 때 어떤 위험이 있는가?

---

## 7. 회상키포인트

### Chapter 1 (탄생배경) — 회상 키포인트
1. 노드 조인은 인프라 확장 시 가장 빈번한 운영 행위
2. DSPAAS VM Pre-setting은 최소 20개 이상의 개별 구성 작업 포함
3. CA 인증서가 없으면 CSI 볼륨 마운트 실패
4. VM 초기 상태는 Kubernetes 요구사항과 불일치하므로 사전 조정 필요
5. 노드 조인 절차: VM Pre-setting(1-1~1-11) → Ansible Playbook(2-1~2-2) → Post-deployment 검증(3-1~4-2)

### Chapter 2 (정의) — 회상 키포인트
1. DSPAAS VM Pre-setting은 신규 VM을 기존 클러스터에 조인하기 위한 사전 설정 프로세스
2. 6개 핵심 구성 요소: dspaas 계정, SSH Key, System Config, Filesystem Reconfig, CA Cert Distribution, Package Install
3. 모든 노드가 동일한 상태여야 함 (containerd 버전, kernel 버전 등)

### Chapter 3 (하위개념) — 회상 키포인트
1. DSPAAS 1-4의 ROOT 하부 단계: 계정 확인 → 계정 생성 → sudoers 수정 → 비밀번호 설정 (총 4단계)
2. DSPAAS 1-7의 5가지 하부 단계: resolv.conf → chrony.conf → NetworkManager.conf → swapoff → logrotate/YUM repo
3. DSPAAS 1-9: fstab 백업 → 디스크 재구성 → swap 주석 처리 → reboot (총 4단계)
4. CA Cert 배포 시 update-ca-trust 필수 실행

### Chapter 4 (관계도) — 회상 키포인트
1. 단계 간 순차적 의존성: 각 단계가 완료되어야 다음 단계 진행 가능
2. Bastion 서버 = 작업 시작점, 신규 노드 = 설정 대상, Nexus 레포지토리 = 중앙 저장소

### Chapter 5 (사례) — 회상 키포인트
1. ssh_copy.sh 실행 시 known_hosts 정리 필요
2. sudoers 파일 수정 전 반드시 백업하고, 잘못될 경우 KVM/IPMI로 복구 필요
3. chrony 동기화 실패 → kubelet time drift 오류 발생
4. CA Cert 미배포 → PVC 마운트 실패 (Pending 상태)

### Chapter 6 (오해) — 회상 키포인트
1. sshpass는 임시용, 공개키 인증 필수
2. SELinux disabled: RHEL/CentOS 기본값 enforced이므로 반드시 비활성화 필요
3. kubelet의 --fail-swap-on 플래그: swap 활성화 시 Pod 스케줄링 방지
4. NetworkManager의 dns=none 설정: resolv.conf 변경 무시 방지

**[RETRIEVE: 1-4의 ROOT 하부 단계 중 sudoers 수정 후 어떤 문제가 발생할 수 있는가?]**
**[RETRIEVE: CA Cert 배포 시 update-ca-trust를 실행하지 않으면 어떤 문제가 발생하는가?]**
**[RETRIEVE: --fail-swap-on 플래그는 어떤 상황을 방지하는가?]**

### Chapter 7 (회상키포인트) — 회상 키포인트
- 이 문서는 DSPAAS VM Pre-setting Node Join Procedure의 전 과정을 학습하기 위한 자료입니다.
- 각 챕터 말미의 Recall Questions를 통해 자신의 이해도를 확인하세요.
- 실제 작업 시에는 원본 문서(Kubespray scale-out reference)를 반드시 함께 참조하세요.

---

## 참고자료

1. DSPAAS VM Pre-setting Node Join Procedure — Scale-out Reference (Original source: /home/user01/project/work/issue/cases/2026-04-23-node-join-dspaas-vm-scale-out-reference/raw/bundles/20260423-node-join-dspaas-vm-reference/raw.txt)
2. Kubespray v2.24.1 Documentation — https://kubespray.io/docs/v2.24.1/
3. Kubernetes Node Management Guide — https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/
4. containerd SSL/TLS Configuration — https://containerd.io/docs/reference/configuration/#certificates
5. SELinux User's Guide (RHEL 8) — https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_and_managing_selinux/getting-started-with-selinux_red-hat-enterprise-linux-8_configuring-and-managing-selinux
6. Chrony NTP Configuration Guide — https://chrony-project.org/doc/4.2/chrony-administration-guide.html

**[RETRIEVE: DSPAAS VM Pre-setting의 핵심 구성 요소는 무엇인가?]**
**[RETRIEVE: 왜 각 단계가 순차적으로 수행되어야 하는가?]**
**[RETRIEVE: 기존 노드와 신규 노드의 상태를 동일하게 유지해야 하는 이유는?]**

## Chapter 7 Recall Questions

- **사실 기반:** DSPAAS VM Pre-setting에서 CA Cert 배포 시 `update-ca-trust` 명령어를 실행하지 않으면 어떤 문제가 발생하는가?
- **비교:** sshpass 기반 SSH 인증과 공개키 기반 SSH 인증의 차이점을 설명하시오.
- **이해:** --fail-swap-on 플래그는 어떤 상황에서 어떤 역할을 수행하는가?
