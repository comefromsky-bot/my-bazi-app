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

@dataclass
class Bazi:
    year: str; month: str; day: str; hour: str
    def __post_init__(self):
        self.stems = [self.year[0], self.month[0], self.day[0], self.hour[0]]
        self.branches = [self.year[1], self.month[1], self.day[1], self.hour[1]]

# --- 2. 邏輯函數 ---
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

def render_professional_chart(bazi):
    me_stem = bazi.stems[2]
    pillar_data = [
        {"title": "年柱", "p": bazi.year, "s": bazi.stems[0], "b": bazi.branches[0]},
        {"title": "月柱", "p": bazi.month,"s": bazi.stems[1], "b": bazi.branches[1]},
        {"title": "日柱", "p": bazi.day,  "s": bazi.stems[2], "b": bazi.branches[2]},
        {"title": "時柱", "p": bazi.hour, "s": bazi.stems[3], "b": bazi.branches[3]}
    ]

    results = []
    for p in pillar_data:
        hidden_stems = HIDDEN_STEMS.get(p["b"], [])
        hidden_info = [{"stem": s, "god": get_ten_god(me_stem, s)} for s in hidden_stems]
        results.append({
            "title": p["title"],
            "ten_god": get_ten_god(me_stem, p["s"]) if p["title"] != "日柱" else "日主",
            "nayin": NAYIN_DATA.get(p["p"], "未知"),
            "stem": p["s"],
            "branch": p["b"],
            "hidden": hidden_info
        })

    html = f"""
    <div style="overflow-x: auto; margin: 20px 0;">
        <table style="width:100%; border-collapse: collapse; text-align: center; border: 2px solid #333; font-family: 'Microsoft JhengHei';">
            <tr style="background-color: #f1f1f1; font-weight: bold;">
                <td style="width: 100px; background: #eee; border: 1px solid #ddd; padding: 10px;">位置</td>
                <td style="border: 1px solid #ddd;">{results[0]['title']}</td>
                <td style="border: 1px solid #ddd;">{results[1]['title']}</td>
                <td style="border: 1px solid #ddd; background-color: #fff5f5;">{results[2]['title']}</td>
                <td style="border: 1px solid #ddd;">{results[3]['title']}</td>
            </tr>
            <tr>
                <td style="background: #eee; border: 1px solid #ddd; padding: 10px; font-weight: bold;">十神</td>
                <td style="border: 1px solid #ddd;">{results[0]['ten_god']}</td>
                <td style="border: 1px solid #ddd;">{results[1]['ten_god']}</td>
                <td style="border: 1px solid #ddd; color: #d63031; font-weight: bold;">{results[2]['ten_god']}</td>
                <td style="border: 1px solid #ddd;">{results[3]['ten_god']}</td>
            </tr>
            <tr style="font-size: 32px; font-weight: bold;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 10px; font-size: 16px;">天干</td>
                <td style="border: 1px solid #ddd;">{results[0]['stem']}</td>
                <td style="border: 1px solid #ddd;">{results[1]['stem']}</td>
                <td style="border: 1px solid #ddd; color: #d63031;">{results[2]['stem']}</td>
                <td style="border: 1px solid #ddd;">{results[3]['stem']}</td>
            </tr>
            <tr style="font-size: 32px; font-weight: bold;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 10px; font-size: 16px;">地支</td>
                <td style="border: 1px solid #ddd;">{results[0]['branch']}</td>
                <td style="border: 1px solid #ddd;">{results[1]['branch']}</td>
                <td style="border: 1px solid #ddd;">{results[2]['branch']}</td>
                <td style="border: 1px solid #ddd;">{results[3]['branch']}</td>
            </tr>
            <tr style="font-size: 14px; background-color: #fafafa;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 10px; font-weight: bold;">地支藏干</td>
                {"".join([f'<td style="border: 1px solid #ddd; padding: 5px;">{" ".join([h["stem"] for h in r["hidden"]])}</td>' for r in results])}
            </tr>
            <tr style="font-size: 12px; color: #666;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 10px; font-weight: bold;">藏干十神</td>
                {"".join([f'<td style="border: 1px solid #ddd; padding: 5px;">{" ".join([h["god"] for h in r["hidden"]])}</td>' for r in results])}
            </tr>
            <tr style="font-size: 13px; color: #777;">
                <td style="background: #eee; border: 1px solid #ddd; padding: 10px; font-weight: bold;">納音</td>
                <td style="border: 1px solid #ddd;">{results[0]['nayin']}</td>
                <td style="border: 1px solid #ddd;">{results[1]['nayin']}</td>
                <td style="border: 1px solid #ddd;">{results[2]['nayin']}</td>
                <td style="border: 1px solid #ddd;">{results[3]['nayin']}</td>
            </tr>
        </table>
    </div>
    """
    return html

# --- 3. Streamlit 介面 ---
st.set_page_config(page_title="專業 AI 八字命盤", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")

input_text = st.text_input("請輸入八字（例：乙巳 戊寅 辛亥 壬辰）", "乙巳 戊寅 辛亥 壬辰")

if input_text:
    matches = re.findall(r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]', input_text)
    if len(matches) >= 4:
        bazi = Bazi(matches[0], matches[1], matches[2], matches[3])
        st.markdown(render_professional_chart(bazi), unsafe_allow_html=True)
    else:
        st.error("請輸入正確的四柱干支格式。")
