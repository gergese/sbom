import subprocess
import json

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

def get_library_version(library_path):
    # 라이브러리의 버전 정보를 추출합니다.
    result = subprocess.run(["readelf", "-V", library_path], stdout=subprocess.PIPE, text=True)
    return result.stdout

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

def get_recursive_dependencies(library_path, processed_libraries):
    # 라이브러리의 모든 종속성을 재귀적으로 가져옵니다.
    needed_libraries = get_needed_libraries(library_path)
    dependencies = []
    for lib in needed_libraries:
        lib_path = get_library_path(lib)
        if lib_path and lib_path not in processed_libraries:
            processed_libraries.add(lib_path)  # 처리한 라이브러리 추가
            dependencies.append({
                "library": lib_path,
                "version_info": get_library_version(lib_path),
                "dependencies": get_recursive_dependencies(lib_path, processed_libraries)
            })
    return dependencies

def main():
    # 실행 중인 모든 프로세스가 사용하는 라이브러리 버전을 JSON 파일에 저장합니다.
    processed_libraries = set()  # 처리된 라이브러리 경로를 저장할 집합
    libraries_info = []  # 라이브러리 정보를 저장할 리스트

    pids = get_process_ids()
    for pid in pids:
        libraries = get_dynamic_libraries_for_pid(pid)
        for lib in libraries:
            if lib not in processed_libraries:
                processed_libraries.add(lib)  # 중복 방지
                library_info = {
                    "library": lib,
                    "version_info": get_library_version(lib),
                    "dependencies": get_recursive_dependencies(lib, processed_libraries)
                }
                libraries_info.append(library_info)

    # JSON 파일로 저장
    with open("sbom_library_versions.json", "w") as file:
        json.dump(libraries_info, file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
