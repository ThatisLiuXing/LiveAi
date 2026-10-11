# User Instruction Memory

This file records user instructions, preferences, and teachings for reference in future interactions.

## Format

### User Instruction Entry
User instruction entries should follow this format:

[User Instruction Summary]
- Date: [YYYY-MM-DD]
- Context: [Mentioned scenario or time]
- Instructions:
  - [Content of user teaching or instruction, described line by line]

### Project Knowledge Entry
Entries discovered by the Agent during task execution should follow this format:

[Project Knowledge Summary]
- Date: [YYYY-MM-DD]
- Context: Discovered by Agent while performing [specific task description]
- Category: [Operations & Deployment|Build Methods|Testing Methods|Troubleshooting & Debugging|Workflow & Collaboration|Environment Configuration]
- Instructions:
  - [Specific knowledge points, described line by line]

## Deduplication Strategy
- Before adding a new entry, check for similar or identical instructions.
- If a duplicate is found, skip the new entry or merge it with the existing one.
- When merging, update the context or date information.
- This helps avoid redundant entries and keeps the memory file tidy.

## Entries

### 环境命令与环境变量
- Date: 2026-10-11
- Context: 优化 LiveAi 代码库时发现
- Category: Environment Configuration
- Instructions:
  - 环境只有 `python3`，没有 `python` 命令（`python` 会报 `command not found`）
  - 编译验证用 `python3 -m py_compile <file1> <file2> ...`，必要时配合 `python3 -c "import ast; ast.parse(...)"` 做 AST 校验

### 测试运行方式
- Date: 2026-10-11
- Context: 为 LiveAi 建立离线单元测试时发现
- Category: Testing Methods
- Instructions:
  - 无 pytest/tox 配置；用标准库 `unittest` + `python3 -m unittest discover -s test -p "test_<name>.py" -v`
  - `test/` 下原有文件多为需真实 API/网络的渠道测试（如 test_aipai_via_class.py），无法离线跑；离线测试应放入 `test/test_*.py` 且不 import 需要真实凭据的模块
  - `test/` 目录无 `__init__.py`，import 测试模块需用 discover 而非 `python3 -m unittest test.test_xxx`
  - 存储层核心读写逻辑集中在 `core/ai_repository.py` + `pack/json_store.py` + `pack/scoped_memory_store.py`，可用临时目录离线验证 round-trip
