# mcp-server config
```json
{
    "audit-agent": {
        "command": "/Users/ham-yunsig/.local/bin/uv", // which uv
        "args":[
          "--directory",
          "/Users/ham-yunsig/Documents/github/audit_agent", // this repo path
          "run",
          "main.py"
        ]
      }
}
```

# Setup
Set up your environment
First, let’s install uv and set up our Python project and environment:
```zsh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

가상환경 생성
```zsh
uv venv
source .venv/bin/activate
uv pip install .
```

의존성 설치
```zsh
uv venv
```

확인
```zsh
uv run main.py
```


# 사용 방법
```
git clone https://github.com/Uniswap/v4-core.git
cd v4-core
forge build
cursor .
```

>info: main.py의 부트스트랩을 실행하면 senarios 폴더의 시나리오들이 db에 저장되는데, 현재는 phase1, phase2와 무관하게 유닛테스트 검증을 하기 위해 llm이 자동 생성함.

### cursor query
> audit-agent tool 사용해서 유닛테스트 검증해줘 @PoolManager.t.sol 
> @src 코드 베이스 스키밍 후에 mcp 툴을 통해 fuse의 CEther 토큰 풀에 대한 fuse 재진입 가능성에 대해 poc 코드를 작성해줘
> 시나리오와 유사한 유닛테스트 등록/실행 후 검증 진행해줘
> ...