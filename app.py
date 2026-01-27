import streamlit as st
import datetime
import re
import plotly.graph_objects as go
from dataclasses import dataclass

# 導入專業曆法庫
try:
    from lunar_python import Solar, Lunar
except ImportError:
    st.error("系統偵測到缺少庫，請執行： pip install --upgrade lunar-python")

# --- 1. 基礎資料定義 ---
BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']
STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

ELEMENTS_MAP = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土', '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水',
    '寅': '木', '卯': '木', '巳': '火', '午': '火', '申': '金', '酉': '金', '亥': '水', '子': '水', '辰': '土', '戌': '土', '丑': '土', '未': '土'
}

NAYIN_DATA = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "爐中火", "丁卯": "爐中火", "戊辰": "大林木", "己巳": "大林木",
    "庚午": "路旁土", "辛未": "路旁土", "壬申": "劍鋒金", "癸酉": "劍鋒金", "甲戌": "山頭火", "乙亥": "山頭火",
    "丙子": "澗下水", "丁丑": "澗下水", "戊寅": "城頭土", "己卯": "城頭土", "庚辰": "白蠟金", "辛巳": "白蠟金",
    "壬午": "楊柳木", "癸未": "楊柳木", "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹靂火", "己丑": "霹靂火", "庚寅": "松柏木", "辛卯": "松柏木", "壬辰": "長流水", "癸巳": "長流水",
    "甲午": "砂中金", "乙未": "砂中金", "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金", "甲辰": "佛燈火", "乙巳": "佛燈火",
    "丙午": "天河水", "丁未": "天河水", "戊申": "大驛土", "己酉": "大驛土", "庚戌": "釵釧金", "辛亥": "釵釧金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水", "丙辰": "沙中土", "丁巳": "沙中土",
    "戊午": "天上火", "己未": "天上火", "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水"
}

RELATION_MAP = {
    ('木', '木'): '同我', ('木', '火'): '我生', ('木', '土'): '我剋', ('木', '金'): '剋我', ('木', '水'): '生我',
    ('火', '火'): '同我', ('火', '土'): '我生', ('火', '金'): '我剋', ('火', '水'): '剋我', ('火', '木'): '生我',
    ('土', '土'): '同我', ('土', '金'): '我生', ('土', '水'): '我剋', ('土', '木'): '剋我', ('土', '火'): '生我',
    ('金', '金'): '同我', ('金', '水'): '我生', ('金', '木'): '我剋', ('金', '火'): '我剋', ('金', '土'): '生我',
    ('水', '水'): '同我', ('水', '木'): '我生', ('水', '火'): '我剋', ('水', '土'): '剋我', ('水', '金'): '生我',
}

HIDDEN_STEMS_DATA = {
    '子': [('癸', 100)], '丑': [('己', 60), ('癸', 30), ('辛', 10)],
    '寅': [('甲', 60), ('丙', 30), ('戊', 10)], '卯': [('乙', 100)],
    '辰': [('戊', 60), ('乙', 30), ('癸', 10)], '巳': [('丙', 60), ('庚', 30), ('戊', 10)],
    '午': [('丁', 70), ('己', 30)], '未': [('己', 60), ('丁', 30), ('乙', 10)],
    '申': [('庚', 60), ('壬', 30), ('戊', 10)], '酉': [('辛', 100)],
    '戌': [('戊', 60), ('辛', 30), ('丁', 10)], '亥': [('壬', 70), ('甲', 30)]
}

LIFE_STAGES = {
    '甲': {'亥': '長生', '子': '沐浴', '丑': '冠帶', '寅': '臨官', '卯': '帝旺', '辰': '衰', '巳': '病', '午': '死', '未': '墓', '申': '絕', '酉': '胎', '戌': '養'},
    '乙': {'午': '長生', '巳': '沐浴', '辰': '冠帶', '卯': '臨官', '寅': '帝旺', '丑': '衰', '子': '病', '亥': '死', '戌': '墓', '酉': '絕', '申': '胎', '未': '養'},
    '丙': {'寅': '長生', '卯': '沐浴', '辰': '冠帶', '巳': '臨官', '午': '帝旺', '未': '衰', '申': '病', '酉': '死', '戌': '墓', '亥': '絕', '子': '胎', '丑': '養'},
    '丁': {'酉': '長生', '申': '沐浴', '未': '冠帶', '午': '臨官', '巳': '帝旺', '辰': '衰', '卯': '病', '寅': '死', '丑': '墓', '子': '絕', '亥': '胎', '戌': '養'},
    '戊': {'寅': '長生', '卯': '沐浴', '辰': '冠帶', '巳': '臨官', '午': '帝旺', '未': '衰', '申': '病', '酉': '死', '戌': '墓', '亥': '絕', '子': '胎', '丑': '養'},
    '己': {'酉': '長生', '申': '沐浴', '未': '冠帶', '午': '臨官', '巳': '帝旺', '辰': '衰', '卯': '病', '寅': '死', '丑': '墓', '子': '絕', '亥': '胎', '戌': '養'},
    '庚': {'巳': '長生', '午': '沐浴', '未': '冠帶', '申': '臨官', '酉': '帝旺', '戌': '衰', '亥': '病', '子': '死', '丑': '墓', '寅': '絕', '卯': '胎', '辰': '養'},
    '辛': {'子': '長生', '亥': '沐浴', '戌': '冠帶', '酉': '臨官', '申': '帝旺', '未': '衰', '午': '病', '巳': '死', '辰': '墓', '卯': '絕', '寅': '胎', '丑': '養'},
    '壬': {'申': '長生', '酉': '沐浴', '戌': '冠帶', '亥': '臨官', '子': '帝旺', '丑': '衰', '寅': '病', '卯': '死', '辰': '墓', '巳': '絕', '午': '胎', '未': '養'},
    '癸': {'卯': '長生', '寅': '沐浴', '丑': '冠帶', '子': '臨官', '亥': '帝旺', '戌': '衰', '酉': '病', '申': '死', '未': '墓', '午': '絕', '巳': '胎', '辰': '養'}
}

@dataclass
class Bazi:
    year: str; month: str; day: str; hour: str
    def __post_init__(self):
        self.stems = [self.year[0], self.month[0], self.day[0], self.hour[0]]
        self.branches = [self.year[1], self.month[1], self.day[1], self.hour[1]]
        self.pillars = [self.year, self.month, self.day, self.hour]

# --- 2. 核心運算 ---

def get_ten_god(me_stem, target_stem):
    if not me_stem or not target_stem: return ""
    me = STEM_PROPS[me_stem]; target = STEM_PROPS[target_stem]
    relation = RELATION_MAP.get((me['element'], target['element']))
    return {'同我': {True: '比肩', False: '劫財'}, '我生': {True: '食神', False: '傷官'},
            '我剋': {True: '偏財', False: '正財'}, '剋我': {True: '七殺', False: '正官'},
            '生我': {True: '偏印', False: '正印'}}.get(relation, {}).get(me['polarity'] == target['polarity'], "未知")

# --- 3. 全方位交互關係引擎 (重點修正：子午衝、半合等) ---

def analyze_all_interactions(bazi):
    s = bazi.stems; b = bazi.branches
    p_names = ["年", "月", "日", "時"]
    res = {"天干": [], "地支合化": [], "地支刑衝害": [], "地支生剋": []}

    # 天干五合、四衝
    s_combos = {('甲','己'):'甲己合化土', ('乙','庚'):'乙庚合化金', ('丙','辛'):'丙辛合化水', ('丁','壬'):'丁壬合化木', ('戊','癸'):'戊癸合化火'}
    s_clashes = {('甲','庚'):'甲庚相衝', ('乙','辛'):'乙辛相衝', ('丙','壬'):'丙壬相衝', ('丁','癸'):'丁癸相衝'}

    # 地支六合、六衝、六害、三刑
    b_6_combos = {('子','丑'):'子丑合土', ('寅','亥'):'寅亥合木', ('卯','戌'):'卯戌合火', ('辰','酉'):'辰酉合金', ('巳','申'):'巳申合水', ('午','未'):'午未合火'}
    b_clashes = {('子','午'):'子午相衝', ('丑','未'):'丑未相衝', ('寅','申'):'寅申相衝', ('卯','酉'):'卯酉相衝', ('辰','戌'):'辰戌相衝', ('巳','亥'):'巳亥相衝'}
    b_harms = {('子','未'):'子未相害', ('丑','午'):'丑午相害', ('寅','巳'):'寅巳相害', ('卯','辰'):'卯辰相害', ('申','亥'):'申亥相害', ('酉','戌'):'酉戌相害'}
    
    # 地支半合 (全掃描)
    semi_list = {
        ('申','子'):'申子半合水局', ('子','辰'):'子辰半合水局',
        ('寅','午'):'寅午半合火局', ('午','戌'):'午戌半合火局',
        ('亥','卯'):'亥卯半合木局', ('卯','未'):'卯未半合木局',
        ('巳','酉'):'巳酉半合金局', ('酉','丑'):'酉丑半合金局'
    }

    # 執行全域兩兩交叉比對 (6種組合)
    for i in range(4):
        for j in range(i+1, 4):
            pair_s = tuple(sorted((s[i], s[j])))
            pair_b = tuple(sorted((b[i], b[j])))
            
            # 天干
            if pair_s in s_combos: res["天干"].append(f"{p_names[i]}{p_names[j]} {s_combos[pair_s]}")
            if pair_s in s_clashes: res["天干"].append(f"{p_names[i]}{p_names[j]} {s_clashes[pair_s]}")
            
            # 地支合、衝、害
            if pair_b in b_6_combos: res["地支合化"].append(f"{p_names[i]}{p_names[j]} {b_6_combos[pair_b]}")
            if pair_b in semi_list: res["地支合化"].append(f"{p_names[i]}{p_names[j]} {semi_list[pair_b]}")
            if pair_b in b_clashes: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b_clashes[pair_b]}")
            if pair_b in b_harms: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b_harms[pair_b]}")
            
            # 地支刑 (無禮、恃勢、無恩、自刑)
            if pair_b == ('子','卯'): res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} 子卯無禮之刑")
            if b[i] == b[j] and b[i] in ['辰','午','酉','亥']: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b[i]}自刑")
            if pair_b in [('寅','巳'),('巳','申'),('申','寅')]: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} 恃勢之刑")
            if pair_b in [('丑','未'),('未','戌'),('戌','丑')]: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} 無恩之刑")

            # 生剋
            e1, e2 = ELEMENTS_MAP[b[i]], ELEMENTS_MAP[b[j]]
            rel = RELATION_MAP.get((e1, e2))
            if rel == '我生': res["地支生剋"].append(f"{p_names[i]}支{e1} 生 {p_names[j]}支{e2}")
            elif rel == '我剋': res["地支生剋"].append(f"{p_names[i]}支{e1} 剋 {p_names[j]}支{e2}")
            elif rel == '剋我': res["地支生剋"].append(f"{p_names[j]}支{e2} 剋 {p_names[i]}支{e1}")

    return res

# --- 4. 專業渲染 ---

def render_professional_chart(bazi):
    me_stem = bazi.stems[2]
    pillar_data = [
        {"title": "年柱", "p": bazi.year, "s": bazi.stems[0], "b": bazi.branches[0], "note": "祖輩童年", "idx": 0},
        {"title": "月柱", "p": bazi.month, "s": bazi.stems[1], "b": bazi.branches[1], "note": "父母青年", "idx": 1},
        {"title": "日柱", "p": bazi.day,  "s": bazi.stems[2], "b": bazi.branches[2], "note": "自身配偶", "idx": 2},
        {"title": "時柱", "p": bazi.hour, "s": bazi.stems[3], "b": bazi.branches[3], "note": "子女晚年", "idx": 3}
    ]
    results = []
    for p in pillar_data:
        hidden = HIDDEN_STEMS_DATA.get(p["b"], [])
        results.append({
            "title": p["title"], "ten_god": get_ten_god(me_stem, p["s"]) if p["title"] != "日柱" else "日主",
            "stem": p["s"], "branch": p["b"], "nayin": NAYIN_DATA.get(p["p"], "未知"),
            "hidden_stems": [h[0] for h in hidden],
            "hidden_details": [f"{h[0]}({get_ten_god(me_stem, h[0])}) {h[1]}%" for h in hidden],
            "note": p["note"]
        })

    l_fs = "20px"; c_fs = "18px"
    html = f"""
    <div style="overflow-x: auto; margin: 20px 0; font-family: '標楷體'; text-align: center;">
        <table style="width:100%; border-collapse: collapse; border: 2.5px solid #333;">
            <tr style="background: #f2f2f2; font-size: {l_fs}; font-weight: bold;">
                <td style="width: 150px; background: #e8e8e8; border: 1px solid #ccc; padding: 15px;">位置</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["title"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {l_fs}; color: #d35400; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1px solid #ccc; padding: 15px;">宮位意涵</td>
                {"".join([f'<td style="border: 1px solid #ccc; background: #fffcf5;">{r["note"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {c_fs};">
                <td style="background: #e8e8e8; border: 1px solid #ccc; padding: 15px;">十神</td>
                {"".join([f'<td style="border: 1px solid #ccc; color:#c0392b;">{r["ten_god"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 42px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">天干</td>
                {"".join([f'<td style="border: 1px solid #ccc; color:#c0392b;">{r["stem"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 42px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">地支</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["branch"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 22px; font-weight: bold; color: #16a085;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">地支藏干</td>
                {"".join([f'<td style="border: 1px solid #ccc; padding: 10px;">{"、".join(r["hidden_stems"])}</td>' for r in results])}
            </tr>
            <tr style="font-size: 15px; color: #555;">
                <td style="background: #e8e8e8; border: 1px solid #ccc; font-weight: bold;">藏干十神比例</td>
                {"".join([f'<td style="border: 1px solid #ccc; padding: 10px;">{"<br>".join(r["hidden_details"])}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #666;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">納音</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["nayin"]}</td>' for r in results])}
            </tr>
        </table>
    </div>
    """
    
    # 交互關係分類呈現
    rels = analyze_all_interactions(bazi)
    rel_html = f"""
    <div style="margin-top: 35px; font-family: '標楷體'; text-align: left; padding: 25px; border: 2.5px solid #2c3e50; border-radius: 15px; background: #ffffff;">
        <h2 style="color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px;">📜 四柱干支交互關係分析</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-top: 20px;">
            <div>
                <h4 style="color: #d35400; background: #fff4e6; padding: 10px; border-left: 5px solid #d35400;">【天干合衝】</h4>
                <ul style="font-size: 18px;">{"".join([f"<li>{x}</li>" for x in rels['天干']]) if rels['天干'] else "<li>無顯著合衝</li>"}</ul>
                <h4 style="color: #27ae60; background: #eef9f1; padding: 10px; border-left: 5px solid #27ae60;">【地支合化】</h4>
                <ul style="font-size: 18px;">{"".join([f"<li>{x}</li>" for x in rels['地支合化']]) if rels['地支合化'] else "<li>無顯著合化</li>"}</ul>
            </div>
            <div>
                <h4 style="color: #c0392b; background: #fdf2f2; padding: 10px; border-left: 5px solid #c0392b;">【地支刑衝害】</h4>
                <ul style="font-size: 18px;">{"".join([f"<li>{x}</li>" for x in rels['地支刑衝害']]) if rels['地支刑衝害'] else "<li>無顯著刑衝害</li>"}</ul>
                <h4 style="color: #2980b9; background: #f0f7ff; padding: 10px; border-left: 5px solid #2980b9;">【地支生剋】</h4>
                <ul style="font-size: 18px;">{"".join([f"<li>{x}</li>" for x in rels['地支生剋']]) if rels['地支生剋'] else "<li>無顯著生剋</li>"}</ul>
            </div>
        </div>
    </div>
    """
    return html + rel_html

# --- 5. 主程式 ---

st.set_page_config(page_title="專業 AI 八字排盤", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")

c1, c2, c3, c4 = st.columns(4)
with c1: birth_date = st.date_input("選擇日期", value=datetime.date(1990, 1, 1), min_value=datetime.date(1900, 1, 1), max_value=datetime.date(2100, 12, 31))
with c4: birth_hour = st.selectbox("小時", range(24), format_func=lambda x: f"{x:02d}:00")

if st.button("🔮 開始精確排盤"):
    y, m, d, h = birth_date.year, birth_date.month, birth_date.day, birth_hour
    solar = Solar.fromYmdHms(y, m, d, h, 0, 0)
    eight_char = solar.getLunar().getEightChar()
    y_p, m_p, d_p = eight_char.getYear(), eight_char.getMonth(), eight_char.getDay()
    h_p = getattr(eight_char, 'getHour', getattr(eight_char, 'getTime', lambda: "時柱錯誤"))()
    
    st.success(f"✅ 轉換成功：{y_p} {m_p} {d_p} {h_p}")
    st.markdown(render_professional_chart(Bazi(y_p, m_p, d_p, h_p)), unsafe_allow_html=True)
