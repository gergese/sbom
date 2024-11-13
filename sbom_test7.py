import subprocess
import re
import json
from collections import defaultdict

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

def save_all_library_versions(library_path, processed_libraries):
    # 이미 처리한 라이브러리인지 확인
    if library_path in processed_libraries:
        return None
    
    # 라이브러리 버전 정보를 하나의 문자열로 가져옵니다.
    result = subprocess.run(["readelf", "-V", library_path], stdout=subprocess.PIPE, text=True)
    library_version_info = result.stdout
    
    # 라이브러리를 처리한 것으로 표시
    processed_libraries.add(library_path)
    
    return library_version_info

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
            dependencies.append(lib_path)
            dependencies.extend(get_recursive_dependencies(lib_path, processed_libraries))
    return dependencies

def parse_readelf_output(library_info):
    parsed_info = []

    for lib_name, lib_data in library_info.items():
        # 경로에서 파일 이름만 추출
        file_name = re.search(r"([^/]+)$", lib_name).group(1)

        # .gnu.version_d 섭션에서 Flags: BASE가 없는 Name 추출
        gnu_version_d_pattern = r"\.gnu\.version_d.*?(?=\.gnu\.version_r|$)"
        gnu_version_d_section = re.search(gnu_version_d_pattern, lib_data, re.DOTALL)
        
        if gnu_version_d_section:
            # gnu_version_d 섹션 내에서 Flags: BASE가 없는 Name 항목만 추출
            name_pattern = r"Name:\s+([A-Za-z0-9\._/-]+)"
            gnu_version_d_matches = [match.group(1) for match in re.finditer(name_pattern, gnu_version_d_section.group(0))]
            # 첫 번째 항목을 제외하고 저장
            gnu_version_d_matches = gnu_version_d_matches[1:]  # 첫 번째 항목 제외
        else:
            gnu_version_d_matches = []

        # .gnu.version_r 섹션에서 File, Name, Version 추출
        file_pattern = r"File:\s+([A-Za-z0-9\._/-]+).*?Cnt:.*?(?=File:|$)"
        file_matches = re.finditer(file_pattern, lib_data, re.DOTALL)

        # 각 File을 개별적으로 처리하여 Name과 Version을 추출
        gnu_version_r_matches = []
        for file_match in file_matches:
            file_block = file_match.group(0)  # 특정 File 블록
            file_name_in_r = file_match.group(1)  # File 이름
            
            # 해당 File 블록 내에서 Name과 Version 추출
            name_version_pattern = r"Name:\s+([A-Za-z0-9\._/-]+)\s+Flags:.*?Version:\s+(\d+)"
            name_version_matches = re.findall(name_version_pattern, file_block)
            
            # Name과 Version을 ref_ver_info 형식으로 저장
            ref_ver_info = [{"name": name, "version": int(version)} for name, version in name_version_matches]
            
            # 파일 이름 및 해당하는 Name-Version 정보 추가
            gnu_version_r_matches.append({
                "ref_lib": file_name_in_r,  # 경로가 아닌 파일 이름
                "ref_ver_info": ref_ver_info
            })

        # JSON 데이터 구조 생성
        parsed_info.append({
            "lib_name": file_name,  # lib_name 추가
            "lib_path": lib_name,   # 원본 경로 저장
            "lib_version": {
                "gnu_version_d": [{"name": name} for name in gnu_version_d_matches],
                "gnu_version_r": gnu_version_r_matches
            }
        })

    return parsed_info

def main():
    processed_libraries = set()  # 처리된 라이브러리 경로를 저장할 집합
    library_info = {}  # 라이브러리 정보 저장할 딕셔너리

    # 실행 중인 모든 프로세스가 사용하는 라이브러리 정보를 메모리에서 처리합니다.
    pids = get_process_ids()
    for pid in pids:
        libraries = get_dynamic_libraries_for_pid(pid)
        for lib in libraries:
            library_version_info = save_all_library_versions(lib, processed_libraries)  # 라이브러리 버전 정보 가져오기
            if library_version_info:
                library_info[lib] = library_version_info
            dependencies = get_recursive_dependencies(lib, processed_libraries)

    # 라이브러리 정보 분석하여 JSON 형태로 변환
    parsed_library_info = parse_readelf_output(library_info)

    # JSON 파일로 저장
    json_output_file = 'sbom_library_versions.json'  # JSON 파일로 저장할 경로
    with open(json_output_file, 'w') as json_file:
        json.dump(parsed_library_info, json_file, indent=4)

    print(f"JSON 파일이 '{json_output_file}'로 저장되었습니다.")

if __name__ == "__main__":
    main()
