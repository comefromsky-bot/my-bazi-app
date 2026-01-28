import streamlit as st
import datetime
import re
from dataclasses import dataclass

# 導入專業曆法庫
try:
    from lunar_python import Solar, Lunar
except ImportError:
    st.error("系統偵測到缺少庫，請執行： pip install --upgrade lunar-python")

# --- 1. 基礎資料定義 (全域變數最優先初始化) --- [cite: 1]
BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥'] [cite: 1]
STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸'] [cite: 1]

ELEMENTS_MAP = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土', '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水',
    '寅': '木', '卯': '木', '巳': '火', '午': '火', '申': '金', '酉': '金', '亥': '水', '子': '水', 
    '辰': '土', '戌': '土', '丑': '土', '未': '土'
} [cite: 1, 2]

STEM_PROPS = {
    '甲': {'element': '木', 'polarity': '陽'}, '乙': {'element': '木', 'polarity': '陰'},
    '丙': {'element': '火', 'polarity': '陽'}, '丁': {'element': '火', 'polarity': '陰'},
    '戊': {'element': '土', 'polarity': '陽'}, '己': {'element': '土', 'polarity': '陰'},
    '庚': {'element': '金', 'polarity': '陽'}, '辛': {'element': '金', 'polarity': '陰'},
    '壬': {'element': '水', 'polarity': '陽'}, '癸': {'element': '水', 'polarity': '陰'}
} [cite: 2]

RELATION_MAP = {
    ('木', '木'): '同我', ('木', '火'): '我生', ('木', '土'): '我剋', ('木', '金'): '剋我', ('木', '水'): '生我',
    ('火', '火'): '同我', ('火', '土'): '我生', ('火', '金'): '我剋', ('火', '水'): '剋我', ('火', '木'): '生我',
    ('土', '土'): '同我', ('土', '金'): '我生', ('土', '水'): '我剋', ('土', '木'): '剋我', ('土', '火'): '生我',
    ('金', '金'): '同我', ('金', '水'): '我生', ('金', '木'): '我剋', ('金', '火'): '剋我', ('金', '土'): '生我',
    ('水', '水'): '同我', ('水', '木'): '我生', ('水', '火'): '我剋', ('水', '土'): '剋我', ('水', '金'): '生我',
} [cite: 2, 3]

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
} [cite: 3, 4, 5]

HIDDEN_STEMS_DATA = {
    '子': [('癸', 100)], '丑': [('己', 60), ('癸', 30), ('辛', 10)],
    '寅': [('甲', 60), ('丙', 30), ('戊', 10)], '卯': [('乙', 100)],
    '辰': [('戊', 60), ('乙', 30), ('癸', 10)], '巳': [('丙', 60), ('庚', 30), ('戊', 10)],
    '午': [('丁', 70), ('己', 30)], '未': [('己', 60), ('丁', 30), ('乙', 10)],
    '申': [('庚', 60), ('壬', 30), ('戊', 10)], '酉': [('辛', 100)],
    '戌': [('戊', 60), ('辛', 30), ('丁', 10)], '亥': [('壬', 70), ('甲', 30)]
} [cite: 5, 6]

# --- 神煞解析資料庫 (對應 Excel) --- [cite: 6]
SHEN_SHA_CONFIG = {
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
    '三奇貴人': {'feature': '卓越、特立獨行、成就非凡。', 'effect': '思想超前，多為奇才或傳奇人物。'}
} [cite: 7]

@dataclass
class Bazi:
    year: str; month: str; day: str; hour: str; gender: str [cite: 8, 9]
    def __post_init__(self):
        self.stems = [self.year[0], self.month[0], self.day[0], self.hour[0]] [cite: 9]
        self.branches = [self.year[1], self.month[1], self.day[1], self.hour[1]] [cite: 9]
        self.pillars = [self.year, self.month, self.day, self.hour] [cite: 9]

# --- 2. 核心運算 ---

def get_ten_god(me_stem, target_stem):
    if not me_stem or not target_stem: return "" [cite: 10]
    me = STEM_PROPS[me_stem]; target = STEM_PROPS[target_stem] [cite: 10]
    relation = RELATION_MAP.get((me['element'], target['element'])) [cite: 10]
    return {'同我': {True: '比肩', False: '劫財'}, '我生': {True: '食神', False: '傷官'},
            '我剋': {True: '偏財', False: '正財'}, '剋我': {True: '七殺', False: '正官'},
            '生我': {True: '偏印', False: '正印'}}.get(relation, {}).get(me['polarity'] == target['polarity'], "未知") [cite: 10]

def get_nayin_element(pillar):
    full = NAYIN_DATA.get(pillar, "   ") [cite: 10]
    return full[-1] if len(full) >= 3 else "" [cite: 10]

def get_xun_kong(pillar):
    s_idx = STEMS.index(pillar[0])
    b_idx = BRANCHES.index(pillar[1])
    diff = (b_idx - s_idx) % 12
    return [BRANCHES[(diff - 2) % 12], BRANCHES[(diff - 1) % 12]]

# --- 3. 神煞引擎 ---

def get_55_shen_sha(bazi, pillar_idx):
    y_s, m_s, d_s, h_s = bazi.stems [cite: 11]
    y_b, m_b, d_b, h_b = bazi.branches [cite: 11]
    y_p, m_p, d_p, h_p = bazi.pillars [cite: 11]
    t_s, t_b, t_p = bazi.stems[pillar_idx], bazi.branches[pillar_idx], bazi.pillars[pillar_idx] [cite: 11]
    
    found = [] [cite: 11]

    # 貴人與祿刃 (天乙、天德、月德等)
    ty_map = {'甲':['丑','未'],'戊':['丑','未'],'庚':['丑','未'],'乙':['子','申'],'己':['子','申'],'丙':['亥','酉'],'丁':['亥','酉'],'壬':['卯','巳'],'癸':['卯','巳'],'辛':['午','寅']} [cite: 11]
    if t_b in ty_map.get(d_s, []) or t_b in ty_map.get(y_s, []): found.append("天乙貴人") [cite: 11]

    # 華蓋邏輯 (年日互查，排除自身) 
    hg_map = {'寅':'戌', '午':'戌', '戌':'戌', '巳':'丑', '酉':'丑', '丑':'丑', '申':'辰', '子':'辰', '辰':'辰', '亥':'未', '卯':'未', '未':'未'} [cite: 17]
    if pillar_idx != 0 and t_b == hg_map.get(y_b): found.append("華蓋") [cite: 18]
    if pillar_idx != 2 and t_b == hg_map.get(d_b): 
        if "華蓋" not in found: found.append("華蓋") [cite: 18]

    # 空亡與童子煞 [cite: 21, 25, 26]
    if t_b in get_xun_kong(d_p) or t_b in get_xun_kong(y_p): found.append("空亡") [cite: 21]
    
    y_ele = get_nayin_element(y_p) [cite: 25]
    if (m_b in ['寅','卯','辰','申','酉','戌'] and t_b in ['寅','子']) or (m_b in ['巳','午','未','亥','子','丑'] and t_b in ['卯','未','辰']): found.append("童子煞") [cite: 25]
    elif (y_ele in ['金','木'] and t_b in ['午','卯']) or (y_ele in ['水','火'] and t_b in ['酉','戌']) or (y_ele == '土' and t_b in ['辰','巳']):
        if "童子煞" not in found: found.append("童子煞") [cite: 25, 26]

    # 天羅地網與血刃 [cite: 22, 29]
    is_fire = (y_ele == '火' or y_s in ['丙', '丁']) [cite: 28]
    all_b = bazi.branches [cite: 28]
    if (is_fire or bazi.gender == "男") and ('戌' in all_b and '亥' in all_b) and t_b in ['戌', '亥']: found.append("天羅") [cite: 29]
    if (y_ele in ['水', '土'] or bazi.gender == "女") and ('辰' in all_b and '巳' in all_b) and t_b in ['辰', '巳']: found.append("地網") [cite: 29]

    xr_map = {'寅':'丑', '卯':'未', '辰':'寅', '巳':'申', '午':'卯', '未':'酉', '申':'辰', '酉':'戌', '戌':'巳', '亥':'亥', '子':'午', '丑':'子'} [cite: 22]
    if t_b == xr_map.get(m_b): found.append("血刃") [cite: 22]

    return sorted(list(set(found))) [cite: 30]

# --- 4. 深度交互分析引擎 ---

def analyze_all_interactions(bazi):
    s, b = bazi.stems, bazi.branches [cite: 30]
    p_names = ["年", "月", "日", "時"] [cite: 30]
    res = {"天干合衝": [], "地支合化": [], "地支刑衝害": []} [cite: 31]
    
    s_combos = {tuple(sorted(('甲','己'))): '甲己合土', tuple(sorted(('乙','庚'))): '乙庚合金', tuple(sorted(('丙','辛'))): '丙辛合水', tuple(sorted(('丁','壬'))): '丁壬合木', tuple(sorted(('戊','癸'))): '戊癸合火'} [cite: 31]
    s_clashes = {tuple(sorted(('甲','庚'))): '甲庚相衝', tuple(sorted(('乙','辛'))): '乙辛相衝', tuple(sorted(('丙','壬'))): '丙壬相衝', tuple(sorted(('丁','癸'))): '丁癸相衝'} [cite: 31]
    b_clashes = {tuple(sorted(('子','午'))): '子午相衝', tuple(sorted(('丑','未'))): '丑未相衝', tuple(sorted(('寅','申'))): '寅申相衝', tuple(sorted(('卯','酉'))): '卯酉相衝', tuple(sorted(('辰','戌'))): '辰戌相衝', tuple(sorted(('巳','亥'))): '巳亥相衝'} [cite: 31]
    semi_list = {tuple(sorted(('申','子'))): '申子半合水局', tuple(sorted(('子','辰'))): '子辰半合水局', tuple(sorted(('寅','午'))): '寅午半合火局', tuple(sorted(('午','戌'))): '午戌半合火局', tuple(sorted(('亥','卯'))): '亥卯半合木局', tuple(sorted(('卯','未'))): '卯未半合木局', tuple(sorted(('巳','酉'))): '巳酉半合金局', tuple(sorted(('酉','丑'))): '酉丑半合金局'} [cite: 31]

    for i in range(4): [cite: 31]
        for j in range(i+1, 4): [cite: 32]
            ps, pb = tuple(sorted((s[i], s[j]))), tuple(sorted((b[i], b[j]))) [cite: 32]
            if ps in s_combos: res["天干合衝"].append(f"{p_names[i]}{p_names[j]} {s_combos[ps]}") [cite: 32]
            if ps in s_clashes: res["天干合衝"].append(f"{p_names[i]}{p_names[j]} {s_clashes[ps]}") [cite: 32]
            if pb in semi_list: res["地支合化"].append(f"{p_names[i]}{p_names[j]} {semi_list[pb]}") [cite: 32]
            if pb in b_clashes: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b_clashes[pb]}") [cite: 33]
            if b[i] == b[j] and b[i] in ['辰', '午', '酉', '亥']: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b[i]}自刑") [cite: 33]
    return res [cite: 33]

# --- 5. 渲染 ---

def render_chart(bazi):
    me_stem = bazi.stems[2] [cite: 33]
    pillar_data = [{"title":"年柱","idx":0},{"title":"月柱","idx":1},{"title":"日柱","idx":2},{"title":"時柱","idx":3}] [cite: 33]
    results = [] [cite: 33]
    all_found_ss = set() [cite: 33]
    
    for p in pillar_data: [cite: 34]
        s_sha = get_55_shen_sha(bazi, p["idx"]) [cite: 34]
        all_found_ss.update(s_sha) [cite: 34]
        h = HIDDEN_STEMS_DATA.get(bazi.branches[p["idx"]], []) [cite: 34]
        results.append({
            "title":p["title"], "ten_god": get_ten_god(me_stem, bazi.stems[p["idx"]]) if p["title"] != "日柱" else "日主",
            "stem":bazi.stems[p["idx"]], "branch":bazi.branches[p["idx"]], "nayin":NAYIN_DATA.get(bazi.pillars[p["idx"]], ""),
            "h_stems":[x[0] for x in h], "h_details":[f"{x[0]}({get_ten_god(me_stem,x[0])}) {x[1]}%" for x in h],
            "shen_sha": s_sha
        }) [cite: 34, 35]

    l_fs, c_fs = "20px", "18px" [cite: 35]
    html = f"""<div style="overflow-x: auto; font-family: '標楷體'; text-align: center;"> [cite: 35, 36]
        <table style="width:100%; border-collapse: collapse; border: 2.5px solid #333;"> [cite: 37]
            <tr style="background: #f2f2f2; font-size: {l_fs}; font-weight: bold;"> [cite: 37, 38]
                <td style="width: 150px; background: #e8e8e8; border: 1px solid #ccc; padding: 15px;">位置</td> [cite: 39]
                {"".join([f'<td style="border: 1px solid #ccc;">{r["title"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {c_fs};">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">十神</td> [cite: 40]
                {"".join([f'<td style="border: 1px solid #ccc; color:#c0392b;">{r["ten_god"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 42px; font-weight: bold;"> [cite: 40, 41]
                <td style="background: #e8e8e8; border: 1px solid #ccc;">天干</td> [cite: 41, 42]
                {"".join([f'<td style="border: 1px solid #ccc; color:#c0392b;">{r["stem"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 42px; font-weight: bold;"> [cite: 42, 43]
                <td style="background: #e8e8e8; border: 1px solid #ccc;">地支</td> [cite: 43, 44]
                {"".join([f'<td style="border: 1px solid #ccc;">{r["branch"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 20px; font-weight: bold; color: #16a085;"> [cite: 44, 45]
                <td style="background: #e8e8e8; border: 1px solid #ccc;">地支藏干</td> [cite: 45, 46]
                {"".join([f'<td style="border: 1px solid #ccc; padding: 10px;">{"、".join(r["h_stems"])}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #555;"> [cite: 46, 47]
                <td style="background: #e8e8e8; border: 1px solid #ccc;">藏干比例</td> [cite: 47, 48]
                {"".join([f'<td style="border: 1px solid #ccc; padding: 10px;">{"<br>".join(r["h_details"])}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #8e44ad;"> [cite: 48, 49]
                <td style="background: #e8e8e8; border: 1px solid #ccc;">神煞</td> [cite: 49, 50]
                {"".join([f'<td style="border: 1px solid #ccc; font-weight: bold;">{"<br>".join(r["shen_sha"]) if r["shen_sha"] else "—"}</td>' for r in results])}
            </tr>
        </table>
    </div>""" [cite: 50]
    
    rels = analyze_all_interactions(bazi) [cite: 50]
    rel_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; text-align: left; padding: 25px; border: 2.5px solid #2c3e50; border-radius: 15px; background: #ffffff;"> [cite: 50, 51, 52]
        <h2 style="color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px;">📜 四柱干支交互關係詳解</h2> [cite: 52, 53]
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-top: 20px;"> [cite: 53, 54]
            <div><h4 style="color: #d35400;">【天干合衝】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['天干合衝']]) if rels['天干合衝'] else "<li>無顯著合衝</li>"}</ul></div>
            <div><h4 style="color: #27ae60;">【地支合化】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['地支合化']]) if rels['地支合化'] else "<li>無顯著合化</li>"}</ul><h4 style="color: #c0392b;">【地支刑衝害】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['地支刑衝害']]) if rels['地支刑衝害'] else "<li>無顯著刑衝害</li>"}</ul></div>
        </div>
    </div>""" [cite: 54]

    detail_rows = [] [cite: 54]
    for ss in sorted(list(all_found_ss)): [cite: 54]
        info = SHEN_SHA_CONFIG.get(ss, {'feature': '暫無資料', 'effect': '暫無資料'}) [cite: 55]
        detail_rows.append(f"""<tr><td style='border:1px solid #ccc;padding:10px;font-weight:bold;color:#8e44ad;width:150px;'>{ss}</td><td style='border:1px solid #ccc;padding:10px;'>{info['feature']}</td><td style='border:1px solid #ccc;padding:10px;color:#d35400;'>{info['effect']}</td></tr>""") [cite: 55]
    
    ss_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; text-align: center; padding: 25px; border: 2.5px solid #8e44ad; border-radius: 15px; background: #fdfbff;"> 
        <h2 style="color: #8e44ad; border-bottom: 2px solid #8e44ad; padding-bottom: 10px;">🔮 命盤神煞深度解析</h2> [cite: 57, 58]
        <table style="width:100%; border-collapse: collapse; margin-top: 15px;"> [cite: 59]
            <tr style="background: #f4f0ff; font-weight: bold;"> [cite: 59, 60]
                <td style="border: 1px solid #ccc; padding: 10px;">神煞名稱</td> [cite: 61]
                <td style="border: 1px solid #ccc; padding: 10px;">綜合特徵</td> [cite: 62]
                <td style="border: 1px solid #ccc; padding: 10px;">實際作用</td> [cite: 63]
            </tr>
            {"".join(detail_rows) if detail_rows else "<tr><td colspan='3' style='padding:20px;'>本命盤無特殊神煞解析</td></tr>"}
        </table>
    </div>""" [cite: 63]
    return html + rel_html + ss_html [cite: 63]

# --- 6. 主程式 ---
st.set_page_config(page_title="專業 AI 八字解析", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")

c1, c2, c3, c4 = st.columns(4)
with c1: birth_date = st.date_input("選擇日期", value=datetime.date(1990, 1, 1), min_value=datetime.date(1900, 1, 1), max_value=datetime.date(2100, 12, 31))
with c4: gender = st.radio("性別", ["男", "女"], horizontal=True)
birth_hour = st.selectbox("小時", range(24), format_func=lambda x: f"{x:02d}:00")

if st.button("🔮 開始精確排盤"): [cite: 63]
    solar = Solar.fromYmdHms(birth_date.year, birth_date.month, birth_date.day, birth_hour, 0, 0) [cite: 64]
    eight_char = solar.getLunar().getEightChar()
    y_p, m_p, d_p = eight_char.getYear(), eight_char.getMonth(), eight_char.getDay()
    h_p = getattr(eight_char, 'getHour', getattr(eight_char, 'getTime', lambda: "時柱錯誤"))()
    st.markdown(render_chart(Bazi(y_p, m_p, d_p, h_p, gender)), unsafe_allow_html=True) [cite: 64]
