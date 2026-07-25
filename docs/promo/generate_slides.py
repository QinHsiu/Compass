"""Generate Compass promo UI mock slides (Pillow) for 林思远 demo journey."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)

W, H = 1440, 900
BLUE = (43, 109, 229)
INK = (28, 36, 52)
MUTED = (107, 114, 128)
BG = (238, 242, 248)
PANEL = (255, 255, 255)
SIDE = (18, 32, 58)
OK = (15, 118, 110)


def _pil():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
        from PIL import Image, ImageDraw, ImageFont
    return Image, ImageDraw, ImageFont


def font(size: int, bold: bool = False):
    Image, _, ImageFont = _pil()
    candidates = [
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def chrome(title: str, active: str):
    Image, ImageDraw, _ = _pil()
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # sidebar
    d.rectangle([0, 0, 220, H], fill=SIDE)
    d.text((24, 28), "Compass", font=font(28, True), fill=(232, 238, 252))
    d.text((130, 36), "Web", font=font(14), fill=(142, 182, 255))
    nav = [
        ("工作台", "desk"),
        ("查岗", "discover"),
        ("匹配", "match"),
        ("简历", "resume"),
        ("面试", "interview"),
        ("诊断", "diagnose"),
        ("图谱", "timeline"),
    ]
    y = 90
    for label, key in nav:
        if key == active:
            d.rounded_rectangle([12, y - 6, 208, y + 32], radius=10, fill=BLUE)
            d.text((28, y), label, font=font(16, True), fill=(255, 255, 255))
        else:
            d.text((28, y), label, font=font(16), fill=(197, 212, 240))
        y += 46
    d.text((20, H - 70), "demo · 林思远", font=font(12), fill=(138, 160, 200))
    d.text((20, H - 48), "证据门禁 · 本地优先", font=font(11), fill=(138, 160, 200))
    # top bar
    d.rounded_rectangle([240, 20, W - 24, 72], radius=12, fill=PANEL)
    d.text((260, 34), title, font=font(18, True), fill=INK)
    return im, d


def card(d, xy, wh, title, lines, accent=BLUE):
    x, y = xy
    w, h = wh
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=PANEL, outline=(221, 229, 240))
    d.rectangle([x, y, x + 6, y + h], fill=accent)
    d.text((x + 20, y + 14), title, font=font(16, True), fill=INK)
    yy = y + 48
    for ln in lines:
        d.text((x + 20, yy), ln[:72], font=font(13), fill=MUTED if ln.startswith("·") else INK)
        yy += 22


def slide_home():
    im, d = chrome("工作台 · 求职闭环", "desk")
    d.rounded_rectangle([240, 90, W - 24, 210], radius=16, fill=(255, 255, 255))
    d.text((268, 110), "你好，林思远", font=font(26, True), fill=INK)
    d.text((268, 150), "目标：星河支付 · 后端开发（交易链路） · 工作 1 年+ 的证据驱动求职", font=font(15), fill=MUTED)
    d.text((268, 178), "流程：查岗 → 匹配 → 简历门禁 → 模拟面试 → 诊断 → 一页终稿", font=font(14), fill=BLUE)
    card(d, (240, 230), (360, 200), "今日待办", ["· 导入星河 JD", "· 重建证据索引", "· 生成面试包", "· 导出一页简历"], OK)
    card(d, (620, 230), (380, 200), "证据库", ["ev_order_idempotency  幂等", "ev_pay_reconcile  对账", "ev_p99_query  延迟", "ev_kafka_incident  复盘"], BLUE)
    card(d, (1020, 230), (396, 200), "匹配快照", ["综合匹配度 78/100 · B", "band: strong", "硬性缺口：0", "可注入 bullet：4"], (180, 83, 9))
    im.save(SHOTS / "01-home.png")


def slide_discover():
    im, d = chrome("查岗 · discover / multi", "discover")
    card(
        d,
        (240, 100),
        (560, 320),
        "多源发现（合规）",
        [
            "sources: ats, feeds, companies",
            "· greenhouse / lever / ashby / SR",
            "· remotive / arbeitnow 公开 feed",
            "· 官方 careers → markdown",
            "",
            "命令：discover --source multi",
            "已入库 18 条 · 新岗 3",
        ],
        BLUE,
    )
    card(
        d,
        (820, 100),
        (596, 320),
        "命中岗位",
        [
            "★ 星河支付 · 后端（交易）",
            "  上海 · Kafka · 对账",
            "· 云栈内部转岗（跳过）",
            "· Remotive · Remote Java",
            "",
            "未启用：Boss / LinkedIn 爬虫",
        ],
        OK,
    )
    d.text((260, 450), "林思远选择「星河支付」进入匹配。", font=font(16), fill=INK)
    im.save(SHOTS / "02-discover.png")


def slide_match():
    im, d = chrome("匹配 · requirement matrix", "match")
    card(
        d,
        (240, 100),
        (700, 380),
        "星河支付 JD × 证据",
        [
            "direct  Java / Spring Boot     → ev_pay_reconcile",
            "direct  幂等 / 回调             → ev_order_idempotency",
            "direct  Kafka / 稳定性         → ev_kafka_incident",
            "partial 支付对账经验           → ev_pay_reconcile",
            "partial 查询性能               → ev_p99_query",
            "",
            "grade: B · 78/100 · recommendation: strong",
        ],
        BLUE,
    )
    card(
        d,
        (960, 100),
        (456, 380),
        "红旗扫描",
        [
            "未发现「螺丝钉/996」",
            "JD 表述偏工程向",
            "",
            "建议追问：",
            "· on-call 频率",
            "· 对账人工占比",
        ],
        OK,
    )
    im.save(SHOTS / "03-match.png")


def slide_gap():
    im, d = chrome("简历分析 · skill-gap", "resume")
    card(
        d,
        (240, 100),
        (560, 360),
        "技能桶",
        [
            "existing: Java, MySQL, Redis",
            "supported_by_evidence:",
            "  幂等 · 对账 · P99 · Kafka 复盘",
            "gap:（本 JD）无致命缺口",
            "",
            "不会把 gap 写进简历。",
        ],
        BLUE,
    )
    card(
        d,
        (820, 100),
        (596, 360),
        "门禁检查",
        [
            "✓ 指标可回溯到 evidence_id",
            "✓ 无 UNVERIFIED 夸大",
            "✓ 实习/正式边界清晰",
            "",
            "风险：工作仅 1 年，",
            "面试需讲清「独立边界」。",
        ],
        OK,
    )
    im.save(SHOTS / "04-resume-analysis.png")


def slide_patch():
    im, d = chrome("简历修改 · resume-patch", "resume")
    card(
        d,
        (240, 100),
        (1176, 420),
        "证据门禁 patch（摘录）",
        [
            "云栈科技 · 后端开发工程师",
            "· 支付回调对账：日切差异约 40→<5 笔（ev_pay_reconcile）",
            "· 交易查询 P99：约 280ms→95ms（ev_p99_query）",
            "· 参与 Kafka 积压止血与复盘（ev_kafka_incident）",
            "",
            "迅达零售 · 实习",
            "· 库存扣减幂等，重复扣减工单归零（ev_order_idempotency）",
            "",
            "主题：compact · 已剔除无证据空话",
        ],
        BLUE,
    )
    im.save(SHOTS / "05-resume-patch.png")


def slide_interview():
    im, d = chrome("模拟面试 · interview-pack", "interview")
    card(
        d,
        (240, 100),
        (560, 400),
        "Session 提纲",
        [
            "Warm-up: 为何适合交易链路？",
            "Deep: 幂等边界如何划？",
            "STAR → ev_order_idempotency",
            "Stress: 积压时你个人动作？",
            "",
            "persona: challenging",
        ],
        BLUE,
    )
    card(
        d,
        (820, 100),
        (596, 400),
        "口述示例（节选）",
        [
            "Q: 讲一次对账经历",
            "A: Situation 回调乱序…",
            "   Action 幂等键+状态机…",
            "   Result 差异 40→<5…",
            "   cite ev_pay_reconcile",
        ],
        OK,
    )
    im.save(SHOTS / "06-interview.png")


def slide_diagnose():
    im, d = chrome("面试解读 · scorecard / diagnose", "diagnose")
    card(
        d,
        (240, 100),
        (560, 380),
        "五维评分",
        [
            "substance     4.2",
            "structure     4.0",
            "relevance     3.8",
            "credibility   4.5",
            "jd_fit        4.1",
            "",
            "gate_pass_rate 0.85",
        ],
        BLUE,
    )
    card(
        d,
        (820, 100),
        (596, 380),
        "建议",
        [
            "P0 补一句「独立负责边界」",
            "P1 准备对账失败坏例",
            "P1 量化 on-call 参与度",
            "",
            "根因：结构尚可，",
            "需加强「我 vs 团队」区分。",
        ],
        (180, 83, 9),
    )
    im.save(SHOTS / "07-diagnose.png")


def slide_resume_final():
    """Submit-ready one-pager mock (no scores / evidence IDs / demo chrome)."""
    Image, ImageDraw, _ = _pil()
    im, d = chrome("终稿 · 可投递一页简历", "resume")
    # paper + left sidebar
    d.rounded_rectangle([340, 60, 1100, 860], radius=4, fill=(255, 255, 255), outline=(200, 210, 225))
    d.rectangle([340, 60, 530, 860], fill=(26, 35, 50))
    d.text((360, 90), "林思远", font=font(22, True), fill=(255, 255, 255))
    d.text((360, 125), "后端开发工程师", font=font(12, True), fill=(153, 246, 228))
    d.text((360, 150), "上海 · 1年经验", font=font(11), fill=(148, 163, 184))
    d.text((360, 195), "联系方式", font=font(11, True), fill=(94, 234, 212))
    for i, t in enumerate(["138-****-6621", "siyuan.lin@example.com", "github.com/siyuan-lin", "意向：交易/支付后端"]):
        d.text((360, 220 + i * 22), t, font=font(10), fill=(203, 213, 225))
    d.text((360, 325), "专业技能", font=font(11, True), fill=(94, 234, 212))
    for i, t in enumerate(
        ["Java 17 / SQL", "Spring Boot / MyBatis", "MySQL / Redis / Kafka", "Docker / Grafana", "幂等 · 对账 · 慢SQL"]
    ):
        d.text((360, 350 + i * 24), "· " + t, font=font(11), fill=(226, 232, 240))
    d.text((360, 490), "教育背景", font=font(11, True), fill=(94, 234, 212))
    d.text((360, 518), "华东某重点高校", font=font(12, True), fill=(241, 245, 249))
    d.text((360, 545), "软件工程 · 本科", font=font(11), fill=(148, 163, 184))
    d.text((360, 568), "2020.09 – 2024.06", font=font(11), fill=(148, 163, 184))
    d.text((360, 620), "工具", font=font(11, True), fill=(94, 234, 212))
    d.text((360, 648), "Git · Maven · Jenkins", font=font(11), fill=(203, 213, 225))
    d.text((360, 672), "Arthas · Grafana", font=font(11), fill=(203, 213, 225))

    # main
    d.text((555, 80), "个人简历", font=font(18, True), fill=INK)
    d.text((555, 110), "后端开发工程师 · Java          可到岗：一个月内", font=font(12), fill=MUTED)
    d.line([(555, 135), (1075, 135)], fill=OK, width=2)

    d.text((555, 155), "个人优势", font=font(13, True), fill=OK)
    d.rounded_rectangle([555, 178, 1075, 250], radius=3, fill=(238, 247, 246))
    for i, t in enumerate(
        [
            "一年 Java 后端经验，熟悉 Spring Boot 微服务交付。侧重支付回调、",
            "日切对账、查询性能与消息消费稳定性；能独立完成中等需求落地。",
        ]
    ):
        d.text((568, 190 + i * 26), t, font=font(12), fill=INK)

    d.text((555, 270), "工作经历", font=font(13, True), fill=OK)
    d.text((555, 298), "云栈科技 · 后端开发工程师                    2024.07 – 至今", font=font(12, True), fill=INK)
    d.text((555, 322), "职责：支付回调落库、日切对账、交易查询、值班答疑与文档", font=font(11), fill=MUTED)
    for i, t in enumerate(
        [
            "· 对账：幂等键+状态机，差异约40→<5笔，核对约90→25分钟",
            "· 查询：索引+短缓存，P99约280→95ms，慢SQL 30+→<5",
            "· 稳定性：参与Kafka积压止血与复盘，推动死信/超时预算",
            "· 交付：微服务迭代、访问路径评审、关键路径审计日志",
            "· 协作：Code Review、单测补充、客诉一致性排查清单",
        ]
    ):
        d.text((560, 348 + i * 22), t, font=font(11), fill=INK)

    d.text((555, 470), "迅达零售 · 后端开发实习生                    2023.07 – 2024.03", font=font(12, True), fill=INK)
    d.text((555, 494), "职责：库存扣减、超时关单联调、接口文档与集成测试", font=font(11), fill=MUTED)
    for i, t in enumerate(
        [
            "· 库存幂等：Redis令牌+唯一约束，6周重复扣减工单归零",
            "· 关单链路：延迟队列联调，减少状态未闭环资损工单",
            "· 工程基础：单测、联调手册，跟随完整提测发布流程",
        ]
    ):
        d.text((560, 520 + i * 22), t, font=font(11), fill=INK)

    d.text((555, 600), "项目经历", font=font(13, True), fill=OK)
    d.text((555, 628), "订单幂等组件练习项目 · Java / Redis / MySQL", font=font(12, True), fill=INK)
    d.text((560, 654), "· 整理令牌占用+唯一约束+集成测试样例，覆盖重试与并发场景", font=font(11), fill=INK)

    d.text((555, 700), "教育经历", font=font(13, True), fill=OK)
    d.text((555, 728), "华东某重点高校 · 软件工程 · 本科          2020.09 – 2024.06", font=font(12), fill=INK)
    d.text((555, 820), "可直接投递 · A4 一页", font=font(11), fill=MUTED)
    im.save(SHOTS / "08-resume-final.png")


def slide_end():
    Image, ImageDraw, _ = _pil()
    im = Image.new("RGB", (W, H), SIDE)
    d = ImageDraw.Draw(im)
    d.text((80, 280), "Compass", font=font(64, True), fill=(255, 255, 255))
    d.text((80, 370), "证据驱动的求职罗盘", font=font(28), fill=(142, 182, 255))
    d.text((80, 440), "查岗 · 匹配 · 门禁简历 · 模拟面试 · 一页终稿", font=font(18), fill=(197, 212, 240))
    d.text((80, 520), "github.com/QinHsiu/Compass", font=font(20, True), fill=(255, 255, 255))
    d.text((80, 580), "python -m compass_core.cli web", font=font(16), fill=(180, 200, 230))
    d.text((80, 720), "演示人物林思远为虚构 · 经历模式取材于常见后端业务场景", font=font(13), fill=(120, 140, 170))
    im.save(SHOTS / "09-endcard.png")


def main() -> int:
    slide_home()
    slide_discover()
    slide_match()
    slide_gap()
    slide_patch()
    slide_interview()
    slide_diagnose()
    slide_resume_final()
    slide_end()
    print(f"wrote slides -> {SHOTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
