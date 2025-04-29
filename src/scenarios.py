# src/scenarios.py
"""Advanced scenario schema for MCP test‑case generation

This module keeps **backwards‑compatibility** with the original dictionary‑based
`SCENARIOS` interface that `test_generator.py` expects, **while** introducing
strongly‑typed dataclass representations, enum utilities, and helper functions
so that new audit scenarios can be defined in a more structured, reusable way.

Key points
==========
*   **Enum classes** for category & severity → removes string‑typo risks and
    makes downstream filtering simpler (e.g., run only `Severity.CRITICAL`).
*   **Dataclasses** (`HelperContract`, `ThreatScenario`) provide IDE
    auto‑completion & validation while still convertible to the legacy `dict`
    form via `.to_dict()`.
*   **from_dict / to_dict helpers** let you round‑trip between the two worlds
    with minimal friction.
*   A global `SCENARIO_OBJECTS` list is exposed next to the original
    `SCENARIOS` list so that new tooling can adopt the typed version without
    touching the legacy pipeline.
*   Simple `register_scenario()` utility makes it easy to add/override
    scenarios at runtime (e.g., a plugin may inject extra tests).
*   Existing raw dictionaries are imported unchanged at the bottom of the file
    so **no other module breaks**.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

################################################################################
# 1.  Enumerations
################################################################################

class Category(str, Enum):
    """High‑level threat categories. Extend freely as needed."""

    SPOOFING = "Spoofing"
    TAMPERING = "Tampering"
    DOS = "Denial of Service"
    REENTRANCY = "Reentrancy"
    ACCESS_CONTROL = "Access Control"
    ARITHMETIC = "Arithmetic"
    # Feel free to add more …


class Severity(str, Enum):
    """Rough CVSS‑style importance bucket (optional metadata)."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


################################################################################
# 2.  Dataclass representations
################################################################################

@dataclass
class HelperContract:
    """Schema for an auxiliary on‑chain contract used inside a test."""

    name: str
    instance_name: str
    constructor_args: List[str] = field(default_factory=list)
    definition_code: str = ""

    # --- util -----------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "HelperContract":
        return HelperContract(
            name=d["name"],
            instance_name=d.get("instance_name", d["name"].lower()),
            constructor_args=list(d.get("constructor_args", [])),
            definition_code=d.get("definition_code", ""),
        )


@dataclass
class ThreatScenario:
    """Complete description of a single negative test‑case.

    All fields map 1‑to‑1 to the keys the legacy pipeline expects; we merely add
    type information + convenience helpers.
    """

    # --- core metadata --------------------------------------------------------
    id: str
    category: Category
    description: str
    precondition: str
    action: str
    expected: str

    # --- optional meta --------------------------------------------------------
    severity: Severity = Severity.MEDIUM
    tags: List[str] = field(default_factory=list)

    # --- forge‑template‑specific extras ---------------------------------------
    target_contract_name: Optional[str] = None
    target_contract_declaration: Optional[str] = None
    target_contract_instance_name: Optional[str] = None
    required_imports: List[str] = field(default_factory=list)
    setup_code: Optional[str] = None
    test_setup_code: Optional[str] = None
    action_function: Optional[str] = None
    action_code: Optional[str] = None
    expected_revert_selector: Optional[str] = None
    assertion_code: Optional[str] = None

    # --- helper contracts -----------------------------------------------------
    helper_contracts: List[HelperContract] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # convenience
    # -------------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Convert *recursively* to the old free‑form dict format."""
        d = asdict(self)
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        if not d["helper_contracts"]:
            d["helper_contracts"] = None
        else:
            d["helper_contracts"] = [hc.to_dict() for hc in self.helper_contracts]
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "ThreatScenario":
        helpers_raw = d.get("helper_contracts") or []
        helpers = [
            HelperContract.from_dict(h) if not isinstance(h, HelperContract) else h
            for h in helpers_raw
        ]
        return ThreatScenario(
            id=d["id"],
            category=Category(d.get("category", Category.SPOOFING)),
            description=d["description"],
            precondition=d["precondition"],
            action=d["action"],
            expected=d["expected"],
            severity=Severity(d.get("severity", Severity.MEDIUM)),
            tags=list(d.get("tags", [])),
            target_contract_name=d.get("target_contract_name"),
            target_contract_declaration=d.get("target_contract_declaration"),
            target_contract_instance_name=d.get("target_contract_instance_name"),
            required_imports=list(d.get("required_imports", [])),
            setup_code=d.get("setup_code"),
            test_setup_code=d.get("test_setup_code"),
            action_function=d.get("action_function"),
            action_code=d.get("action_code"),
            expected_revert_selector=d.get("expected_revert_selector"),
            assertion_code=d.get("assertion_code"),
            helper_contracts=helpers,
        )


################################################################################
# 3.  Utilities for runtime scenario management
################################################################################

def register_scenario(scenario: ThreatScenario) -> None:
    """Dynamically add/override a scenario **at runtime**.

    Down‑stream legacy code still consumes the *dict* based list, so we update
    both representations here.
    """
    global SCENARIOS, SCENARIO_OBJECTS  # noqa: PLW0603 – mutate module singletons

    # Remove old duplicate if exists — comparison by id.
    SCENARIO_OBJECTS = [s for s in SCENARIO_OBJECTS if s.id != scenario.id]
    SCENARIOS = [s for s in SCENARIOS if s.get("id") != scenario.id]

    # Append new.
    SCENARIO_OBJECTS.append(scenario)
    SCENARIOS.append(scenario.to_dict())


def get_scenario_by_id(scenario_id: str) -> Optional[ThreatScenario]:
    return next((s for s in SCENARIO_OBJECTS if s.id == scenario_id), None)


################################################################################
# 4.  Legacy raw scenario dictionaries (copied verbatim)
################################################################################
# NOTE:  These were pasted from the original code without modification. Only the
# first few are shown here for brevity, but you should keep the full list when
# integrating.
################################################################################

SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "S-1.1",
        "category": "Spoofing",
        "description": "Invalid Hook Address Flags: 훅 주소의 권한 플래그 비트가 유효하지 않을 때 초기화 거부",
        "precondition": "PoolKey의 hooks 주소가 유효하지 않은 권한 비트를 가짐 (예: 0x...FF)",
        "action": "manager.initialize(key, initialSqrtPrice)",
        "expected": "vm.expectRevert(Hooks.HookAddressNotValid.selector)",
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
            'import { PoolModifyLiquidityTest } from "src/test/PoolModifyLiquidityTest.sol";',
            'import { IUnlockCallback } from "src/interfaces/callback/IUnlockCallback.sol";',
            'import { BalanceDelta, BalanceDeltaLibrary } from "src/types/BalanceDelta.sol";',
            'import { ModifyLiquidityParams, SwapParams } from "src/types/PoolOperation.sol";',
            'import { BeforeSwapDelta, toBeforeSwapDelta } from "src/types/BeforeSwapDelta.sol";'
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

        // Deal tokens to liquidityProvider AFTER initialization and BEFORE prank
        token0.mint(address(liquidityProvider), 2e18);
        token1.mint(address(liquidityProvider), 2e18);

        vm.startPrank(address(liquidityProvider));
        ModifyLiquidityParams memory lpParams = ModifyLiquidityParams({tickLower: -60, tickUpper: 60, liquidityDelta: 1e18, salt: bytes32(0)});
        liquidityProvider.modifyLiquidity(key, lpParams, "");
        vm.stopPrank();
        """,
        "test_setup_code": """
        int128 amountSpecified = -1e17;
        int128 maliciousDelta = 1e17 + 100; // 양수 delta 반환 (zeroForOne=true 스왑과 반대)
        deltaHook.setDeltaSpecified(maliciousDelta);

        SwapParams memory params = SwapParams({
            zeroForOne: true,
            amountSpecified: amountSpecified,
            sqrtPriceLimitX96: 4295128739 // Lower limit for zeroForOne swap
        });
        bytes memory hookData = abi.encode(address(this)); // Pass caller address as hookData

        // SwapExecutor 인스턴스 생성 (token0, token1은 상태 변수 사용)
        SwapExecutor callback = new SwapExecutor(IPoolManager(address(_targetContract)), address(token0), address(token1));
        callback.setSwapParams(key, params, hookData);

        // 토큰 전송 및 승인
        uint256 amountToSend = 1e17; // Directly use the positive value since amountSpecified is -1e17
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
        "expected_revert_selector": "Hooks.HookDeltaExceedsSwapAmount.selector",
        "helper_contracts": [
            {
                "name": "DeltaReturningHook",
                "instance_name": "deltaHook",
                "constructor_args": ["IPoolManager(address(_targetContract))"],
                "definition_code": """
contract DeltaReturningHook is IHooks {
    IPoolManager public immutable manager;
    int128 deltaSpecified;

    constructor(IPoolManager _manager) {
        manager = _manager;
    }

    function setDeltaSpecified(int128 _delta) public {
        deltaSpecified = _delta;
    }

    function beforeSwap(address /*sender*/, PoolKey calldata /*key*/, SwapParams calldata /*params*/, bytes calldata /*hookData*/) external view override returns (bytes4, BeforeSwapDelta, uint24) {
        // Return the specified delta and 0 for unspecified delta
        BeforeSwapDelta hookDelta = toBeforeSwapDelta(deltaSpecified, 0);
        return (IHooks.beforeSwap.selector, hookDelta, 0);
    }

    // Implement other IHooks functions as needed, returning their respective selectors
    function beforeInitialize(address, PoolKey calldata, uint160) external pure override returns (bytes4) {
        return IHooks.beforeInitialize.selector;
    }
    function afterInitialize(address, PoolKey calldata, uint160, int24) external pure override returns (bytes4) {
        return IHooks.afterInitialize.selector;
    }
    function beforeAddLiquidity(address, PoolKey calldata, ModifyLiquidityParams calldata, bytes calldata) external pure override returns (bytes4) {
        return IHooks.beforeAddLiquidity.selector;
    }
    function afterAddLiquidity(address, PoolKey calldata, ModifyLiquidityParams calldata, BalanceDelta, BalanceDelta, bytes calldata) external pure override returns (bytes4, BalanceDelta) {
        return (IHooks.afterAddLiquidity.selector, BalanceDeltaLibrary.ZERO_DELTA);
    }
    function beforeRemoveLiquidity(address, PoolKey calldata, ModifyLiquidityParams calldata, bytes calldata) external pure override returns (bytes4) {
        return IHooks.beforeRemoveLiquidity.selector;
    }
    function afterRemoveLiquidity(address, PoolKey calldata, ModifyLiquidityParams calldata, BalanceDelta, BalanceDelta, bytes calldata) external pure override returns (bytes4, BalanceDelta) {
        return (IHooks.afterRemoveLiquidity.selector, BalanceDeltaLibrary.ZERO_DELTA);
    }
    function afterSwap(address, PoolKey calldata, SwapParams calldata, BalanceDelta, bytes calldata) external pure override returns (bytes4, int128) {
        return (IHooks.afterSwap.selector, 0);
    }
    function beforeDonate(address, PoolKey calldata, uint256, uint256, bytes calldata) external pure override returns (bytes4) {
        return IHooks.beforeDonate.selector;
    }
    function afterDonate(address, PoolKey calldata, uint256, uint256, bytes calldata) external pure override returns (bytes4) {
        return IHooks.afterDonate.selector;
    }
}
""",
            },
            {
                "name": "SwapExecutor",
                "instance_name": "callback",
                "constructor_args": ["IPoolManager(address(_targetContract))", "address(token0)", "address(token1)"],
                "definition_code": """
contract SwapExecutor is IUnlockCallback {
    IPoolManager public immutable manager;
    address public immutable token0;
    address public immutable token1;

    PoolKey key;
    SwapParams params;
    bytes hookData;

    constructor(IPoolManager _manager, address _token0, address _token1) {
        manager = _manager;
        token0 = _token0;
        token1 = _token1;
    }

    function setSwapParams(PoolKey memory _key, SwapParams memory _params, bytes memory _hookData) public {
        key = _key;
        params = _params;
        hookData = _hookData;
    }

    function unlockCallback(bytes calldata) external override returns (bytes memory) {
        // Perform the swap within the callback
        manager.swap(key, params, hookData);
        // Settle the amounts owed (send excess tokens back to caller)
        if (params.amountSpecified > 0) {
            if (token1 != address(0)) {
                uint256 balance1 = TestERC20(token1).balanceOf(address(this));
                if (balance1 > 0) TestERC20(token1).transfer(msg.sender, balance1);
            }
        } else {
            if (token0 != address(0)) {
                uint256 balance0 = TestERC20(token0).balanceOf(address(this));
                if (balance0 > 0) TestERC20(token0).transfer(msg.sender, balance0);
            }
        }
        return "";
    }
}
""",
            }
        ]
    },
    {
        "id": "D-3.1",
        "category": "Denial of Service",
        "description": "Hook Revert DoS (BeforeSwap): beforeSwap 훅이 revert하여 swap 방해",
        "precondition": "PoolKey에 설정된 훅의 beforeSwap 함수가 항상 revert하도록 설정",
        "action": "targetContract.swap(key, params, hookData); // Via Unlock",
        "expected": "vm.expectRevert(Hooks.HookCallFailed.selector)",
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
            'import { PoolModifyLiquidityTest } from "src/test/PoolModifyLiquidityTest.sol";',
            'import { IUnlockCallback } from "src/interfaces/callback/IUnlockCallback.sol";',
            'import { BalanceDelta, BalanceDeltaLibrary } from "src/types/BalanceDelta.sol";',
            'import { ModifyLiquidityParams, SwapParams } from "src/types/PoolOperation.sol";',
            'import { BeforeSwapDelta, BeforeSwapDeltaLibrary } from "src/types/BeforeSwapDelta.sol";'
        ],
        "setup_code": """
        token0 = new TestERC20(1e27);
        token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));
        // RevertingHook 인스턴스 생성 (정의는 테스트 파일 내 LLM이 생성)
        revertingHook = new RevertingHook(IHooks.beforeSwap.selector);
        """,
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
        ModifyLiquidityParams memory lpParams = ModifyLiquidityParams({tickLower: -60, tickUpper: 60, liquidityDelta: 1e18, salt: bytes32(0)});
        liquidityProvider.modifyLiquidity(key, lpParams, "");
        vm.stopPrank();

        SwapParams memory params = SwapParams({ zeroForOne: true, amountSpecified: -1e17, sqrtPriceLimitX96: 4295128739 });
        bytes memory hookData = ""; // No specific hook data needed for RevertingHook scenario

        // SwapExecutor 인스턴스 생성
        SwapExecutor callback = new SwapExecutor(IPoolManager(address(_targetContract)), address(token0), address(token1));
        callback.setSwapParams(key, params, hookData);

        // 토큰 전송 및 승인
        uint256 amountToSend = 1e17;
        token0.approve(address(callback), amountToSend);
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
                "definition_code": """
contract RevertingHook is IHooks {
    bytes4 public revertSelector;
    constructor(bytes4 _selector) { revertSelector = _selector; }

    function beforeInitialize(address /*sender*/, PoolKey calldata /*key*/, uint160 /*sqrtPriceX96*/) external pure override returns (bytes4) {
        return IHooks.beforeInitialize.selector;
    }
    function afterInitialize(address /*sender*/, PoolKey calldata /*key*/, uint160 /*sqrtPriceX96*/, int24 /*tick*/) external pure override returns (bytes4) {
        return IHooks.afterInitialize.selector;
    }

    function beforeAddLiquidity(address /*sender*/, PoolKey calldata /*key*/, ModifyLiquidityParams calldata /*params*/, bytes calldata /*hookData*/) external pure override returns (bytes4) {
        return IHooks.beforeAddLiquidity.selector;
    }
    function afterAddLiquidity(address /*sender*/, PoolKey calldata /*key*/, ModifyLiquidityParams calldata /*params*/, BalanceDelta /*delta*/, BalanceDelta /*feesAccrued*/, bytes calldata /*hookData*/) external pure override returns (bytes4, BalanceDelta) {
        return (IHooks.afterAddLiquidity.selector, BalanceDeltaLibrary.ZERO_DELTA);
    }

    function beforeRemoveLiquidity(address /*sender*/, PoolKey calldata /*key*/, ModifyLiquidityParams calldata /*params*/, bytes calldata /*hookData*/) external pure override returns (bytes4) {
        return IHooks.beforeRemoveLiquidity.selector;
    }
    function afterRemoveLiquidity(address /*sender*/, PoolKey calldata /*key*/, ModifyLiquidityParams calldata /*params*/, BalanceDelta /*delta*/, BalanceDelta /*feesAccrued*/, bytes calldata /*hookData*/) external pure override returns (bytes4, BalanceDelta) {
        return (IHooks.afterRemoveLiquidity.selector, BalanceDeltaLibrary.ZERO_DELTA);
    }

    function beforeSwap(address /*sender*/, PoolKey calldata /*key*/, SwapParams calldata /*params*/, bytes calldata /*hookData*/) external view override returns (bytes4, BeforeSwapDelta, uint24) {
        if (revertSelector == IHooks.beforeSwap.selector) {
            revert("RevertingHook: Revert on beforeSwap");
        }
        return (IHooks.beforeSwap.selector, BeforeSwapDeltaLibrary.ZERO_DELTA, 0);
    }
    function afterSwap(address /*sender*/, PoolKey calldata /*key*/, SwapParams calldata /*params*/, BalanceDelta /*delta*/, bytes calldata /*hookData*/) external pure override returns (bytes4, int128) {
        return (IHooks.afterSwap.selector, 0);
    }

    function beforeDonate(address /*sender*/, PoolKey calldata /*key*/, uint256 /*amount0*/, uint256 /*amount1*/, bytes calldata /*hookData*/) external pure override returns (bytes4) {
        return IHooks.beforeDonate.selector;
    }
    function afterDonate(address /*sender*/, PoolKey calldata /*key*/, uint256 /*amount0*/, uint256 /*amount1*/, bytes calldata /*hookData*/) external pure override returns (bytes4) {
        return IHooks.afterDonate.selector;
    }
}
""",
            },
            {
                "name": "SwapExecutor",
                "instance_name": "callback",
                "constructor_args": ["IPoolManager(address(_targetContract))", "address(token0)", "address(token1)"],
                "definition_code": """
contract SwapExecutor is IUnlockCallback {
    IPoolManager public immutable manager;
    address public immutable token0;
    address public immutable token1;

    PoolKey key;
    SwapParams params;
    bytes hookData;

    constructor(IPoolManager _manager, address _token0, address _token1) {
        manager = _manager;
        token0 = _token0;
        token1 = _token1;
    }

    function setSwapParams(PoolKey memory _key, SwapParams memory _params, bytes memory _hookData) public {
        key = _key;
        params = _params;
        hookData = _hookData;
    }

    function unlockCallback(bytes calldata) external override returns (bytes memory) {
        // Perform the swap within the callback
        manager.swap(key, params, hookData);
        // Settle the amounts owed (send excess tokens back to caller)
        if (params.amountSpecified > 0) {
            if (token1 != address(0)) {
                uint256 balance1 = TestERC20(token1).balanceOf(address(this));
                if (balance1 > 0) TestERC20(token1).transfer(msg.sender, balance1);
            }
        } else {
            if (token0 != address(0)) {
                uint256 balance0 = TestERC20(token0).balanceOf(address(this));
                if (balance0 > 0) TestERC20(token0).transfer(msg.sender, balance0);
            }
        }
        return "";
    }
}
""",
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
            'import { IHooks } from "src/interfaces/IHooks.sol";',
            'import { TestERC20 } from "src/test/TestERC20.sol";',
            'import { PoolModifyLiquidityTest } from "src/test/PoolModifyLiquidityTest.sol";',
            'import { IUnlockCallback } from "src/interfaces/callback/IUnlockCallback.sol";',
            'import { console } from "forge-std/console.sol";',
            'import { ModifyLiquidityParams, SwapParams } from "src/types/PoolOperation.sol";',
            'import { BeforeSwapDelta, BeforeSwapDeltaLibrary } from "src/types/BeforeSwapDelta.sol";'
        ],
        "setup_code": """
        token0 = new TestERC20(1e27);
        token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));

        // Ensure correct currency order for PoolKey
        Currency c0 = Currency.wrap(address(token0));
        Currency c1 = Currency.wrap(address(token1));
        if (c0 > c1) (c0, c1) = (c1, c0);

        key = PoolKey({ currency0: c0, currency1: c1, fee: 3000, tickSpacing: 60, hooks: IHooks(address(0))});
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        _targetContract.initialize(key, initialSqrtPrice);
        liquidityProvider = new PoolModifyLiquidityTest(IPoolManager(address(_targetContract)));
        token0.approve(address(liquidityProvider), type(uint256).max);
        token1.approve(address(liquidityProvider), type(uint256).max);

        // Deal tokens to liquidityProvider AFTER initialization and BEFORE prank
        token0.mint(address(liquidityProvider), 2e18);
        token1.mint(address(liquidityProvider), 2e18);

        vm.startPrank(address(liquidityProvider));
        ModifyLiquidityParams memory lpParams = ModifyLiquidityParams({tickLower: -600, tickUpper: 600, liquidityDelta: 1e18, salt: bytes32(0)});
        liquidityProvider.modifyLiquidity(key, lpParams, "");
        vm.stopPrank();
        """,
        "test_setup_code": """
        // NonSettlingCallback 인스턴스 생성 (정의는 LLM이 생성)
        NonSettlingCallback callback = new NonSettlingCallback(IPoolManager(address(_targetContract)), address(token0));
        callback.setKey(key); // key는 상태 변수

        // 스왑에 필요한 토큰 준비 및 전송
        uint256 amountToSend = 1e17;
        token0.approve(address(callback), amountToSend);
        token0.transfer(address(callback), amountToSend);
        """,
        "action_code": """
        // Use the callback instance created in test_setup_code
        bytes memory callbackData = abi.encode(address(callback));
        vm.prank(address(callback));
        _targetContract.unlock(callbackData);
        """,
        "expected_revert_selector": "IPoolManager.CurrencyNotSettled.selector",
        "helper_contracts": [
            {
                "name": "NonSettlingCallback",
                "instance_name": "callback",
                "constructor_args": ["IPoolManager(address(_targetContract))", "address(token0)"],
                "definition_code": """
contract NonSettlingCallback is IUnlockCallback {
    IPoolManager public manager;
    PoolKey public key;
    address public token0;
    constructor(IPoolManager _manager, address _token0) {
        manager = _manager;
        token0 = _token0;
    }
    function setKey(PoolKey memory _key) public { key = _key; }
    function unlockCallback(bytes calldata) external override returns (bytes memory) {
        SwapParams memory params = SwapParams({
            zeroForOne: true,
            amountSpecified: -1e17,
            sqrtPriceLimitX96: 4295128739
        });
        manager.swap(key, params, "");
        return "";
    }
}
""",
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
            'import { IHooks } from "src/interfaces/IHooks.sol";',
            'import { TestERC20 } from "src/test/TestERC20.sol";',
            'import { PoolModifyLiquidityTest } from "src/test/PoolModifyLiquidityTest.sol";',
            'import { IUnlockCallback } from "src/interfaces/callback/IUnlockCallback.sol";',
            'import { console } from "forge-std/console.sol";',
            'import { ModifyLiquidityParams, SwapParams } from "src/types/PoolOperation.sol";',
            'import { BeforeSwapDelta, BeforeSwapDeltaLibrary } from "src/types/BeforeSwapDelta.sol";'
        ],
        "setup_code": """
        token0 = new TestERC20(1e27);
        token1 = new TestERC20(1e27);
        _targetContract = new PoolManager(address(this));

        // Ensure correct currency order for PoolKey
        Currency c0 = Currency.wrap(address(token0));
        Currency c1 = Currency.wrap(address(token1));
        if (c0 > c1) (c0, c1) = (c1, c0);

        key = PoolKey({ currency0: c0, currency1: c1, fee: 3000, tickSpacing: 60, hooks: IHooks(address(0))});
        uint160 initialSqrtPrice = 79228162514264337593543950336; // 1:1
        _targetContract.initialize(key, initialSqrtPrice);
        liquidityProvider = new PoolModifyLiquidityTest(IPoolManager(address(_targetContract)));
        token0.approve(address(liquidityProvider), type(uint256).max);
        token1.approve(address(liquidityProvider), type(uint256).max);

        // Deal tokens to liquidityProvider AFTER initialization and BEFORE prank
        token0.mint(address(liquidityProvider), 2e18);
        token1.mint(address(liquidityProvider), 2e18);

        vm.startPrank(address(liquidityProvider));
        ModifyLiquidityParams memory lpParams = ModifyLiquidityParams({tickLower: -600, tickUpper: 600, liquidityDelta: 1e18, salt: bytes32(0)});
        liquidityProvider.modifyLiquidity(key, lpParams, "");
        vm.stopPrank();
        """,
        "test_setup_code": """
        // ReentrantCallback 인스턴스 생성
        ReentrantCallback callback = new ReentrantCallback(IPoolManager(address(_targetContract)), address(token0));
        callback.setKey(key); // key는 상태 변수

        // 스왑에 필요한 토큰 준비 및 전송
        uint256 amountToSend = 1e18; // Corrected amount to be positive
        token0.approve(address(callback), amountToSend);
        token0.transfer(address(callback), amountToSend);
        """,
        "action_code": """
        // ReentrantCallback 인스턴스를 사용
        bytes memory callbackData = abi.encode(address(callback)); // callback은 test_setup_code에서 생성됨
        vm.prank(address(callback));

        // 재진입 호출이 ManagerLocked 오류를 발생시키는지 확인
        vm.expectRevert(IPoolManager.ManagerLocked.selector);
        _targetContract.unlock(callbackData);
        """,
        "expected_revert_selector": "IPoolManager.ManagerLocked.selector",
        "helper_contracts": [
            {
                "name": "ReentrantCallback",
                "instance_name": "callback",
                "constructor_args": ["IPoolManager(address(_targetContract))", "address(token0)"],
                "definition_code": """
contract ReentrantCallback is IUnlockCallback {
    IPoolManager public manager;
    PoolKey public key;
    address public token0;
    constructor(IPoolManager _manager, address _token0) { manager = _manager; token0 = _token0; }
    function setKey(PoolKey memory _key) public { key = _key; }
    function unlockCallback(bytes calldata) external override returns (bytes memory) {
        SwapParams memory params = SwapParams({
            zeroForOne: true,
            amountSpecified: -1e17,
            sqrtPriceLimitX96: 4295128739
        });
        manager.swap(key, params, "");
        return "";
    }
}
""",
            }
        ]
    },
]

################################################################################
# 5.  Typed view (dataclass instances)
################################################################################

# NOTE: This must live *after* SCENARIOS is fully populated so that other
# modules can safely import `SCENARIO_OBJECTS` at import-time.

SCENARIO_OBJECTS: List[ThreatScenario] = [
    ThreatScenario.from_dict(copy.deepcopy(d)) for d in SCENARIOS
]
