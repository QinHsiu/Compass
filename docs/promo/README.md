# Compass 宣传物料

以「工作 1 年的后端工程师 · 林思远（虚构）」走完：查岗 → 匹配 → 简历分析/修改 → 模拟面试 → 诊断 → 一页终稿。

## 播放

- 本地打开 [`out/play.html`](out/play.html)
- 有声成片：[`out/compass-backend-demo.mp4`](out/compass-backend-demo.mp4)
- 一页简历：[`out/resume_onepager_lin.html`](out/resume_onepager_lin.html)（浏览器打印为 PDF）
- 人设说明：[`PERSONA.md`](PERSONA.md) · 分镜口播：[`COMPASS_DEMO_PLAYBOOK.md`](COMPASS_DEMO_PLAYBOOK.md)

## 重新生成

```powershell
cd <repo-root>   # e.g. after: git clone …/Compass && cd Compass
python docs/promo/generate_slides.py
python docs/promo/make_slideshow.py
python docs/promo/add_narration.py
```

演示数据：`content/demo_persona/`（证据 + JD + resume.json）。

## 注意

- 林思远为**宣传虚构人物**；经历模式对标常见订单/支付后端场景，勿当作真实履历使用。
- 分镜为 Compass Web 风格 UI 合成，便于可复现成片；实机录屏可按 Playbook 叠加。
