import streamlit as st
import datetime
import re
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
    '寅': '木', '卯': '木', '巳': '火', '午': '火', '申': '金', '酉': '金', '亥': '水', '子': '水',
    '辰': '土', '戌': '土', '丑': '土', '未': '土'
}

STEM_PROPS = {
    '甲': {'element': '木', 'polarity': '陽'}, '乙': {'element': '木', 'polarity': '陰'},
    '丙': {'element': '火', 'polarity': '陽'}, '丁': {'element': '火', 'polarity': '陰'},
    '戊': {'element': '土', 'polarity': '陽'}, '己': {'element': '土', 'polarity': '陰'},
    '庚': {'element': '金', 'polarity': '陽'}, '辛': {'element': '金', 'polarity': '陰'},
    '壬': {'element': '水', 'polarity': '陽'}, '癸': {'element': '水', 'polarity': '陰'}
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

HIDDEN_STEMS_DATA = {
    '子': [('癸', 100)], '丑': [('己', 60), ('癸', 30), ('辛', 10)],
    '寅': [('甲', 60), ('丙', 30), ('戊', 10)], '卯': [('乙', 100)],
    '辰': [('戊', 60), ('乙', 30), ('癸', 10)], '巳': [('丙', 60), ('庚', 30), ('戊', 10)],
    '午': [('丁', 70), ('己', 30)], '未': [('己', 60), ('丁', 30), ('乙', 10)],
    '申': [('庚', 60), ('壬', 30), ('戊', 10)], '酉': [('辛', 100)],
    '戌': [('戊', 60), ('辛', 30), ('丁', 10)], '亥': [('壬', 70), ('甲', 30)]
}

SHEN_SHA_INFO = {
    '天乙貴人': {'feature': '命中最吉之神，代表高層次助力。', 'effect': '逢凶化吉，一生少病災，多得提拔。'},
    '天德貴人': {'feature': '積善、德行、寬厚、化煞。', 'effect': '減輕凶性，遇難呈祥，化解意外。'},
    '月德貴人': {'feature': '柔和、吉祥、長壽、處世無憂。', 'effect': '與天德並稱「二德」，主一生平安。'},
    '太極貴人': {'feature': '專注精神、直覺、研究心、宗教緣。', 'effect': '有神祕學、藝術天賦，晚景康泰。'},
    '文昌貴人': {'feature': '聰明才智、文筆、名氣、領悟力。', 'effect': '利求學考試、文書工作，利於成名。'},
    '國印貴人': {'feature': '正直忠厚、按部就班、權力象徵。', 'effect': '利於公職、公務員，代表官運與誠信。'},
    '學堂': {'feature': '智慧、書香、儒雅、金榜題名。', 'effect': '學習能力強，代表有學位與高學歷。'},
    '祿神': {'feature': '衣食、俸祿、事業基礎、身體根基。', 'effect': '主財祿豐盈，身弱者可增強氣勢。'},
    '驛馬': {'feature': '動力、變動、出國、升遷、不安現狀。', 'effect': '主遷徙轉職，動中求財，效率高。'},
    '桃花': {'feature': '魅力、社交、異性緣、審美。', 'effect': '利於人際公關，過多則招感情煩惱。'},
    '紅鸞': {'feature': '婚姻、喜事、浪漫、性格開朗。', 'effect': '主早婚、情緣美滿，一生喜氣多。'},
    '天喜': {'feature': '喜慶、生育、家庭、歡樂。', 'effect': '帶來偏財喜事，利於懷孕與添丁。'},
    '羊刃': {'feature': '剛烈、勇猛、競爭、爭奪。', 'effect': '身弱者助身，身強者易傷身破財。'},
    '空亡': {'feature': '虛幻、不實、落空、能量減半。', 'effect': '吉神遇空不吉，凶神遇空不凶。'},
    '天廚貴人': {'feature': '口福、福壽、經濟寬裕。', 'effect': '有食神之祿，代表富裕且懂得生活。'},
    '華蓋': {'feature': '藝術、宗教、孤獨、思想深度。', 'effect': '有才藝但清高，喜靜、好學佛道。'},
    '血刃': {'feature': '病災、手術、流血、意外。', 'effect': '應注意身體健康，易有血光之險。'},
    '天羅': {'feature': '困頓、束縛、官司、阻礙。', 'effect': '多主生活艱辛或法律糾紛，宜沉穩。'},
    '地網': {'feature': '困頓、束縛、官司、阻礙。', 'effect': '多主生活艱辛或法律糾紛，宜沉穩。'},
    '童子煞': {'feature': '感覺敏銳，多有神秘緣分，婚遲。', 'effect': '婚姻晚成、體弱、靈異感。'},
    '劫煞': {'feature': '徒勞、波折、損失、外傷。', 'effect': '處理事務多阻礙，容易因意外損財。'},
    '災煞': {'feature': '衝撞、牢獄、血光、不測。', 'effect': '多主凶險、官非，代表不穩定因素。'},
    '亡神': {'feature': '城府深、計謀、心理壓力。', 'effect': '處理得當為奇策，不得當為官非。'},
    '月德合': {'feature': '和諧、穩定、貴人扶助。', 'effect': '強化月德吉祥，化解人際矛盾。'},
    '天德合': {'feature': '輔助天德、增吉減凶。', 'effect': '化解災禍的力量倍增。'}
}

@dataclass
class Bazi:
    year: str; month: str; day: str; hour: str; gender: str; dayun: str = ""; liunian: str = ""
    def __post_init__(self):
        # 六柱順序：0:流年, 1:大運, 2:年, 3:月, 4:日, 5:時
        self.pillars = [self.liunian, self.dayun, self.year, self.month, self.day, self.hour]
        self.stems = [p[0] if (p and len(p)>0 and p[0] in STEMS) else "" for p in self.pillars]
        self.branches = [p[1] if (p and len(p)>1 and p[1] in BRANCHES) else "" for p in self.pillars]

# --- 2. 核心運算 (修正 KeyError) ---

def get_ten_god(me_stem, target_stem):
    # 防錯機制：若目標不是合法天干，回傳空字串
    if me_stem not in STEM_PROPS or target_stem not in STEM_PROPS:
        return ""
    
    me = STEM_PROPS[me_stem]
    target = STEM_PROPS[target_stem]
    
    rel_matrix = {
        ('木', '木'): '同我', ('木', '火'): '我生', ('木', '土'): '我剋', ('木', '金'): '剋我', ('木', '水'): '生我',
        ('火', '火'): '同我', ('火', '土'): '我生', ('火', '金'): '我剋', ('火', '水'): '剋我', ('火', '木'): '生我',
        ('土', '土'): '同我', ('土', '金'): '我生', ('土', '水'): '我剋', ('土', '木'): '剋我', ('土', '火'): '生我',
        ('金', '金'): '同我', ('金', '水'): '我生', ('金', '木'): '我剋', ('金', '火'): '剋我', ('金', '土'): '生我',
        ('水', '水'): '同我', ('水', '木'): '我生', ('水', '火'): '我剋', ('水', '土'): '剋我', ('水', '金'): '生我',
    }
    relation = rel_matrix.get((me['element'], target['element']))
    gods = {'同我': {True: '比肩', False: '劫財'}, '我生': {True: '食神', False: '傷官'},
            '我剋': {True: '偏財', False: '正財'}, '剋我': {True: '七殺', False: '正官'},
            '生我': {True: '偏印', False: '正印'}}
    return gods.get(relation, {}).get(me['polarity'] == target['polarity'], "未知")

def get_nayin_element(pillar):
    if not pillar or len(pillar) < 2: return ""
    full = NAYIN_DATA.get(pillar, "   ")
    return full[-1] if len(full) >= 3 else ""

def get_xun_kong(pillar):
    if not pillar or len(pillar) < 2 or pillar[0] not in STEMS: return []
    s_idx = STEMS.index(pillar[0])
    b_idx = BRANCHES.index(pillar[1])
    diff = (b_idx - s_idx) % 12
    return [BRANCHES[(diff - 2) % 12], BRANCHES[(diff - 1) % 12]]

# --- 3. 神煞引擎 ---

def get_55_shen_sha(bazi, pillar_idx):
    # 索引對應：2:年, 3:月, 4:日
    y_s, m_s, d_s = bazi.stems[2], bazi.stems[3], bazi.stems[4]
    y_b, m_b, d_b = bazi.branches[2], bazi.branches[3], bazi.branches[4]
    y_p, d_p = bazi.pillars[2], bazi.pillars[4]
    
    t_s, t_b = bazi.stems[pillar_idx], bazi.branches[pillar_idx]
    if not t_b: return []
    
    found = []
    # 貴人
    ty_map = {'甲':['丑','未'],'戊':['丑','未'],'庚':['丑','未'],'乙':['子','申'],'己':['子','申'],'丙':['亥','酉'],'丁':['亥','酉'],'壬':['卯','巳'],'癸':['卯','巳'],'辛':['午','寅']}
    if t_b in ty_map.get(d_s, []) or t_b in ty_map.get(y_s, []): found.append("天乙貴人")

    # 華蓋 (互查排除自身)
    hg_map = {'寅':'戌', '午':'戌', '戌':'戌', '巳':'丑', '酉':'丑', '丑':'丑', '申':'辰', '子':'辰', '辰':'辰', '亥':'未', '卯':'未', '未':'未'}
    if pillar_idx != 2 and t_b == hg_map.get(y_b): found.append("華蓋")
    if pillar_idx != 4 and t_b == hg_map.get(d_b): 
        if "華蓋" not in found: found.append("華蓋")

    # 天德/月德合
    ydh_map = {'寅': '辛', '午': '辛', '戌': '辛', '申': '丁', '子': '丁', '辰': '丁', '巳': '乙', '酉': '乙', '丑': '乙', '亥': '己', '卯': '己', '未': '己'}
    if t_s == ydh_map.get(m_b): found.append("月德合")
    tdh_map = {'寅': '壬', '卯': '巳', '辰': '丁', '巳': '丙', '午': '寅', '未': '己', '申': '戊', '酉': '亥', '戌': '辛', '亥': '庚', '子': '申', '丑': '乙'}
    if t_s == tdh_map.get(m_b) or t_b == tdh_map.get(m_b): found.append("天德合")

    # 血刃
    xr_map = {'寅':'丑', '卯':'未', '辰':'寅', '巳':'申', '午':'卯', '未':'酉', '申':'辰', '酉':'戌', '戌':'巳', '亥':'亥', '子':'午', '丑':'子'}
    if t_b == xr_map.get(m_b): found.append("血刃")

    return sorted(list(set(found)))

# --- 4. 交互分析與渲染 ---

def analyze_all_interactions(bazi):
    s, b = bazi.stems, bazi.branches
    p_names = {2:"年", 3:"月", 4:"日", 5:"時"}
    res = {"天干合衝": [], "地支合化": [], "地支刑衝害": []}
    
    s_combos = {tuple(sorted(('甲','己'))): '甲己合土', tuple(sorted(('乙','庚'))): '乙庚合金', tuple(sorted(('丙','辛'))): '丙辛合水', tuple(sorted(('丁','壬'))): '丁壬合木', tuple(sorted(('戊','癸'))): '戊癸合火'}
    b_6_combos = {tuple(sorted(('子','丑'))): '子丑合土', tuple(sorted(('寅','亥'))): '寅亥合木', tuple(sorted(('卯','戌'))): '卯戌合火', tuple(sorted(('辰','酉'))): '辰酉合金', tuple(sorted(('巳','申'))): '巳申合水', tuple(sorted(('午','未'))): '午未合火'}
    b_clashes = {tuple(sorted(('子','午'))): '子午相衝', tuple(sorted(('丑','未'))): '丑未相衝', tuple(sorted(('寅','申'))): '寅申相衝', tuple(sorted(('卯','酉'))): '卯酉相衝', tuple(sorted(('辰','戌'))): '辰戌相衝', tuple(sorted(('巳','亥'))): '巳亥相衝'}

    p_idx = [2, 3, 4, 5]
    for i in range(len(p_idx)):
        for j in range(i+1, len(p_idx)):
            idx1, idx2 = p_idx[i], p_idx[j]
            ps, pb = tuple(sorted((s[idx1], s[idx2]))), tuple(sorted((b[idx1], b[idx2])))
            if ps in s_combos: res["天干合衝"].append(f"{p_names[idx1]}{p_names[idx2]} {s_combos[ps]}")
            if pb in b_6_combos: res["地支合化"].append(f"{p_names[idx1]}{p_names[idx2]} {b_6_combos[pb]}")
            if pb in b_clashes: res["地支刑衝害"].append(f"{p_names[idx1]}{p_names[idx2]} {b_clashes[pb]}")
    return res

def render_chart(bazi):
    me_stem = bazi.stems[4]
    pillar_data = [{"title":"流年","idx":0}, {"title":"十年大運","idx":1}, {"title":"年柱","idx":2}, {"title":"月柱","idx":3}, {"title":"日柱","idx":4}, {"title":"時柱","idx":5}]
    results = []
    all_ss = set()
    for p in pillar_data:
        ss = get_55_shen_sha(bazi, p["idx"])
        all_ss.update(ss)
        h = HIDDEN_STEMS_DATA.get(bazi.branches[p["idx"]], [])
        results.append({
            "title":p["title"], "ten_god": get_ten_god(me_stem, bazi.stems[p["idx"]]) if p["idx"] != 4 else "日主",
            "stem":bazi.stems[p["idx"]], "branch":bazi.branches[p["idx"]], "nayin":NAYIN_DATA.get(bazi.pillars[p["idx"]], ""),
            "h_stems":[x[0] for x in h], "h_details":[f"{x[0]}({get_ten_god(me_stem,x[0])}) {x[1]}%" for x in h],
            "shen_sha": ss
        })

    html = f"""<div style="overflow-x: auto; font-family: '標楷體'; text-align: center;">
        <table style="width:100%; border-collapse: collapse; border: 2.5px solid #333;">
            <tr style="background: #f2f2f2; font-weight: bold;">
                <td style="width: 120px; background: #e8e8e8; border: 1px solid #ccc; padding: 10px;">位置</td>
                {"".join([f'<td style="border: 1px solid #ccc; background:{"#fff9e6" if r["title"] in ["流年","十年大運"] else "white"};">{r["title"]}</td>' for r in results])}
            </tr>
            <tr>
                <td style="background: #e8e8e8; border: 1px solid #ccc;">十神</td>
                {"".join([f'<td style="border: 1px solid #ccc; color:#c0392b;">{r["ten_god"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 38px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">天干</td>
                {"".join([f'<td style="border: 1px solid #ccc; color:#c0392b;">{r["stem"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 38px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">地支</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["branch"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 13px; color: #8e44ad;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">神煞</td>
                {"".join([f'<td style="border: 1px solid #ccc; font-weight: bold;">{"<br>".join(r["shen_sha"]) if r["shen_sha"] else "—"}</td>' for r in results])}
            </tr>
            <tr style="font-size: 13px; color: #1e3799; background: #f0f3ff;">
                <td style="background: #e1e7ff; border: 1px solid #ccc;">納音五行</td>
                {"".join([f'<td style="border: 1px solid #ccc; font-weight: bold;">{r["nayin"]}</td>' for r in results])}
            </tr>
        </table>
    </div>"""
    
    rels = analyze_all_interactions(bazi)
    rel_html = f"""<div style="margin-top: 30px; font-family: '標楷體'; text-align: left; padding: 20px; border: 2px solid #2c3e50; border-radius: 10px; background: white;">
        <h3 style="text-align: center; border-bottom: 2px solid #333;">📜 四柱干支交互關係 (命盤內部)</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div><h4 style="color: #d35400;">【天干合衝】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['天干合衝']]) if rels['天干合衝'] else "<li>無</li>"}</ul></div>
            <div><h4 style="color: #27ae60;">【地支合化】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['地支合化']]) if rels['地支合化'] else "<li>無</li>"}</ul><h4 style="color: #c0392b;">【地支刑衝害】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['地支刑衝害']]) if rels['地支刑衝害'] else "<li>無</li>"}</ul></div>
        </div>
    </div>"""

    detail_rows = []
    for ss in sorted(list(all_ss)):
        info = SHEN_SHA_INFO.get(ss, {'feature': '暫無資料', 'effect': '暫無資料'})
        detail_rows.append(f"<tr><td style='border:1px solid #ccc;padding:10px;font-weight:bold;color:#8e44ad;width:150px;'>{ss}</td><td style='border:1px solid #ccc;padding:10px;'>{info['feature']}</td><td style='border:1px solid #ccc;padding:10px;color:#d35400;'>{info['effect']}</td></tr>")
    
    ss_html = f"""<div style="margin-top: 30px; font-family: '標楷體'; text-align: center; padding: 20px; border: 2.5px solid #8e44ad; border-radius: 10px; background: #fdfbff;">
        <h3 style="color: #8e44ad; border-bottom: 2px solid #8e44ad;">🔮 命盤神煞深度解析 (含大運流年)</h3>
        <table style="width:100%; border-collapse: collapse; margin-top: 10px; background: white;">
            <tr style="background: #f4f0ff; font-weight: bold;"><td>神煞名稱</td><td>綜合特徵</td><td>實際作用</td></tr>
            {"".join(detail_rows) if detail_rows else "<tr><td colspan='3' style='padding:20px;'>本命盤無特殊神煞解析</td></tr>"}
        </table>
    </div>"""
    return html + rel_html + ss_html

# --- 5. 主程式 ---
st.set_page_config(page_title="專業 AI 八字解析系統", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")

c1, c2, c3, c4 = st.columns(4)
with c1: birth_date = st.date_input("出生日期", value=datetime.date(1990, 1, 1), min_value=datetime.date(1900, 1, 1))
with c2: analysis_year = st.number_input("分析年份 (流年)", 1900, 2100, 2024)
with c3: gender = st.radio("性別", ["男", "女"], horizontal=True)
with c4: birth_hour = st.selectbox("小時", range(24), format_func=lambda x: f"{x:02d}:00")

if st.button("🔮 開始精確排盤"):
    solar = Solar.fromYmdHms(birth_date.year, birth_date.month, birth_date.day, birth_hour, 0, 0)
    eight_char = solar.getLunar().getEightChar()
    liunian_pillar = Solar.fromYmd(analysis_year, 6, 1).getLunar().getYearInGanZhi()
    
    current_dayun = "— —"
    try:
        da_yun_obj = eight_char.getDaYun(1 if gender == "男" else 0)
        for p in da_yun_obj.getDaYunPeriods():
            if p.getStartYear() <= analysis_year <= p.getEndYear():
                current_dayun = p.getGanZhi(); break
    except: pass
            
    bazi_data = Bazi(year=eight_char.getYear(), month=eight_char.getMonth(), day=eight_char.getDay(), hour=getattr(eight_char, 'getHour', getattr(eight_char, 'getTime', lambda: " "))(), gender=gender, dayun=current_dayun, liunian=liunian_pillar)
    st.markdown(render_chart(bazi_data), unsafe_allow_html=True)
