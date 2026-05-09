# 贡献指南

欢迎贡献 Hermestrix！

## 开发环境

```bash
git clone https://github.com/yourname/hermestrix.git
cd hermestrix
pip install -r requirements.txt
```

## 测试

```bash
export HERMESTRIX_HOME=$PWD
python3 scripts/kanban.py create "测试任务" --org Zhongshu --official 太子
python3 scripts/kanban.py list
```

## 提交规范

- feat: 新功能
- fix: 修复
- docs: 文档
- style: 格式
- refactor: 重构
- test: 测试
- chore: 工具

## Agent SOUL规范

新增Agent时：
1. 在 `agents/` 下创建 `{agent_id}/SOUL.md`
2. 定义职责、权限、工作流程
3. 添加单元测试
4. 更新 ARCHITECTURE.md
