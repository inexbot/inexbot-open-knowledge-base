# 控制器二次开发 SDK：常见 API 误读陷阱

整理用户问"控制器 SDK API"类问题时，AI 容易混淆或答错的概念。

## 1. `NRC_GetRobotTypeConfig` 不是"控制器型号"

这是最常见的误读。

| 接口 | 实际返回 | 误读为 |
|---|---|---|
| `NRC_GetRobotTypeConfig(std::string& type)` | 机器人结构类型枚举字符串，如 `"R_GENERAL_6S"`、`"R_SCARA"`、`"R_FOURAXIS_PALLET"`、`"R_GENERAL_7S_RBT"` | 控制器硬件型号（如 `C2201`、`C1201`） |

返回值的合法取值见 `~/.hermes/kb/inexbot-open/md/zh-04.控制器-02.二次开发API-机器人基本参数设置.md` 第 1012 行附近。一共 13 种机器人类型枚举。

如果用户要的是硬件型号（C2201 / C1201 / C2200 系列），C++ SDK 没有直接接口，需走 JSON 协议命令字 0x10C0 / 0x10C1，返回字段：

```json
{
  "controllerID": "1234567890ABCDEF",
  "controllerModel": "C2201"
}
```

文档位置：`zh-07.JSON-协议-02.RTL-24.03-01.系统-01.系统.md` 第 862 行附近（命令字 0x10C0/0x10C1，"获取控制器基础信息"）。

## 2. "NexMotion 库版本" ≠ "控制器型号/固件版本"

| 接口 | 返回 |
|---|---|
| `NRC_GetNexMotionLibVersion()` | SDK 库版本（libNexRob.a 的版本号） |
| `NRC_GetSyncVersion()` | 同步版本号（外部轴相关） |
| `NRC_GetControlCycle()` | 控制器与伺服的通讯周期（int） |

三个都不返回控制器硬件型号。文档位置：同一份"机器人基本参数设置.md" 第 588 行起。

## 3. "机器人轴数" ≠ "外部轴轴数"

| 接口 | 返回 |
|---|---|
| `NRC_GetRobotAxisSum()` | 机器人本体轴数（6、4、7 等） |
| `NRC_GetSyncAxisSum()` | 外部轴轴数 |

## 4. 多机版接口带 `Rbt_` 前缀

多机模式下机器人编号 1～4，对应接口名前缀加 `Rbt_`：

- `NRC_Rbt_GetRobotTypeConfig(int robotNum, std::string& type)`
- `NRC_Rbt_GetCurrentPos(int robotNum, ...)`
- `NRC_Rbt_SetServoModerOfOperation(...)`

非多机版调用 `NRC_GetRobotTypeConfig` 即可。

## 5. 调用顺序

任何 `NRC_*` 接口调用前必须先 `NRC_StartController()`，并轮询 `NRC_GetControlInitComplete()` 直到返回 1，否则会拿到 -102/-103 错误。

```cpp
NRC_StartController();
while (NRC_GetControlInitComplete() != 1) {
    NRC_Delayms(100);
}
// 现在才能调 NRC_GetRobotTypeConfig 等
```

## 6. 已知不在 SDK 中的常见查询

| 用户问 | 是否在 C++ SDK | 替代方案 |
|---|---|---|
| 控制器硬件型号（C2201 等） | ❌ 无 | JSON 协议 0x10C0 |
| 控制器 SN/ID | ❌ 无（JSON 协议有 controllerID） | JSON 协议 0x10C0 |
| 控制器 IP | 部分（`NRC_ModifyControllerIP` 是设置） | 走系统命令或示教器界面 |
| IO 板型号 | ❌ 无 | JSON 协议 0x2F23 |
| 伺服型号 | ✅ `NRC_GetConnectServoTypeList()` | — |

## 7. 上位机 C++ 接口页是 TOC 占位 — 结构体字段要查 JSON 协议

**陷阱**：open.inexbot.com 上 `/04.上位机/01.C++/02.接口说明/07.作业文件操作`（以及同类接口说明页）当前是**只有目录的占位页**——只列出 `job_insert_io_out_command` / `job_insert_timer_command` / `job_insert_until` 这类函数名，**没有参数结构体的字段定义**。

但用户的 SDK 代码里**确实**有一个 `IOCommandParams` / `TimerCommandParams` / 等结构体要传。这种结构体的字段定义要去 JSON 协议页找：

- 作业文件插入指令（job_insert_*_command）：`/05.JSON-协议/02.RTL-24.03/03.程序/02.程序-指令增删改查/0X.指令-XXX类/`
  - 03.指令-输入输出类（DOUT/DIN/AIN/AOUT/PULSEOUT/READ_DOUT）—— `IOCommandParams`
  - 07.指令-定时器类（TIMER）—— `TimerCommandParams`
  - 05.指令-条件控制类（UNTIL/WHILE/IF）—— `LogicCommandParams`
  - 其他类推
- 通用规律：所有 `job_insert_*_command` 系列的 `*CommandParams` 结构体，其字段名 = 对应 JSON 指令的字段名（大小写以手上 nrc_interface.h 为准），且每条指令都有这几个通用头字段：
  - `logout` (bool)、`type` (int，指令类型枚举)、`userParamInt` (int)、`userParamString` (string)
  - 指令特有的参数（如 DOUT 的 `ParaGroupNum` / `ParaGroupValue` / `ParaGroupTime` / `groupType` / `errorHanding`）

**举例：DOUT 指令（`job_insert_io_out_command`，type=16）完整字段**：

```cpp
IOCommandParams params;
params.logout          = false;
params.type            = 16;       // DOUT 枚举值（DIN=17 AIN=21 AOUT=20 PULSEOUT=22 READ_DOUT=97）
params.userParamInt    = 0;
params.userParamString = "";
params.groupType       = "OT#";    // 1路输出；4路="OGH#"，8路="OG#"
// ParaGroupNum.value = IO板序号 × 16 / 路数（如 8 路板的第 3 个端口 = 8*2=16）
params.paraGroupNum    = {2.0, 0, 0, ""};       // {data, secondvalue, value, varname}
params.paraGroupValue  = {0.0, 0, 1, ""};       // 高电平=1；用变量就填 varname 如 "I001"
params.errorHanding    = 1;        // 1=计时结束停止，0=保持
params.paraGroupTime   = {3.0, 0, 0, ""};       // 持续 3 秒

int ret = job_insert_io_out_command(line, params);
```

完整权威定义见 `zh-05.JSON-协议-02.RTL-24.03-03.程序-02.程序-指令增删改查-03.指令-输入输出类.md` 第 70+ 行起。

## 8. 别把 `job_insert_io_out_command`（上位机 SDK）和 `NRC_JobfileInsertDOUT`（控制器端 API）搞混

两者**不是同一个东西**，名字相似但属于不同侧：

| 接口 | 所属侧 | 函数原型 | 适用场景 |
|---|---|---|---|
| `job_insert_io_out_command` | 上位机 C++ SDK（PC 端调控制器） | `int job_insert_io_out_command(int line, IOCommandParams& params)` | 用 C++ 在 PC 上往控制器作业文件里**插入**一条指令 |
| `NRC_JobfileInsertDOUT` | 控制器二次开发 API（Lua/插件） | `int NRC_JobfileInsertDOUT(int line, int port, int value, double time_sec)` | 在**控制器内部**自定义指令/Lua 脚本里插入指令 |

控制器端详细定义：`zh-06.控制器-02.接口说明-02.作业文件-指令操作.md` 第 ~700+ 行（DOUT 段）。

判断方法：看头文件——如果是 `nrc_interface.h` 或类似 PC 端头文件，用 `job_insert_*_command` + 结构体；如果是控制器 Lua 引擎或 C 插件环境，用 `NRC_JobfileInsert*` + 标量。

---

## 9. `job_insert_until` 的 Condition/ParaGroup/LogicType 结构怎么填

上位机 SDK 函数签名：

```cpp
Result job_insert_until(
    SOCKETFD socketFd,
    int line,
    const std::vector<std::vector<Condition>>& conditionGroups,
    const std::vector<int>& logic,                // 外层逻辑：并列组之间的关系
    const std::vector<std::vector<int>>& logicGroup // 内层逻辑：每个并列组内 Condition 之间的关系
);
```

对应的 JSON 结构（UNTIL 指令 type=87 in 24.03 / 85 in 22.07）：

| C++ 字段 | JSON 字段 | 含义 |
|---|---|---|
| `conditionGroups` | `untilconditionArrayFINAL.conditionGroup` | 二维数组。外层每个 vector 是一个并列判断组，内层是该组内的多条 Condition |
| `logic` | `untilconditionArrayFINAL.logic` | **外层**逻辑：并列组之间的关系，size = conditionGroups.size() - 1；`0`=与，`1`=或 |
| `logicGroup` | `untilconditionArrayFINAL.logicGroup` | **内层**逻辑：每个并列组内 Condition 之间的关系；外层 size = conditionGroups.size()，每个内层 size = conditionGroups[i].size() - 1；`0`=与，`1`=或，无意义时填 `null` 或留空 |
| `Condition.logicType` (LogicType) | `logicType` | 比较方式：`1`== 等于、`2`< 小于、`3`> 大于、`4`<= 小于等于、`5`>= 大于等于、`6`!= 不等于 |
| `Condition.paraGroupOne` / `paraGroupTwo` | `paraGroupOne` / `paraGroupTwo` | 比较的左右两侧，都是 ParaGroup 结构 |
| `Condition.key` | `key` | 主参数变量名（冗余字段，填 `paraGroupOne.varname` 同名即可） |
| `Condition.desValue` | `desValue` | UI 显示用的字符串常量，调试用，默认 `"0"` |

`ParaGroup` 结构 `{data, secondvalue, value, varname}`：

- `value` 决定 `data` 与 `varname` 怎么解释：
  - `0` = 手填常量：`data` 是数值，`varname` 留空 `""`
  - `1` = 局部 `I`，`2` = 局部 `D`，`3` = 局部 `B`，`4` = 全局 `GI`，`5` = 全局 `GD`，`6` = 全局 `GB`，`7` = 字符串手填值，`8` = 字符串变量 `S`
  - 选 `1~8` 时填 `varname`，`data` 写 0
- `secondvalue` 几乎总是 `0`，保留字段

典型示例：表示 `(I001==I002 AND I003==I004) OR (I005==I006)`

```cpp
// 外层 2 个并列组：(组0) OR (组1)
// 组 0 内 2 条 Condition，关系 AND
// 组 1 内 1 条 Condition，无内层逻辑

Condition c1; c1.key="I001"; c1.logicType=LogicType::EQUAL_TO;
c1.paraGroupOne={0.0, 0, 1, "I001"};
c1.paraGroupTwo={0.0, 0, 1, "I002"};

Condition c2; c2.key="I003"; c2.logicType=LogicType::EQUAL_TO;
c2.paraGroupOne={0.0, 0, 1, "I003"};
c2.paraGroupTwo={0.0, 0, 1, "I004"};

Condition c3; c3.key="I005"; c3.logicType=LogicType::EQUAL_TO;
c3.paraGroupOne={0.0, 0, 1, "I005"};
c3.paraGroupTwo={0.0, 0, 1, "I006"};

std::vector<std::vector<Condition>> conditionGroups = {
    { c1, c2 },   // 组 0
    { c3 }        // 组 1
};

// logic（外层）: 1 个关系（两组之间） → OR
std::vector<int> logic = { 1 };

// logicGroup（内层）: 组 0 有 1 个关系 → AND，组 1 无关系 → 空 vector
std::vector<std::vector<int>> logicGroup = { { 0 }, {} };

int ret = job_insert_until(fd, line, conditionGroups, logic, logicGroup);
```

权威定义：`zh-05.JSON-协议-02.RTL-24.03-03.程序-02.程序-指令增删改查-05.指令-条件控制类.md` UNTIL 段；`logicType` 数值映射来自同目录下 IF/WHILE/JUMP 章节的「比较方式」注释。

注意：调用 `job_insert_until` 会**同时插入 ENDUNTIL**，二者必须成对删除，否则程序会报错。

## 10. C# SDK 特有陷阱：`get_current_position` 首调返回非 SUCCESS，必须点动一次才正常显示

**问题**：用户 WinForms 上 `JogTimer_Tick` 里调用 `nrc_interface.get_current_position(fd, 0, pos)` 想要关节/直角坐标实时显示，但上电后位置一直是空，必须在界面上点一下 J1 按钮，其他坐标才开始显示。

**根因**：连接成功后控制器还没进入"可查询"状态——首次调用 `get_current_position` 返回的不是 `Result.SUCCESS`，所以 `if (res == Result.SUCCESS)` 内部的 `JPosition1.Text = pos[0]...` 一行**根本没执行**。点 J1 触发的 `robot_start_jogging` 让控制器进入活跃态后，后续 tick 才返回 SUCCESS。

注：C++ SDK 的 `NRC_*` 接口在 `NRC_StartController()` + `NRC_GetControlInitComplete()==1` 之后才稳定（见 gotcha #5），C# SDK 的 `connect_robot` 没做这个轮询，所以定时器一上来就调 `get_current_position` 会踩到同样的窗口期。

**修复三选一（推荐第一种）**：

1. **连接成功回调里手动喂一帧**——`connect_robot` 返回 >0 后，立刻主动调一次 `JogTimer_Tick(this, EventArgs.Empty)`，再 `JogTimer.Start()`。最简单，不破坏原结构。

2. **把 `JogTimer.Start()` 从 `Form_Load` 挪到连接成功分支里**——fd 未就绪前定时器根本不会跑，避免空窗口。

3. **轮询首帧**——`connect_robot` 成功后 `await Task.Run(...)` 跑一个 5 秒内的重试循环（每 100ms 一次），拿到第一个 SUCCESS 才退出，再 `JogTimer.Start()`。最稳但代码略重。

**典型错误模式（要避免）**：把所有 `Label.Text = pos[i].ToString("F2")` 写在各自的 `if (res == Result.SUCCESS) { ... }` 里。结果是只要某次调用 res 失败，对应控件就一直显示旧值或空。一上电即失败 + 多控件分别判断 = "必须先点哪个按钮才全部显示"。

**多机版**：多机模式用 `nrc_interface.Rbt_get_current_position(fd, robotNum, coord, pos)`，robotNum 从 1 起；非多机版直接 `get_current_position(fd, coord, pos)`。

**KB 文档现状**：C# 的 SDK KB 当前只有 `zh-06.上位机-02.CSharp-02.接口示例-01.连接示例.md` 一篇连接示例文档，`get_current_position` / `start_jogging` 等接口示例需要参考 C++ 的对应页面（函数签名几乎一致，参数语义相同）。

## 11. `robot_start_jogging` 的 `axis` 参数：依坐标系语义变化，关节坐标系下 1~6 = J1~J6

**问题**：用户问 `robot_start_jogging(fd, axis, positive)` 里 axis=1 到 6 是不是对应 J1~J6？

**结论**：**在关节坐标系下 axis=1..6 就是 J1..J6**；在直角/工具/用户坐标系下 axis=1..6 对应 X/Y/Z/A/B/C（或 TX/TY/TZ/TA/TB/TC、UX/UY/UZ/UA/UB/UC）；**axis=7** 是 psi 轴；**外部轴从 axis=8 开始**。

**证据**：
- C++ SDK 接口页 `zh-04.上位机-01.C++-02.接口说明-01.基础连接与系统接口.md` 仅给签名 `Result robot_start_jogging(SOCKETFD socketFd, ...);` 参数用 `...` 省略，**文档站开箱限制**，无 axis 枚举说明。
- 下层 JSON 协议命令字 `0x2901 JOG_OPERATION_MOVE`（22.07 在 `zh-07.JSON-协议-01.RTL-22.07-02.6000-端口通讯(2207)-01.运动控制-03.机器人设置.md` 第 ~1430 行起；24.03 同名命令字）给出的 axis 轴号说明表如下，**注意官方表只列了直角/工具/用户三行**，关节坐标系未单独成行：

  | 当前坐标系 | axis=1 | axis=2 | axis=3 | axis=4 | axis=5 | axis=6 | axis=7 |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | 直角坐标系 | X 轴 | Y 轴 | Z 轴 | A 轴 | B 轴 | C 轴 | psi 轴 |
  | 工具坐标系 | TX 轴 | TY 轴 | TZ 轴 | TA 轴 | TB 轴 | TC 轴 | psi 轴 |
  | 用户坐标系 | UX 轴 | UY 轴 | UZ 轴 | UA 轴 | UB 轴 | UC 轴 | psi 轴 |

- 关节坐标系 axis=1..6 = J1..J6 的交叉验证（KB 没有专门说明，但可从以下三点推出）：
  1. 同协议下 `0x3B02 JOINTPARAMETER_INQUIRE` 字段说明明确写"**AxisNum int 是 关节编号（1代表 J1）**"——关节轴号就是 1~6。
  2. `0x3B03 JOINTPARAMETER_RESPOND` 返回的关节参数与 `AxisNum` 字段 1:1 对应。
  3. 关节坐标系的轴就只有 6 个本体轴（J1~J6），直角/工具/用户坐标系下 axis=1..6 对应 XYZABC 三平移+三姿态共 6 个轴，关节坐标系下也只能是 J1~J6。
- 关节坐标系下停止点动用 `robot_stop_jogging(fd, axis)`，参数同上。

**示教器本体按键命名差异（不要混淆）**：22.07 系统操作手册 `4.1.1 坐标` 一节把关节坐标系下的按键命名为 **S、L、U、R、B、T**（基本轴 S/L/U + 腕部轴 R/B/T），不是 J1~J6。但这只是示教器按键标识，对 SDK 编程无影响，SDK 一律用 axis=1~6 = J1~J6。