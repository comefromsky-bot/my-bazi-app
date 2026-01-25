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

NAYIN_DATA = {
    # 木屬性
    "戊辰": "大林木", "己巳": "大林木", "壬午": "楊柳木", "癸未": "楊柳木",
    "庚寅": "松柏木", "辛卯": "松柏木", "戊戌": "平地木", "己亥": "平地木",
    "壬子": "桑柘木", "癸丑": "桑柘木", "庚申": "石榴木", "辛酉": "石榴木",
    
    # 火屬性
    "丙寅": "爐中火", "丁卯": "爐中火", "甲戌": "山頭火", "乙亥": "山頭火",
    "戊子": "霹靂火", "己丑": "霹靂火", "丙申": "山下火", "丁酉": "山下火",
    "甲辰": "佛燈火", "乙巳": "佛燈火", "戊午": "天上火", "己未": "天上火",
    
    # 土屬性
    "庚午": "路旁土", "辛未": "路旁土", "戊寅": "城頭土", "己卯": "城頭土",
    "丙戌": "屋上土", "丁亥": "屋上土", "庚子": "壁上土", "辛丑": "壁上土",
    "丙辰": "沙中土", "丁巳": "沙中土", "戊申": "大驛土", "己酉": "大驛土",
    
    # 金屬性
    "甲子": "海中金", "乙丑": "海中金", "壬申": "劍鋒金", "癸酉": "劍鋒金",
    "庚辰": "白蠟金", "辛巳": "白蠟金", "甲午": "砂中金", "乙未": "砂中金",
    "壬寅": "金箔金", "癸卯": "金箔金", "庚戌": "釵釧金", "辛亥": "釵釧金",
    
    # 水屬性
    "丙子": "澗下水", "丁丑": "澗下水", "甲申": "泉中水", "乙酉": "泉中水",
    "壬辰": "長流水", "癸巳": "長流水", "丙午": "天河水", "丁未": "天河水",
    "甲寅": "大溪水", "乙卯": "大溪水", "壬戌": "大海水", "癸亥": "大海水"
}
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

# --- 2. 核心邏輯函數 ---

def get_ten_god(me_stem, target_stem):
    if not me_stem or not target_stem: return ""
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
    return NAYIN_DATA.get(pillar, "未知")

def parse_text(text):
    matches = re.findall(r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]', text)
    return Bazi(matches[0], matches[1], matches[2], matches[3]) if len(matches) >= 4 else None

def calc_elements(bazi):
    scores = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for s in bazi.stems: scores[ELEMENTS_MAP[s]] += 1.0
    for b in bazi.branches:
        hidden = HIDDEN_STEMS.get(b, [])
        for i, h in enumerate(hidden):
            scores[ELEMENTS_MAP[h]] += (1.0 if i == 0 else 0.3)
    return scores

def get_shen_sha(bazi):
    found = []
    mapping = {'甲':['丑','未'], '乙':['子','申'], '丙':['亥','酉'], '丁':['亥','酉'], '戊':['丑','未'], '己':['子','申'], '庚':['丑','未'], '辛':['午','寅'], '壬':['卯','巳'], '癸':['卯','巳']}
    targets = mapping.get(bazi.stems[2], [])
    for b in bazi.branches:
        if b in targets: 
            found.append("天乙貴人")
            break
    return list(set(found))

# --- 3. 專業排盤渲染 ---

def render_professional_chart(bazi):
    me_stem = bazi.stems[2]
    # 定義四柱：時、日、月、年
    pillar_data = [
        {"name": "時柱", "p": bazi.hour, "s": bazi.stems[3], "b": bazi.branches[3]},
        {"name": "日柱", "p": bazi.day,  "s": bazi.stems[2], "b": bazi.branches[2]},
        {"name": "月柱", "p": bazi.month,"s": bazi.stems[1], "b": bazi.branches[1]},
        {"name": "年柱", "p": bazi.year, "s": bazi.stems[0], "b": bazi.branches[0]}
    ]

    results = []
    for p in pillar_data:
        results.append({
            "ten_god": get_ten_god(me_stem, p["s"]) if p["name"] != "日柱" else "命主",
            "nayin": get_nayin(p["p"]),
            "stem": p["s"],
            "branch": p["b"]
        })

    html = f"""
    <div style="overflow-x: auto; margin-bottom: 20px;">
        <table style="width:100%; border-collapse: collapse; text-align: center; border: 2px solid #333; font-family: 'Microsoft JhengHei';">
            <tr style="background-color: #f8f9fa; font-weight: bold;">
                <td style="padding: 10px; border: 1px solid #ddd;">{results[0]['ten_god']}</td>
                <td style="padding: 10px; border: 1px solid #ddd; color: #d63031;">{results[1]['ten_god']}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{results[2]['ten_god']}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{results[3]['ten_god']}</td>
                <td rowspan="2" style="background: #eee; width: 60px; border: 1px solid #ddd;">主星</td>
            </tr>
            <tr style="font-size: 28px; font-weight: bold;">
                <td style="padding: 15px; border: 1px solid #ddd;">{results[0]['stem']}</td>
                <td style="padding: 15px; border: 1px solid #ddd; background-color: #fffaf0;">{results[1]['stem']}</td>
                <td style="padding: 15px; border: 1px solid #ddd;">{results[2]['stem']}</td>
                <td style="padding: 15px; border: 1px solid #ddd;">{results[3]['stem']}</td>
            </tr>
            <tr style="font-size: 28px; font-weight: bold;">
                <td style="padding: 15px; border: 1px solid #ddd;">{results[0]['branch']}</td>
                <td style="padding: 15px; border: 1px solid #ddd; background-color: #fffaf0;">{results[1]['branch']}</td>
                <td style="padding: 15px; border: 1px solid #ddd;">{results[2]['branch']}</td>
                <td style="padding: 15px; border: 1px solid #ddd;">{results[3]['branch']}</td>
                <td style="font-size: 16px; background: #eee; border: 1px solid #ddd;">八字</td>
            </tr>
            <tr style="font-size: 14px; color: #555;">
                <td style="padding: 8px; border: 1px solid #ddd;">{results[0]['nayin']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{results[1]['nayin']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{results[2]['nayin']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{results[3]['nayin']}</td>
                <td style="background: #eee; border: 1px solid #ddd;">納音</td>
            </tr>
        </table>
    </div>
    """
    return html

# --- 4. Streamlit 網頁介面 ---
st.set_page_config(page_title="AI 八字命盤系統", layout="wide")
st.title("🔮 AI 八字全方位解析系統")

with st.sidebar:
    st.header("⚙️ 系統設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    st.info("API Key 用於啟動『大師批命』AI 點評功能。")

input_text = st.text_input("請輸入八字（例：乙巳 戊寅 辛亥 壬辰）", "乙巳 戊寅 辛亥 壬辰")

if input_text:
    bazi = parse_text(input_text)
    if bazi:
        # 顯示專業命盤
        st.subheader("📋 專業命盤資訊")
        chart_html = render_professional_chart(bazi)
        st.markdown(chart_html, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("✨ 神煞分析")
            ss_list = get_shen_sha(bazi)
            if ss_list:
                for s in ss_list:
                    with st.expander(f"✅ 偵測到：{s}", expanded=True):
                        st.write(SHEN_SHA_DATA.get(s, "尚無詳細解釋"))
            else:
                st.info("目前格局未觸發特定神煞。")
        
        with col2:
            st.subheader("📊 五行能量分佈")
            scores = calc_elements(bazi)
            categories = list(scores.keys())
            values = list(scores.values())
            
            fig = go.Figure(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself',
                line=dict(color='#ff4b4b')
            ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(values)+1])), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        
        # AI 點評區
        if st.button("🧙 啟動 AI 大師批命"):
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    prompt = f"你是一位資深命理大師，請根據八字「{input_text}」與五行強弱分佈 {scores}，提供約 300 字的性格、事業與運勢建議。請用繁體中文回覆。"
                    
                    with st.spinner("大師正在夜觀星象..."):
                        response = model.generate_content(prompt)
                        st.success("### 🔮 大師點評")
                        st.write(response.text)
                except Exception as e:
                    st.error(f"AI 呼叫失敗：{str(e)}")
            else:
                st.warning("請先在左側邊欄輸入 API Key 才能使用 AI 功能。")
    else:
        st.error("輸入格式有誤，請確保輸入包含四組干支（如：乙巳 戊寅 辛亥 壬辰）。")





