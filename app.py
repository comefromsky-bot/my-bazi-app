import streamlit as st
import re
import datetime
import plotly.graph_objects as go
from dataclasses import dataclass

# 導入曆法庫 (請確保已安裝：pip install lunar-python)
try:
    from lunar_python import Solar, Lunar
except ImportError:
    st.error("請確認已安裝/更新轉換庫： pip install --upgrade lunar-python")

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

STEM_PROPS = {
    '甲': {'element': '木', 'polarity': '陽'}, '乙': {'element': '木', 'polarity': '陰'},
    '丙': {'element': '火', 'polarity': '陽'}, '丁': {'element': '火', 'polarity': '陰'},
    '戊': {'element': '土', 'polarity': '陽'}, '己': {'element': '土', 'polarity': '陰'},
    '庚': {'element': '金', 'polarity': '陽'}, '辛': {'element': '金', 'polarity': '陰'},
    '壬': {'element': '水', 'polarity': '陽'}, '癸': {'element': '水', 'polarity': '陰'}
}

# 修正 RELATION_MAP (火金為我剋)
RELATION_MAP = {
    ('木', '木'): '同我', ('木', '火'): '我生', ('木', '土'): '我剋', ('木', '金'): '剋我', ('木', '水'): '生我',
    ('火', '火'): '同我', ('火', '土'): '我生', ('火', '金'): '我剋', ('火', '水'): '剋我', ('火', '木'): '生我',
    ('土', '土'): '同我', ('土', '金'): '我生', ('土', '水'): '我剋', ('土', '木'): '剋我', ('土', '火'): '生我',
    ('金', '金'): '同我', ('金', '水'): '我生', ('金', '木'): '我剋', ('金', '火'): '剋我', ('金', '土'): '生我',
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

# --- 3. 完整 55 神煞引擎 ---

def get_55_shen_sha(bazi, pillar_idx):
    y_s, m_s, d_s, h_s = bazi.stems
    y_b, m_b, d_b, h_b = bazi.branches
    y_p, m_p, d_p, h_p = bazi.pillars
    t_s, t_b, t_p = bazi.stems[pillar_idx], bazi.branches[pillar_idx], bazi.pillars[pillar_idx]
    
    found = []

    # 1. 天乙貴人
    ty_map = {'甲':['丑','未'],'戊':['丑','未'],'庚':['丑','未'],'乙':['子','申'],'己':['子','申'],'丙':['亥','酉'],'丁':['亥','酉'],'壬':['卯','巳'],'癸':['卯','巳'],'辛':['午','寅']}
    if t_b in ty_map.get(d_s, []) or t_b in ty_map.get(y_s, []): found.append("天乙貴人")

    # 2. 天德 / 3. 月德
    td_map = {'寅':'丁','卯':'申','辰':'壬','巳':'辛','午':'亥','未':'甲','申':'癸','酉':'寅','戌':'丙','亥':'乙','子':'巳','丑':'庚'}
    yd_map = {'寅':'丙','午':'丙','戌':'丙','申':'壬','子':'壬','辰':'壬','亥':'甲','卯':'甲','未':'甲','巳':'庚','酉':'庚','丑':'庚'}
    if t_s == td_map.get(m_b) or t_b == td_map.get(m_b): found.append("天德貴人")
    if t_s == yd_map.get(m_b): found.append("月德貴人")

    # 4. 太極 / 5. 文昌 / 6. 國印
    tj_map = {'甲':['子','午'],'乙':['子','午'],'丙':['卯','酉'],'丁':['卯','酉'],'戊':['辰','戌','丑','未'],'己':['辰','戌','丑','未'],'庚':['寅','亥'],'辛':['寅','亥'],'壬':['巳','申'],'癸':['巳','申']}
    wc_map = {'甲':'巳','乙':'午','丙':'申','丁':'酉','戊':'申','己':'酉','庚':'亥','辛':'子','壬':'寅','癸':'卯'}
    gy_map = {'甲':'戌','乙':'亥','丙':'丑','丁':'寅','戊':'丑','己':'寅','庚':'辰','辛':'巳','壬':'未','癸':'申'}
    if t_b in tj_map.get(d_s, []) or t_b in tj_map.get(y_s, []): found.append("太極貴人")
    if t_b == wc_map.get(d_s) or t_b == wc_map.get(y_s): found.append("文昌貴人")
    if t_b == gy_map.get(d_s) or t_b == gy_map.get(y_s): found.append("國印貴人")

    # 7. 學堂 / 8. 詞館 / 22. 正詞館 / 23. 正學堂
    ny_d_ele = get_nayin_element(d_p)
    if t_b == {'金':'巳','木':'亥','水':'申','火':'寅','土':'申'}.get(ny_d_ele):
        found.append("學堂")
        if get_ten_god(d_s, t_s) == "偏印": found.append("正學堂")
    if t_p == {'甲':'庚寅','乙':'乙巳','丙':'乙巳','丁':'庚寅','戊':'丁巳','己':'庚申','庚':'壬申','辛':'壬子','壬':'壬寅','癸':'癸巳'}.get(d_s):
        found.append("詞館")
        if get_ten_god(d_s, t_s) in ["正官", "正印"]: found.append("正詞館")

    # 9. 祿神 / 14. 羊刃 / 30. 飛刃
    lu = {'甲':'寅','乙':'卯','丙':'巳','丁':'午','戊':'巳','己':'午','庚':'申','辛':'酉','壬':'亥','癸':'子'}
    yr = {'甲':'卯','乙':'寅','丙':'午','丁':'巳','戊':'午','己':'巳','庚':'酉','辛':'申','壬':'子','癸':'亥'}
    if t_b == lu.get(d_s): found.append("祿神")
    if t_b == yr.get(d_s): found.append("羊刃")
    if t_b == {'子':'午','午':'子','丑':'未','未':'丑','寅':'申','申':'寅','卯':'酉','酉':'卯','辰':'戌','戌':'辰','巳':'亥','亥':'巳'}.get(yr.get(d_s)): found.append("飛刃")

    # 10-11, 27-28 驛馬, 咸池, 將星, 華蓋
    def star_check(ref_b):
        res = []
        if ref_b in ['申','子','辰']:
            if t_b == '寅': res.append("驛馬")
            if t_b == '酉': res.append("咸池")
            if t_b == '子': res.append("將星")
            if t_b == '辰': res.append("華蓋")
        if ref_b in ['寅','午','戌']:
            if t_b == '申': res.append("驛馬")
            if t_b == '卯': res.append("咸池")
            if t_b == '午': res.append("將星")
            if t_b == '戌': res.append("華蓋")
        if ref_b in ['巳','酉','丑']:
            if t_b == '亥': res.append("驛馬")
            if t_b == '午': res.append("咸池")
            if t_b == '酉': res.append("將星")
            if t_b == '丑': res.append("華蓋")
        if ref_b in ['亥','卯','未']:
            if t_b == '巳': res.append("驛馬")
            if t_b == '子': res.append("咸池")
            if t_b == '卯': res.append("將星")
            if t_b == '未': res.append("華蓋")
        return res
    found.extend(star_check(y_b)); found.extend(star_check(d_b))

    # 12. 紅鸞 / 13. 天喜 / 15-16, 37 劫煞, 災煞, 亡神
    hl_map = {'子':'卯','丑':'寅','寅':'丑','卯':'子','辰':'亥','巳':'戌','午':'酉','未':'申','申':'未','酉':'午','戌':'巳','亥':'辰'}
    tx_map = {'子':'酉','丑':'申','寅':'未','卯':'午','辰':'巳','巳':'辰','午':'卯','未':'寅','申':'丑','酉':'子','戌':'亥','亥':'戌'}
    if t_b == hl_map.get(y_b): found.append("紅鸞")
    if t_b == tx_map.get(y_b): found.append("天喜")

    if y_b in ['申','子','辰']:
        if t_b == '巳': found.append("劫煞")
        if t_b == '午': found.append("災煞")
        if t_b == '亥': found.append("亡神")
    if y_b in ['寅','午','戌']:
        if t_b == '亥': found.append("劫煞")
        if t_b == '子': found.append("災煞")
        if t_b == '巳': found.append("亡神")
    if y_b in ['巳','酉','丑']:
        if t_b == '寅': found.append("劫煞")
        if t_b == '卯': found.append("災煞")
        if t_b == '申': found.append("亡神")
    if y_b in ['亥','卯','未']:
        if t_b == '申': found.append("劫煞")
        if t_b == '酉': found.append("災煞")
        if t_b == '寅': found.append("亡神")

    # 17-19 空亡, 福星, 天廚
    if t_b in get_xun_kong(d_p) or t_b in get_xun_kong(y_p): found.append("空亡")
    fx = {'甲':['寅','子'],'丙':['寅','子'],'乙':['亥','丑'],'丁':['亥','丑'],'戊':'申','己':'未','庚':'午','辛':'巳','壬':'辰','癸':'卯'}
    if t_b in fx.get(d_s, []) or t_b in fx.get(y_s, []): found.append("福星貴人")
    tc = {'丙':'巳', '丁':'午', '戊':'申', '己':'酉', '庚':'亥', '辛':'子', '壬':'寅', '癸':'卯'}
    if t_b == tc.get(d_s) or t_b == tc.get(y_s): found.append("天廚貴人")

    # 20. 德秀 / 21. 天醫 / 31. 血刃
    if m_b in ['寅','午','戌'] and t_s in ['丙','丁','戊','癸']: found.append("德秀貴人")
    if m_b in ['申','子','辰'] and t_s in ['壬','癸','戊','己']: found.append("德秀貴人")
    if m_b in ['申','子','辰'] and t_s in ['丙','辛','甲','乙']: found.append("德秀貴人")
    if m_b in ['巳','酉','丑'] and t_s in ['庚','辛','乙']: found.append("德秀貴人")
    if m_b in ['亥','卯','未'] and t_s in ['甲','乙','丁','壬']: found.append("德秀貴人")
    if t_b == BRANCHES[(BRANCHES.index(m_b)-1)%12]: found.append("天醫")
    xr = {'寅':'丑','卯':'未','辰':'寅','巳':'申','午':'卯','未':'戌','申':'亥','酉':'午','戌':'子','亥':'巳','子':'辰','丑':'酉'}
    if t_b == xr.get(m_b): found.append("血刃")

    # 26. 三奇貴人
    if "".join(bazi.stems[:3]) in ["甲戊庚", "乙丙丁", "壬癸辛"]: found.append("三奇貴人")

    # 29, 36, 38, 41 魁罡, 紅艷, 金輿, 流霞
    if pillar_idx == 2 and t_p in ['壬辰','庚戌','庚辰','戊戌']: found.append("魁罡")
    hy = {'甲':'午','乙':'午','丙':'寅','丁':'未','戊':'辰','己':'辰','庚':'戌','辛':'酉','壬':'子','癸':'申'}
    if t_b == hy.get(d_s): found.append("紅艷煞")
    if t_b == BRANCHES[(BRANCHES.index(lu.get(d_s))+2)%12]: found.append("金輿")
    lx = {'甲':'酉','乙':'戌','丙':'未','丁':'申','戊':'巳','己':'午','庚':'午','辛':'卯','壬':'亥','癸':'子'}
    if t_b == lx.get(d_s): found.append("流霞")

    # 32. 勾絞煞 / 33. 元辰 (大耗)
    if t_b == BRANCHES[(BRANCHES.index(y_b)+3)%12] or t_b == BRANCHES[(BRANCHES.index(y_b)-3)%12]: found.append("勾絞煞")
    if t_b == {'子':'未','丑':'申','寅':'酉','卯':'戌','辰':'亥','巳':'子','午':'丑','未':'寅','申':'卯','酉':'辰','戌':'巳','亥':'午'}.get(y_b): found.append("元辰")

    # 34. 孤辰 / 35. 寡宿
    if y_b in ['寅','卯','辰'] and t_b == '巳': found.append("孤辰")
    if y_b in ['寅','卯','辰'] and t_b == '丑': found.append("寡宿")
    if y_b in ['巳','午','未'] and t_b == '申': found.append("孤辰")
    if y_b in ['巳','午','未'] and t_b == '辰': found.append("寡宿")
    
    # 42-44 喪門, 弔客, 披麻
    if t_b == BRANCHES[(BRANCHES.index(y_b)+2)%12]: found.append("喪門")
    if t_b == BRANCHES[(BRANCHES.index(y_b)-2)%12]: found.append("弔客")
    if t_b == BRANCHES[(BRANCHES.index(y_b)+3)%12]: found.append("披麻")

    # 45. 童子煞
    ny_y_ele = get_nayin_element(y_p)
    if (m_b in ['寅','卯','辰','申','酉','戌'] and t_b in ['子','寅']) or (m_b in ['巳','午','未','亥','子','丑'] and t_b in ['卯','未','辰']):
        found.append("童子煞")
    elif (ny_y_ele in ['金','木'] and t_b in ['午','卯']) or (ny_y_ele in ['水','火'] and t_b in ['酉','戌']) or (ny_y_ele == '土' and t_b in ['辰','巳']):
        found.append("童子煞")

    # 46-51, 53-54 (十靈、八專、六秀、九醜、四廢、十惡大敗、陰差陽錯、孤鸞)
    if pillar_idx == 2:
        if t_p in ['甲辰','乙亥','丙辰','丁酉','庚戌','庚寅','癸未','癸亥','辛亥','壬寅']: found.append("十靈日")
        if t_p in ['甲寅','乙卯','己未','丁未','庚申','辛酉','戊戌','癸丑']: found.append("八專日")
        if t_p in ['丙午','丁未','戊子','戊午','己丑','己未']: found.append("六秀日")
        if t_p in ['乙卯','乙酉','己卯','己酉','辛卯','辛酉','壬子','壬午','戊子']: found.append("九醜日")
        if (m_b in ['寅','卯','辰'] and t_p in ['庚申','辛酉']) or (m_b in ['巳','午','未'] and t_p in ['壬子','癸亥']) or (m_b in ['申','酉','戌'] and t_p in ['甲寅','乙卯']) or (m_b in ['亥','子','丑'] and t_p in ['丙午','丁未']): found.append("四廢日")
        if t_p in ['甲辰','乙巳','丙申','丁亥','戊戌','己丑','庚辰','辛巳','壬申','癸亥']: found.append("十惡大敗")
        if t_p in ['丙子','丁丑','戊寅','辛卯','壬辰','癸巳','丙午','丁未','戊申','辛酉','壬戌','癸亥']: found.append("陰差陽錯")
        if t_p in ['乙巳','丁巳','辛亥','丙午','戊午','甲子']: found.append("孤鸞煞")
        if (m_b in ['寅','卯','辰'] and t_p == '戊寅') or (m_b in ['巳','午','未'] and t_p == '甲午') or (m_b in ['申','酉','戌'] and t_p == '戊申') or (m_b in ['亥','子','丑'] and t_p == '甲子'): found.append("天赦日")

    # 52. 天羅地網
    if (ny_y_ele == '火' and t_b in ['戌','亥']): found.append("天羅")
    if (ny_y_ele in ['水','土'] and t_b in ['辰','巳']): found.append("地網")

    # 55. 拱祿
    if pillar_idx == 3:
        if (d_p == '癸亥' and h_p == '癸丑') or (d_p == '癸丑' and h_p == '癸亥'): found.append("拱祿(子)")
        if (d_p == '丁巳' and h_p == '丁未') or (d_p == '丁未' and h_p == '丁巳'): found.append("拱祿(午)")
        if (d_p == '戊辰' and h_p == '戊午') or (d_p == '戊午' and h_p == '戊辰'): found.append("拱祿(巳)")

    return sorted(list(set(found)))


# --- 4. 專業渲染 ---

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
                <td style="width: 150px; background: #e8e8e8; border: 1px solid #ccc; padding: 15px;">位置</td>
                {"".join([f'<td style="border: 1px solid #ccc; {"background:#fffafa;" if r["title"]=="日柱" else ""}">{r["title"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {l_fs}; color: #d35400; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1px solid #ccc; padding: 15px;">宮位意涵</td>
                {"".join([f'<td style="border: 1px solid #ccc; background: #fffcf5;">{r["note"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: {c_fs};">
                <td style="background: #e8e8e8; border: 1px solid #ccc; padding: 15px;">十神</td>
                {"".join([f'<td style="border: 1px solid #ccc; color:#c0392b;">{r["ten_god"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 40px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">天干</td>
                {"".join([f'<td style="border: 1px solid #ccc; color:#c0392b;">{r["stem"]}</td>' for r in results])}
            </tr>
            <tr style="font-size: 40px; font-weight: bold;">
                <td style="background: #e8e8e8; border: 1px solid #ccc;">地支</td>
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

st.subheader("📅 請輸入西元出生時間 (支援 1900 年之後)")
c1, c2, c3, c4 = st.columns(4)
with c1:
    birth_date = st.date_input(
        "出生日期", 
        value=datetime.date(1980, 1, 1),
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date(2100, 12, 31)
    )
with c4:
    birth_hour = st.selectbox("出生時辰", range(24), format_func=lambda x: f"{x:02d}:00")

if st.button("🔮 開始精確排盤"):
    y, m, d, h = birth_date.year, birth_date.month, birth_date.day, birth_hour
    
    solar = Solar.fromYmdHms(y, m, d, h, 0, 0)
    eight_char = solar.getLunar().getEightChar()
    
    # 採用多重偵測方式獲取 pillar，解決 AttributeError
    y_p = eight_char.getYear()
    m_p = eight_char.getMonth()
    d_p = eight_char.getDay()
    
    # 嘗試不同的方法名稱以解決庫版本相容性
    if hasattr(eight_char, 'getHour'):
        h_p = eight_char.getHour()
    elif hasattr(eight_char, 'getTime'):
        h_p = eight_char.getTime()
    else:
        # 如果方法都失效，嘗試直接轉換字串 (最後手段)
        h_p = str(eight_char).split(' ')[-1]
    
    st.success(f"✅ 轉換成功： {y_p} {m_p} {d_p} {h_p}")
    bazi_obj = Bazi(y_p, m_p, d_p, h_p)
    st.markdown(render_professional_chart(bazi_obj), unsafe_allow_html=True)
