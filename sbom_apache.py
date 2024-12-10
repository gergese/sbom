import subprocess
import re
import json
from collections import defaultdict

def get_apache_pids():
    # 'httpd' 또는 'apache2'로 실행 중인 Apache 프로세스의 PID를 가져옵니다.
    result = subprocess.run(["ps", "aux"], stdout=subprocess.PIPE, text=True)
    apache_pids = [
        line.split()[1]
        for line in result.stdout.splitlines()[1:]  # 첫 번째 줄 제외
        if "httpd" in line or "apache2" in line
    ]
    return apache_pids

def get_dynamic_libraries_for_pid(pid):
    # 특정 프로세스 ID에 대한 동적 라이브러리를 가져옵니다.
    result = subprocess.run(["sudo", "pldd", pid], stdout=subprocess.PIPE, text=True)
    libraries = []
    for line in result.stdout.splitlines()[2:]:  # 첫 두 줄 제외
        parts = line.split()
        if len(parts) > 0:
            libraries.append(parts[0])
    return libraries

def save_all_library_versions(library_path, processed_libraries):
    if library_path in processed_libraries:
        return None
    
    result = subprocess.run(["readelf", "-V", library_path], stdout=subprocess.PIPE, text=True)
    library_version_info = result.stdout
    processed_libraries.add(library_path)
    return library_version_info

def get_needed_libraries(library_path):
    result = subprocess.run(["readelf", "-d", library_path], stdout=subprocess.PIPE, text=True)
    needed_libraries = []
    for line in result.stdout.splitlines():
        if "NEEDED" in line:
            needed_libraries.append(line.split()[4].strip('[]'))
    return needed_libraries

def get_library_path(lib_name):
    result = subprocess.run(["ldconfig", "-p"], stdout=subprocess.PIPE, text=True)
    for line in result.stdout.splitlines():
        if lib_name in line:
            return line.split()[-1]
    return None

def get_recursive_dependencies(library_path, processed_libraries):
    needed_libraries = get_needed_libraries(library_path)
    dependencies = []
    for lib in needed_libraries:
        lib_path = get_library_path(lib)
        if lib_path and lib_path not in processed_libraries:
            dependencies.append(lib_path)
            dependencies.extend(get_recursive_dependencies(lib_path, processed_libraries))
    return dependencies

def get_lib_type(library_path):
    system_paths = ["/usr/lib", "/lib", "/lib64"]
    external_paths = ["/usr/lib/apache2/modules", "/usr/share", "/usr/local/lib"]
    if any(library_path.startswith(path) for path in external_paths):
        return "external"
    elif any(library_path.startswith(path) for path in system_paths):
        return "system"

def parse_readelf_output(library_info):
    parsed_info = []
    for lib_name, lib_data in library_info.items():
        file_name = re.search(r"([^/]+)$", lib_name).group(1)
        gnu_version_d_pattern = r"\.gnu\.version_d.*?(?=\.gnu\.version_r|$)"
        gnu_version_d_section = re.search(gnu_version_d_pattern, lib_data, re.DOTALL)
        gnu_version_d_matches = []
        if gnu_version_d_section:
            name_pattern = r"Name:\s+([A-Za-z0-9\._/-]+)"
            gnu_version_d_matches = [match.group(1) for match in re.finditer(name_pattern, gnu_version_d_section.group(0))]
            gnu_version_d_matches = gnu_version_d_matches[1:]
        file_pattern = r"File:\s+([A-Za-z0-9\._/-]+).*?Cnt:.*?(?=File:|$)"
        file_matches = re.finditer(file_pattern, lib_data, re.DOTALL)
        gnu_version_r_matches = []
        for file_match in file_matches:
            file_block = file_match.group(0)
            file_name_in_r = file_match.group(1)
            name_version_pattern = r"Name:\s+([A-Za-z0-9\._/-]+)\s+Flags:.*?Version:\s+(\d+)"
            name_version_matches = re.findall(name_version_pattern, file_block)
            ref_ver_info = [{"name": name, "version": int(version)} for name, version in name_version_matches]
            gnu_version_r_matches.append({"ref_lib": file_name_in_r, "ref_ver_info": ref_ver_info})
        lib_type = get_lib_type(lib_name)
        parsed_info.append({
            "lib_name": file_name,
            "lib_path": lib_name,
            "lib_type": lib_type,
            "lib_version": {
                "gnu_version_d": [{"name": name} for name in gnu_version_d_matches],
                "gnu_version_r": gnu_version_r_matches
            }
        })
    return parsed_info

def main():
    processed_libraries = set()
    library_info = []

    pids = get_apache_pids()
    for pid in pids:
        try:
            libraries = get_dynamic_libraries_for_pid(pid)
            for lib in libraries:
                library_version_info = save_all_library_versions(lib, processed_libraries)
                if library_version_info:
                    parsed_info = parse_readelf_output({lib: library_version_info})
                    if parsed_info:
                        library_info.extend(parsed_info)
                dependencies = get_recursive_dependencies(lib, processed_libraries)
                for dep in dependencies:
                    dep_version_info = save_all_library_versions(dep, processed_libraries)
                    if dep_version_info:
                        parsed_info = parse_readelf_output({dep: dep_version_info})
                        if parsed_info:
                            library_info.extend(parsed_info)
        except Exception as e:
            print(f"PID {pid} 처리 중 오류 발생: {e}")

    json_output_file = 'sbom_library_versions_apache2.json'
    with open(json_output_file, 'w') as json_file:
        json.dump(library_info, json_file, indent=4)

    print(f"JSON 파일이 '{json_output_file}'로 저장되었습니다.")

if __name__ == "__main__":
    main()
