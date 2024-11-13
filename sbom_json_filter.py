import re
import json

# 파일 경로 지정
file_path = 'sbom_library_versions2.txt'  # 여기서 'readelf_output.txt'는 텍스트 파일 경로입니다.

# 텍스트 파일에서 readelf -V 출력 결과 읽기
with open(file_path, 'r') as file:
    readelf_output = file.read()

# 라이브러리 이름에 해당하는 정규식
lib_pattern = re.compile(r"Library:\s*(/[\w/\.-]+\.so[\.\d]+)")

# 각 라이브러리 정보에 해당하는 섹션
libs = re.split(lib_pattern, readelf_output)[1:]

# 결과를 저장할 딕셔너리
library_info = {}

# 라이브러리별로 데이터를 나누기
for i in range(0, len(libs), 2):
    lib_name = libs[i].strip()
    lib_data = libs[i+1].strip()

    # .gnu.version_d에서 name 추출
    gnu_version_d_pattern = r"\s+Name:\s+([A-Za-z0-9\._/-]+)"
    gnu_version_d_matches = re.findall(gnu_version_d_pattern, lib_data)

    # .gnu.version_r에서 name과 version 추출
    gnu_version_r_pattern = r"Name:\s+([A-Za-z0-9\._/-]+)\s+Flags:.*?Version:\s+(\d+)"
    gnu_version_r_matches = re.findall(gnu_version_r_pattern, lib_data)

    # JSON 데이터 구조 생성
    library_info[lib_name] = {
        "gnu_version_d": [{"name": name} for name in gnu_version_d_matches],
        "gnu_version_r": [{"name": name, "version": int(version)} for name, version in gnu_version_r_matches]
    }

# JSON 파일로 저장
output_file = 'output.json'  # JSON 파일로 저장할 경로
with open(output_file, 'w') as json_file:
    json.dump(library_info, json_file, indent=4)

print(f"JSON 파일이 '{output_file}'로 저장되었습니다.")
