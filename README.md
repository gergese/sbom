sbom 개인 프로젝트

명령어
ps aux
sudo pldd 233438 - pid
readelf -V /lib/x86_64-linux-gnu/libwrap.so.0

우선 쉽게 find로 requirement.txt 확인해서 확인해보고
그 다음에 프로세스들의 동적 라이브러리 확인해서 하나의 파일에 다 모으기


1. 우분투에서 실행중인 프로세스들의 라이브러리 정보 수집
sudo sysctl -w kernel.yama.ptrace_scope=0 => ptrace 차단 해제?

ps aux => 실행되고 있는 프로세스들 출력
ps aux | awk '{print $2}' => pid만 출력

pldd 233438 => 해당 프로세스가 참조하는 동적 라이브러리 출력

readelf -V /lib/x86_64-linux-gnu/libwrap.so.0 => 라이브러리 버전 정보 확인

readelf -d /lib64/ld-linux-x86-64.so.2 => 여기서 type = needed가 참조하는 동적 라이브러리 부분
readelf -d /lib/x86_64-linux-gnu/libwrap.so.0 | grep NEEDED | awk -F'[][]|:' '{print $3}' => 참조하는 동적 라이브러리만 출력

ldconfig -p | grep libnsl.so.2 => 참조하는 동적 라이브러리 경로 확인
ldconfig -p | grep libnsl.so.2 | awk '{print $NF}' => 경로만 출력

2. 재귀적으로 버전 확인
3. 동적 라이브러리 경로를 재귀적으로 전달

sudo sysctl -w kernel.yama.ptrace_scope=0 => ptrace 차단
중복제거

=> sbom_printAll.py - 결과 출력
=> sbom_SaveAll_txt.py - 결과를 txt파일로 저장
=> sbom_rmDup_txt.py - 결과 중 중복되는 라이브러리는 제거하고 저장



4. json으로 저장
5. 라이브러리 이름, 경로, 버전 정보, 불러오는 것들의 정보

=> sbom_json_filter.py - 라이브러리별 정보 저장
=> sbom_json_jsonParse.py - json 형식 정리



6. apache 같은 서비스에서 자체적으로 사용하는 라이브러리, 참조하는데 사용하는 라이브러리, 리눅스 자체 내장 라이브러리를 구분
7. json으로 저장



각 서버 spring에 있는 log4j 버전을 확인하고 취약 유무를 판별
1. spring 의존성 버전 추출
./gradlew dependencies --configuration runtimeClasspath
=> 기존 추출 방식과 달라 새로 추출
=> sbom_spring.py - 의존성 추출 코드
=> sbom_spring_dependencies.json - 추출 결과

2. elk에 올려서 데이터 확인

3. log4j 취약 버전 CVE로 확인하고 비교
