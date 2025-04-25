# src/scenarios.py
from typing import TypedDict, List, Optional

class ThreatScenario(TypedDict, total=False):
    """위협 시나리오 메타데이터 구조"""
    id: str           # 고유 식별자 (예: "S-1", "T-2.1")
    category: str     # 위협 카테고리 (예: "Spoofing", "Tampering", "Reentrancy")
    description: str  # 시나리오에 대한 간략한 설명
    precondition: str # 테스트 실행 전 필요한 상태나 조건 (자유 형식 설명)
    action: str       # 실행할 핵심 동작 (자유 형식 설명 또는 코드 조각 키)
    expected: str     # 예상되는 결과 (자유 형식 설명)
    template: str     # 사용할 Forge 테스트 템플릿 파일 이름

    # --- 범용 템플릿을 위한 상세 필드 (선택적) ---
    target_contract_name: Optional[str] # 테스트 대상 주 컨트랙트 이름 (예: PoolManager)
    target_contract_declaration: Optional[str] # 테스트 파일 내 대상 컨트랙트 변수 선언 (예: PoolManager internal targetContract;)
    target_contract_instance_name: Optional[str] # 테스트 파일 내 대상 컨트랙트 변수 이름 (예: targetContract)
    required_imports: Optional[List[str]] # 테스트 파일에 필요한 추가 import 구문 목록
    setup_code: Optional[str]           # setUp() 함수 내에 들어갈 일반 설정 코드 조각
    test_setup_code: Optional[str]      # 테스트 함수 내부에 들어갈 시나리오 특화 설정 코드 조각
    action_function: Optional[str]        # 실행할 핵심 함수의 이름
    action_code: Optional[str]            # 실행할 실제 Solidity 코드 조각 (action_function 대신 사용 가능)
    expected_revert_selector: Optional[str] # vm.expectRevert에 사용할 에러 셀렉터 문자열 (예: "Hooks.HookAddressNotValid.selector")
    assertion_code: Optional[str]         # revert가 아닐 경우 사용할 Solidity 검증 코드 조각

# 초기 시나리오 목록 (예시 값 포함)
SCENARIOS: List[ThreatScenario] = [
    {
        "id": "S-1.1",
        "category": "Spoofing",
        "description": "Invalid Hook Address Flags: 훅 주소의 권한 플래그 비트가 유효하지 않을 때 초기화 거부",
        "precondition": "PoolKey의 hooks 주소가 유효하지 않은 권한 비트를 가짐 (예: 0x...FF)",
        "action": "manager.initialize(key, initialSqrtPrice)",
        "expected": "vm.expectRevert(Hooks.HookAddressNotValid.selector)",
        "template": "forge_test_base.t.sol.j2",
        # --- 상세 필드 (예시) ---
        "target_contract_name": "PoolManager",
        "target_contract_declaration": "PoolManager internal targetContract;",
        "target_contract_instance_name": "targetContract",
        "required_imports": [
            'import { PoolManager } from "../src/PoolManager.sol";',
            'import { IPoolManager } from "../src/interfaces/IPoolManager.sol";',
            'import { PoolKey } from "../src/types/PoolKey.sol";',
            'import { Currency, CurrencyLibrary } from "../src/types/Currency.sol";',
            'import { IHooks } from "../src/interfaces/IHooks.sol";',
            'import { Hooks } from "../src/libraries/Hooks.sol";',
            'import { TestERC20 } from "../test/TestERC20.sol";'
        ],
        "setup_code": "token0 = new TestERC20(1e27);\ntoken1 = new TestERC20(1e27);\ntargetContract = new PoolManager(address(this));",
        "test_setup_code": """
        TestERC20 token0 = new TestERC20(1e27);
        TestERC20 token1 = new TestERC20(1e27);
        address invalidHookAddress = address(uint160(bytes20(keccak256(\"invalid_flags\"))));
        PoolKey memory key = PoolKey({
            currency0: Currency.wrap(address(token0)),
            currency1: Currency.wrap(address(token1)),
            fee: 3000,
            tickSpacing: 60,
            hooks: IHooks(invalidHookAddress)
        });
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        """,
        "action_function": "initialize",
        "action_code": "targetContract.initialize(key, initialSqrtPrice);",
        "expected_revert_selector": "Hooks.HookAddressNotValid.selector"
    },
    {
        "id": "S-1.2",
        "category": "Spoofing",
        "description": "Invalid Hook for Dynamic Fee: 동적 수수료 플래그가 설정되었으나 훅 주소가 0x0일 때 초기화 거부",
        "precondition": "PoolKey의 fee가 DYNAMIC_FEE_FLAG이고 hooks가 address(0)",
        "action": "manager.initialize(key, initialSqrtPrice)",
        "expected": "vm.expectRevert(Hooks.HookAddressNotValid.selector)",
        "template": "forge_test_base.t.sol.j2",
        # --- 상세 필드 (예시) ---
        "target_contract_name": "PoolManager",
        "target_contract_declaration": "PoolManager internal targetContract;",
        "target_contract_instance_name": "targetContract",
        "required_imports": [
            'import { PoolManager } from "../src/PoolManager.sol";',
            'import { IPoolManager } from "../src/interfaces/IPoolManager.sol";',
            'import { PoolKey } from "../src/types/PoolKey.sol";',
            'import { Currency, CurrencyLibrary } from "../src/types/Currency.sol";',
            'import { IHooks } from "../src/interfaces/IHooks.sol";',
            'import { Hooks } from "../src/libraries/Hooks.sol";',
            'import { LPFeeLibrary } from "../src/libraries/LPFeeLibrary.sol";',
            'import { TestERC20 } from "../test/TestERC20.sol";'
        ],
        "setup_code": "token0 = new TestERC20(1e27);\ntoken1 = new TestERC20(1e27);\ntargetContract = new PoolManager(address(this));",
        "test_setup_code": """
        TestERC20 token0 = new TestERC20(1e27);
        TestERC20 token1 = new TestERC20(1e27);
        PoolKey memory key = PoolKey({
            currency0: Currency.wrap(address(token0)),
            currency1: Currency.wrap(address(token1)),
            fee: LPFeeLibrary.DYNAMIC_FEE_FLAG,
            tickSpacing: 60,
            hooks: IHooks(address(0))
        });
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        """,
        "action_function": "initialize",
        "action_code": "targetContract.initialize(key, initialSqrtPrice);",
        "expected_revert_selector": "Hooks.HookAddressNotValid.selector"
    },
    {
        "id": "T-2.1",
        "category": "Tampering",
        "description": "Hook Return Manipulation (BeforeSwap Delta): beforeSwap 훅이 스왑 방향을 뒤집는 델타 반환 시 거부",
        "precondition": "beforeSwap 훅이 amountSpecified 절대값보다 큰 반대 부호의 deltaSpecified 반환 설정",
        "action": "manager.swap(key, params, hookData)",
        "expected": "vm.expectRevert(Hooks.HookDeltaExceedsSwapAmount.selector)",
        "template": "forge_test_base.t.sol.j2",
        "target_contract_name": "PoolManager",
        "expected_revert_selector": "Hooks.HookDeltaExceedsSwapAmount.selector",
        # ... setup_code, test_setup_code, action_code 등 구체화 필요 ...
        "required_imports": ["import { Hooks } from \"../src/libraries/Hooks.sol\";"], # 예시
        "action_code": "// Placeholder: targetContract.swap(...);"
    },
    {
        "id": "D-3.1",
        "category": "Denial of Service",
        "description": "Hook Revert DoS (BeforeSwap): beforeSwap 훅이 revert하여 swap 방해",
        "precondition": "PoolKey에 설정된 훅의 beforeSwap 함수가 항상 revert하도록 설정",
        "action": "manager.swap(key, params, hookData)",
        "expected": "vm.expectRevert(Hooks.HookCallFailed.selector)",
        "template": "forge_test_base.t.sol.j2",
        "target_contract_name": "PoolManager",
        "expected_revert_selector": "Hooks.HookCallFailed.selector",
        # ... setup_code, test_setup_code (RevertingHook 배포 등), action_code 등 구체화 필요 ...
         "required_imports": ["import { Hooks } from \"../src/libraries/Hooks.sol\";"], # 예시
        "action_code": "// Placeholder: targetContract.swap(...);"
    },
    {
        "id": "D-3.3",
        "category": "Denial of Service",
        "description": "Callback Non-Settlement DoS: unlockCallback에서 델타 발생 후 정산하지 않아 종료 시 revert",
        "precondition": "NonSettlingCallback 컨트랙트가 unlockCallback에서 swap 실행 후 settle/take 미호출",
        "action": "manager.unlock(abi.encode(nonSettlingCallback))",
        "expected": "vm.expectRevert(IPoolManager.CurrencyNotSettled.selector)",
        "template": "forge_test_base.t.sol.j2",
        "target_contract_name": "PoolManager",
        "expected_revert_selector": "IPoolManager.CurrencyNotSettled.selector",
        # ... setup_code (NonSettlingCallback 배포 등), test_setup_code, action_code (unlock 호출) 등 구체화 필요 ...
        "required_imports": ["import { IPoolManager } from \"../src/interfaces/IPoolManager.sol\";"], # 예시
        "action_code": "// Placeholder: targetContract.unlock(...);"
    },
    {
        "id": "R-6.1",
        "category": "Reentrancy",
        "description": "UnlockCallback Reentrancy Defense: unlockCallback 중 manager.swap 재호출 시도 시 ManagerLocked 에러로 방어",
        "precondition": "ReentrantCallback 컨트랙트가 unlockCallback 내에서 manager.swap 호출 시도",
        "action": "manager.unlock(abi.encode(reentrantCallback))",
        "expected": "vm.expectRevert(IPoolManager.ManagerLocked.selector)",
        "template": "forge_test_base.t.sol.j2",
        "target_contract_name": "PoolManager",
        "expected_revert_selector": "IPoolManager.ManagerLocked.selector",
        # ... setup_code (ReentrantCallback 배포 등), test_setup_code, action_code (unlock 호출) 등 구체화 필요 ...
         "required_imports": ["import { IPoolManager } from \"../src/interfaces/IPoolManager.sol\";"], # 예시
        "action_code": "// Placeholder: targetContract.unlock(...);"
    },
]

def get_scenarios() -> List[ThreatScenario]:
    """정의된 위협 시나리오 목록을 반환합니다."""
    return SCENARIOS