import streamlit as st
import re
import plotly.graph_objects as go
import google.generativeai as genai
from dataclasses import dataclass

# --- 1. 基礎資料定義 ---
ELEMENTS_MAP = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土', '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水',
    '寅': '木', '卯': '木', '巳': '火', '午': '火', '申': '金', '酉': '金', '亥': '水', '子': '水', '辰': '土', '戌': '土', '丑': '土', '未': '土'
}

# 定義地支藏干及其能量佔比 (%)
HIDDEN_STEMS_DATA = {
    '子': [('癸', 100)],
    '丑': [('己', 60), ('癸', 30), ('辛', 10)],
    '寅': [('甲', 60), ('丙', 30), ('戊', 10)],
    '卯': [('乙', 100)],
    '辰': [('戊', 60), ('乙', 30), ('癸', 10)],
    '巳': [('丙', 60), ('庚', 30), ('戊', 10)],
    '午': [('丁', 70), ('己', 30)],
    '未': [('己', 60), ('丁', 30), ('乙', 10)],
    '申': [('庚', 60), ('壬', 30), ('戊', 10)],
    '酉': [('辛', 100)],
    '戌': [('戊', 60), ('辛', 30), ('丁', 10)],
    '亥': [('壬', 70), ('甲', 30)]
}

# 十二運星矩陣 (日干: {地支: 運星})
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

STEM_PROPS = {
    '甲': {'element': '木', 'polarity': '陽'}, '乙': {'element': '木', 'polarity': '陰'},
    '丙': {'element': '火', 'polarity': '陽'}, '丁': {'element': '火', 'polarity': '陰'},
    '戊': {'element': '土', 'polarity': '陽'}, '己': {'element': '土', 'polarity': '陰'},
    '庚': {'element': '金', 'polarity': '陽'}, '辛': {'element': '金', 'polarity': '陰'},
    '壬': {'element': '水', 'polarity': '陽'}, '癸': {'element': '水', 'polarity': '陰'}
}

RELATION_MAP = {
    ('木', '木'): '同我', ('木', '火'): '我生', ('木', '土'): '我剋', ('木', '金'): '剋我', ('木', '水'): '生我',
    ('火', '火'): '同我', ('火', '土'): '我生', ('火', '金'): '我剋', ('火', '水'): '剋我', ('火', '木'): '生我',
    ('土', '土'): '同我', ('土', '金'): '我生', ('土', '水'): '我剋', ('土', '木'): '剋我', ('土', '火'): '生我',
    ('金', '金'): '同我', ('金', '水'): '我生', ('金', '木'): '我剋', ('金', '火'): '剋我', ('金', '土'): '生我',
    ('水', '水'): '同我', ('水', '木'): '我生', ('水', '火'): '我剋', ('水', '土'): '剋我', ('水', '金'): '生我',
}

SHEN_SHA_INFO = {
    "天乙貴人": "命中最吉之神，逢凶化吉，易得貴人助。",
    "祿神": "主祿祿亨通，生活富足。",
    "羊刃": "主個性剛毅，易生波折。",
    "驛馬": "主變動、外向、奔波。",
    "桃花": "主人緣佳、具魅力。"
}

@dataclass
class Bazi:
    year: str; month: str; day: str; hour: str
    def __post_init__(self):
        self.stems = [self.year[0], self.month[0], self.day[0], self.hour[0]]
        self.branches = [self.year[1], self.month[1], self.day[1], self.hour[1]]

# --- 2. 邏輯運算函數 ---
def get_ten_god(me_stem, target_stem):
    if not me_stem or not target_stem: return ""
    me = STEM_PROPS[me_stem]; target = STEM_PROPS[target_stem]
    relation = RELATION_MAP[(me['element'], target['element'])]
    same_polarity = (me['polarity'] == target['polarity'])
    gods = {
        '同我': {True: '比肩', False: '劫財'}, '我生': {True: '食神', False: '傷官'},
        '我剋': {True: '偏財', False: '正財'}, '剋我': {True: '七殺', False: '正官'},
        '生我': {True: '偏印', False: '正印'}
    }
    return gods[relation][same_polarity]

def get_shen_sha(bazi, pillar_idx):
    me = bazi.stems[2]; branch = bazi.branches[pillar_idx]
    found = []
    # 天乙貴人
    ty_map = {'甲':['丑','未'], '乙':['子','申'], '丙':['亥','酉'], '丁':['亥','酉'], '戊':['丑','未'], '己':['子','申'], '庚':['丑','未'], '辛':['午','寅'], '壬':['卯','巳'], '癸':['卯','巳']}
    if branch in ty_map.get(me, []): found.append("天乙貴人")
    # 祿神
    lu_map = {'甲':'寅', '乙':'卯', '丙':'巳', '丁':'午', '戊':'巳', '己':'午', '庚':'申', '辛':'酉', '壬':'亥', '癸':'子'}
    if branch == lu_map.get(me): found.append("祿神")
    # 驛馬 (簡化邏輯)
    ym_map = {'申':'寅','子':'寅','辰':'寅','巳':'亥','酉':'亥','丑':'亥','寅':'申','午':'申','戌':'申','亥':'巳','卯':'巳','未':'巳'}
    if branch == ym_map.get(bazi.branches[2]): found.append("驛馬")
    return found

# --- 3. 渲染專業命盤 ---
def render_professional_chart(bazi):
    me_stem = bazi.stems[2]
    # 順序：年、月、日、時
    pillar_data = [
        {"title": "年柱", "p": bazi.year, "s": bazi.stems[0], "b": bazi.branches[0], "idx": 0},
        {"title": "月柱", "p": bazi.month, "s": bazi.stems[1], "b": bazi.branches[1], "idx": 1},
        {"title": "日柱", "p": bazi.day,  "s": bazi.stems[2], "b": bazi.branches[2], "idx": 2},
        {"title": "時柱", "p": bazi.hour, "s": bazi.stems[3], "b": bazi.branches[3], "idx": 3}
    ]

    results = []
    for p in pillar_data:
        hidden = HIDDEN_STEMS_DATA.get(p["b"], [])
        results.append({
            "title": p["title"],
            "ten_god": get_ten_god(me_stem, p["s"]) if p["title"] != "日柱" else "日主",
            "stem": p["s"],
            "branch": p["b"],
            "life_stage": LIFE_STAGES[me_stem][p["b"]],
            "nayin": NAYIN_DATA.get(p["p"], ""),
            "hidden_info": [{"stem": s, "weight": w, "god": get_ten_god(me_stem, s)} for s, w in hidden],
            "shen_sha": get_shen_sha(bazi, p["idx"])
        })

    html = f"""
    <div style="overflow-x: auto; margin: 20px 0;">
        <table style="width:100%; border-collapse: collapse; text-align: center; border: 2.5px solid #333; font-family: 'Microsoft JhengHei';">
            <tr style="background-color: #f1f1f1; font-weight: bold;">
                <td style="width: 120px; background: #eee; border: 1px solid #ddd; padding: 12px;">位置</td>
                {"".join([f'<td style="border: 1px solid #ddd; {"background:#fff5f5;" if r["title"]=="日柱" else ""}">{r["title"]}</td>' for r in results])}
            </tr>
            <tr>
                <td style="background: #eee; border: 1px solid #ddd; padding: 12px; font-weight: bold;">十神</td>
                {"".join([f'<td style="border: 1px solid #ddd; {"color:#d63031;font-weight:bold;" if r["title"]=="日柱" else ""}">{r["ten_god"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 32px; font-weight: bold;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 12px; font-size: 16px;">天干</td>
                {"".join([f'<td style="border: 1px solid #ddd; {"color:#d63031;" if r["title"]=="日柱" else ""}">{r["stem"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 32px; font-weight: bold;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 12px; font-size: 16px;">地支</td>
                {"".join([f'<td style="border: 1px solid #ddd;">{r["branch"]}</td>' for r in results])}
            </tr>
            <tr>
                <td style="background: #eee; border: 1px solid #ddd; padding: 12px; font-weight: bold;">藏干十神比例</td>
                {"".join([f'''<td style="border: 1px solid #ddd; font-size: 13px; text-align: left; padding: 8px;">
                    {"".join([f'<div>{h["stem"]}({h["god"]}) {h["weight"]}%</div>' for h in r["hidden_info"]])}
                </td>''' for r in results])}
            </tr>
            <tr style="color: #2980b9; font-weight: bold;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 12px;">十二運星</td>
                {"".join([f'<td style="border: 1px solid #ddd;">{r["life_stage"]}</td>' for r in results])}
            </tr>
            <tr style="color: #8e44ad; font-size: 13px;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 12px; font-weight: bold;">神煞系統</td>
                {"".join([f'<td style="border: 1px solid #ddd; font-weight:bold;">{"<br>".join(r["shen_sha"]) if r["shen_sha"] else "-"}</td>' for r in results])}
            </tr>
            <tr style="font-size: 13px; color: #777;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 12px; font-weight: bold;">納音</td>
                {"".join([f'<td style="border: 1px solid #ddd;">{r["nayin"]}</td>' for r in results])}
            </tr>
        </table>
    </div>
    """
    return html

# --- 4. Streamlit 介面與啟動 ---
st.set_page_config(page_title="專業 AI 八字系統", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")

with st.sidebar:
    st.header("⚙️ 設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")

input_text = st.text_input("請輸入八字（例：乙巳 戊寅 辛亥 壬辰）", "乙巳 戊寅 辛亥 壬辰")

if input_text:
    matches = re.findall(r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]', input_text)
    if len(matches) >= 4:
        bazi = Bazi(matches[0], matches[1], matches[2], matches[3])
        
        # 顯示專業命盤
        st.markdown(render_professional_chart(bazi), unsafe_allow_html=True)
        
        # 五行能量分析
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📊 五行能量分佈")
            scores = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
            for s in bazi.stems: scores[ELEMENTS_MAP[s]] += 1.0
            for b in bazi.branches:
                for s, w in HIDDEN_STEMS_DATA[b]:
                    scores[ELEMENTS_MAP[s]] += (w/100.0)
            
            fig = go.Figure(go.Scatterpolar(r=list(scores.values())+[list(scores.values())[0]], theta=list(scores.keys())+[list(scores.keys())[0]], fill='toself'))
            st.plotly_chart(fig, use_container_width=True)
            
        with col2:
            if api_key and st.button("🧙 大師批命"):
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash-latest')
                prompt = f"你是一位資深命理大師，請根據八字「{input_text}」與五行能量 {scores} 提供 300 字左右的分析。"
                response = model.generate_content(prompt)
                st.write(response.text)
    else:
        st.error("請確認輸入格式為四組干支（如：乙巳 戊寅 辛亥 壬辰）")
