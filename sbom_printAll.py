import subprocess

def get_process_ids():
    # ps aux | awk '{print $2}' -> 프로세스 ID 출력
    result = subprocess.run(["ps", "aux"], stdout=subprocess.PIPE, text=True)
    pids = [line.split()[1] for line in result.stdout.splitlines()[1:]]  # 첫 번째 줄 제외하고 PID 추출
    return pids

def get_dynamic_libraries_for_pid(pid):
    # sudo pldd {pid} -> 해당 프로세스가 참조하는 동적 라이브러리 출력
    result = subprocess.run(["sudo", "pldd", pid], stdout=subprocess.PIPE, text=True)
    libraries = []
    
    # 첫 번째 두 줄을 제외한 후 나머지 라인에서 라이브러리 경로 추출
    for line in result.stdout.splitlines()[2:]:  # 첫 두 줄 제외
        parts = line.split()
        if len(parts) > 0:  # 두 번째 항목이 있는 경우만 처리
            libraries.append(parts[0])
    return libraries

def get_library_version(library_path):
    # readelf -V {library_path} -> 라이브러리 버전 정보 출력
    result = subprocess.run(["readelf", "-V", library_path], stdout=subprocess.PIPE, text=True)
    return result.stdout

def get_needed_libraries(library_path):
    # readelf -d {library_path} | grep NEEDED -> 참조하는 동적 라이브러리 출력
    result = subprocess.run(["readelf", "-d", library_path], stdout=subprocess.PIPE, text=True)
    needed_libraries = []
    for line in result.stdout.splitlines():
        if "NEEDED" in line:
            # awk -F'[][]|:' '{print $3}' -> 동적 라이브러리 이름만 출력
            needed_libraries.append(line.split()[4].strip('[]'))
    return needed_libraries

def get_library_path(lib_name):
    # ldconfig -p | grep {lib_name} -> 참조하는 동적 라이브러리 경로 확인
    result = subprocess.run(["ldconfig", "-p"], stdout=subprocess.PIPE, text=True)
    for line in result.stdout.splitlines():
        if lib_name in line:
            # awk '{print $NF}' -> 경로만 출력
            return line.split()[-1]
    return None

def get_recursive_dependencies(library_path):
    # 동적 라이브러리 경로를 재귀적으로 탐색하여 종속성을 확인
    needed_libraries = get_needed_libraries(library_path)
    dependencies = []
    for lib in needed_libraries:
        lib_path = get_library_path(lib)
        if lib_path:
            dependencies.append(lib_path)
            dependencies.extend(get_recursive_dependencies(lib_path))
    return dependencies

def main():
    # 모든 실행 중인 프로세스에 대해 동적 라이브러리 경로 재귀적으로 출력
    pids = get_process_ids()
    for pid in pids:
        print(f"Process ID: {pid}")
        libraries = get_dynamic_libraries_for_pid(pid)
        for lib in libraries:
            print(f"  Library: {lib}")
            dependencies = get_recursive_dependencies(lib)
            print(f"    Dependencies:")
            for dep in dependencies:
                print(f"      - {dep}")

if __name__ == "__main__":
    main()
