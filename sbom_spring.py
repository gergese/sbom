import re
import json
import subprocess

# Gradle 명령을 실행할 디렉토리
gradle_project_dir = "/home/user/spring/hello"

def parse_gradle_dependencies_from_command():
    # Gradle 명령어 실행
    result = subprocess.run(["./gradlew", "dependencies", "--configuration", "runtimeClasspath"], 
                            cwd=gradle_project_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # 명령어 실행 결과를 stdout에서 추출
    output = result.stdout

    dependencies = []
    seen_dependencies = set()  # 중복을 확인할 set

    stack = []

    # 패턴 수정: +---와 | +--- 모두 처리
    pattern = re.compile(r"(\s*\+---|\|.*\+---|\|.*\s*\\---|\s*\\---) ([\w\.\-]+):([\w\.\-]+)(?::([\w\.\-]+))?(?:\s*->\s*([\w\.\-]+))?")

    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            indent_level = line.find(match.group(2))  # 들여쓰기 레벨 추출
            version = match.group(5) if match.group(5) else match.group(4)  # -> 뒤 버전이 있으면 그 버전 사용

            # 의존성 정보
            dependency = {
                "group": match.group(2),
                "dependency": match.group(3),
                "version": version,  # 버전 업데이트 처리
            }

            # 중복 체크: (group, dependency, version)을 tuple로 변환하여 확인
            dependency_key = (dependency["group"], dependency["dependency"], dependency["version"])
            if dependency_key not in seen_dependencies:
                # 중복되지 않으면 의존성 목록에 추가
                dependencies.append(dependency)
                seen_dependencies.add(dependency_key)

            # 스택에서 깊은 레벨을 제거
            while stack and stack[-1]["indent"] >= indent_level:
                stack.pop()

            # 현재 레벨을 스택에 추가
            stack.append({"dependency": dependency, "indent": indent_level})

    return dependencies

# Gradle 명령어에서 의존성 정보 추출
dependencies = parse_gradle_dependencies_from_command()

# JSON으로 저장
output_file = "sbom_spring_dependencies.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(dependencies, f, indent=4, ensure_ascii=False)

print(f"의존성 저장 : {output_file}")
