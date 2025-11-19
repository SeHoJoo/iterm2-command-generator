# iTerm2 AI 명령어 생성기

iTerm2에서 자연어로 원하는 작업을 설명하면 AI가 적절한 쉘 명령어를 생성해주는 플러그인입니다.

## 기능

- **자연어 → 명령어 변환**: "지난 7일간 수정된 파일 찾기" → `find . -mtime -7`
- **명령어 설명**: 생성된 명령어의 각 플래그와 옵션에 대한 상세 설명
- **위험 명령어 경고**: `rm -rf /` 같은 위험한 명령어에 대한 경고 표시
- **히스토리 저장**: 자주 사용하는 명령어를 저장하고 재사용

## 설치

### 요구사항

- macOS 10.14+
- iTerm2 3.3+
- Python 3.7+
- Google Gemini API 키 (https://aistudio.google.com/apikey)

### 설치 방법

1. **iTerm2 Python Runtime 설치**

iTerm2 > Scripts > Manage > Install Python Runtime

2. **설치 스크립트 실행**

```bash
./install.sh
```

3. **iTerm2 재시작**

처음 실행 시 Gemini API 키 입력 창이 나타납니다.

## 사용법

1. `Ctrl+Shift+A`를 눌러 입력 창 활성화
2. 원하는 작업을 자연어로 입력
3. 생성된 명령어가 터미널에 자동 삽입됨 (위험 명령어는 경고 후 확인)

### 단축키

- `Ctrl+Shift+A`: AI 명령어 생성
- `Ctrl+Shift+L`: 히스토리 열기

### 사용 예시

```
입력: "현재 디렉토리의 모든 파일 크기 확인"
결과: ls -lh

입력: "지난 7일간 수정된 파일 찾기"
결과: find . -mtime -7 -type f

입력: "포트 3000을 사용하는 프로세스 찾기"
결과: lsof -i :3000

입력: "README.md 파일에서 'TODO' 찾기"
결과: grep -n "TODO" README.md

입력: "node_modules 폴더 제외하고 .js 파일 찾기"
결과: find . -name "*.js" -not -path "*/node_modules/*"
```

### 동작 방식

- **일반 명령어**: 확인 없이 터미널에 바로 삽입 (Enter는 직접 눌러야 함)
- **위험 명령어**: 경고 다이얼로그 표시 후 삽입 여부 선택
- **히스토리**: 모든 생성된 명령어는 자동으로 히스토리에 저장

## API 키 설정

첫 실행 시 Gemini API 키 입력 프롬프트가 나타납니다.

수동 설정:
```bash
python3 -c "import keyring; keyring.set_password('iterm2-ai-generator', 'gemini-api-key', 'YOUR_API_KEY')"
```

## 개발

```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 개발 의존성 설치
pip install -r requirements-dev.txt

# 테스트 실행
pytest tests/
```

## 트러블슈팅

### 플러그인이 로드되지 않음

1. iTerm2 > Scripts 메뉴에서 스크립트가 보이는지 확인
2. Python Runtime이 설치되어 있는지 확인: iTerm2 > Scripts > Manage > Install Python Runtime
3. 로그 파일 확인: `~/.config/iterm2-ai-generator/debug.log`

### API 키 오류

```bash
# API 키 삭제 후 재설정
security delete-generic-password -s "iterm2-ai-generator" -a "gemini-api-key"
```

### 단축키가 작동하지 않음

1. iTerm2 설정에서 키보드 단축키 충돌 확인
2. 다른 앱에서 동일한 단축키 사용 여부 확인
3. iTerm2 재시작

### Rate Limit 오류

Google Gemini API는 무료 티어에서 분당 요청 제한이 있습니다.
- 잠시 후 다시 시도
- 또는 유료 플랜으로 업그레이드

### 히스토리 초기화

```bash
rm ~/.config/iterm2-ai-generator/history.json
```

### 설정 초기화

```bash
rm ~/.config/iterm2-ai-generator/config.json
```

## 파일 위치

- 설정: `~/.config/iterm2-ai-generator/config.json`
- 히스토리: `~/.config/iterm2-ai-generator/history.json`
- 로그: `~/.config/iterm2-ai-generator/debug.log`
- API 키: macOS Keychain (iterm2-ai-generator)

## 라이선스

MIT License
