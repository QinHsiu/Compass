# Multi-source job intel（防虚假）

岗位 / 工作内容 / 薪资 / 工时·风评·裁员风险 一律 **多源交叉**；单源只标 `UNVERIFIED`；离谱薪资直接 `rejected`，不当事实展示。

## 规则

| 状态 | 条件 |
|:--|:--|
| `corroborated` | ≥2 个独立 `source` 且取值一致 |
| `unverified` | 仅 1 源 |
| `conflict` | 多源互相矛盾 |
| `rejected` | 合理性过滤失败（例：硕+2年·年薪1000万） |

薪资过滤：资历带上限、硬上限、同伴中位 3.5× 离群、早期高薪组合等（见 `plausibility.py`）。**不编造**市场价。

安全着陆分：仅用已标注信号启发式打分，附 reasons + disclaimer。

## CLI

```bash
# 谣言薪资一键拒绝
python -m compass_core.cli intel verify-salary --claimed "年薪1000万" --years 2 --degree 硕士 --title 大模型开发

# 多源档案（本地 JD + warehouse + 薪资样本；可加 --live）
python -m compass_core.cli intel dossier --root content --company 百度 --title 大模型 --years 2 --degree 硕士 --claimed "年薪1000万"

python -m compass_core.cli intel dossier --root content --job-id <id> --live --i-accept-tos-risk
```

产物：`content/intel/dossier_*.json|.md`

`comp lookup --live` 也会自动剔除 `rejected_implausible` 样本。
