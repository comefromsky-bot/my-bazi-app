import streamlit as st
import re
import plotly.graph_objects as go
from dataclasses import dataclass

# --- 1. 基礎資料與納音定義 ---
BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']

ELEMENTS_MAP = {
    '甲': '木', '乙': '木', '丙': '火', '丁': '火', '戊': '土', '己': '土', '庚': '金', '辛': '金', '壬': '水', '癸': '水',
    '寅': '木', '卯': '木', '巳': '火', '午': '火', '申': '金', '酉': '金', '亥': '水', '子': '水', '辰': '土', '戌': '土', '丑': '土', '未': '土'
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

# 納音五行查詢
def get_nayin(pillar):
    nayin_map = {
        '金': ['甲子','乙丑','壬寅','癸卯','庚辰','辛巳','甲午','乙未','壬申','癸酉','庚戌','辛亥'],
        '木': ['壬子','癸丑','庚寅','辛卯','戊辰','己巳','壬午','癸未','庚申','辛酉','戊戌','己亥'],
        '水': ['丙子','丁丑','甲寅','乙卯','壬辰','癸巳','丙午','丁開','甲申','乙酉','壬戌','癸亥'],
        '火': ['戊子','己丑','丙寅','丁卯','甲辰','乙巳','戊午','己未','丙申','丁酉','甲戌','乙亥'],
        '土': ['庚子','辛丑','戊寅','己卯','丙辰','丁巳','庚午','辛未','戊申','己酉','丙戌','丁亥']
    }
    for k, v in nayin_map.items():
        if pillar in v: return k
    return None

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
        self.pillars = [self.year, self.month, self.day, self.hour]

# --- 2. 核心運算函數 ---
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

def get_shen_sha_per_pillar(bazi, pillar_idx):
    # 獲取基準值
    year_branch = bazi.branches[0]
    month_branch = bazi.branches[1]
    day_stem = bazi.stems[2]
    day_branch = bazi.branches[2]
    
    # 獲取當前柱的值
    target_branch = bazi.branches[pillar_idx]
    target_stem = bazi.stems[pillar_idx]
    target_pillar = bazi.pillars[pillar_idx]
    
    found = []

    # --- 第一部分：年支基準 ---
    yi_ma = {'子':'巳', '丑':'寅', '寅':'亥', '卯':'申', '辰':'巳', '巳':'寅', '午':'亥', '未':'申', '申':'巳', '酉':'寅', '戌':'亥', '亥':'申'}
    if target_branch == yi_ma.get(year_branch): found.append("驛馬")
    
    wang_shen = {'子':'寅', '丑':'亥', '寅':'申', '卯':'巳', '辰':'寅', '巳':'亥', '午':'申', '未':'巳', '申':'寅', '酉':'亥', '戌':'申', '亥':'巳'}
    if target_branch == wang_shen.get(year_branch): found.append("亡神")
    
    jie_sha = {'子':'申', '丑':'巳', '寅':'寅', '卯':'亥', '辰':'申', '巳':'巳', '午':'寅', '未':'亥', '申':'申', '酉':'巳', '戌':'寅', '亥':'亥'}
    if target_branch == jie_sha.get(year_branch): found.append("劫煞")
    
    tao_hua = {'子':'酉', '丑':'午', '寅':'卯', '卯':'子', '辰':'酉', '巳':'午', '午':'卯', '未':'子', '申':'酉', '酉':'午', '戌':'卯', '亥':'子'}
    if target_branch == tao_hua.get(year_branch): found.append("桃花")
    
    gu_chen = {'子':'寅','丑':'寅','寅':'巳','卯':'巳','辰':'巳','巳':'申','午':'申','未':'申','申':'亥','酉':'亥','戌':'亥','亥':'寅'}
    if target_branch == gu_chen.get(year_branch): found.append("孤辰")
    
    gua_su = {'子':'戌','丑':'戌','寅':'丑','卯':'丑','辰':'丑','巳':'辰','午':'辰','未':'辰','申':'未','酉':'未','戌':'未','亥':'戌'}
    if target_branch == gua_su.get(year_branch): found.append("寡宿")
    
    jiang_xing = {'子':'子', '丑':'酉', '寅':'午', '卯':'卯', '辰':'子', '巳':'酉', '午':'午', '未':'卯', '申':'子', '酉':'酉', '戌':'午', '亥':'卯'}
    if target_branch == jiang_xing.get(year_branch): found.append("將星")
    
    huagai_zimu = {'子':'癸未', '丑':'壬辰', '寅':'乙丑', '卯':'甲戌', '辰':'癸未', '巳':'壬辰', '午':'乙丑', '未':'甲戌', '申':'癸未', '酉':'壬辰', '戌':'乙丑', '亥':'甲戌'}
    if target_pillar == huagai_zimu.get(year_branch): found.append("華蓋自墓")

    pan_an = {'子':'辰','丑':'丑','寅':'戌','卯':'未','辰':'辰','巳':'丑','午':'戌','未':'未','申':'辰','酉':'丑','戌':'戌','亥':'未'}
    if target_branch == pan_an.get(year_branch): found.append("攀鞍")

    yuan_chen = {'子':'午','丑':'亥','寅':'未','卯':'申','辰':'酉','巳':'戌','午':'子','未':'丑','申':'寅','酉':'卯','戌':'辰','亥':'巳'} # 元辰依陰陽干有別，此為簡化版
    if target_branch == yuan_chen.get(year_branch): found.append("元辰")

    gou_jiao = {'子':['卯','酉'],'丑':['辰','戌'],'寅':['巳','亥'],'卯':['午','子'],'辰':['未','丑'],'巳':['申','寅'],'午':['酉','卯'],'未':['戌','辰'],'申':['亥','巳'],'酉':['子','午'],'戌':['丑','未'],'亥':['寅','申']}
    if target_branch in gou_jiao.get(year_branch, []): found.append("勾絞")

    sang_men = {'子':'寅','丑':'卯','寅':'辰','卯':'巳','辰':'午','巳':'未','午':'申','未':'酉','申':'戌','酉':'亥','戌':'子','亥':'丑'}
    if target_branch == sang_men.get(year_branch): found.append("喪門")
    
    diao_ke = {'子':'戌','丑':'亥','寅':'子','卯':'丑','辰':'寅','巳':'卯','午':'辰','未':'巳','申':'午','酉':'未','戌':'申','亥':'酉'}
    if target_branch == diao_ke.get(year_branch): found.append("弔客")

    # --- 第二部分：月支基準 ---
    yue_de = {'寅':'甲', '卯':'壬', '辰':'庚', '巳':'丙', '午':'甲', '未':'壬', '申':'庚', '酉':'丙', '戌':'甲', '亥':'壬', '子':'庚', '丑':'丙'}
    if target_stem == yue_de.get(month_branch): found.append("月德")
    
    yue_de_he = {'寅':'己', '卯':'丁', '辰':'乙', '巳':'辛', '午':'己', '未':'丁', '申':'乙', '酉':'辛', '戌':'己', '亥':'丁', '子':'乙', '丑':'辛'}
    if target_stem == yue_de_he.get(month_branch): found.append("月德合")
    
    tian_she = {'寅':'戊寅', '卯':'戊寅', '辰':'戊寅', '巳':'甲午', '午':'甲午', '未':'甲午', '申':'戊申', '酉':'戊申', '戌':'戊申', '亥':'甲子', '子':'甲子', '丑':'甲子'}
    if target_pillar == tian_she.get(month_branch): found.append("天赦")
    
    tian_yi_month = {'寅':'丑', '卯':'寅', '辰':'卯', '巳':'辰', '午':'巳', '未':'午', '申':'未', '酉':'申', '戌':'酉', '亥':'戌', '子':'亥', '丑':'子'}
    if target_branch == tian_yi_month.get(month_branch): found.append("天醫")

    tian_de = {'寅':'丁','卯':'申','辰':'壬','巳':'辛','午':'亥','未':'甲','申':'癸','酉':'寅','戌':'丙','亥':'乙','子':'巳','丑':'庚'}
    if target_stem == tian_de.get(month_branch) or target_branch == tian_de.get(month_branch): found.append("天德")

    tian_xi = {'寅':'戌','卯':'戌','辰':'戌','巳':'丑','午':'丑','未':'丑','申':'辰','酉':'辰','戌':'辰','亥':'未','子':'未','丑':'未'}
    if target_branch == tian_xi.get(month_branch): found.append("天喜神")

    xiu_qi = {'寅':['丁','壬'], '卯':['丙','辛','甲','己'], '辰':['乙','庚'], '巳':['戊','癸'], '午':['丁','壬'], '未':['丙','辛','甲','己'], '申':['乙','庚'], '酉':['戊','癸'], '戌':['丁','壬'], '亥':['丙','辛','甲','己'], '子':['乙','庚'], '丑':['戊','癸']}
    if target_stem in xiu_qi.get(month_branch, []): found.append("秀氣")

    xue_ji = {'寅':'丑','卯':'未','辰':'寅','巳':'申','午':'卯','未':'戌','申':'亥','酉':'午','戌':'子','亥':'巳','子':'辰','丑':'酉'}
    if target_branch == xue_ji.get(month_branch): found.append("血忌")

    # --- 第三部分：日干基準 ---
    lu_shen = {'甲':'寅', '乙':'卯', '丙':'巳', '丁':'午', '戊':'巳', '己':'午', '庚':'申', '辛':'酉', '壬':'亥', '癸':'子'}
    if target_branch == lu_shen.get(day_stem): found.append("祿神")
    
    yang_ren = {'甲':'卯', '乙':'辰', '丙':'午', '丁':'未', '戊':'午', '己':'未', '庚':'酉', '辛':'戌', '壬':'子', '癸':'丑'}
    if target_branch == yang_ren.get(day_stem): found.append("陽刃")
    
    if target_pillar in ['壬辰', '庚辰', '庚戌', '戊戌']: found.append("魁罡")
    
    jin_yu_day = {'甲':'辰', '乙':'巳', '丙':'未', '丁':'申', '戊':'未', '己':'申', '庚':'戌', '辛':'亥', '壬':'丑', '癸':'寅'}
    if target_branch == jin_yu_day.get(day_stem): found.append("金轝")
    
    if target_pillar in ['甲辰', '乙亥', '丙辰', '丁酉', '戊午', '庚戌', '辛亥', '壬寅', '癸卯']: found.append("十靈日")
    
    hong_yan_day = {'甲':'午', '乙':'申', '丙':'寅', '丁':'未', '戊':'辰', '己':'辰', '庚':'戌', '辛':'酉', '壬':'子', '癸':'申'}
    if target_branch == hong_yan_day.get(day_stem): found.append("紅艷煞")
    
    if target_pillar in ['丙子', '丁丑', '戊寅', '辛卯', '壬辰', '癸巳', '丙午', '丁開', '戊申', '辛酉', '壬戌', '癸亥']: found.append("陰陽差錯")
    
    if target_pillar in ['甲辰', '乙巳', '丙申', '丁亥', '戊戌', '己丑', '庚辰', '辛巳', '壬申', '癸亥']: found.append("十惡大敗")

    yuan_xing = {'甲':'申','乙':'寅','丙':'亥','丁':'卯','戊':'戌','己':'丑','庚':'子','辛':'辰','壬':'酉','癸':'巳'}
    if target_branch == yuan_xing.get(day_stem): found.append("元星")

    tian_guan = {'甲':'午','乙':'未','丙':'辰','丁':'巳','戊':'寅','己':'卯','庚':'酉','辛':'亥','壬':'酉','癸':'戌'}
    if target_branch == tian_guan.get(day_stem): found.append("天官")

    sui_de = {'甲':'戊','乙':'甲','丙':'庚','丁':'丙','戊':'壬','己':'甲','庚':'甲','辛':'庚','壬':'丙','癸':'壬'}
    if target_stem == sui_de.get(day_stem): found.append("歲德")

    sui_de_he = {'甲':'癸','乙':'己','丙':'乙','丁':'辛','戊':'丁','己':'己','庚':'己','辛':'乙','壬':'辛','癸':'丁'}
    if target_stem == sui_de_he.get(day_stem): found.append("歲德合")

    tian_yuan_an_lu = {'丙':'巳','丁':'申','庚':'亥','辛':'寅'}
    if day_stem in tian_yuan_an_lu and target_branch == tian_yuan_an_lu.get(day_stem): found.append("天元暗祿")

    shi_da_kong_wang = {'甲':'申','乙':'申','丙':'申','丁':'申','戊':'申','己':'戌','庚':'戌','辛':'丑','壬':'丑','癸':'申'}
    if target_branch == shi_da_kong_wang.get(day_stem): found.append("十大空亡")

    guan_gui_xue_tang = {'甲':'申','乙':'巳','丙':'巳','丁':'申','戊':'申','己':'亥','庚':'亥','辛':'寅','壬':'寅','癸':'申'}
    if target_branch == guan_gui_xue_tang.get(day_stem): found.append("官貴學堂")

    # --- 第四部分：日支基準 (對時支) ---
    if pillar_idx == 3: # 如果是時柱
        tian_tu_sha = {'子':'丑','丑':'午','寅':'亥','卯':'戌','辰':'酉','巳':'申','午':'未','未':'子','申':'巳','酉':'辰','戌':'卯','亥':'寅'}
        if target_branch == tian_tu_sha.get(day_branch): found.append("天屠殺")
        
        ge_jiao_sha_1 = {'子':'子','丑':'亥','寅':'戌','卯':'酉','辰':'申','巳':'未','午':'午','未':'巳','申':'辰','酉':'卯','戌':'寅','亥':'丑'}
        if target_branch == ge_jiao_sha_1.get(day_branch): found.append("隔角殺")

    # --- 第五部分：納音基準 ---
    nayin_e = get_nayin(bazi.pillars[0]) # 以年柱納音為準
    if nayin_e:
        xue_tang_nayin = {'金':'己亥', '火':'丙寅', '木':'戊申', '水':'辛巳', '土':'甲申'}
        if target_pillar == xue_tang_nayin.get(nayin_e): found.append("學堂")
        
        ci_guan_nayin = {'金':'庚寅', '火':'乙巳', '木':'己亥', '水':'壬申', '土':'癸亥'}
        if target_pillar == ci_guan_nayin.get(nayin_e): found.append("詞館")
        
        zi_si_nayin = {'金':'壬午', '火':'丁酉', '木':'己卯', '水':'甲子', '土':'乙卯'}
        if target_pillar == zi_si_nayin.get(nayin_e): found.append("自死")

    return list(set(found))

# --- 3. 專業排盤渲染 ---
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
            "stem": p["s"],
            "branch": p["b"],
            "life_stage": LIFE_STAGES[me_stem][p["b"]],
            "nayin": get_nayin(p["p"]),
            "hidden": [{"stem": s, "weight": w, "god": get_ten_god(me_stem, s)} for s, w in hidden],
            "shen_sha": get_shen_sha_per_pillar(bazi, p["idx"]),
            "note": p["note"]
        })

    base_font = "'DFKai-SB', 'BiauKai', '標楷體', serif"
    l_fs = "20px"; c_fs = "18px"
    
    html = f"""
    <div style="overflow-x: auto; margin: 20px 0; font-family: {base_font}; text-align: center;">
        <table style="width:100%; border-collapse: collapse; text-align: center; border: 2.5px solid #333;">
            <tr style="background-color: #f2f2f2; font-weight: bold; font-size: {l_fs};">
                <td style="width: 140px; background: #e8e8e8; border: 1.5px solid #ccc; padding: 12px;">位置</td>
                {"".join([f'<td style="border: 1px solid #ccc; {"background:#fffafa;" if r["title"]=="日柱" else ""}">{r["title"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {l_fs}; color: #d35400; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc; padding: 12px; color: #333;">宮位意涵</td>
                {"".join([f'<td style="border: 1px solid #ccc; background: #fffcf5;">{r["note"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {c_fs};">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc; padding: 12px; font-weight: bold; font-size: {l_fs};">十神</td>
                {"".join([f'<td style="border: 1px solid #ccc; {"color:#c0392b;font-weight:bold;" if r["title"]=="日柱" else ""}">{r["ten_god"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 36px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc; padding: 15px; font-size: {l_fs};">天干</td>
                {"".join([f'<td style="border: 1px solid #ccc; {"color:#c0392b;" if r["title"]=="日柱" else ""}">{r["stem"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 36px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc; padding: 15px; font-size: {l_fs};">地支</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["branch"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 15px;">
                <td style="background: #e8e8e8; border: 1px solid #ccc; padding: 12px; font-weight: bold;">藏干十神比例</td>
                {"".join([f'''<td style="border: 1px solid #ccc; padding: 10px; vertical-align: middle;">
                    <div style="display: inline-block; text-align: center; width: 100%;">
                        {"".join([f'<div>{h["stem"]}({h["god"]}) {h["weight"]}%</div>' for h in r["hidden"]])}
                    </div>
                </td>''' for r in results])}
            </tr>
            <tr style="font-size: 16px; color: #2e86de; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc; padding: 12px;">十二運星</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["life_stage"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #8e44ad;">
                <td style="background: #e8e8e8; border: 1.5px solid #ccc; padding: 12px; font-weight: bold;">神煞系統</td>
                {"".join([f'<td style="border: 1px solid #ccc; font-weight: bold;">{"<br>".join(r["shen_sha"]) if r["shen_sha"] else "—"}</td>' for r in results])}
            </tr>
            <tr style="font-size: 14px; color: #666;">
                <td style="background: #e8e8e8; border: 1px solid #ccc; padding: 12px; font-weight: bold;">納音</td>
                {"".join([f'<td style="border: 1px solid #ccc;">{r["nayin"]}</td>' for r in results])}
            </tr>
        </table>
    </div>
    """
    return html

# --- 4. Streamlit 介面 ---
st.set_page_config(page_title="專業 AI 八字系統", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")

input_text = st.text_input("請輸入八字（例：乙巳 戊寅 辛亥 壬辰）", "乙巳 戊寅 辛亥 壬辰")

if input_text:
    matches = re.findall(r'[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]', input_text)
    if len(matches) >= 4:
        bazi = Bazi(matches[0], matches[1], matches[2], matches[3])
        st.markdown(render_professional_chart(bazi), unsafe_allow_html=True)
        
        st.divider()
        scores = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
        for s in bazi.stems: scores[ELEMENTS_MAP[s]] += 1.0
        for b in bazi.branches:
            for s, w in HIDDEN_STEMS_DATA[b]: scores[ELEMENTS_MAP[s]] += (w/100.0)
        
        fig = go.Figure(go.Scatterpolar(r=list(scores.values())+[list(scores.values())[0]], theta=list(scores.keys())+[list(scores.keys())[0]], fill='toself'))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("請確認格式：輸入四柱完整的干支。")
