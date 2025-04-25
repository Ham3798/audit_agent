# Q: Threat Modeling으로 나온 주요 자산과 신뢰 바운더리, 위협 시나리오 정리
> 위협 모델링 요약: 주요 자산, 신뢰 경계, 위협 시나리오  
이전에 수행된 상세 위협 모델링 분석 결과를 주요 자산, 신뢰 경계, 핵심 위협 시나리오 중심으로 요약 정리합니다.

## 1. 주요 자산 (Assets)
시스템이 보호해야 하는 핵심 가치들은 다음과 같습니다.

- **사용자 자금 (User Funds):**
  - 정산 전 PoolManager가 보유한 토큰 (네이티브 및 ERC20/ERC6909)
  - 유동성 공급자(LP)의 포지션 가치 (제공된 유동성 및 미수령 수수료)

- **수수료 수익 (Fee Revenue):**
  - 프로토콜이 축적한 수수료 (protocolFeesAccrued)
  - 유동성 공급자에게 분배될 LP 수수료 (포지션의 feeGrowthInside* 관련)

- **풀 상태 무결성 (Pool State Integrity):**
  - 정확한 가격 정보 (sqrtPriceX96, tick)
  - 정확한 유동성 정보 (liquidity, ticks[tick].liquidityGross/Net)
  - 정확한 수수료 성장률 (feeGrowthGlobal*, ticks[tick].feeGrowthOutside*, positions[pos].feeGrowthInside*Last*)
  - 틱 비트맵의 정확성 (tickBitmap)

- **시스템 가용성 (System Availability / Liveness):**
  - 사용자의 스왑, 유동성 관리, 기부 기능의 정상적인 작동
  - 잠금 해제 (unlock) 및 자금 정산 (settle/take) 기능의 정상적인 작동

- **관리자 권한 (Admin Privileges):**
  - owner 및 protocolFeeController의 권한 (프로토콜 수수료 설정 등)

## 2. 신뢰 경계 (Trust Boundaries)
시스템이 외부 또는 잠재적으로 신뢰할 수 없는 컴포넌트와 상호작용하는 지점입니다.

- **사용자 ↔ PoolManager:** 사용자는 스왑 파라미터, 유동성 파라미터, 훅 데이터 등 다양한 입력을 제공합니다. 시스템은 이 입력값들을 검증해야 합니다.
- **PoolManager ↔ 훅 (Hooks):** PoolManager는 외부 훅 컨트랙트를 호출합니다. 훅 컨트랙트의 코드는 신뢰할 수 없으며, 반환값은 PoolManager의 실행 흐름에 영향을 줍니다. 가장 중요한 신뢰 경계 중 하나입니다.
- **PoolManager ↔ IUnlockCallback 구현체:** PoolManager는 unlock을 호출한 컨트랙트의 unlockCallback 함수를 호출합니다. 이 콜백 코드는 신뢰할 수 없습니다.
- **PoolManager ↔ 토큰 컨트랙트:** PoolManager는 settle, take, mint, burn 등에서 외부 토큰 컨트랙트와 상호작용합니다. 비표준 ERC20, 악의적인 토큰(재진입, Fee-on-Transfer 등)과의 상호작용은 위험 요소입니다.
- **Owner/Controller ↔ PoolManager:** owner와 protocolFeeController는 특정 관리 기능을 수행합니다. 이 주체들은 일반적으로 신뢰되지만, 키 탈취나 내부자 위협 가능성은 존재합니다.
- **PoolManager/라이브러리 ↔ EVM:** EVM의 올바른 실행과 표준 라이브러리(예: Solmate Owned)의 정상 동작을 신뢰합니다.

## 3. 주요 위협 시나리오 (Threat Scenarios)

- **위장 (Spoofing):**
  - 악의적인 훅 주소 사용: 잘못된 권한 비트를 가진 주소나 부적절한 훅을 사용하여 풀을 초기화하려는 시도.
  - 권한 위장: protocolFeeController가 아닌 주소가 관련 함수를 호출하려는 시도.

- **변조 (Tampering):**
  - 훅 반환 값 조작: 훅이 잘못된 델타나 수수료 값을 반환하여 스왑 계산 왜곡, 자금 탈취 시도.
  - 임시 저장소 상태 조작: 재진입 공격을 통해 unlock 콜백 실행 중 CurrencyDelta, NonzeroDeltaCount 등 임시 상태 변조 시도.
  - 관리 파라미터 변조: 탈취된 owner 또는 protocolFeeController 권한으로 프로토콜 수수료 등 중요 설정 변경.
  - 풀 상태 변조: 틱 데이터(liquidityNet 등) 조작을 통해 수수료 분배나 스왑 결과 왜곡 시도.

- **정보 노출 (Information Disclosure):**
  - MEV 공격: 트랜잭션 순서 조작(Front-running, Sandwich)을 통해 사용자 스왑 가격 악화 및 이익 탈취.
  - 상태 정보 노출: extsload/exttload로 노출된 상태 정보가 다른 공격(MEV 등)에 활용될 가능성.

- **서비스 거부 (DoS):**
  - 훅/콜백 Revert: 악의적인 훅 또는 unlockCallback 구현체가 revert하여 핵심 기능(스왑, 유동성 관리, unlock) 방해.
  - 정산 실패 DoS: unlockCallback 내에서 정산을 완료하지 않아 CurrencyNotSettled 에러를 유발하고 시스템 잠금 상태 유지.
  - Gas Limit 공격: 과도한 틱 교차 유발, 악의적인 훅/콜백 실행으로 가스 한도 초과 유도.
  - 상태 손상 DoS: 풀의 핵심 상태 변수가 비정상적인 값으로 설정되어 기능 마비.
  - 정산 로직 실패: sync 누락, clear 금액 불일치 등으로 정산 불가 및 시스템 잠금.

- **권한 상승 (Elevation of Privilege):**
  - Owner/Controller 권한 탈취: 접근 제어 취약점을 이용한 관리 권한 탈취.
  - 훅 권한 오용: 훅 컨트랙트가 허가되지 않은 관리 기능(updateDynamicLPFee 등) 호출 시도.

- **경제적 공격 (Economic Attacks):**
  - 가격 조작: 대규모 스왑/유동성 조작으로 가격 왜곡 후 외부 시스템 악용.
  - 수수료 메커니즘 악용: 동적 수수료 조작, Fee-on-Transfer 토큰 처리 오류 이용.
  - 기부금 탈취 (Donate Front-running): JIT 유동성 공급을 통해 기부금 수수료 편취.
  - 유동성 고갈/그리핑: 특정 범위 유동성 소진으로 거래 방해 또는 슬리피지 극대화.

- **재진입 (Reentrancy):**
  - unlockCallback 재진입: 콜백 내 외부 호출 중 PoolManager 재호출 시도.
  - 훅 콜백 재진입: before*/after* 훅 실행 중 PoolManager 재호출 시도.
  - 토큰 전송 재진입: settle/take 시 악의적인 토큰 컨트랙트(ERC777 등)를 통한 PoolManager 재호출 시도.

## 결론:
> 이 시스템의 보안은 훅 시스템의 안전성, 재진입 방어 로직의 견고성, 잠금 및 정산 메커니즘의 정확성, 그리고 복잡한 수학적 계산의 무결성에 크게 의존합니다. 특히 신뢰 경계를 넘나드는 외부 호출(훅, 콜백, 토큰 전송) 지점들이 주요 공격 표면이 됩니다.



# Q2: 검증해야 하는 정확한 시나리오별 체크리스트 생성
> 시나리오가 통하지 않다라는 반증 가능한 명확한 기준이 특정 유니테스트 조건 하에서 검증되어야 함에 대한 체크리스트.
## 1. 위장 (Spoofing)

### 1.1 악의적인 훅 주소 사용 (Invalid Hook Address Flags)
- **위협 시나리오:** 훅 컨트랙트 주소의 권한 플래그(LSBs)가 실제 구현된 훅과 일치하지 않거나 유효하지 않을 때 풀 초기화를 시도.
- **검증 목표:** PoolManager가 Hooks.HookAddressNotValid 에러와 함께 초기화를 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** IHooks 인터페이스를 따르지만, 주소 비트와 불일치하는 권한을 가진 (또는 권한이 없는) 목업 훅 컨트랙트 배포 또는 주소 계산. PoolKey에 해당 주소 설정.
  - **Execution:** manager.initialize() 호출.
  - **Assertion:** vm.expectRevert(Hooks.HookAddressNotValid.selector)가 통과해야 함.

### 1.2 악의적인 훅 주소 사용 (Dynamic Fee Mismatch)
- **위협 시나리오:** PoolKey에 동적 수수료 플래그(DYNAMIC_FEE_FLAG)가 설정되었으나, 훅 주소가 address(0)일 때 풀 초기화를 시도.
- **검증 목표:** PoolManager가 Hooks.HookAddressNotValid 에러와 함께 초기화를 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** PoolKey의 fee를 LPFeeLibrary.DYNAMIC_FEE_FLAG로 설정하고, hooks를 IHooks(address(0))으로 설정.
  - **Execution:** manager.initialize() 호출.
  - **Assertion:** vm.expectRevert(Hooks.HookAddressNotValid.selector)가 통과해야 함.

### 1.3 관리자 권한 위장 (Unauthorized Protocol Fee Setting)
- **위협 시나리오:** protocolFeeController가 아닌 주소가 setProtocolFee를 호출하여 프로토콜 수수료를 변경하려 시도.
- **검증 목표:** ProtocolFees 컨트랙트가 IProtocolFees.InvalidCaller 에러와 함께 호출을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** PoolManager 배포 (protocolFeeController는 배포자 또는 특정 주소로 설정됨). 임의의 PoolKey 생성. attacker 주소 정의.
  - **Execution:** vm.prank(attacker)를 사용하여 attacker로 manager.setProtocolFee() 호출.
  - **Assertion:** vm.expectRevert(IProtocolFees.InvalidCaller.selector)가 통과해야 함.

---

## 2. 변조 (Tampering)

### 2.1 훅 반환 값 조작 (BeforeSwap - Delta Exceeds Amount)
- **위협 시나리오:** beforeSwap 훅이 반환하는 deltaSpecified가 원래 amountSpecified와 합쳐져 스왑 방향(ExactIn/ExactOut)을 바꾸거나 0을 초과/미달하게 만듦.
- **검증 목표:** Hooks 라이브러리가 Hooks.HookDeltaExceedsSwapAmount 에러와 함께 호출을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** beforeSwap에서 특정 deltaSpecified를 반환하는 훅 배포 및 풀 초기화, 유동성 공급. amountSpecified가 음수인 ExactIn 스왑 준비. deltaSpecified를 abs(amountSpecified)보다 크게 설정.
  - **Execution:** 해당 풀과 훅을 사용하여 스왑 실행 (manager.swap()).
  - **Assertion:** vm.expectRevert(Hooks.HookDeltaExceedsSwapAmount.selector)가 통과해야 함.

### 2.2 훅 반환 값 조작 (AfterSwap - Delta Accounting)
- **위협 시나리오:** afterSwap 훅이 델타를 반환할 때, 이 델타가 사용자의 최종 잔액 델타 계산에서 올바르게 차감/가산되지 않아 자금 유실 발생.
- **검증 목표:** 사용자의 최종 currencyDelta가 PoolManager가 반환한 스왑 델타에서 훅이 반환한 델타만큼 정확히 조정되었는지 확인. 훅 컨트랙트 자체의 델타도 올바른지 확인.
- **테스트 조건:**
  - **Setup:** afterSwap에서 0이 아닌 deltaUnspecified를 반환하는 훅 배포 및 풀 초기화, 유동성 공급. 스왑 실행 전후 사용자와 훅의 currencyDelta 기록.
  - **Execution:** 스왑 실행 (manager.swap()).
  - **Assertion:** assertEq(finalUserDelta, initialUserDelta + swapDeltaPoolManager - hookDelta) 및 assertEq(finalHookDelta, initialHookDelta + hookDelta) 검증.

### 2.3 훅 반환 값 조작 (Invalid Fee Override)
- **위협 시나리오:** 동적 수수료 풀의 beforeSwap 훅이 OVERRIDE_FEE_FLAG와 함께 유효하지 않은 LP 수수료(> MAX_LP_FEE)를 반환.
- **검증 목표:** LPFeeLibrary가 LPFeeLibrary.LPFeeTooLarge 에러와 함께 스왑을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** beforeSwap에서 OVERRIDE_FEE_FLAG 및 MAX_LP_FEE + 1 값을 포함하는 lpFeeOverride를 반환하는 훅 배포. 동적 수수료 풀 초기화 및 유동성 공급.
  - **Execution:** 해당 풀과 훅을 사용하여 스왑 실행 (manager.swap()).
  - **Assertion:** vm.expectRevert(LPFeeLibrary.LPFeeTooLarge.selector)가 통과해야 함.

---

## 3. 서비스 거부 (Denial of Service)

### 3.1 훅 Revert DoS (Generic)
- **위협 시나리오:** 풀 라이프사이클(Initialize, ModifyLiquidity, Swap, Donate) 중 호출되는 before* 또는 after* 훅이 의도적으로 revert하여 해당 작업을 방해.
- **검증 목표:** PoolManager 또는 Hooks 라이브러리가 훅 revert 시 Hooks.HookCallFailed (또는 래핑된 에러)와 함께 전체 트랜잭션을 revert 시키는지 확인.
- **테스트 조건:**
  - **Setup:** 특정 훅 인터페이스(예: beforeSwap)에서 revert하는 훅 컨트랙트 배포. 해당 훅을 사용하는 풀 초기화 및 필요시 유동성 공급.
  - **Execution:** 해당 훅을 트리거하는 작업 실행 (예: manager.swap()).
  - **Assertion:** vm.expectRevert(Hooks.HookCallFailed.selector) (또는 래핑된 에러의 selector)가 통과해야 함.

### 3.2 콜백 Revert DoS (UnlockCallback)
- **위협 시나리오:** unlock을 호출하는 컨트랙트의 unlockCallback 함수가 의도적으로 revert하여 unlock 트랜잭션 자체를 실패시킴.
- **검증 목표:** unlock 호출이 콜백의 revert와 함께 실패하는지 확인.
- **테스트 조건:**
  - **Setup:** unlockCallback에서 revert하는 IUnlockCallback 구현 컨트랙트 배포.
  - **Execution:** 해당 콜백 컨트랙트 주소로 manager.unlock() 호출.
  - **Assertion:** vm.expectRevert("Callback Revert Message") (실제 revert 메시지 확인 필요)가 통과해야 함.

### 3.3 콜백 미정산 DoS (CurrencyNotSettled)
- **위협 시나리오:** unlockCallback 내에서 스왑, 유동성 제거 등으로 인해 PoolManager에 델타(자금 이동 의무)가 발생했지만, 콜백 종료 전에 settle 또는 take을 통해 정산하지 않음.
- **검증 목표:** unlock 함수 종료 시점에 NonzeroDeltaCount가 0이 아니어서 IPoolManager.CurrencyNotSettled 에러와 함께 revert 되는지 확인.
- **테스트 조건:**
  - **Setup:** unlockCallback에서 manager.swap() 또는 manager.modifyLiquidity()를 호출하여 델타를 발생시키고, settle/take를 호출하지 않는 콜백 컨트랙트 배포. 풀 초기화 및 유동성 공급.
  - **Execution:** 해당 콜백 컨트랙트 주소로 manager.unlock() 호출.
  - **Assertion:** vm.expectRevert(IPoolManager.CurrencyNotSettled.selector)가 통과해야 함.

### 3.4 정산 로직 실패 DoS (Clear Incorrect Amount)
- **위협 시나리오:** 사용자가 clear 함수를 호출할 때, 인자로 전달하는 amount가 해당 통화의 실제 양수 델타와 정확히 일치하지 않음.
- **검증 목표:** PoolManager가 IPoolManager.MustClearExactPositiveDelta 에러와 함께 clear 호출을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** 사용자에게 특정 통화에 대한 양수 델타를 발생시킴 (예: 스왑 결과 수령).
  - **Execution:** manager.clear()를 호출하되, amount 인자를 실제 델타보다 크거나 작게 설정.
  - **Assertion:** vm.expectRevert(IPoolManager.MustClearExactPositiveDelta.selector)가 통과해야 함.

### 3.5 정산 로직 실패 DoS (Non-native Settle with Value)
- **위협 시나리오:** ERC20 토큰을 정산(sync 후 settle 호출)하려 하면서 msg.value에 0보다 큰 값을 포함하여 호출.
- **검증 목표:** PoolManager가 IPoolManager.NonzeroNativeValue 에러와 함께 settle 호출을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** 사용자에게 ERC20 토큰 델타 발생. manager.sync(erc20Token) 호출.
  - **Execution:** manager.settle{value: 1 ether}() 호출.
  - **Assertion:** vm.expectRevert(IPoolManager.NonzeroNativeValue.selector)가 통과해야 함.

---

## 4. 권한 상승 (Elevation of Privilege)

### 4.1 훅 권한 오용 (Unauthorized Dynamic Fee Update)
- **위협 시나리오:** 동적 수수료 풀에 대해, 해당 풀의 훅 컨트랙트 주소가 아닌 다른 주소가 updateDynamicLPFee를 호출하여 수수료를 변경하려 시도. 또는 정적 수수료 풀에 대해 업데이트 시도.
- **검증 목표:** PoolManager가 IPoolManager.UnauthorizedDynamicLPFeeUpdate 에러와 함께 호출을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** 동적 수수료 풀(훅 A 사용)과 정적 수수료 풀 각각 초기화. attacker 주소 정의.
  - **Execution 1:** vm.prank(attacker)로 동적 수수료 풀에 manager.updateDynamicLPFee() 호출.
  - **Assertion 1:** vm.expectRevert(IPoolManager.UnauthorizedDynamicLPFeeUpdate.selector) 통과 확인.
  - **Execution 2:** vm.prank(address(hookA))로 정적 수수료 풀에 manager.updateDynamicLPFee() 호출.
  - **Assertion 2:** vm.expectRevert(IPoolManager.UnauthorizedDynamicLPFeeUpdate.selector) 통과 확인.
  - **Execution 3:** vm.prank(address(hookA))로 동적 수수료 풀에 manager.updateDynamicLPFee() 호출 (정상 케이스).
  - **Assertion 3:** Revert하지 않아야 함.

---

## 5. 경제적 공격 (Economic Attacks)

### 5.1 Fee-on-Transfer 토큰 처리 오류 (Delta vs. Actual Transfer)
- **위협 시나리오:** Fee-on-Transfer 토큰을 take 또는 settle 할 때, PoolManager 내부 델타는 명목 금액으로 업데이트되지만 실제 전송되는 양은 수수료가 차감되어 불일치 발생.
- **검증 목표:** take 실행 후 사용자의 외부 잔액 증가량이 내부 델타 감소량과 다른지 (수수료만큼 적은지) 확인. PoolManager의 내부 델타는 0이 되는지 확인.
- **테스트 조건:**
  - **Setup:** 전송 시 수수료를 떼는 목업 ERC20 토큰 배포. 해당 토큰을 사용하는 풀 초기화. 사용자에게 해당 토큰 양수 델타 발생. 사용자와 매니저의 초기 토큰 잔액 기록.
  - **Execution:** 사용자가 manager.take() 호출.
  - **Assertion:** assertEq(finalUserBalance - initialUserBalance, expectedReceivedAmount) (수수료 차감된 양), assertEq(manager.currencyDelta(user, feeToken), 0). PoolManager의 최종 외부 잔액도 확인 (수수료만큼 증가했을 수 있음).

---

## 6. 재진입 (Reentrancy)

### 6.1 unlockCallback 재진입 방어
- **위협 시나리오:** unlockCallback 실행 중 외부 호출(예: 다른 컨트랙트 호출)을 통해 다시 PoolManager의 잠금 필요한 함수(예: swap, modifyLiquidity)를 호출 시도.
- **검증 목표:** PoolManager의 onlyWhenUnlocked 제어자가 IPoolManager.ManagerLocked 에러와 함께 재진입 호출을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** unlockCallback 내에서 manager.swap() 등을 호출하는 재진입 콜백 컨트랙트 배포. 풀 초기화 및 유동성 공급.
  - **Execution:** 해당 콜백 컨트랙트 주소로 manager.unlock() 호출.
  - **Assertion:** 콜백 내부의 manager.swap() 호출 지점에서 vm.expectRevert(IPoolManager.ManagerLocked.selector)가 통과해야 함.

### 6.2 훅 콜백 재진입 방어 (AfterSwap)
- **위협 시나리오:** afterSwap 훅 실행 중 다시 manager.swap()을 호출 시도.
- **검증 목표:** PoolManager의 락 메커니즘 또는 Hooks 라이브러리의 noSelfCall 제어자가 IPoolManager.ManagerLocked 에러와 함께 재진입 호출을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** afterSwap 내에서 manager.swap()을 호출하는 훅 컨트랙트 배포. 해당 훅을 사용하는 풀 초기화 및 유동성 공급.
  - **Execution:** 해당 풀에서 스왑 실행 (manager.swap() 또는 테스트용 라우터 사용).
  - **Assertion:** 훅 내부의 manager.swap() 호출 지점에서 vm.expectRevert(IPoolManager.ManagerLocked.selector)가 통과해야 함. (또는 훅의 noSelfCall 로직에 의해 다른 방식으로 실패할 수도 있음)

### 6.3 토큰 전송 재진입 방어 (Take)
- **위협 시나리오:** take 함수 실행 중 currency.transfer() 호출 시, 악의적인 토큰 컨트랙트(ERC777 등)가 tokensReceived 훅 등을 통해 다시 PoolManager의 잠금 필요한 함수를 호출 시도.
- **검증 목표:** PoolManager의 락 메커니즘(onlyWhenUnlocked)이 IPoolManager.ManagerLocked 에러와 함께 재진입 호출을 거부하는지 확인.
- **테스트 조건:**
  - **Setup:** transfer 함수 내에서 PoolManager의 함수(예: swap)를 호출하는 악성 토큰 컨트랙트 배포. 해당 토큰을 사용하는 풀 초기화. 사용자에게 해당 토큰 양수 델타 발생.
  - **Execution:** 사용자가 해당 악성 토큰에 대해 manager.take() 호출.
  - **Assertion:** 악성 토큰의 transfer 함수 내부에서 manager.swap() 호출 시 vm.expectRevert(IPoolManager.ManagerLocked.selector)가 통과해야 함.




# 위협 시나리오 검증을 위한 도구 조합

MCP(Minimum Checkable Proof) 기반의 유닛 테스트를 통해 위협 모델링에서 도출된 시나리오들을 검증하기 위해 필요한 도구들을 **Forge**, **정적 분석**, **동적 분석** 관점에서 정리하면 다음과 같습니다. 각 도구는 특정 유형의 위협 시나리오를 효과적으로 검증하는 데 도움을 줍니다.

---

## 1. Forge 도구 (핵심 테스트 실행 및 시뮬레이션)

Forge는 유닛 테스트 작성 및 실행의 핵심 도구이며, 대부분의 MCP 검증에 필수적입니다.

### 🔹 forge test (핵심 테스트 프레임워크)
- **용도:** Solidity로 작성된 유닛 테스트 (*.t.sol) 실행. 기본적인 함수 호출, 상태 변경, 결과 검증.
- **검증 시나리오:** 대부분의 위협 시나리오에 대한 기본적인 기능 검증 (예: 정상적인 입력 처리, 예상된 이벤트 발생 등).

### 🔹 vm 치트코드 (Cheat Codes)

- **vm.prank / vm.startPrank / vm.stopPrank**
  - **용도:** 특정 주소(msg.sender)에서 함수를 호출하는 것처럼 시뮬레이션.
  - **검증 시나리오:** 
    - 위장 (Spoofing)
    - 권한 상승 (Elevation of Privilege)

- **vm.expectRevert**
  - **용도:** 특정 에러(문자열 또는 셀렉터)와 함께 함수 실행 실패(revert) 검증.
  - **검증 시나리오:** 
    - 서비스 거부 (DoS)
    - 권한 상승 (EoP)
    - 변조 (Tampering)
    - 위장 (Spoofing)

- **vm.expectEmit**
  - **용도:** 특정 이벤트가 예상된 파라미터와 함께 발생하는지 검증.
  - **검증 시나리오:** 상태 변경 로직의 정확성 검증 (정보 노출과 간접적 관련).

- **vm.deal**
  - **용도:** 특정 주소에 네이티브 토큰(ETH) 잔액 설정.
  - **검증 시나리오:** 네이티브 토큰 정산 관련 시나리오 설정.

- **vm.store / vm.load** (주의)
  - **용도:** 컨트랙트 저장소(storage) 슬롯 직접 조작.
  - **검증 시나리오:** 변조 (Tampering), 엣지 케이스 설정.

- **vm.etch** (고급)
  - **용도:** 특정 주소에 배포된 컨트랙트의 바이트코드 변경.
  - **검증 시나리오:** 비표준 토큰, 재진입 토큰 등 목업(Mock) 컨트랙트 시뮬레이션.

---

### 🔹 퍼징 테스트 (forge test --fuzz)
- **용도:** 함수에 무작위 입력을 대량으로 넣어 엣지 케이스 탐색.
- **검증 시나리오:** 
  - 변조 (Tampering)
  - 서비스 거부 (DoS)
  - 수학/정밀도 오류

### 🔹 불변성 테스트 (Invariant Testing)
- **용도:** 시스템 상태 변화와 관계없이 항상 유지되어야 하는 불변 속성을 정의, 위반 탐지.
- **검증 시나리오:** 
  - 경제적 공격 (Economic Attacks)
  - 변조 (Tampering)
  - 재진입 후 상태 일관성 검증

### 🔹 포크 테스트 (forge test --fork-url)
- **용도:** 메인넷/테스트넷 상태 복제 후 테스트.
- **검증 시나리오:** 
  - 경제적 공격 (Economic Attacks)
  - MEV 시나리오 재현
  - 외부 프로토콜과 호환성 검증

### 🔹 가스 스냅샷 (forge snapshot)
- **용도:** 함수 실행 가스 비용 측정 및 비교.
- **검증 시나리오:** 
  - 서비스 거부 (DoS)
  - 가스 비용 회귀 테스트

---

## 2. 정적 분석 도구 (Static Analysis)

### 🔹 Slither
- **용도:** Solidity 코드 분석 산업 표준 도구.
- **검증 시나리오:** 
  - 재진입 (Reentrancy)
  - 권한 상승 (EoP)
  - 변조 (Tampering)
  - 서비스 거부 (DoS)

### 🔹 Solhint
- **용도:** 코드 스타일, 보안 가이드라인 준수 검사.
- **검증 시나리오:** 직접적 탐지보단 코드 품질 향상을 통한 오류 가능성 감소.

---

## 3. 동적 분석 도구 (Dynamic Analysis)

### 🔹 Forge Fuzz / Invariant Testing
- **설명:** 실행 기반 분석으로 실제 상태 변화 추적.

### 🔹 수동 코드 검토 및 디버깅
- **용도:** 복잡한 로직 흐름, unlock 콜백, 훅 상호작용 디버깅.
- **검증 시나리오:** 
  - 재진입 (Reentrancy)
  - 변조 (Tampering)
  - 서비스 거부 (DoS)
  - 자동화 도구가 놓친 논리적 결함

---

## 시나리오별 도구 매핑 요약

| 위협 카테고리           | 주요 검증 도구 (Forge)                                            | 보조/탐색 도구 (정적/동적)                                          |
| :---------------------- | :--------------------------------------------------------------- | :----------------------------------------------------------------- |
| 위장 (Spoofing)         | forge test, vm.prank, vm.expectRevert                             | Slither (접근 제어 패턴)                                           |
| 변조 (Tampering)        | forge test, vm.expectRevert, Fuzz, Invariant, vm.store (주의)     | Slither (연산/상태 접근), Manual Review, Forge Debugger            |
| 정보 노출 (Info Disclosure) | forge test, Fork Testing                                          | Manual Review (MEV 벡터 분석)                                     |
| 서비스 거부 (DoS)       | forge test, vm.expectRevert, Fuzz, Gas Snapshots                  | Slither (revert 경로), Manual Review (정산 로직)                   |
| 권한 상승 (EoP)         | forge test, vm.prank, vm.expectRevert                             | Slither (접근 제어, delegatecall), Manual Review                   |
| 경제적 공격 (Economic)  | forge test, Invariant Testing, Fork Testing                       | Slither (토큰 상호작용), Manual Review (인센티브 분석)             |
| 재진입 (Reentrancy)     | forge test, vm.expectRevert, Invariant (상태 일관성)              | Slither (재진입 패턴), Manual Review, Forge Debugger               |
| 수학/정밀도 오류        | Fuzz Testing, Invariant Testing, forge test (엣지 케이스)         | Slither (연산 오류), Manual Review (계산 로직)                     |

---

## 결론

위협 시나리오 검증을 위한 **MCP 기반 테스트**는 Forge를 중심으로 Slither 등의 정적 분석 도구, 퍼징/불변성 테스트, 수동 검토/디버깅으로 보완하는 **다층적 접근**이 효과적입니다. 각 도구는 상호 보완적으로 사용될 때 강력한 검증 체계를 형성합니다.
