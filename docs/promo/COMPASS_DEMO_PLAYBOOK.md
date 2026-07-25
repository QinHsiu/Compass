# Compass 宣传演示：1 年后端工程师求职闭环

> 角色：**林思远**（虚构）· 工作约 1 年的 Java 后端  
> 目标岗：星河支付 · 后端开发工程师（交易链路）  
> 用途：分镜截图 · 口播 · 有声成片（约 2.5–3.5 分钟）

---

## 一句话卖点

**证据门禁求职罗盘**——查岗、匹配、改简历、模拟面试到一页终稿，全程可引用 `evidence_id`，不编造经历。

---

## 流程骨架

| 阶段 | 画面 | 口播要点 |
|:-----|:-----|:---------|
| 0 开场 | Web 首页 / Compass brand | 我是工作一年的后端，想转支付链路 |
| 1 查岗 | discover / multi / recommend | 官方 ATS + 远程 feed，不爬 Boss |
| 2 匹配 | match / grade / 矩阵 | 星河 JD 对上幂等、对账、Kafka |
| 3 简历分析 | skill-gap / redflags | 缺口清晰，红旗词可追问 |
| 4 简历修改 | resume-patch | 只注入有证据的 bullet |
| 5 模拟面试 | interview-pack / session | STAR 映射 requirement |
| 6 面试解读 | scorecard / diagnose | 五维分 + 根因建议 |
| 7 终稿 | 一页简历 | 打印级一页纸交付 |

---

## 口播稿（约 3 分钟）

见 `out/narration.zh.srt`。合成：`python docs/promo/add_narration.py`。

---

## 重新生成

```powershell
cd projects/Compass
python docs/promo/generate_slides.py
python docs/promo/make_slideshow.py
python docs/promo/add_narration.py
```

产物：`docs/promo/out/compass-backend-demo.mp4`（有声）· `play.html` · `resume_onepager_lin.html`
