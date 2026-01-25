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

HIDDEN_STEMS = {
    '子': ['癸'], '丑': ['己', '癸', '辛'], '寅': ['甲', '丙', '戊'], '卯': ['乙'], '辰': ['戊', '乙', '癸'],
    '巳': ['丙', '庚', '戊'], '午': ['丁', '己'], '未': ['己', '丁', '乙'], '申': ['庚', '壬', '戊'], '酉': ['辛'],
    '戌': ['戊', '辛', '丁'], '亥': ['壬', '甲']
}

# 建議放在程式碼上方的資料定義區
NAYIN_DATA = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "爐中火", "丁卯": "爐中火",
    "戊辰": "大林木", "己巳": "大林木", "庚午": "路旁土", "辛未": "路旁土",
    "壬申": "劍鋒金", "癸酉": "劍鋒金", "甲戌": "山頭火", "乙亥": "山頭火",
    "丙子": "澗下水", "丁丑": "澗下水", "戊寅": "城頭土", "己卯": "城頭土",
    "庚辰": "白蠟金", "辛巳": "白蠟金", "壬午": "楊柳木", "癸未": "楊柳木",
    "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹靂火", "己丑": "霹靂火", "庚寅": "松柏木", "辛卯": "松柏木",
    "壬辰": "長流水", "癸巳": "長流水", "甲午": "砂中金", "乙未": "砂中金",
    "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金",
    "甲辰": "佛燈火", "乙巳": "佛燈火", "丙午": "天河水", "丁未": "天河水",
    "戊申": "大驛土", "己酉": "大驛土", "庚戌": "釵釧金", "辛亥": "釵釧金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水",
    "丙辰": "沙中土", "丁巳": "沙中土", "戊午": "天上火", "己未": "天上火",
    "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水"
}

STEM_PROPS = {
    '甲': {'element': '木', 'polarity': '陽'}, '乙': {'element': '木', 'polarity': '陰'},
    '丙': {'element': '火', 'polarity': '陽'}, '丁': {'element': '火', 'polarity': '陰'},
    '戊': {'element': '土', 'polarity': '陽'}, '己': {'element': '土', 'polarity': '陰'},
    '庚': {'element': '金', 'polarity': '陽'}, '辛': {'element': '金', 'polarity': '陰'},
    '壬': {'element': '水', 'polarity': '陽'}, '癸': {'element': '水', 'polarity': '陰'}
}

# 生剋關係定義
RELATION_MAP = {
    ('木', '木'): '同我', ('木', '火'): '我生', ('木', '土'): '我剋', ('木', '金'): '剋我', ('木', '水'): '生我',
    ('火', '火'): '同我', ('火', '土'): '我生', ('火', '金'): '我剋', ('火', '水'): '剋我', ('火', '木'): '生我',
    ('土', '土'): '同我', ('土', '金'): '我生', ('土', '水'): '我剋', ('土', '木'): '剋我', ('土', '火'): '生我',
    ('金', '金'): '同我', ('金', '水'): '我生', ('金', '木'): '我剋', ('金', '火'): '剋我', ('金', '土'): '生我',
    ('水', '水'): '同我', ('水', '木'): '我生', ('水', '火'): '我剋', ('水', '土'): '剋我', ('水', '金'): '生我',
}

# 納音與十神工具放在這裡
NAYIN_DATA = { ... } # 填入之前的 60 甲子資料
STEM_PROPS = { ... } # 填入陰陽五行定義
RELATION_MAP = { ... } # 填入五行生剋定義

def get_nayin(pillar):
    return NAYIN_DATA.get(pillar, "未知")

def get_ten_god(me_stem, target_stem):
    # ... 填入之前的十神判斷邏輯 ...

SHEN_SHA_DATA = {
    "天乙貴人": "命中最吉之神，逢凶化吉，易得貴人助。",
    "桃花": "主人緣佳、具魅力，異性緣豐富。",
    "驛馬": "主變動、外向、奔波，適合遠方發展。",
    "天醫": "主健康與醫學有緣，適合從事療癒相關行業。"
}

@dataclass
class Bazi:
    year: str; month: str; day: str; hour: str
    def __post_init__(self):
        self.stems = [self.year[0], self.month[0], self.day[0], self.hour[0]]
        self.branches = [self.year[1], self.month[1], self.day[1], self.hour[1]]

# --- 2. 核心邏輯 ---
def parse_text(text):
    matches = re.findall(r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]', text)
    return Bazi(matches[0], matches[1], matches[2], matches[3]) if len(matches) >= 4 else None

def calc_elements(bazi):
    scores = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for s in bazi.stems: scores[ELEMENTS_MAP[s]] += 1.0
    for b in bazi.branches:
        for i, h in enumerate(HIDDEN_STEMS[b]):
            scores[ELEMENTS_MAP[h]] += (1.0 if i == 0 else 0.3)
    return scores

def get_shen_sha(bazi):
    found = []
    # 簡易示例：日干查天乙
    mapping = {'甲':['丑','未'], '乙':['子','申'], '丙':['亥','酉'], '丁':['亥','酉'], '戊':['丑','未'], '己':['子','申'], '庚':['丑','未'], '辛':['午','寅'], '壬':['卯','巳'], '癸':['卯','巳']}
    targets = mapping.get(bazi.stems[2], [])
    for b in bazi.branches:
        if b in targets: found.append("天乙貴人"); break
    return list(set(found))

def get_ten_god(me_stem, target_stem):
    if me_stem == target_stem: return "日主" if target_stem == bazi.stems[2] else "比肩"
    
    me = STEM_PROPS[me_stem]
    target = STEM_PROPS[target_stem]
    
    relation = RELATION_MAP[(me['element'], target['element'])]
    same_polarity = (me['polarity'] == target['polarity'])
    
    gods = {
        '同我': {True: '比肩', False: '劫財'},
        '我生': {True: '食神', False: '傷官'},
        '我剋': {True: '偏財', False: '正財'},
        '剋我': {True: '七殺', False: '正官'},
        '生我': {True: '偏印', False: '正印'}
    }
    return gods[relation][same_polarity]

def get_nayin(pillar):
    """輸入柱別（如 '丙辰'），回傳納音字串"""
    return NAYIN_DATA.get(pillar, "未知")

def render_professional_chart(bazi):
    me = bazi.stems[2]  # 日主
    
    # 這裡將柱順序調整為圖片所示：時、日、月、年
    pillars = [
        {"name": "時柱", "p": bazi.hour, "s": bazi.stems[3], "b": bazi.branches[3]},
        {"name": "日柱", "p": bazi.day,  "s": bazi.stems[2], "b": bazi.branches[2]},
        {"name": "月柱", "p": bazi.month,"s": bazi.stems[1], "b": bazi.branches[1]},
        {"name": "年柱", "p": bazi.year, "s": bazi.stems[0], "b": bazi.branches[0]}
    ]

    html = f"""
    <style>
        .bazi-table {{ width: 100%; border: 1px solid #333; border-collapse: collapse; font-family: 'PMingLiU', 'Serif'; }}
        .bazi-table td {{ border: 1px solid #ccc; text-align: center; padding: 5px; }}
        .header-row {{ background-color: #f4f4f4; font-weight: bold; }}
        .stem-cell {{ font-size: 24px; font-weight: bold; }}
        .branch-cell {{ font-size: 24px; font-weight: bold; }}
        .ten-god {{ color: #2c3e50; font-size: 14px; }}
        .nayin {{ font-size: 12px; color: #666; background: #eee; }}
    </style>
    <table class="bazi-table">
        <tr class="header-row">
            <td>{get_ten_god(me, pillars[0]['s'])}</td>
            <td>命主</td>
            <td>{get_ten_god(me, pillars[1]['s'])}</td>
            <td>{get_ten_god(me, pillars[2]['s'])}</td>
            <td rowspan="2">主星</td>
        </tr>
        <tr>
            <td class="stem-cell">{pillars[0]['s']}</td>
            <td class="stem-cell">{pillars[1]['s']}</td>
            <td class="stem-cell">{pillars[2]['s']}</td>
            <td class="stem-cell">{pillars[3]['s']}</td>
        </tr>
        <tr>
            <td class="branch-cell">{pillars[0]['b']}</td>
            <td class="branch-cell">{pillars[1]['b']}</td>
            <td class="branch-cell">{pillars[2]['b']}</td>
            <td class="branch-cell">{pillars[3]['b']}</td>
            <td>八字</td>
        </tr>
        <tr style="font-size: 13px;">
            <td>{get_life_stage(me, pillars[0]['b'])}</td>
            <td>{get_life_stage(me, pillars[1]['b'])}</td>
            <td>{get_life_stage(me, pillars[2]['b'])}</td>
            <td>{get_life_stage(me, pillars[3]['b'])}</td>
            <td>運</td>
        </tr>
        <tr class="nayin">
            <td>{NAYIN_MAP.get(pillars[0]['p'], "")}</td>
            <td>{NAYIN_MAP.get(pillars[1]['p'], "")}</td>
            <td>{NAYIN_MAP.get(pillars[2]['p'], "")}</td>
            <td>{NAYIN_MAP.get(pillars[3]['p'], "")}</td>
            <td>納音</td>
        </tr>
    </table>
    """
    return html

def render_professional_chart(bazi):
    me_stem = bazi.stems[2]  # 取得日主
    
    # 定義四柱順序：時、日、月、年（符合圖片從左到右）
    pillar_data = [
        {"name": "時柱", "pillar": bazi.hour, "stem": bazi.stems[3]},
        {"name": "日柱", "pillar": bazi.day,  "stem": bazi.stems[2]},
        {"name": "月柱", "pillar": bazi.month, "stem": bazi.stems[1]},
        {"name": "年柱", "pillar": bazi.year,  "stem": bazi.stems[0]}
    ]

    # 計算每一柱的十神與納音，存入清單
    results = []
    for p in pillar_data:
        results.append({
            "ten_god": get_ten_god(me_stem, p["stem"]),
            "nayin": get_nayin(p["pillar"]),
            "stem": p["stem"],
            "branch": p["pillar"][1]
        })

    # 將計算好的結果塞進 HTML 表格中
    html = f"""
    <table class="bazi-table">
        <tr class="header-row">
            <td>{results[0]['ten_god']}</td>
            <td>命主</td> <td>{results[2]['ten_god']}</td>
            <td>{results[3]['ten_god']}</td>
            <td rowspan="2">主星</td>
        </tr>
        <tr class="stem-cell">
            <td>{results[0]['stem']}</td>
            <td>{results[1]['stem']}</td>
            <td>{results[2]['stem']}</td>
            <td>{results[3]['stem']}</td>
        </tr>
        <tr class="branch-cell">
            <td>{results[0]['branch']}</td>
            <td>{results[1]['branch']}</td>
            <td>{results[2]['branch']}</td>
            <td>{results[3]['branch']}</td>
            <td>八字</td>
        </tr>
        <tr class="nayin-row">
            <td>{results[0]['nayin']}</td>
            <td>{results[1]['nayin']}</td>
            <td>{results[2]['nayin']}</td>
            <td>{results[3]['nayin']}</td>
            <td>納音</td>
        </tr>
    </table>
    """
    return html

if bazi:
    st.subheader("📋 專業命盤")
    
    # 呼叫我們剛剛寫的 HTML 渲染函數
    chart_html = render_professional_chart(bazi)
    
    # 在 Streamlit 中顯示 HTML
    st.markdown(chart_html, unsafe_allow_html=True)
    
    st.divider()
    
    # 後面再接五行雷達圖與 AI 分析
    col_chart, col_ai = st.columns(2)
    # ... (其餘原有的代碼)

# --- 3. 網頁介面 (Streamlit) ---
st.set_page_config(page_title="AI 八字命盤系統", layout="wide")
st.title("🔮 AI 八字全方位解析系統")

with st.sidebar:
    st.header("設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    st.info("請輸入 API Key 以啟動 AI 點評功能。")

input_text = st.text_area("請貼上八字（如：辛亥年 庚子月 甲寅日 乙丑時）", "乙巳 戊寅 辛亥 壬辰")

if input_text:
    bazi = parse_text(input_text)
    if bazi:
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader("📋 命盤資訊")
            st.code(f"年：{bazi.year}  月：{bazi.month}  日：{bazi.day}  時：{bazi.hour}")
            ss = get_shen_sha(bazi)
            if ss:
                for s in ss:
                    explanation = SHEN_SHA_DATA.get(s, "尚無詳細解釋")
                    # 改用折疊面板取代彈窗
                    with st.expander(f"✅ 偵測到神煞：{s}", expanded=True):
                        st.write(explanation)
            else:
                st.info("目前格局未觸發特定神煞。")
            
        with col2:
            st.subheader("📊 五行能量")
            scores = calc_elements(bazi)
            fig = go.Figure(go.Scatterpolar(r=list(scores.values())+[list(scores.values())[0]], theta=list(scores.keys())+[list(scores.keys())[0]], fill='toself'))
            st.plotly_chart(fig, use_container_width=True)

        if api_key and st.button("🧙 大師批命"):
            genai.configure(api_key=AIzaSyBhZRfa01APz16GXkP1HjBIJv4waFrQjIM)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(f"請根據八字 {input_text} 與五行得分 {scores} 給予 200 字命理建議。")
            st.write(response.text)
    else:

        st.error("格式錯誤，請確保輸入包含四組干支。")




