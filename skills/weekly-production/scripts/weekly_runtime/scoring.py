# SPDX-License-Identifier: GPL-3.0-only
"""The published composite formula and its auditable, deterministic terms.

Independent implementation of the rule card in 周刊娘 #852 (00:36).
The upstream automation consumes a precomputed score; it is not a score API.
"""
from decimal import Decimal, ROUND_HALF_UP, localcontext

ALGORITHM = "aigirl-weekly-score-v1"
SOURCE_VIDEO = "https://www.bilibili.com/video/BV1bQnL6LEpz/?t=36"
SOURCE_CODE = "https://github.com/Neutralization/BiliBiliRankingScripts/blob/f2f2e4de37e588dd8b41096eda9f5fdbd44a0458/generate.py"
INPUTS = ("view", "reply", "danmaku", "favorite", "coin")


def rounded(value, places):
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def calculate(metrics, part_count=1, algorithm=ALGORITHM):
    if metrics is None:
        return None
    if algorithm == "views-v1":
        return {"algorithm": algorithm, "score": metrics["view"], "legacy": True}
    if algorithm != ALGORITHM:
        raise ValueError("未实现的计分规则：" + str(algorithm))
    if not isinstance(part_count, int) or isinstance(part_count, bool) or part_count < 1:
        raise ValueError("计分需要有效的分 P 数")
    for key in INPUTS:
        value = metrics.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("计分指标缺失或为负，须复核：" + key)
    with localcontext() as context:
        context.prec = 40
        v, r, m, f, k = (Decimal(metrics[key]) for key in INPUTS)
        one = Decimal(1)
        p = rounded(Decimal(4) / (part_count + 3), 3)
        a = min(one, (v + 1_000_000) / (2 * v)) if v else one
        b_den = v + 10 * k + 50 * r
        c_den = 2 * v + 10 * f + 20 * k
        b = rounded(min(one, (20 * f + 10 * k) / b_den), 2) if b_den else Decimal(0)
        c = rounded(min(one, (50 * r + m) / c_den), 2) if c_den else Decimal(0)
        d = rounded((r + m + 10).log10() / (v + f + k + 10).log10(), 3)
        terms = {"view": v * p * a, "reply": r * b * 50, "coin": k * c * 20, "favorite": f * c}
        raw = sum(terms.values()) * d
        return {
            "algorithm": algorithm, "score": int(rounded(raw, 0)),
            "raw_score": str(raw), "part_count": part_count,
            "coefficients": {key: str(value) for key, value in {"P": p, "A": a, "B": b, "C": c, "D": d}.items()},
            "terms_before_D": {key: str(value) for key, value in terms.items()},
            "inputs": {key: metrics[key] for key in INPUTS},
        }


def sort_key(row):
    score = row.get("score")
    return (-(score if score is not None else -10**30), row["bvid"])


def rule_info(algorithm=ALGORITHM):
    if algorithm == "views-v1":
        return {"id": algorithm, "description": "旧测试规则：仅按播放量排序。", "legacy": True}
    if algorithm != ALGORITHM:
        raise ValueError("未实现的计分规则：" + str(algorithm))
    return {
        "id": ALGORITHM,
        "description": "按综合得分降序排序；创刊期代入累计指标，常规周榜代入各指标的周期净增量。",
        "formula": "S = (V*P*A + R*B*50 + K*C*20 + F*C)*D",
        "variables": {"V": "播放", "R": "评论", "M": "弹幕", "F": "收藏", "K": "投币", "N": "分P数"},
        "coefficients": {
            "P": "round_half_up(4/(N+3),3)",
            "A": "min(1,(1000000+V)/(2*V))",
            "B": "round_half_up(min(1,(20*F+10*K)/(V+10*K+50*R)),2)",
            "C": "round_half_up(min(1,(50*R+M)/(2*V+10*F+20*K)),2)",
            "D": "round_half_up(log10(R+M+10)/log10(V+F+K+10),3)",
        },
        "rounding": "十进制 ROUND_HALF_UP；P、D 保留三位，B、C 保留两位；A 不提前舍入；最终总分四舍五入到整数。",
        "zero_handling": "V=0 时 A=1；B、C 分母为零时取 0；全零输入得分为 0。",
        "negative_handling": "计分指标净增量为负时进入异常复核，不自动归零，不参加排名。",
        "tie_break": "最终整数得分相同，按 BV 号区分大小写的字典升序排列；不增加隐藏加权。",
        "display_only": ["like", "share"],
        "data_basis": "先求各指标净增量再代入公式；不计算两次累计综合得分之差。",
        "scope": "已发现且经主题复核的 AI 拟人二创视频；不宣称全站无遗漏。",
        "sources": [SOURCE_VIDEO, SOURCE_CODE],
        "attribution": "参考周刊娘第852期公开主榜公式；零值、负增量、舍入与同分细则为本项目明确规定，非官方分数接口。",
    }
