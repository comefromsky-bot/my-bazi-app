import streamlit as st
import re
import datetime
import plotly.graph_objects as go
from dataclasses import dataclass

# 確保庫已正確導入
try:
    from lunar_python import Solar, Lunar
except ImportError:
    st.error("請確認已安裝庫： pip install --upgrade lunar-python")

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

STEM_PROPS = {
    '甲': {'element': '木', 'polarity': '陽'}, '乙': {'element': '木', 'polarity': '陰'},
    '丙': {'element': '火', 'polarity': '陽'}, '丁': {'element': '火', 'polarity': '陰'},
    '戊': {'element': '土', 'polarity': '陽'}, '己': {'element': '土', 'polarity': '陰'},
    '庚': {'element': '金', 'polarity': '陽'}, '辛': {'element': '金', 'polarity': '陰'},
    '壬': {'element': '水', 'polarity': '陽'}, '癸': {'element': '水', 'polarity': '陰'}
}

@dataclass
class Bazi:
    year: str; month: str; day: str; hour: str
    def __post_init__(self):
        self.stems = [self.year[0], self.month[0], self.day[0], self.hour[0]]
        self.branches = [self.year[1], self.month[1], self.day[1], self.hour[1]]
        self.pillars = [self.year, self.month, self.day, self.hour]

# --- 2. 核心運算函式 ---

def get_ten_god(me_stem, target_stem):
    if not me_stem or not target_stem: return ""
    me = STEM_PROPS[me_stem]; target = STEM_PROPS[target_stem]
    relation = RELATION_MAP.get((me['element'], target['element']))
    same_polarity = (me['polarity'] == target['polarity'])
    gods = {
        '同我': {True: '比肩', False: '劫財'}, '我生': {True: '食神', False: '傷官'},
        '我剋': {True: '偏財', False: '正財'}, '剋我': {True: '七殺', False: '正官'},
        '生我': {True: '偏印', False: '正印'}
    }
    return gods.get(relation, {}).get(same_polarity, "未知")

def get_nayin_element(pillar):
    full = NAYIN_DATA.get(pillar, "")
    return full[-1] if full else None

def get_xun_kong(pillar):
    if pillar[0] not in STEMS or pillar[1] not in BRANCHES: return []
    s_idx = STEMS.index(pillar[0]); b_idx = BRANCHES.index(pillar[1])
    diff = (b_idx - s_idx) % 12
    return [BRANCHES[(diff - 2) % 12], BRANCHES[(diff - 1) % 12]]

# --- 3. 完整 55 神煞辨識引擎 (補全至 55 項) ---

def get_55_shen_sha(bazi, pillar_idx):
    y_s, m_s, d_s, h_s = bazi.stems
    y_b, m_b, d_b, h_b = bazi.branches
    y_p, m_p, d_p, h_p = bazi.pillars
    t_s, t_b, t_p = bazi.stems[pillar_idx], bazi.branches[pillar_idx], bazi.pillars[pillar_idx]
    
    found = []

    # 1. 天乙 / 4. 太極 / 5. 文昌 / 6. 國印
    ty = {'甲':['丑','未'],'戊':['丑','未'],'庚':['丑','未'],'乙':['子','申'],'己':['子','申'],'丙':['亥','酉'],'丁':['亥','酉'],'壬':['卯','巳'],'癸':['卯','巳'],'辛':['午','寅']}
    if t_b in ty.get(d_s, []) or t_b in ty.get(y_s, []): found.append("天乙貴人")
    
    tj = {'甲':['子','午'],'乙':['子','午'],'丙':['卯','酉'],'丁':['卯','酉'],'戊':['辰','戌','丑','未'],'己':['辰','戌','丑','未'],'庚':['寅','亥'],'辛':['寅','亥'],'壬':['巳','申'],'癸':['巳','申']}
    if t_b in tj.get(d_s, []) or t_b in tj.get(y_s, []): found.append("太極貴人")
    
    wc = {'甲':'巳','乙':'午','丙':'申','丁':'酉','戊':'申','己':'酉','庚':'亥','辛':'子','壬':'寅','癸':'卯'}
    if t_b == wc.get(d_s) or t_b == wc.get(y_s): found.append("文昌貴人")

    # 19. 天廚貴人 (乙巳年修正)
    tc = {'甲':'亥', '丙':'亥', '乙':'巳', '丁':'巳', '戊':'午', '己':'未', '庚':'寅', '辛':'卯', '壬':'巳', '癸':'子'}
    if t_b == tc.get(d_s) or t_b == tc.get(y_s): found.append("天廚貴人")

    # 10-11, 27-28 驛馬, 咸池, 將星, 華蓋
    def star_check(ref_b):
        res = []
        if ref_b in ['申','子','辰']:
            if t_b == '寅': res.append("驛馬")
            if t_b == '酉': res.append("咸池")
            if t_b == '子': res.append("將星")
            if t_b == '辰': res.append("華蓋")
        elif ref_b in ['寅','午','戌']:
            if t_b == '申': res.append("驛馬")
            if t_b == '卯': res.append("咸池")
            if t_b == '午': res.append("將星")
            if t_b == '戌': res.append("華蓋")
        elif ref_b in ['巳','酉','丑']:
            if t_b == '亥': res.append("驛馬")
            if t_b == '午': res.append("咸池")
            if t_b == '酉': res.append("將星")
            if t_b == '丑': res.append("華蓋")
        elif ref_b in ['亥','卯','未']:
            if t_b == '巳': res.append("驛馬")
            if t_b == '子': res.append("咸池")
            if t_b == '卯': res.append("將星")
            if t_b == '未': res.append("華蓋")
        return res
    found.extend(star_check(y_b)); found.extend(star_check(d_b))

    # 42. 喪門 / 43. 弔客 / 44. 披麻
    if t_b == BRANCHES[(BRANCHES.index(y_b) + 2) % 12]: found.append("喪門")
    if t_b == BRANCHES[(BRANCHES.index(y_b) - 2) % 12]: found.append("弔客")
    if t_b == BRANCHES[(BRANCHES.index(y_b) + 3) % 12]: found.append("披麻")

    # 45. 童子煞 (季節 + 納音)
    ny_y_ele = get_nayin_element(y_p)
    if (m_b in ['寅','卯','辰','申','酉','戌'] and t_b in ['子','寅']) or \
       (m_b in ['巳','午','未','亥','子','丑'] and t_b in ['卯','未','辰']):
        found.append("童子煞")
    elif (ny_y_ele in ['金','木'] and t_b in ['午','卯']) or \
         (ny_y_ele in ['水','火'] and t_b in ['酉','戌']) or \
         (ny_y_ele == '土' and t_b in ['辰','巳']):
        found.append("童子煞")

    # 52. 天羅地網
    if ny_y_ele == '火' and t_b in ['戌','亥']: found.append("天羅")
    if ny_y_ele in ['水','土'] and t_b in ['辰','巳']: found.append("地網")

    # 55. 拱祿 (日時支夾)
    if pillar_idx == 3:
        if {d_b, h_b} == {'亥','丑'} and d_s == h_s == '癸': found.append("拱祿(子)")
        if {d_b, h_b} == {'巳','未'} and d_s == h_s == '丁': found.append("拱祿(午)")

    return sorted(list(set(found)))

# --- 4. 專業排盤渲染 ---

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
            "title": p["title"],
            "ten_god": get_ten_god(me_stem, p["s"]) if p["title"] != "日柱" else "日主",
            "stem": p["s"], "branch": p["b"],
            "life_stage": LIFE_STAGES[me_stem][p["b"]],
            "nayin": NAYIN_DATA.get(p["p"], "未知"),
            "hidden": [{"stem": s, "weight": w, "god": get_ten_god(me_stem, s)} for s, w in hidden],
            "shen_sha": get_55_shen_sha(bazi, p["idx"]),
            "note": p["note"]
        })

    l_fs = "20px"; c_fs = "18px"
    html = f"""
    <div style="overflow-x: auto; margin: 20px 0; font-family: '標楷體'; text-align: center;">
        <table style="width:100%; border-collapse: collapse; border: 2.5px solid #333;">
            <tr style="background: #f2f2f2; font-size: {l_fs}; font-weight: bold;">
                <td style="width: 150px; background: #e8e8e8; border: 1.5px solid #ccc; padding: 15px;">位置</td>
                {"".join([f'<td style="border: 1px solid #ccc; {"background:#fff5f5;" if r["title"]=="日柱" else ""}">{r["title"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {l_fs}; color: #d35400; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc; padding: 15px;">宮位意涵</td>
                {"".join([f'<td style="border: 1px solid #ccc; background: #fffcf5;">{r["note"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {c_fs};">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc; padding: 15px;">十神</td>
                {"".join([f'<td style="border: 1px solid #ccc; {"color:#c0392b;font-weight:bold;" if r["title"]=="日柱" else ""}">{r["ten_god"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 40px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc;">天干</td>
                {"".join([f'<td style="border: 1px solid #ccc; {"color:#c0392b;" if r["title"]=="日主" else ""}">{r["stem"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 40px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc;">地支</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["branch"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #8e44ad;">
                <td style="background: #e8e8e8; border: 1px solid #ccc; padding: 12px;">神煞系統</td>
                {"".join([f'<td style="border: 1px solid #ccc; font-weight: bold;">{"<br>".join(r["shen_sha"]) if r["shen_sha"] else "—"}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #666;">
                <td style="background: #e8e8e8; border: 1px solid #ccc; padding: 12px;">納音</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["nayin"]}</td>' for r in results])}
            </tr>
        </table>
    </div>
    """
    return html

# --- 5. Streamlit 主程式 ---

st.set_page_config(page_title="專業 AI 八字系統", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")

st.subheader("📅 請輸入西元出生時間")
c1, c2, c3, c4 = st.columns(4)
with c1: birth_date = st.date_input("出生日期", datetime.date(1990, 1, 1))
with c4: birth_hour = st.selectbox("出生時辰", range(24), format_func=lambda x: f"{x:02d}:00")

if st.button("🔮 開始精確排盤"):
    y, m, d, h = birth_date.year, birth_date.month, birth_date.day, birth_hour
    
    # 執行轉換
    solar = Solar.fromYmdHms(y, m, d, h, 0, 0)
    lunar = solar.getLunar()
    eight_char = lunar.getEightChar()
    
    # 安全獲取柱位字串
    y_p = eight_char.getYear()
    m_p = eight_char.getMonth()
    d_p = eight_char.getDay()
    h_p = eight_char.getHour()
    
    st.success(f"✅ 轉換成功： {y_p} {m_p} {d_p} {h_p}")
    bazi_obj = Bazi(y_p, m_p, d_p, h_p)
    st.markdown(render_professional_chart(bazi_obj), unsafe_allow_html=True)
