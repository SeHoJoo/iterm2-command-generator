# iTerm2 AI Command Generator / AI 명령어 생성기

> AI command generator for iTerm2 using Google Gemini - Generate shell commands with natural language

[![macOS](https://img.shields.io/badge/macOS-10.14+-blue)](https://www.apple.com/macos/)
[![Python](https://img.shields.io/badge/Python-3.7+-green)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](./LICENSE)

An iTerm2 plugin that generates shell commands from natural language descriptions using AI.

iTerm2에서 자연어로 원하는 작업을 설명하면 AI가 적절한 쉘 명령어를 생성해주는 플러그인입니다.

## Demo

![Demo](assets/commands.gif)

## Features / 기능

- **Natural Language → Command**: "Find files modified in the last 7 days" → `find . -mtime -7`
- **Script Generation**: Generate complex bash scripts and copy to clipboard or save to file
- **Dangerous Command Warning**: Warning alerts for dangerous commands like `rm -rf /`
- **History**: Save and reuse frequently used commands
- **Model Selection**: Switch between Gemini models as needed
- **Custom Instructions**: Save custom instructions to apply to all prompts

---

- **자연어 → 명령어 변환**: "지난 7일간 수정된 파일 찾기" → `find . -mtime -7`
- **스크립트 생성**: 복잡한 bash 스크립트 생성 후 클립보드에 복사
- **위험 명령어 경고**: `rm -rf /` 같은 위험한 명령어에 대한 경고 표시
- **히스토리 저장**: 자주 사용하는 명령어를 저장하고 재사용
- **모델 선택**: 상황에 맞게 Gemini 모델 변경 가능
- **사용자 지침**: 커스텀 지침을 저장하여 모든 프롬프트에 자동 적용

## Installation / 설치

### Requirements / 요구사항

- macOS 10.14+
- iTerm2 3.3+
- Python 3.7+
- Google Gemini API Key (https://aistudio.google.com/apikey)

### Installation Steps / 설치 방법

1. **Install iTerm2 Python Runtime / iTerm2 Python Runtime 설치**

iTerm2 > Scripts > Manage > Install Python Runtime

2. **Run installation script / 설치 스크립트 실행**

```bash
./install.sh
```

3. **Restart iTerm2 / iTerm2 재시작**

On first run, you will be prompted to enter your Gemini API key.

처음 실행 시 Gemini API 키 입력 창이 나타납니다.

## Usage / 사용법

1. Press `Ctrl+Cmd+A` to open input dialog / `Ctrl+Cmd+A`를 눌러 입력 창 활성화
2. Describe what you want in natural language / 원하는 작업을 자연어로 입력
3. Generated command is inserted into terminal / 생성된 명령어가 터미널에 자동 삽입됨

### Shortcuts / 단축키

- `Ctrl+Cmd+A`: Generate command / AI 명령어 생성
- `Ctrl+Cmd+S`: Generate script / AI 스크립트 생성
- `Ctrl+Cmd+H`: Open history / 히스토리 열기
- `Ctrl+Cmd+M`: Change model / 모델 변경
- `Ctrl+Cmd+I`: Custom instructions / 사용자 지침 설정

### Available Models / 사용 가능한 모델

- `gemini-2.5-flash-lite` (default, fastest / 기본값, 가장 빠름)
- `gemini-2.5-flash`
- `gemini-2.5-pro` (best for complex scripts / 복잡한 스크립트에 적합)
- `gemini-2.0-flash`
- `gemini-2.0-flash-lite`

### Examples / 사용 예시

```
Input: "List all file sizes in current directory"
Result: ls -lh

Input: "Find files modified in the last 7 days"
Result: find . -mtime -7 -type f

Input: "Find process using port 3000"
Result: lsof -i :3000

Input: "Search for 'TODO' in README.md"
Result: grep -n "TODO" README.md

Input: "Find .js files excluding node_modules"
Result: find . -name "*.js" -not -path "*/node_modules/*"
```

### How It Works / 동작 방식

- **Normal commands**: Inserted directly into terminal (press Enter to execute)
- **Dangerous commands**: Warning dialog shown before insertion
- **History**: All generated commands are automatically saved

---

- **일반 명령어**: 확인 없이 터미널에 바로 삽입 (Enter는 직접 눌러야 함)
- **위험 명령어**: 경고 다이얼로그 표시 후 삽입 여부 선택
- **히스토리**: 모든 생성된 명령어는 자동으로 히스토리에 저장

## API Key Setup / API 키 설정

On first run, you will be prompted to enter your Gemini API key.

첫 실행 시 Gemini API 키 입력 프롬프트가 나타납니다.

Manual setup / 수동 설정:
```bash
python3 -c "import keyring; keyring.set_password('iterm2-ai-generator', 'gemini-api-key', 'YOUR_API_KEY')"
```

## Development / 개발

```bash
# Create virtual environment / 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# Install dev dependencies / 개발 의존성 설치
pip install -r requirements-dev.txt

# Run tests / 테스트 실행
pytest tests/
```

## Troubleshooting / 트러블슈팅

### Plugin not loading / 플러그인이 로드되지 않음

1. Check if script is visible in iTerm2 > Scripts menu
2. Verify Python Runtime is installed: iTerm2 > Scripts > Manage > Install Python Runtime
3. Check log file: `~/.config/iterm2-ai-generator/debug.log`

### API Key Error / API 키 오류

```bash
# Delete and reset API key / API 키 삭제 후 재설정
security delete-generic-password -s "iterm2-ai-generator" -a "gemini-api-key"
```

### Shortcuts not working / 단축키가 작동하지 않음

**1. Check script console for errors / 스크립트 콘솔에서 오류 확인**

```
iTerm2 > Scripts > Manage > Console
```

If no logs, the plugin is not loaded. / 로그가 없다면 플러그인이 로드되지 않은 것입니다.

**2. Manually run script to test / 수동으로 스크립트 실행하여 테스트**

```
iTerm2 > Scripts > AutoLaunch > ai_command_generator.py > __main__.py
```

Check Console for error messages after clicking.

**3. ModuleNotFoundError: No module named 'keyring'**

If module shows in `pip3 list` but import fails:

```bash
# Find Python path used by iTerm2
find ~/.config/iterm2/AppSupport/iterm2env -name "python3" -type f 2>/dev/null | head -1

# Install directly with that Python (example)
/Users/YOUR_USERNAME/.config/iterm2/AppSupport/iterm2env/versions/3.14.0/bin/python3 -m pip install keyring google-generativeai iterm2

# Verify installation
/Users/YOUR_USERNAME/.config/iterm2/AppSupport/iterm2env/versions/3.14.0/bin/python3 -c "import keyring; print('OK')"
```

**4. Other checks / 기타 확인 사항**

1. Check for keyboard shortcut conflicts in iTerm2 settings
2. Check if other apps use the same shortcuts
3. Fully restart iTerm2 (Cmd+Q then reopen)

### Rate Limit Error

Google Gemini API has rate limits on the free tier.
- Wait and try again later
- Or upgrade to a paid plan

### Reset History / 히스토리 초기화

```bash
rm ~/.config/iterm2-ai-generator/history.json
```

### Reset Config / 설정 초기화

```bash
rm ~/.config/iterm2-ai-generator/config.json
```

## File Locations / 파일 위치

- Config / 설정: `~/.config/iterm2-ai-generator/config.json`
- History / 히스토리: `~/.config/iterm2-ai-generator/history.json`
- Custom Instructions / 사용자 지침: `~/.config/iterm2-ai-generator/instructions.txt`
- Log / 로그: `~/.config/iterm2-ai-generator/debug.log`
- API Key: macOS Keychain (iterm2-ai-generator)

## License / 라이선스

MIT License
