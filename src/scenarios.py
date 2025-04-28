# src/scenarios.py
from typing import TypedDict, List, Optional

# 'template' 필드 제거됨
class ThreatScenario(TypedDict, total=False):
    """위협 시나리오 메타데이터 구조"""
    id: str           # 고유 식별자 (예: "S-1", "T-2.1")
    category: str     # 위협 카테고리 (예: "Spoofing", "Tampering", "Reentrancy")
    description: str  # 시나리오에 대한 간략한 설명
    precondition: str # 테스트 실행 전 필요한 상태나 조건 (자유 형식 설명)
    action: str       # 실행할 핵심 동작 (자유 형식 설명 또는 코드 조각 키)
    expected: str     # 예상되는 결과 (자유 형식 설명)
    # template: str     # 사용할 Forge 테스트 템플릿 파일 이름 (제거됨)

    # --- 범용 템플릿을 위한 상세 필드 (선택적) ---
    target_contract_name: Optional[str] # 테스트 대상 주 컨트랙트 이름 (예:PoolManager)
    target_contract_declaration: Optional[str] # 테스트 파일 내 대상 컨트랙트 변수 선언 (예: PoolManager internal targetContract;)
    target_contract_instance_name: Optional[str] # 테스트 파일 내 대상 컨트랙트 변수 이름 (예: targetContract)
    required_imports: Optional[List[str]] # 테스트 파일에 필요한 추가 import 구문 목록
    setup_code: Optional[str]           # setUp() 함수 내에 들어갈 일반 설정 코드 조각
    test_setup_code: Optional[str]      # 테스트 함수 내부에 들어갈 시나리오 특화 설정 코드 조각
    action_function: Optional[str]        # 실행할 핵심 함수의 이름
    action_code: Optional[str]            # 실행할 실제 Solidity 코드 조각 (action_function 대신 사용 가능)
    expected_revert_selector: Optional[str] # vm.expectRevert에 사용할 에러 셀렉터 문자열 (예: "Hooks.HookAddressNotValid.selector")
    assertion_code: Optional[str]         # revert가 아닐 경우 사용할 Solidity 검증 코드 조각
    # --- 헬퍼 컨트랙트 관련 필드 (선택적) ---
    helper_contracts: Optional[List[dict]]  # 시나리오별로 필요한 헬퍼 컨트랙트 정보 리스트 (이름, 생성자 인자, 정의 코드 등)

# 초기 시나리오 목록 (예시 값 포함)
SCENARIOS: List[ThreatScenario] = [
    {
        "id": "S-1.1",
        "category": "Spoofing",
        "description": "Invalid Hook Address Flags: 훅 주소의 권한 플래그 비트가 유효하지 않을 때 초기화 거부",
        "precondition": "PoolKey의 hooks 주소가 유효하지 않은 권한 비트를 가짐 (예: 0x...FF)",
        "action": "manager.initialize(key, initialSqrtPrice)",
        "expected": "vm.expectRevert(Hooks.HookAddressNotValid.selector)",
        # "template": "forge_test_base.t.sol.j2", # 제거됨
        "target_contract_name": "PoolManager",
        "target_contract_declaration": "PoolManager internal _targetContract;",
        "target_contract_instance_name": "_targetContract",
        "required_imports": [
            'import { PoolManager } from "src/PoolManager.sol";',
            'import { IPoolManager } from "src/interfaces/IPoolManager.sol";',
            'import { PoolKey } from "src/types/PoolKey.sol";',
            'import { Currency, CurrencyLibrary } from "src/types/Currency.sol";',
            'import { IHooks } from "src/interfaces/IHooks.sol";',
            'import { Hooks } from "src/libraries/Hooks.sol";',
            'import { TestERC20 } from "src/test/TestERC20.sol";'
        ],
        "setup_code": """
        TestERC20 token0 = new TestERC20(1e27);
        TestERC20 token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));
        """,
        "test_setup_code": """
        TestERC20 token0 = new TestERC20(1e27);
        TestERC20 token1 = new TestERC20(1e27);
        // 실제로는 특정 권한 비트가 없는 주소를 사용해야 함
        // 예: 모든 플래그가 설정된 주소 (유효하지 않을 가능성 높음)
        address invalidHookAddress = address(uint160(Hooks.ALL_HOOK_MASK));
        // 또는 단순히 예측 불가능한 주소
        // address invalidHookAddress = address(uint160(bytes20(keccak256("invalid_hook"))));

        PoolKey memory key = PoolKey({
            currency0: Currency.wrap(address(token0)),
            currency1: Currency.wrap(address(token1)),
            fee: 3000,
            tickSpacing: 60,
            hooks: IHooks(invalidHookAddress)
        });
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        """,
        "action_code": "_targetContract.initialize(key, initialSqrtPrice);",
        "expected_revert_selector": "Hooks.HookAddressNotValid.selector"
    },
    {
        "id": "S-1.2",
        "category": "Spoofing",
        "description": "Invalid Hook for Dynamic Fee: 동적 수수료 플래그가 설정되었으나 훅 주소가 0x0일 때 초기화 거부",
        "precondition": "PoolKey의 fee가 DYNAMIC_FEE_FLAG이고 hooks가 address(0)",
        "action": "manager.initialize(key, initialSqrtPrice)",
        "expected": "vm.expectRevert(Hooks.HookAddressNotValid.selector)",
        # "template": "forge_test_base.t.sol.j2", # 제거됨
        "target_contract_name": "PoolManager",
        "target_contract_declaration": "PoolManager internal _targetContract;",
        "target_contract_instance_name": "_targetContract",
        "required_imports": [
            'import { PoolManager } from "src/PoolManager.sol";',
            'import { IPoolManager } from "src/interfaces/IPoolManager.sol";',
            'import { PoolKey } from "src/types/PoolKey.sol";',
            'import { Currency, CurrencyLibrary } from "src/types/Currency.sol";',
            'import { IHooks } from "src/interfaces/IHooks.sol";',
            'import { Hooks } from "src/libraries/Hooks.sol";',
            'import { LPFeeLibrary } from "src/libraries/LPFeeLibrary.sol";',
            'import { TestERC20 } from "src/test/TestERC20.sol";'
        ],
        "setup_code": """
        TestERC20 token0 = new TestERC20(1e27);
        TestERC20 token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));
        """,
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
        "action_code": "_targetContract.initialize(key, initialSqrtPrice);",
        "expected_revert_selector": "Hooks.HookAddressNotValid.selector"
    },
    {
        "id": "T-2.1",
        "category": "Tampering",
        "description": "Hook Return Manipulation (BeforeSwap Delta): beforeSwap 훅이 스왑 방향을 뒤집는 델타 반환 시 거부",
        "precondition": "beforeSwap 훅이 amountSpecified 절대값보다 큰 반대 부호의 deltaSpecified 반환 설정",
        "action": "targetContract.swap(key, params, hookData); // Via Unlock",
        "expected": "vm.expectRevert(Hooks.HookDeltaExceedsSwapAmount.selector)",
        # "template": "forge_test_base.t.sol.j2", # 제거됨
        "target_contract_name": "PoolManager",
        "target_contract_declaration": """
        PoolManager internal _targetContract;
        TestERC20 internal token0;
        TestERC20 internal token1;
        DeltaReturningHook internal deltaHook;
        PoolModifyLiquidityTest internal liquidityProvider;
        PoolKey internal key; // setup과 test_setup에서 공유되므로 상태 변수로 이동
        """,
        "target_contract_instance_name": "_targetContract",
        "required_imports": [
            'import { PoolManager } from "src/PoolManager.sol";',
            'import { IPoolManager } from "src/interfaces/IPoolManager.sol";',
            'import { PoolKey } from "src/types/PoolKey.sol";',
            'import { Currency, CurrencyLibrary } from "src/types/Currency.sol";',
            'import { IHooks } from "src/interfaces/IHooks.sol";',
            'import { Hooks } from "src/libraries/Hooks.sol";',
            'import { TestERC20 } from "src/test/TestERC20.sol";',
            'import { DeltaReturningHook } from "src/test/DeltaReturningHook.sol";',
            'import { PoolModifyLiquidityTest } from "src/test/PoolModifyLiquidityTest.sol";',
            'import { IUnlockCallback } from "src/interfaces/callback/IUnlockCallback.sol";',
            'import { BalanceDelta } from "src/types/BalanceDelta.sol";'
        ],
        "setup_code": """
        token0 = new TestERC20(1e27);
        token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));
        deltaHook = new DeltaReturningHook(IPoolManager(address(_targetContract)));

        key = PoolKey({
            currency0: Currency.wrap(address(token0)),
            currency1: Currency.wrap(address(token1)),
            fee: 3000,
            tickSpacing: 60,
            hooks: IHooks(address(deltaHook))
        });
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        _targetContract.initialize(key, initialSqrtPrice);

        liquidityProvider = new PoolModifyLiquidityTest(IPoolManager(address(_targetContract)));
        token0.approve(address(liquidityProvider), type(uint256).max);
        token1.approve(address(liquidityProvider), type(uint256).max);
        vm.startPrank(address(liquidityProvider));
        IPoolManager.ModifyLiquidityParams memory lpParams = IPoolManager.ModifyLiquidityParams({
            tickLower: -600, tickUpper: 600, liquidityDelta: 1e18, salt: bytes32(0)
        });
        liquidityProvider.modifyLiquidity(key, lpParams, "");
        vm.stopPrank();
        """,
        # SwapExecutor 정의는 여기서 제거됨. 인스턴스 생성만 남김.
        "test_setup_code": """
        int128 amountSpecified = -1e17;
        int128 maliciousDelta = 1e17 + 100; // 양수 delta 반환 (zeroForOne=true 스왑과 반대)
        deltaHook.setDeltaSpecified(maliciousDelta);

        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({
            zeroForOne: true,
            amountSpecified: amountSpecified,
            sqrtPriceLimitX96: 4295128739 // Lower limit for zeroForOne swap
        });
        bytes memory hookData = abi.encode(address(this)); // Pass caller address as hookData

        // SwapExecutor 인스턴스 생성 (token0, token1은 상태 변수 사용)
        SwapExecutor callback = new SwapExecutor(IPoolManager(address(_targetContract)), address(token0), address(token1));
        callback.setSwapParams(key, params, hookData);

        // 토큰 전송 및 승인
        uint256 amountToSend = uint256(-amountSpecified); // amountSpecified is negative
        token0.approve(address(callback), amountToSend);
        // vm.deal(address(callback), 1 ether); // Ether deal might not be necessary if callback pays with tokens
        token0.transfer(address(callback), amountToSend);
        """,
        "action_code": """
        // Use the callback instance created in test_setup_code
        bytes memory unlockData = abi.encodeWithSelector(SwapExecutor.unlockCallback.selector, bytes("")); // Pass empty bytes if unlockCallback doesn't expect specific data
        vm.prank(address(callback));
        _targetContract.unlock(unlockData);
        """,
        "expected_revert_selector": "Hooks.HookDeltaExceedsSwapAmount.selector"
    },
    {
        "id": "D-3.1",
        "category": "Denial of Service",
        "description": "Hook Revert DoS (BeforeSwap): beforeSwap 훅이 revert하여 swap 방해",
        "precondition": "PoolKey에 설정된 훅의 beforeSwap 함수가 항상 revert하도록 설정",
        "action": "targetContract.swap(key, params, hookData); // Via Unlock",
        "expected": "vm.expectRevert(Hooks.HookCallFailed.selector)",
        # "template": "forge_test_base.t.sol.j2", # 제거됨
        "target_contract_name": "PoolManager",
        "target_contract_declaration": """
        PoolManager internal _targetContract;
        TestERC20 internal token0;
        TestERC20 internal token1;
        RevertingHook internal revertingHook; // setup에서 정의
        PoolModifyLiquidityTest internal liquidityProvider;
        PoolKey internal key; // 상태 변수로 이동
        """,
        "target_contract_instance_name": "_targetContract",
        "required_imports": [
            'import { PoolManager } from "src/PoolManager.sol";',
            'import { IPoolManager } from "src/interfaces/IPoolManager.sol";',
            'import { PoolKey } from "src/types/PoolKey.sol";',
            'import { Currency, CurrencyLibrary } from "src/types/Currency.sol";',
            'import { IHooks } from "src/interfaces/IHooks.sol";',
            'import { Hooks } from "src/libraries/Hooks.sol";',
            'import { TestERC20 } from "src/test/TestERC20.sol";',
            # 'import { RevertingHook } from "./utils/RevertingHook.sol";', # LLM이 생성할 것이므로 import 불필요
            'import { PoolModifyLiquidityTest } from "src/test/PoolModifyLiquidityTest.sol";',
            'import { IUnlockCallback } from "src/interfaces/callback/IUnlockCallback.sol";',
            'import { BalanceDelta } from "src/types/BalanceDelta.sol";'
        ],
        "setup_code": """
        token0 = new TestERC20(1e27);
        token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));
        // RevertingHook 인스턴스 생성 (정의는 테스트 파일 내 LLM이 생성)
        revertingHook = new RevertingHook(IHooks.beforeSwap.selector);
        """,
        # SwapExecutor 정의 제거됨
        "test_setup_code": """
        // key 정의 시 revertingHook 사용
        key = PoolKey({
            currency0: Currency.wrap(address(token0)),
            currency1: Currency.wrap(address(token1)),
            fee: 3000,
            tickSpacing: 60,
            hooks: IHooks(address(revertingHook)) // revertingHook 주소 사용
        });
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        _targetContract.initialize(key, initialSqrtPrice);

        // liquidityProvider 설정 및 유동성 공급 (key 사용)
        liquidityProvider = new PoolModifyLiquidityTest(IPoolManager(address(_targetContract)));
        token0.approve(address(liquidityProvider), 1e18);
        token1.approve(address(liquidityProvider), 1e18);
        vm.startPrank(address(liquidityProvider));
        IPoolManager.ModifyLiquidityParams memory lpParams = IPoolManager.ModifyLiquidityParams({tickLower: -60, tickUpper: 60, liquidityDelta: 1e18, salt: bytes32(0)});
        liquidityProvider.modifyLiquidity(key, lpParams, "");
        vm.stopPrank();

        IPoolManager.SwapParams memory params = IPoolManager.SwapParams({ zeroForOne: true, amountSpecified: -1e17, sqrtPriceLimitX96: 4295128739 });
        bytes memory hookData = ""; // No specific hook data needed for RevertingHook scenario

        // SwapExecutor 인스턴스 생성
        SwapExecutor callback = new SwapExecutor(IPoolManager(address(_targetContract)), address(token0), address(token1));
        callback.setSwapParams(key, params, hookData);

        // 토큰 전송 및 승인
        uint256 amountToSend = 1e17;
        token0.approve(address(callback), amountToSend);
        // vm.deal(address(callback), 1 ether);
        token0.transfer(address(callback), amountToSend);
        """,
        "action_code": """
        // Use the callback instance created in test_setup_code
        bytes memory unlockData = abi.encodeWithSelector(SwapExecutor.unlockCallback.selector, bytes(""));
        vm.prank(address(callback));
        _targetContract.unlock(unlockData);
        """,
        "expected_revert_selector": "Hooks.HookCallFailed.selector",
        "helper_contracts": [
            {
                "name": "RevertingHook",
                "instance_name": "revertingHook",
                "constructor_args": ["IHooks.beforeSwap.selector"],
                "definition_code": "// beforeSwap이 무조건 revert하는 훅 컨트랙트 정의"
            }
        ]
    },
    {
        "id": "D-3.3",
        "category": "Denial of Service",
        "description": "Callback Non-Settlement DoS: unlockCallback에서 델타 발생 후 정산하지 않아 종료 시 revert",
        "precondition": "NonSettlingCallback 컨트랙트가 unlockCallback에서 swap 실행 후 settle/take 미호출",
        "action": "manager.unlock(abi.encode(nonSettlingCallback))",
        "expected": "vm.expectRevert(IPoolManager.CurrencyNotSettled.selector)",
        # "template": "forge_test_base.t.sol.j2", # 제거됨
        "target_contract_name": "PoolManager",
        "target_contract_declaration": """
        PoolManager internal _targetContract;
        TestERC20 internal token0;
        TestERC20 internal token1;
        PoolModifyLiquidityTest internal liquidityProvider;
        PoolKey internal key; // 상태 변수로 이동
        """,
        "target_contract_instance_name": "_targetContract",
        "required_imports": [
            'import { PoolManager } from "src/PoolManager.sol";',
            'import { IPoolManager } from "src/interfaces/IPoolManager.sol";',
            'import { PoolKey } from "src/types/PoolKey.sol";',
            'import { Currency, CurrencyLibrary } from "src/types/Currency.sol";',
            'import { IHooks } from "src/interfaces/IHooks.sol";', # NonSettlingCallback 에서 PoolKey 사용 시 필요 가정
            'import { TestERC20 } from "src/test/TestERC20.sol";',
            'import { PoolModifyLiquidityTest } from "src/test/PoolModifyLiquidityTest.sol";',
            'import { IUnlockCallback } from "src/interfaces/callback/IUnlockCallback.sol";',
            'import { console } from "forge-std/console.sol";' # NonSettlingCallback 에서 사용
        ],
        "setup_code": """
        token0 = new TestERC20(1e27);
        token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));
        key = PoolKey({ currency0: Currency.wrap(address(token0)), currency1: Currency.wrap(address(token1)), fee: 3000, tickSpacing: 60, hooks: IHooks(address(0))});
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        _targetContract.initialize(key, initialSqrtPrice);
        liquidityProvider = new PoolModifyLiquidityTest(IPoolManager(address(_targetContract)));
        token0.approve(address(liquidityProvider), type(uint256).max);
        token1.approve(address(liquidityProvider), type(uint256).max);
        vm.startPrank(address(liquidityProvider));
        IPoolManager.ModifyLiquidityParams memory lpParams = IPoolManager.ModifyLiquidityParams({ tickLower: -600, tickUpper: 600, liquidityDelta: 1e18, salt: bytes32(0) });
        liquidityProvider.modifyLiquidity(key, lpParams, "");
        vm.stopPrank();
        """,
        # NonSettlingCallback 정의는 여기서 제거됨. 인스턴스 생성만 남김.
        "test_setup_code": """
        // NonSettlingCallback 인스턴스 생성 (정의는 LLM이 생성)
        NonSettlingCallback callback = new NonSettlingCallback(IPoolManager(address(_targetContract)), address(token0));
        callback.setKey(key); // key는 상태 변수

        // 스왑에 필요한 토큰 준비 및 전송
        uint256 amountToSend = 1e17;
        token0.approve(address(callback), amountToSend);
        token0.transfer(address(callback), amountToSend);
        // vm.deal(address(callback), 1 ether); // Ether 필요 여부 확인
        """,
        "action_code": """
        // Use the callback instance created in test_setup_code
        // Pass callback address directly as data for unlock, assuming Manager uses abi.decode
        // Alternatively, encode the callback address if needed by unlock's internal logic
        // bytes memory callbackData = abi.encode(address(callback));
        vm.prank(address(callback));
        // targetContract.unlock(callbackData);
        // Let's assume unlock takes raw calldata intended for the callback
        // Need to know how unlock is supposed to call the callback
        // Based on Reentrant test, it seems unlock expects data that *it* decodes to find the target
        // However, D-3.3 description says "manager.unlock(abi.encode(nonSettlingCallback))"
        // Let's try encoding just the address as data, as it's the most likely interpretation
        bytes memory callbackData = abi.encode(address(callback));
        _targetContract.unlock(callbackData);
        """,
        "expected_revert_selector": "IPoolManager.CurrencyNotSettled.selector",
        "helper_contracts": [
            {
                "name": "NonSettlingCallback",
                "instance_name": "callback",
                "constructor_args": ["IPoolManager(address(_targetContract))", "address(token0)"],
                "definition_code": "// unlockCallback에서 swap만 실행하고 정산하지 않는 콜백 컨트랙트 정의"
            }
        ]
    },
    {
        "id": "R-6.1",
        "category": "Reentrancy",
        "description": "UnlockCallback Reentrancy Defense: unlockCallback 중 manager.swap 재호출 시도 시 ManagerLocked 에러로 방어",
        "precondition": "ReentrantCallback 컨트랙트가 unlockCallback 내에서 manager.swap 호출 시도",
        "action": "manager.unlock(abi.encode(reentrantCallback))",
        "expected": "vm.expectRevert(IPoolManager.ManagerLocked.selector)",
        # "template": "forge_test_base.t.sol.j2", # 제거됨
        "target_contract_name": "PoolManager",
        "target_contract_declaration": """
        PoolManager internal _targetContract;
        TestERC20 internal token0;
        TestERC20 internal token1;
        PoolModifyLiquidityTest internal liquidityProvider;
        PoolKey internal key; // 상태 변수로 이동
        """,
        "target_contract_instance_name": "_targetContract",
        "required_imports": [
            'import { PoolManager } from "src/PoolManager.sol";',
            'import { IPoolManager } from "src/interfaces/IPoolManager.sol";',
            'import { PoolKey } from "src/types/PoolKey.sol";',
            'import { Currency, CurrencyLibrary } from "src/types/Currency.sol";',
            'import { IHooks } from "src/interfaces/IHooks.sol";', # PoolKey에서 사용
            'import { TestERC20 } from "src/test/TestERC20.sol";',
            'import { PoolModifyLiquidityTest } from "src/test/PoolModifyLiquidityTest.sol";', # 실제 경로 가정
            'import { IUnlockCallback } from "src/interfaces/callback/IUnlockCallback.sol";',
            'import { console } from "forge-std/console.sol";' # ReentrantCallback에서 사용
        ],
        "setup_code": """
        token0 = new TestERC20(1e27);
        token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));
        key = PoolKey({ currency0: Currency.wrap(address(token0)), currency1: Currency.wrap(address(token1)), fee: 3000, tickSpacing: 60, hooks: IHooks(address(0))});
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        _targetContract.initialize(key, initialSqrtPrice);
        liquidityProvider = new PoolModifyLiquidityTest(IPoolManager(address(_targetContract)));
        token0.approve(address(liquidityProvider), type(uint256).max);
        token1.approve(address(liquidityProvider), type(uint256).max);
        vm.startPrank(address(liquidityProvider));
        IPoolManager.ModifyLiquidityParams memory lpParams = IPoolManager.ModifyLiquidityParams({ tickLower: -600, tickUpper: 600, liquidityDelta: 1e18, salt: bytes32(0) });
        liquidityProvider.modifyLiquidity(key, lpParams, "");
        vm.stopPrank();
        """,
        # ReentrantCallback 정의는 여기서 제거됨. 인스턴스 생성만 남김.
        "test_setup_code": """
        // ReentrantCallback 인스턴스 생성 (정의는 LLM이 생성)
        ReentrantCallback callback = new ReentrantCallback(IPoolManager(address(_targetContract)));
        callback.setKey(key); // key는 상태 변수
         """,
        "action_code": """
        // Use the callback instance created in test_setup_code
        // Encode the callback address as data for unlock
        bytes memory callbackData = abi.encode(address(callback));
        vm.prank(address(callback));
        _targetContract.unlock(callbackData);
        """,
        "expected_revert_selector": "IPoolManager.ManagerLocked.selector",
        "helper_contracts": [
            {
                "name": "ReentrantCallback",
                "instance_name": "callback",
                "constructor_args": ["IPoolManager(address(_targetContract))"],
                "definition_code": "// unlockCallback에서 manager.swap을 재진입 호출하는 콜백 컨트랙트 정의"
            }
        ]
    },
]

# Helper contract for swap execution inside unlock (needed for some scenarios)
# 이 코드는 이제 test_generator.py에서 직접 사용되지 않지만,
# LLM(나)이 SwapExecutor 컨트랙트 코드를 생성할 때 참고용으로 사용될 수 있음.
SWAP_EXECUTOR_CONTRACT = """
contract SwapExecutor is IUnlockCallback {
    IPoolManager public immutable manager;
    PoolKey public key;
    IPoolManager.SwapParams public params;
    bytes public hookData;
    TestERC20 public token0;
    TestERC20 public token1;

    constructor(IPoolManager _manager, address t0, address t1) {
         manager = _manager;
         token0 = TestERC20(t0);
         token1 = TestERC20(t1);
    }
    function setSwapParams(PoolKey memory _key, IPoolManager.SwapParams memory _params, bytes memory _hookData) external {
        key = _key; params = _params; hookData = _hookData;
    }
    function unlockCallback(bytes calldata /* data */) external override returns (bytes memory) {
        // Note: The original SWAP_EXECUTOR_CONTRACT used `manager.settle()` and `manager.take()`
        // which are not standard IPoolManager functions based on V4 code.
        // The typical pattern after a swap via unlock is for the *caller* (SwapExecutor)
        // to handle token transfers based on the returned BalanceDelta.
        // Let's adjust the logic assuming standard ERC20 transfers are needed.

        BalanceDelta swapDelta = manager.swap(key, params, hookData);

        // Based on the swapDelta, transfer tokens *to* the PoolManager if we owe,
        // or expect tokens *from* the PoolManager if they owe us (which unlock should handle).
        // The exact settlement logic depends heavily on how PoolManager interacts
        // with callbacks and token transfers in V4, which might differ from V3.
        // Assuming a simple transfer logic for now:

        int128 delta0 = swapDelta.amount0();
        int128 delta1 = swapDelta.amount1();

        if (delta0 < 0) {
            // We owe token0 to the pool
            token0.transfer(address(manager), uint256(-delta0));
        } else if (delta0 > 0) {
            // Pool owes token0 to us. Unlock should ensure this is transferred.
            // Or we might need to call a 'withdraw' or similar function if available.
            // For now, assume unlock handles withdrawal implicitly or via caller balance checks.
            // We could add a check here: require(token0.balanceOf(address(this)) >= uint256(delta0), "Token0 not received");
        }

        if (delta1 < 0) {
            // We owe token1 to the pool
            token1.transfer(address(manager), uint256(-delta1));
        } else if (delta1 > 0) {
            // Pool owes token1 to us.
            // require(token1.balanceOf(address(this)) >= uint256(delta1), "Token1 not received");
        }

        // V4 PoolManager doesn't seem to have settle() or take().
        // Settlement is typically handled by the caller transferring required input tokens
        // and receiving output tokens as a result of the swap call within unlock.

        return abi.encode(swapDelta); // Return the swap delta
    }
}
"""

def get_scenarios() -> List[ThreatScenario]:
    """정의된 위협 시나리오 목록을 반환합니다."""
    return SCENARIOS

def get_swap_executor_code() -> str:
     """SwapExecutor 컨트랙트 코드를 반환합니다."""
     return SWAP_EXECUTOR_CONTRACT
