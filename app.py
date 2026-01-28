import streamlit as st
import datetime
import re
import plotly.graph_objects as go
from dataclasses import dataclass

# 導入專業曆法庫 (請確保執行：pip install --upgrade lunar-python)
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
    ('金', '金'): '同我', ('金', '水'): '我生', ('金', '木'): '我剋', ('金', '火'): '我剋', ('金', '土'): '生我',
    ('水', '水'): '同我', ('水', '木'): '我生', ('水', '火'): '我剋', ('水', '土'): '剋我', ('水', '金'): '生我',
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

# --- 神煞解析資料庫 (對應 Excel 內容) ---
SHEN_SHA_INFO = {
    '天乙貴人': {'feature': '命中最吉之神，代表高層次助力。', 'effect': '逢凶化吉，一生少病災，多得提拔。'},
    '天德貴人': {'feature': '積善、德行、寬厚、化煞。', 'effect': '減輕凶性，遇難呈祥，化解意外。'},
    '月德貴人': {'feature': '柔和、吉祥、長壽、處世無憂。', 'effect': '與天德並稱「二德」，主一生平安。'},
    '太極貴人': {'feature': '專注精神、直覺、研究心、宗教緣。', 'effect': '有神祕學、藝術天賦，晚景康泰。'},
    '文昌貴人': {'feature': '聰明才智、文筆、名氣、領悟力。', 'effect': '利求學考試、文書工作，利於成名。'},
    '國印貴人': {'feature': '正直忠厚、按部就班、權力象徵。', 'effect': '利於公職、公務員，代表官運與誠信。'},
    '學堂': {'feature': '智慧、書香、儒雅、金榜題名。', 'effect': '學習能力強，代表有學位與高學歷。'},
    '詞館': {'feature': '口才、辭章、聲望、交際。', 'effect': '文章蓋世，在文壇或社交界享有盛譽。'},
    '祿神': {'feature': '衣食、俸祿、事業基礎、身體根基。', 'effect': '主財祿豐盈，身弱者可增強氣勢。'},
    '驛馬': {'feature': '動力、變動、出國、升遷、不安現狀。', 'effect': '主遷徙轉職，動中求財，效率高。'},
    '桃花': {'feature': '魅力、社交、異性緣、審美。', 'effect': '利於人際公關，過多則招感情煩惱。'},
    '紅鸞': {'feature': '婚姻、喜事、浪漫、性格開朗。', 'effect': '主早婚、情緣美滿，一生喜氣多。'},
    '天喜': {'feature': '喜慶、生育、家庭、歡樂。', 'effect': '帶來偏財喜事，利於懷孕與添丁。'},
    '羊刃': {'feature': '剛烈、勇猛、競爭、爭奪。', 'effect': '身弱者助身，身強者易傷身破財。'},
    '劫煞': {'feature': '徒勞、波折、損失、外傷。', 'effect': '處理事務多阻礙，容易因意外損財。'},
    '災煞': {'feature': '衝撞、牢獄、血光、不測。', 'effect': '多主凶險、官非，代表不穩定因素。'},
    '空亡': {'feature': '虛幻、不實、落空、能量減半。', 'effect': '吉神遇空不吉，凶神遇空不凶。'},
    '福星貴人': {'feature': '安泰、平穩、知足、多福氣。', 'effect': '一生衣食無慮，不求大富但求心安。'},
    '天廚貴人': {'feature': '口福、福壽、經濟寬裕。', 'effect': '有食神之祿，代表富裕且懂得生活。'},
    '德秀貴人': {'feature': '品學兼優、人中龍鳳、化戾氣。', 'effect': '為人清高，易得好名聲，遠離凶災。'},
    '天醫': {'feature': '醫藥、養生、哲學、康復力。', 'effect': '利醫療行業、心理學，能逢醫必治。'},
    '正詞館': {'feature': '學識正統、權威、名聲。', 'effect': '利官職提升，文書有權。'},
    '正學堂': {'feature': '學問純粹、正途功名。', 'effect': '主科甲之名，利於正當學術成就。'},
    '三奇貴人': {'feature': '卓越、特立獨行、成就非凡。', 'effect': '思想超前，多為奇才或傳奇人物。'},
    '將星': {'feature': '統帥能力、決斷力、威嚴。', 'effect': '代表職權、管理職，能得眾人服從。'},
    '華蓋': {'feature': '藝術、宗教、孤獨、思想深度。', 'effect': '有才藝但清高，喜靜、好學佛道。'},
    '魁罡': {'feature': '剛毅、果敢、威權、嫉惡如仇。', 'effect': '成功與失敗皆劇烈，事業心強。'},
    '飛刃': {'feature': '意外受傷、破財、爭執。', 'effect': '注意血光意外或刀傷手術。'},
    '血刃': {'feature': '病災、手術、流血、意外。', 'effect': '應注意身體健康，易有血光之險。'},
    '天羅': {'feature': '困頓、束縛、官司、阻礙。', 'effect': '多主生活艱辛或法律糾紛，宜沉穩。'},
    '地網': {'feature': '困頓、束縛、官司、阻礙。', 'effect': '多主生活艱辛或法律糾紛，宜沉穩。'},
    '童子煞': {'feature': '婚姻晚成、體弱、靈異感。', 'effect': '感覺敏銳，多有神秘緣分，婚遲。'},
    '喪門': {'feature': '哀傷、喪事、哭泣、情緒低。', 'effect': '流年遇之需注意長輩健康。'},
    '弔客': {'feature': '探病、弔喪、悲傷感。', 'effect': '影響心情，主親友間的憂慮之事。'}
}

@dataclass
class Bazi:
    year: str; month: str; day: str; hour: str; gender: str
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

def get_nayin_element(pillar):
    full = NAYIN_DATA.get(pillar, "   ")
    return full[-1] if len(full) >= 3 else ""

def get_xun_kong(pillar):
    s_idx = STEMS.index(pillar[0]); b_idx = BRANCHES.index(pillar[1])
    diff = (b_idx - s_idx) % 12
    return [BRANCHES[(diff - 2) % 12], BRANCHES[(diff - 1) % 12]]

# --- 3. 神煞辨識引擎 (修復華蓋變數錯誤) ---

def get_55_shen_sha(bazi, pillar_idx):
    y_s, m_b, d_s, y_b, d_b = bazi.stems[0], bazi.branches[1], bazi.stems[2], bazi.branches[0], bazi.branches[2]
    t_b = bazi.branches[pillar_idx]
    found = []

    # 貴人邏輯
    ty = {'甲':['丑','未'],'乙':['子','申'],'丙':['亥','酉'],'丁':['亥','酉'],'戊':['丑','未'],'己':['子','申'],'庚':['丑','未'],'辛':['午','寅'],'壬':['卯','巳'],'癸':['卯','巳']}
    if t_b in ty.get(d_s, []) or t_b in ty.get(y_s, []): found.append("天乙貴人")

    # 華蓋邏輯 (修復 shen_sha -> found 變數錯誤)
    hua_gai_map = {'寅':'戌', '午':'戌', '戌':'戌', '巳':'丑', '酉':'丑', '丑':'丑', '申':'辰', '子':'辰', '辰':'辰', '亥':'未', '卯':'未', '未':'未'}
    if pillar_idx != 0 and t_b == hua_gai_map.get(y_b): found.append("華蓋")
    if pillar_idx != 2 and t_b == hua_gai_map.get(d_b):
        if "華蓋" not in found: found.append("華蓋")

    # 天羅地網
    y_ele = get_nayin_element(bazi.pillars[0])
    is_fire = (y_ele == '火' or y_s in ['丙','丁'])
    is_water_earth = (y_ele in ['水','土'] or y_s in ['壬','癸','戊','己'])
    all_b = bazi.branches
    if (is_fire or bazi.gender=="男") and ('戌' in all_b and '亥' in all_b) and t_b in ['戌','亥']: found.append("天羅")
    if (is_water_earth or bazi.gender=="女") and ('辰' in all_b and '巳' in all_b) and t_b in ['辰','巳']: found.append("地網")

    # 童子煞
    spring_autumn, summer_winter = ['寅','卯','辰','申','酉','戌'], ['巳','午','未','亥','子','丑']
    if (m_b in spring_autumn and t_b in ['寅','子']) or (m_b in summer_winter and t_b in ['卯','未','辰']): found.append("童子煞")
    elif (y_ele in ['金','木'] and t_b in ['午','卯']) or (y_ele in ['水','火'] and t_b in ['酉','戌']) or (y_ele == '土' and t_b in ['辰','巳']):
        if "童子煞" not in found: found.append("童子煞")

    # 血刃
    xr_map = {'寅':'丑', '卯':'未', '辰':'寅', '巳':'申', '午':'卯', '未':'酉', '申':'辰', '酉':'戌', '戌':'巳', '亥':'亥', '子':'午', '丑':'子'}
    if t_b == xr_map.get(m_b): found.append("血刃")

    return sorted(list(set(found)))

# --- 4. 交互分析引擎 ---

def analyze_all_interactions(bazi):
    s, b = bazi.stems, bazi.branches
    p_names = ["年", "月", "日", "時"]
    res = {"天干": [], "地支合化": [], "地支刑衝害": []}
    s_combos = {tuple(sorted(('甲','己'))): '甲己合土', tuple(sorted(('乙','庚'))): '乙庚合金', tuple(sorted(('丙','辛'))): '丙辛合水', tuple(sorted(('丁','壬'))): '丁壬合木', tuple(sorted(('戊','癸'))): '戊癸合火'}
    s_clashes = {tuple(sorted(('甲','庚'))): '甲庚相衝', tuple(sorted(('乙','辛'))): '乙辛相衝', tuple(sorted(('丙','壬'))): '丙壬相衝', tuple(sorted(('丁','癸'))): '丁癸相衝'}
    b_6_combos = {tuple(sorted(('子','丑'))): '子丑合土', tuple(sorted(('寅','亥'))): '寅亥合木', tuple(sorted(('卯','戌'))): '卯戌合火', tuple(sorted(('辰','酉'))): '辰酉合金', tuple(sorted(('巳','申'))): '巳申合水', tuple(sorted(('午','未'))): '午未合火'}
    b_clashes = {tuple(sorted(('子','午'))): '子午相衝', tuple(sorted(('丑','未'))): '丑未相衝', tuple(sorted(('寅','申'))): '寅申相衝', tuple(sorted(('卯','酉'))): '卯酉相衝', tuple(sorted(('辰','戌'))): '辰戌相衝', tuple(sorted(('巳','亥'))): '巳亥相衝'}
    semi_list = {tuple(sorted(('申','子'))): '申子半合水局', tuple(sorted(('子','辰'))): '子辰半合水局', tuple(sorted(('寅','午'))): '寅午半合火局', tuple(sorted(('午','戌'))): '午戌半合火局', tuple(sorted(('亥','卯'))): '亥卯半合木局', tuple(sorted(('卯','未'))): '卯未半合木局', tuple(sorted(('巳','酉'))): '巳酉半合金局', tuple(sorted(('酉','丑'))): '酉丑半合金局'}
    for i in range(4):
        for j in range(i+1, 4):
            ps, pb = tuple(sorted((s[i], s[j]))), tuple(sorted((b[i], b[j])))
            if ps in s_combos: res["天干"].append(f"{p_names[i]}{p_names[j]} {s_combos[ps]}")
            if ps in s_clashes: res["天干"].append(f"{p_names[i]}{p_names[j]} {s_clashes[ps]}")
            if pb in b_6_combos: res["地支合化"].append(f"{p_names[i]}{p_names[j]} {b_6_combos[pb]}")
            if pb in semi_list: res["地支合化"].append(f"{p_names[i]}{p_names[j]} {semi_list[pb]}")
            if pb in b_clashes: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b_clashes[pb]}")
            if b[i] == b[j] and b[i] in ['辰', '午', '酉', '亥']: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b[i]}自刑")
    return res

# --- 5. 渲染 ---

def render_chart(bazi):
    me_stem = bazi.stems[2]
    pillar_data = [{"title":"年柱","idx":0},{"title":"月柱","idx":1},{"title":"日柱","idx":2},{"title":"時柱","idx":3}]
    results = []
    all_found_ss = set()
    for p in pillar_data:
        s_sha = get_55_shen_sha(bazi, p["idx"])
        all_found_ss.update(s_sha)
        h = HIDDEN_STEMS_DATA.get(bazi.branches[p["idx"]], [])
        results.append({
            "title":p["title"], "ten_god": get_ten_god(me_stem, bazi.stems[p["idx"]]) if p["title"] != "日柱" else "日主",
            "stem":bazi.stems[p["idx"]], "branch":bazi.branches[p["idx"]], "nayin":NAYIN_DATA.get(bazi.pillars[p["idx"]], ""),
            "h_stems":[x[0] for x in h], "h_details":[f"{x[0]}({get_ten_god(me_stem,x[0])}) {x[1]}%" for x in h],
            "shen_sha": s_sha
        })

    l_fs, c_fs = "20px", "18px"
    html = f"""<div style="overflow-x: auto; font-family: '標楷體'; text-align: center;">
        <table style="width:100%; border-collapse: collapse; border: 2.5px solid #333;">
            <tr style="background: #f2f2f2; font-size: {l_fs}; font-weight: bold;">
                <td style="width: 150px; background: #e8e8e8; border: 1px solid #ccc; padding: 15px;">位置</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["title"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {c_fs};">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">十神</td>
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
            <tr style="font-size: 20px; font-weight: bold; color: #16a085;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">地支藏干</td>
                {"".join([f'<td style="border: 1px solid #ccc; padding: 10px;">{"、".join(r["h_stems"])}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #555;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">藏干比例</td>
                {"".join([f'<td style="border: 1px solid #ccc; padding: 10px;">{"<br>".join(r["h_details"])}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #8e44ad;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">神煞</td>
                {"".join([f'<td style="border: 1px solid #ccc; font-weight: bold;">{"<br>".join(r["shen_sha"]) if r["shen_sha"] else "—"}</td>' for r in results])}
            </tr>
        </table>
    </div>"""
    
    rels = analyze_all_interactions(bazi)
    rel_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; text-align: left; padding: 25px; border: 2.5px solid #2c3e50; border-radius: 15px; background: #ffffff;">
        <h2 style="color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px;">📜 四柱干支交互關係詳解</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px;">
            <div><h4 style="color: #d35400;">【天干合衝】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['天干']]) if rels['天干'] else "<li>無顯著合衝</li>"}</ul></div>
            <div><h4 style="color: #27ae60;">【地支合化】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['地支合化']]) if rels['地支合化'] else "<li>無顯著合化</li>"}</ul><h4 style="color: #c0392b;">【地支刑衝害】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['地支刑衝害']]) if rels['地支刑衝害'] else "<li>無顯著刑衝害</li>"}</ul></div>
        </div>
    </div>"""

    # --- 新增：神煞深度解析區塊 ---
    detail_rows = []
    for ss in sorted(list(all_found_ss)):
        info = SHEN_SHA_INFO.get(ss, {'feature': '暫無資料', 'effect': '暫無資料'})
        detail_rows.append(f"""<tr><td style='border:1px solid #ccc;padding:10px;font-weight:bold;color:#8e44ad;'>{ss}</td><td style='border:1px solid #ccc;padding:10px;'>{info['feature']}</td><td style='border:1px solid #ccc;padding:10px;color:#d35400;'>{info['effect']}</td></tr>""")
    
    ss_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; text-align: center; padding: 25px; border: 2.5px solid #8e44ad; border-radius: 15px; background: #fdfbff;">
        <h2 style="color: #8e44ad; border-bottom: 2px solid #8e44ad; padding-bottom: 10px;">🔮 命盤神煞深度解析</h2>
        <table style="width:100%; border-collapse: collapse; margin-top: 15px;">
            <tr style="background: #f4f0ff; font-weight: bold;">
                <td style="border: 1px solid #ccc; padding: 10px; width: 150px;">神煞名稱</td>
                <td style="border: 1px solid #ccc; padding: 10px;">綜合特徵</td>
                <td style="border: 1px solid #ccc; padding: 10px;">實際作用</td>
            </tr>
            {"".join(detail_rows) if detail_rows else "<tr><td colspan='3' style='padding:20px;'>本命盤無特殊神煞解析</td></tr>"}
        </table>
    </div>"""
    return html + rel_html + ss_html

# --- 6. 主程式 ---
st.set_page_config(page_title="專業 AI 八字解析", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")
c1, c2, c3, c4 = st.columns(4)
with c1: birth_date = st.date_input("選擇日期", value=datetime.date(1990, 1, 1), min_value=datetime.date(1900, 1, 1))
with c4: gender = st.radio("性別", ["男", "女"], horizontal=True)
birth_hour = st.selectbox("小時", range(24), format_func=lambda x: f"{x:02d}:00")

if st.button("🔮 開始精確分析"):
    solar = Solar.fromYmdHms(birth_date.year, birth_date.month, birth_date.day, birth_hour, 0, 0)
    eight_char = solar.getLunar().getEightChar()
    y_p, m_p, d_p = eight_char.getYear(), eight_char.getMonth(), eight_char.getDay()
    h_p = getattr(eight_char, 'getHour', getattr(eight_char, 'getTime', lambda: "時柱錯誤"))()
    st.markdown(render_chart(Bazi(y_p, m_p, d_p, h_p, gender)), unsafe_allow_html=True)
