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
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(f"請根據八字 {input_text} 與五行得分 {scores} 給予 200 字命理建議。")
            st.write(response.text)
    else:

        st.error("格式錯誤，請確保輸入包含四組干支。")


