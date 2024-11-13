import subprocess

def get_process_ids():
    # 실행 중인 모든 프로세스 ID를 가져옵니다.
    result = subprocess.run(["ps", "aux"], stdout=subprocess.PIPE, text=True)
    pids = [line.split()[1] for line in result.stdout.splitlines()[1:]]  # 첫 번째 줄 제외하고 PID 추출
    return pids

def get_dynamic_libraries_for_pid(pid):
    # 특정 프로세스 ID에 대한 동적 라이브러리를 가져옵니다.
    result = subprocess.run(["sudo", "pldd", pid], stdout=subprocess.PIPE, text=True)
    libraries = []
    
    # 첫 두 줄을 제외한 후 나머지 라인에서 라이브러리 경로를 추출합니다.
    for line in result.stdout.splitlines()[2:]:  # 첫 두 줄 제외
        parts = line.split()
        if len(parts) > 0:
            libraries.append(parts[0])
    return libraries

def save_all_library_versions(library_path, file):
    # 라이브러리 버전 정보를 하나의 파일에 추가합니다.
    result = subprocess.run(["readelf", "-V", library_path], stdout=subprocess.PIPE, text=True)
    file.write(f"Library: {library_path}\n")
    file.write(result.stdout)
    file.write("\n" + "-" * 80 + "\n")  # 구분선 추가

def get_needed_libraries(library_path):
    # 주어진 라이브러리가 참조하는 동적 라이브러리를 가져옵니다.
    result = subprocess.run(["readelf", "-d", library_path], stdout=subprocess.PIPE, text=True)
    needed_libraries = []
    for line in result.stdout.splitlines():
        if "NEEDED" in line:
            needed_libraries.append(line.split()[4].strip('[]'))
    return needed_libraries

def get_library_path(lib_name):
    # 라이브러리 이름을 통해 라이브러리 경로를 찾습니다.
    result = subprocess.run(["ldconfig", "-p"], stdout=subprocess.PIPE, text=True)
    for line in result.stdout.splitlines():
        if lib_name in line:
            return line.split()[-1]
    return None

def get_recursive_dependencies(library_path):
    # 라이브러리의 모든 종속성을 재귀적으로 가져옵니다.
    needed_libraries = get_needed_libraries(library_path)
    dependencies = []
    for lib in needed_libraries:
        lib_path = get_library_path(lib)
        if lib_path:
            dependencies.append(lib_path)
            dependencies.extend(get_recursive_dependencies(lib_path))
    return dependencies

def main():
    # 실행 중인 모든 프로세스가 사용하는 라이브러리 버전을 하나의 파일에 저장합니다.
    with open("sbom_library_versions.txt", "w") as file:
        pids = get_process_ids()
        for pid in pids:
            file.write(f"Process ID: {pid}\n")
            libraries = get_dynamic_libraries_for_pid(pid)
            for lib in libraries:
                # file.write(f"  Library: {lib}\n")
                save_all_library_versions(lib, file)  # 라이브러리 버전을 하나의 파일에 저장
                dependencies = get_recursive_dependencies(lib)
                # file.write(f"    Dependencies:\n")
                # for dep in dependencies:
                #     file.write(f"      - {dep}\n")
            file.write("\n" + "=" * 80 + "\n")  # 각 프로세스 구분선 추가

if __name__ == "__main__":
    main()
