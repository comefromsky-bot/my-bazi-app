import streamlit as st
import datetime
import re
from dataclasses import dataclass

# 導入專業曆法庫
try:
    from lunar_python import Solar, Lunar
except ImportError:
    st.error("系統偵測到缺少庫，請執行： pip install --upgrade lunar-python")

# --- 1. 基礎資料定義 (全域變數最優先初始化，防止 NameError) ---
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
    '咸池': {'feature': '個人的魅力與才華，也與情感波動密切。', 'effect': '賦予命主極佳的「觀眾緣」與人際吸引力，或表現為情感不專一、容易衝動行事，或因男女感情問題而導致財產或名譽受損。'},
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
    '月德合': {'feature': '和諧、穩定、貴人扶助。', 'effect': '強化月德吉祥，化解人際矛盾。'},
    '天德合': {'feature': '輔助天德、增吉減凶。', 'effect': '化解災禍的力量倍增。'},
    '三奇貴人': {'feature': '卓越、特立獨行、成就非凡。', 'effect': '思想超前，多為奇才或傳奇人物。'},
    '將星': {'feature': '統帥能力、決斷力、威嚴。', 'effect': '代表職權、管理職，能得眾人服從。'},
    '華蓋': {'feature': '藝術、宗教、孤獨、思想深度。', 'effect': '有才藝但清高，喜靜、好學佛道。'},
    '魁罡': {'feature': '剛毅、果敢、威權、嫉惡如仇。', 'effect': '成功與失敗皆劇烈，事業心強。'},
    '飛刃': {'feature': '意外受傷、破財、爭執。', 'effect': '注意血光意外或刀傷手術。'},
    '血刃': {'feature': '病災、手術、流血、意外。', 'effect': '應注意身體健康，易有血光之險。'},
    '勾絞煞': {'feature': '羈絆、口舌、糾纏、不順。', 'effect': '處理事情易藕斷絲連，主紛爭官司。'},
    '元辰': {'feature': '思緒混亂、耗神、損財、形貌。', 'effect': '代表消耗與不安，流年遇之多阻滯。'},
    '孤辰': {'feature': '孤獨、男忌、性格內向。', 'effect': '主性格孤僻，利於獨立作業與思考。'},
    '寡宿': {'feature': '寡居、女忌、情感波折。', 'effect': '心理壓力較大，婚姻感較疏離。'},
    '紅艷煞': {'feature': '浪漫、多情、色慾、藝術感。', 'effect': '增加魅力，但需防感情生活混亂。'},
    '亡神': {'feature': '城府深、計謀、心理壓力。', 'effect': '處理得當為奇策，不得當為官非。'},
    '金輿': {'feature': '貴氣、代步工具、配偶相助。', 'effect': '出入平安，利於經濟提升，代表富貴。'},
    '金神': {'feature': '威武、剛強、不屈不撓。', 'effect': '遇火制則能發貴，代表武職威望。'},
    '天赦日': {'feature': '寬免、赦罪、轉危為安。', 'effect': '能化解官災刑罰，一生多平安。'},
    '流霞': {'feature': '產危、出血、手術、意外。', 'effect': '女命主產厄，男命主意外傷災。'},
    '喪門': {'feature': '哀傷、喪事、哭泣、情緒低。', 'effect': '流年遇之需注意長輩健康。'},
    '弔客': {'feature': '探病、弔喪、悲傷感。', 'effect': '影響心情，主親友間的憂慮之事。'},
    '披麻': {'feature': '孝服、家庭憂患、喪服。', 'effect': '主家庭成員的健康問題與哀戚。'},
    '童子煞': {'feature': '婚姻晚成、體弱、靈異感。', 'effect': '感覺敏銳，多有神秘緣分，婚遲。'},
    '十靈日': {'feature': '直覺力、通靈感、智慧高。', 'effect': '聰明有預知力，利從事神祕學研究。'},
    '八專日': {'feature': '專業領域、技術、自信。', 'effect': '在特定領域能成為權威，但性格強勢。'},
    '六秀日': {'feature': '容貌俊美、聰明、才藝。', 'effect': '主人聰明且外型出眾，人緣好。'},
    '九醜日': {'feature': '名譽受損、感情糾葛。', 'effect': '容易發生桃色新聞，影響個人聲譽。'},
    '四廢日': {'feature': '意志消沉、做事費力、半途而廢。', 'effect': '主精力不足，創業不易，宜守舊。'},
    '十惡大敗': {'feature': '財富難守、祖業破敗。', 'effect': '不善理財，花錢無度，忌與人合夥。'},
    '天羅': {'feature': '困頓、束縛、官司、阻礙。', 'effect': '多主生活艱辛或法律糾紛，宜沉穩。'},
    '地網': {'feature': '困頓、束縛、官司、阻礙。', 'effect': '多主生活艱辛或法律糾紛，宜沉穩。'},
    '陰差陽錯': {'feature': '婚姻阻滯、夫妻不睦。', 'effect': '容易與配偶家產生隔閡，婚姻需多磨。'},
    '孤鸞煞': {'feature': '婚姻孤寂、剋配偶、二婚。', 'effect': '主情感生活不美滿，有孤獨感。'},
    '拱祿': {'feature': '暗祿、富貴、官職、擁護。', 'effect': '雖不顯露但有暗財，得人尊敬支持。'}
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
    me = STEM_PROPS[me_stem]
    target = STEM_PROPS[target_stem]
    relation = {
        ('木', '木'): '同我', ('木', '火'): '我生', ('木', '土'): '我剋', ('木', '金'): '剋我', ('木', '水'): '生我',
        ('火', '火'): '同我', ('火', '土'): '我生', ('火', '金'): '我剋', ('火', '水'): '剋我', ('火', '木'): '生我',
        ('土', '土'): '同我', ('土', '金'): '我生', ('土', '水'): '我剋', ('土', '木'): '剋我', ('土', '火'): '生我',
        ('金', '金'): '同我', ('金', '水'): '我生', ('金', '木'): '我剋', ('金', '火'): '剋我', ('金', '土'): '生我',
        ('水', '水'): '同我', ('水', '木'): '我生', ('水', '火'): '我剋', ('水', '土'): '剋我', ('水', '金'): '生我',
    }.get((me['element'], target['element']))
    return {'同我': {True: '比肩', False: '劫財'}, '我生': {True: '食神', False: '傷官'},
            '我剋': {True: '偏財', False: '正財'}, '剋我': {True: '七殺', False: '正官'},
            '生我': {True: '偏印', False: '正印'}}.get(relation, {}).get(me['polarity'] == target['polarity'], "未知")

def get_nayin_element(pillar):
    full = NAYIN_DATA.get(pillar, "   ")
    return full[-1] if len(full) >= 3 else ""

def get_xun_kong(pillar):
    s_idx = STEMS.index(pillar[0])
    b_idx = BRANCHES.index(pillar[1])
    diff = (b_idx - s_idx) % 12
    return [BRANCHES[(diff - 2) % 12], BRANCHES[(diff - 1) % 12]]

# --- 3. 神煞引擎 ---

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

    # 10-11, 27 驛馬, 咸池, 將星
    def star_check(ref_b):
        res = []
        if ref_b in ['申','子','辰']:
            if t_b == '寅': res.append("驛馬")
            if t_b == '酉': res.append("咸池")
            if t_b == '子': res.append("將星")
        if ref_b in ['寅','午','戌']:
            if t_b == '申': res.append("驛馬")
            if t_b == '卯': res.append("咸池")
            if t_b == '午': res.append("將星")
        if ref_b in ['巳','酉','丑']:
            if t_b == '亥': res.append("驛馬")
            if t_b == '午': res.append("咸池")
            if t_b == '酉': res.append("將星")
        if ref_b in ['亥','卯','未']:
            if t_b == '巳': res.append("驛馬")
            if t_b == '子': res.append("咸池")
            if t_b == '卯': res.append("將星")
        return res
    found.extend(star_check(y_b)); found.extend(star_check(d_b))

    # 華蓋邏輯 (年日互查，排除自身)
    hg_map = {'寅':'戌', '午':'戌', '戌':'戌', '巳':'丑', '酉':'丑', '丑':'丑', '申':'辰', '子':'辰', '辰':'辰', '亥':'未', '卯':'未', '未':'未'}
    if pillar_idx != 0 and t_b == hg_map.get(y_b): found.append("華蓋")
    if pillar_idx != 2 and t_b == hg_map.get(d_b): 
        if "華蓋" not in found: found.append("華蓋")
    
        
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

    # 17-18 福星, 天廚
    fx = {'甲':['寅','子'],'丙':['寅','子'],'乙':['亥','丑'],'丁':['亥','丑'],'戊':'申','己':'未','庚':'午','辛':'巳','壬':'辰','癸':'卯'}
    if t_b in fx.get(d_s, []) or t_b in fx.get(y_s, []): found.append("福星貴人")
    tc = {'丙':'巳', '丁':'午', '戊':'申', '己':'酉', '庚':'亥', '辛':'子', '壬':'寅', '癸':'卯'}
    if t_b == tc.get(d_s) or t_b == tc.get(y_s): found.append("天廚貴人")

    # 空亡
    if t_b in get_xun_kong(d_p) or t_b in get_xun_kong(y_p): found.append("空亡")    


    # 20. 德秀 / 21. 天醫 
    if m_b in ['寅','午','戌'] and t_s in ['丙','丁','戊','癸']: found.append("德秀貴人")
    if m_b in ['申','子','辰'] and t_s in ['壬','癸','戊','己']: found.append("德秀貴人")
    if m_b in ['申','子','辰'] and t_s in ['丙','辛','甲','乙']: found.append("德秀貴人")
    if m_b in ['巳','酉','丑'] and t_s in ['庚','辛','乙']: found.append("德秀貴人")
    if m_b in ['亥','卯','未'] and t_s in ['甲','乙','丁','壬']: found.append("德秀貴人")
    if t_b == BRANCHES[(BRANCHES.index(m_b)-1)%12]: found.append("天醫")

    # 31 血刃 (以月支查四柱)
    # 口訣：寅月丑，卯月未，辰月寅，巳月申，午月卯，未月酉，申月辰，酉月戌，戌月巳，亥月亥，子月午，丑月子
    xr_map = {'寅':'丑', '卯':'未', '辰':'寅', '巳':'申', '午':'卯', '未':'酉', '申':'辰', '酉':'戌', '戌':'巳', '亥':'亥', '子':'午', '丑':'子'}
    if t_b == xr_map.get(m_b):
        found.append("血刃")

    # 月德合 (寅午戌見辛...)
    ydh_map = {'寅': '辛', '午': '辛', '戌': '辛', '申': '丁', '子': '丁', '辰': '丁', '巳': '乙', '酉': '乙', '丑': '乙', '亥': '己', '卯': '己', '未': '己'}
    if t_s == ydh_map.get(m_b): found.append("月德合")

    # 天德合 (寅月壬、卯月巳...)
    tdh_map = {'寅': '壬', '卯': '巳', '辰': '丁', '巳': '丙', '午': '寅', '未': '己', '申': '戊', '酉': '亥', '戌': '辛', '亥': '庚', '子': '申', '丑': '乙'}
    target = tdh_map.get(m_b)
    if t_s == target or t_b == target: found.append("天德合")
    
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
    y_nayin = NAYIN_DATA.get(bazi.pillars[0], "")
    y_ele = y_nayin[-1] if y_nayin else ""
    
    # A. 季節查法 (以月支為主)
    spring_autumn = ['寅','卯','辰','申','酉','戌']
    summer_winter = ['巳','午','未','亥','子','丑']
    if m_b in spring_autumn and t_b in ['寅','子']: found.append("童子煞")
    if m_b in summer_winter and t_b in ['卯','未','辰']: found.append("童子煞")
    
    # B. 納音/年干查法
    if (y_ele in ['金','木']) and t_b in ['午','卯']:
        if "童子煞" not in found: found.append("童子煞")
    if (y_ele in ['水','火']) and t_b in ['酉','戌']:
        if "童子煞" not in found: found.append("童子煞")
    if y_ele == '土' and t_b in ['辰','巳']:
        if "童子煞" not in found: found.append("童子煞")



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
    y_nayin = NAYIN_DATA.get(bazi.pillars[0], "")
    nayin_ele = y_nayin[-1] if y_nayin else ""
    
    # 判定命主屬性
    is_fire_life = (nayin_ele == '火' or y_s in ['丙', '丁'])
    is_water_earth_life = (nayin_ele in ['水', '土'] or y_s in ['壬', '癸', '戊', '己'])
    
    all_b = bazi.branches
    has_xu_hai = ('戌' in all_b and '亥' in all_b)
    has_chen_si = ('辰' in all_b and '巳' in all_b)

    # 天羅 (火命或男性，見戌亥)
    if (is_fire_life or bazi.gender == "男") and has_xu_hai:
        if t_b in ['戌', '亥']: found.append("天羅")
    
    # 地網 (水土命或女性，見辰巳)
    if (is_water_earth_life or bazi.gender == "女") and has_chen_si:
        if t_b in ['辰', '巳']: found.append("地網")

    # 55. 拱祿
    if pillar_idx == 3:
        if (d_p == '癸亥' and h_p == '癸丑') or (d_p == '癸丑' and h_p == '癸亥'): found.append("拱祿(子)")
        if (d_p == '丁巳' and h_p == '丁未') or (d_p == '丁未' and h_p == '丁巳'): found.append("拱祿(午)")
        if (d_p == '戊辰' and h_p == '戊午') or (d_p == '戊午' and h_p == '戊辰'): found.append("拱祿(巳)")

    return sorted(list(set(found)))


# --- 4. 五行旺衰分析引擎 ---

def analyze_five_elements(bazi):
    """計算五行強弱及分佈"""
    element_scores = {'木': 0, '火': 0, '土': 0, '金': 0, '水': 0}

    # 天干五行計分 (每個天干 10 分)
    stem_weights = {'年': 8, '月': 10, '日': 12, '時': 8}
    for i, stem in enumerate(bazi.stems):
        ele = ELEMENTS_MAP.get(stem, '')
        if ele:
            weight = list(stem_weights.values())[i]
            element_scores[ele] += weight

    # 地支藏干計分
    branch_weights = {'年': 6, '月': 10, '日': 8, '時': 6}
    for i, branch in enumerate(bazi.branches):
        hidden = HIDDEN_STEMS_DATA.get(branch, [])
        weight = list(branch_weights.values())[i]
        for h_stem, percentage in hidden:
            ele = ELEMENTS_MAP.get(h_stem, '')
            if ele:
                element_scores[ele] += weight * (percentage / 100)

    # 計算日主五行
    day_master = bazi.stems[2]
    day_element = ELEMENTS_MAP.get(day_master, '')

    # 判斷日主強弱
    helping_elements = {
        '木': ['木', '水'], '火': ['火', '木'], '土': ['土', '火'],
        '金': ['金', '土'], '水': ['水', '金']
    }
    weakening_elements = {
        '木': ['金', '火', '土'], '火': ['水', '土', '金'], '土': ['木', '金', '水'],
        '金': ['火', '水', '木'], '水': ['土', '木', '火']
    }

    help_score = sum(element_scores[e] for e in helping_elements.get(day_element, []))
    weaken_score = sum(element_scores[e] for e in weakening_elements.get(day_element, []))

    total = sum(element_scores.values())

    # 判斷身強身弱
    if help_score > weaken_score * 1.3:
        strength = "身強"
        strength_desc = "日主得令得地，元氣充沛"
    elif weaken_score > help_score * 1.3:
        strength = "身弱"
        strength_desc = "日主失令失地，需要扶助"
    else:
        strength = "中和"
        strength_desc = "日主不強不弱，命局平衡"

    # 找出過旺與不足的五行
    avg = total / 5
    excess = [e for e, s in element_scores.items() if s > avg * 1.5]
    lacking = [e for e, s in element_scores.items() if s < avg * 0.5]

    return {
        'scores': element_scores,
        'day_element': day_element,
        'day_master': day_master,
        'strength': strength,
        'strength_desc': strength_desc,
        'help_score': help_score,
        'weaken_score': weaken_score,
        'excess': excess,
        'lacking': lacking,
        'total': total
    }

# --- 4.1 格局與用神判斷 ---

def determine_pattern_and_yongshen(bazi, five_elem_result):
    """判斷命格格局與喜用神"""
    day_master = bazi.stems[2]
    month_branch = bazi.branches[1]
    day_element = five_elem_result['day_element']
    strength = five_elem_result['strength']
    scores = five_elem_result['scores']

    # 十神統計
    ten_gods = {}
    for i, stem in enumerate(bazi.stems):
        if i != 2:  # 排除日主
            tg = get_ten_god(day_master, stem)
            ten_gods[tg] = ten_gods.get(tg, 0) + 1

    for branch in bazi.branches:
        hidden = HIDDEN_STEMS_DATA.get(branch, [])
        for h_stem, pct in hidden:
            tg = get_ten_god(day_master, h_stem)
            ten_gods[tg] = ten_gods.get(tg, 0) + (pct / 100)

    # 格局判斷
    patterns = []
    pattern_desc = ""

    # 正官格
    if ten_gods.get('正官', 0) >= 1.5 and ten_gods.get('七殺', 0) < 1:
        patterns.append("正官格")
        pattern_desc = "正官透出，品性端正，適合從政或管理職位"

    # 七殺格
    if ten_gods.get('七殺', 0) >= 1.5:
        patterns.append("七殺格")
        pattern_desc = "七殺透出，性格剛毅，適合競爭激烈的行業"

    # 正財格
    if ten_gods.get('正財', 0) >= 1.5:
        patterns.append("正財格")
        pattern_desc = "正財透出，勤儉持家，財運穩定"

    # 偏財格
    if ten_gods.get('偏財', 0) >= 1.5:
        patterns.append("偏財格")
        pattern_desc = "偏財透出，善於投資理財，有意外之財"

    # 食神格
    if ten_gods.get('食神', 0) >= 1.5:
        patterns.append("食神格")
        pattern_desc = "食神透出，性格溫和，有藝術天分"

    # 傷官格
    if ten_gods.get('傷官', 0) >= 1.5:
        patterns.append("傷官格")
        pattern_desc = "傷官透出，才華橫溢，思維獨特"

    # 正印格
    if ten_gods.get('正印', 0) >= 1.5:
        patterns.append("正印格")
        pattern_desc = "正印透出，聰明好學，有長輩庇護"

    # 偏印格
    if ten_gods.get('偏印', 0) >= 1.5:
        patterns.append("偏印格")
        pattern_desc = "偏印透出，思想獨特，適合研究工作"

    # 建祿格
    lu_map = {'甲':'寅','乙':'卯','丙':'巳','丁':'午','戊':'巳','己':'午','庚':'申','辛':'酉','壬':'亥','癸':'子'}
    if month_branch == lu_map.get(day_master):
        patterns.append("建祿格")
        pattern_desc = "月支為祿，自立能力強，事業有成"

    # 羊刃格
    yr_map = {'甲':'卯','乙':'寅','丙':'午','丁':'巳','戊':'午','己':'巳','庚':'酉','辛':'申','壬':'子','癸':'亥'}
    if month_branch == yr_map.get(day_master):
        patterns.append("羊刃格")
        pattern_desc = "月支為刃，性格剛強，需防衝動"

    if not patterns:
        patterns.append("普通格局")
        pattern_desc = "命局平和，宜穩中求進"

    # 喜用神判斷
    generating = {'木': '水', '火': '木', '土': '火', '金': '土', '水': '金'}
    same = {'木': '木', '火': '火', '土': '土', '金': '金', '水': '水'}
    controlling = {'木': '金', '火': '水', '土': '木', '金': '火', '水': '土'}
    generated = {'木': '火', '火': '土', '土': '金', '金': '水', '水': '木'}
    controlled = {'木': '土', '火': '金', '土': '水', '金': '木', '水': '火'}

    if strength == "身弱":
        xi_shen = generating.get(day_element, '')  # 喜印星（生我）
        yong_shen = same.get(day_element, '')  # 用比劫（同我）
        ji_shen = [controlling.get(day_element, ''), generated.get(day_element, '')]
        advice = "宜補強日主，多接近喜用神五行"
    elif strength == "身強":
        xi_shen = generated.get(day_element, '')  # 喜食傷（我生）
        yong_shen = controlling.get(day_element, '')  # 用官殺（剋我）
        ji_shen = [generating.get(day_element, ''), same.get(day_element, '')]
        advice = "宜洩秀日主，避免過於剛強"
    else:
        xi_shen = generating.get(day_element, '')
        yong_shen = generated.get(day_element, '')
        ji_shen = []
        advice = "命局中和，順勢而為即可"

    return {
        'patterns': patterns,
        'pattern_desc': pattern_desc,
        'ten_gods': ten_gods,
        'xi_shen': xi_shen,
        'yong_shen': yong_shen,
        'ji_shen': ji_shen,
        'advice': advice,
        'strength': strength
    }

# --- 4.2 性格特質分析 ---

def analyze_personality(bazi, five_elem_result, pattern_result):
    """根據八字分析性格特質"""
    day_master = bazi.stems[2]
    day_element = five_elem_result['day_element']
    strength = five_elem_result['strength']
    polarity = STEM_PROPS[day_master]['polarity']

    # 日主性格基礎
    stem_traits = {
        '甲': {'base': '正直剛毅', 'positive': '有領導力、正義感強、積極進取', 'negative': '固執己見、不善變通'},
        '乙': {'base': '柔韌靈活', 'positive': '善於適應、有藝術天分、人緣好', 'negative': '優柔寡斷、依賴心強'},
        '丙': {'base': '熱情開朗', 'positive': '慷慨大方、光明磊落、感染力強', 'negative': '衝動急躁、不夠細心'},
        '丁': {'base': '溫和細膩', 'positive': '心思細密、有洞察力、重感情', 'negative': '多慮敏感、容易焦慮'},
        '戊': {'base': '穩重厚實', 'positive': '誠信可靠、包容力強、有擔當', 'negative': '保守固執、不夠靈活'},
        '己': {'base': '謙遜務實', 'positive': '踏實認真、善於理財、有耐心', 'negative': '猜疑心重、缺乏自信'},
        '庚': {'base': '剛毅果斷', 'positive': '意志堅定、執行力強、有魄力', 'negative': '性格急躁、容易衝突'},
        '辛': {'base': '精明細緻', 'positive': '審美力強、善於分析、品味高', 'negative': '挑剔苛求、不夠寬容'},
        '壬': {'base': '聰慧多謀', 'positive': '足智多謀、適應力強、有遠見', 'negative': '不夠專一、容易分心'},
        '癸': {'base': '內斂敏銳', 'positive': '直覺敏銳、善於觀察、有智慧', 'negative': '過於低調、缺乏魄力'}
    }

    traits = stem_traits.get(day_master, {'base': '未知', 'positive': '', 'negative': ''})

    # 根據身強身弱調整
    if strength == "身強":
        strength_trait = "自信心強，行動力佳，但需注意不要過於強勢"
    elif strength == "身弱":
        strength_trait = "性格較為謙和，宜多培養自信，善用他人助力"
    else:
        strength_trait = "性格平衡，能屈能伸，進退有度"

    # 十神性格影響
    ten_gods = pattern_result['ten_gods']
    god_traits = []

    if ten_gods.get('食神', 0) > 1:
        god_traits.append("食神旺：為人和善，懂得享受生活，有口福")
    if ten_gods.get('傷官', 0) > 1:
        god_traits.append("傷官旺：才思敏捷，創意豐富，但易得罪人")
    if ten_gods.get('正財', 0) > 1:
        god_traits.append("正財旺：勤儉節約，理財有道，重視物質")
    if ten_gods.get('偏財', 0) > 1:
        god_traits.append("偏財旺：慷慨大方，人脈廣闘，善於投資")
    if ten_gods.get('正官', 0) > 1:
        god_traits.append("正官旺：守規矩、有責任感，適合公職")
    if ten_gods.get('七殺', 0) > 1:
        god_traits.append("七殺旺：有魄力、敢冒險，適合創業")
    if ten_gods.get('正印', 0) > 1:
        god_traits.append("正印旺：愛學習、重名聲，有長輩緣")
    if ten_gods.get('偏印', 0) > 1:
        god_traits.append("偏印旺：思想獨特，適合研究，但較孤僻")
    if ten_gods.get('比肩', 0) > 1:
        god_traits.append("比肩旺：獨立自主，重朋友，但競爭心強")
    if ten_gods.get('劫財', 0) > 1:
        god_traits.append("劫財旺：積極進取，但易破財，需防小人")

    return {
        'day_master': day_master,
        'base_trait': traits['base'],
        'positive': traits['positive'],
        'negative': traits['negative'],
        'strength_trait': strength_trait,
        'god_traits': god_traits,
        'polarity': polarity
    }

# --- 4.3 事業財運分析 ---

def analyze_career_wealth(bazi, five_elem_result, pattern_result):
    """分析事業與財運"""
    day_element = five_elem_result['day_element']
    strength = five_elem_result['strength']
    ten_gods = pattern_result['ten_gods']

    # 適合的行業（根據喜用神五行）
    industry_map = {
        '木': ['文化教育', '出版傳媒', '農林園藝', '服裝紡織', '醫藥保健', '家具木材'],
        '火': ['電子科技', '能源電力', '餐飲美食', '娛樂表演', '廣告設計', '照明光學'],
        '土': ['房地產', '建築工程', '農業種植', '倉儲物流', '礦業開採', '陶瓷建材'],
        '金': ['金融投資', '機械製造', '汽車交通', '珠寶鐘錶', '法律司法', '軍警保全'],
        '水': ['貿易商務', '物流運輸', '旅遊觀光', '水利漁業', '清潔服務', '資訊網路']
    }

    xi_shen = pattern_result['xi_shen']
    yong_shen = pattern_result['yong_shen']

    suitable_industries = []
    if xi_shen:
        suitable_industries.extend(industry_map.get(xi_shen, []))
    if yong_shen and yong_shen != xi_shen:
        suitable_industries.extend(industry_map.get(yong_shen, []))

    # 財運分析
    wealth_analysis = []

    if ten_gods.get('正財', 0) > 1 and ten_gods.get('偏財', 0) > 1:
        wealth_analysis.append("正偏財皆旺，財運亨通，正財偏財兼收")
    elif ten_gods.get('正財', 0) > 1:
        wealth_analysis.append("正財旺盛，適合穩定工作收入，薪資運佳")
    elif ten_gods.get('偏財', 0) > 1:
        wealth_analysis.append("偏財旺盛，有投資運，可獲意外之財")
    else:
        wealth_analysis.append("財星不顯，宜穩健理財，不宜投機")

    if strength == "身強":
        wealth_analysis.append("身強能擔財，財來能守，適合自主創業")
    elif strength == "身弱":
        wealth_analysis.append("身弱財多則難擔，宜合作經營，勿貪大財")

    # 事業發展建議
    if ten_gods.get('正官', 0) > 1:
        career_advice = "正官旺，適合在大企業或政府機關任職，走正統路線"
    elif ten_gods.get('七殺', 0) > 1:
        career_advice = "七殺旺，適合創業或從事競爭激烈的行業，有衝勁"
    elif ten_gods.get('食神', 0) > 1 or ten_gods.get('傷官', 0) > 1:
        career_advice = "食傷旺，適合創意產業、自由職業或技術研發"
    elif ten_gods.get('正印', 0) > 1 or ten_gods.get('偏印', 0) > 1:
        career_advice = "印星旺，適合教育、學術研究或文化產業"
    else:
        career_advice = "命局平和，各行各業皆可發展，宜選擇喜用神相關行業"

    return {
        'suitable_industries': suitable_industries[:8],
        'wealth_analysis': wealth_analysis,
        'career_advice': career_advice,
        'xi_shen': xi_shen,
        'yong_shen': yong_shen
    }

# --- 4.4 婚姻感情分析 ---

def analyze_marriage(bazi, five_elem_result, pattern_result):
    """分析婚姻感情運勢"""
    gender = bazi.gender
    day_master = bazi.stems[2]
    ten_gods = pattern_result['ten_gods']
    strength = five_elem_result['strength']

    # 配偶星分析
    if gender == "男":
        spouse_star = "正財"  # 男命正財為妻
        affair_star = "偏財"
    else:
        spouse_star = "正官"  # 女命正官為夫
        affair_star = "七殺"

    spouse_count = ten_gods.get(spouse_star, 0)
    affair_count = ten_gods.get(affair_star, 0)

    marriage_traits = []

    # 配偶星分析
    if spouse_count >= 2:
        marriage_traits.append(f"{spouse_star}多現，感情經歷豐富，需慎選伴侶")
    elif spouse_count >= 1:
        marriage_traits.append(f"{spouse_star}適中，婚姻運勢穩定")
    else:
        marriage_traits.append(f"{spouse_star}不顯，可能晚婚或需主動追求")

    if affair_count >= 2:
        marriage_traits.append(f"{affair_star}旺盛，異性緣佳，但需注意第三者")

    # 桃花分析
    peach_branches = ['子', '午', '卯', '酉']
    peach_count = sum(1 for b in bazi.branches if b in peach_branches)

    if peach_count >= 3:
        marriage_traits.append("桃花旺盛，異性緣極佳，感情生活精彩")
    elif peach_count >= 2:
        marriage_traits.append("桃花適中，有正常的異性交往機會")
    else:
        marriage_traits.append("桃花較少，感情發展較為平淡穩定")

    # 配偶特質推斷
    day_branch = bazi.branches[2]
    spouse_element = ELEMENTS_MAP.get(day_branch, '')

    spouse_traits = {
        '木': '配偶可能性格正直、有主見、注重健康',
        '火': '配偶可能熱情開朗、積極樂觀、有表現欲',
        '土': '配偶可能穩重踏實、顧家可靠、重視安全感',
        '金': '配偶可能精明幹練、有原則、注重品質',
        '水': '配偶可能聰明靈活、善於交際、適應力強'
    }

    spouse_desc = spouse_traits.get(spouse_element, '配偶特質需結合其他因素分析')

    # 婚姻建議
    if strength == "身強" and spouse_count < 1:
        marriage_advice = "身強財弱，宜主動追求，多參加社交活動"
    elif strength == "身弱" and spouse_count > 2:
        marriage_advice = "身弱財多，宜晚婚，選擇能支持自己的伴侶"
    else:
        marriage_advice = "婚姻運勢平穩，真誠相待，自然會有良緣"

    return {
        'spouse_star': spouse_star,
        'marriage_traits': marriage_traits,
        'spouse_desc': spouse_desc,
        'marriage_advice': marriage_advice,
        'peach_count': peach_count
    }

# --- 4.5 健康養生分析 ---

def analyze_health(bazi, five_elem_result):
    """分析健康狀況與養生建議"""
    scores = five_elem_result['scores']
    day_element = five_elem_result['day_element']
    excess = five_elem_result['excess']
    lacking = five_elem_result['lacking']

    # 五行對應臟腑
    organ_map = {
        '木': {'organs': '肝、膽、眼睛、筋腱', 'excess': '肝火旺、易怒、偏頭痛', 'lack': '肝血不足、視力問題'},
        '火': {'organs': '心、小腸、血脈、舌', 'excess': '心火旺、失眠、焦慮', 'lack': '心血不足、健忘、心悸'},
        '土': {'organs': '脾、胃、肌肉、口唇', 'excess': '脾胃濕熱、消化不良', 'lack': '脾虛、食慾不振、四肢無力'},
        '金': {'organs': '肺、大腸、皮膚、鼻', 'excess': '肺熱、皮膚問題', 'lack': '肺氣虛、呼吸系統弱、易感冒'},
        '水': {'organs': '腎、膀胱、骨骼、耳', 'excess': '腎水過旺、水腫', 'lack': '腎虛、腰膝酸軟、骨質疏鬆'}
    }

    health_warnings = []
    health_tips = []

    # 分析過旺五行
    for elem in excess:
        info = organ_map.get(elem, {})
        health_warnings.append(f"【{elem}過旺】{info.get('excess', '')}")

    # 分析不足五行
    for elem in lacking:
        info = organ_map.get(elem, {})
        health_warnings.append(f"【{elem}不足】{info.get('lack', '')}")

    if not health_warnings:
        health_warnings.append("五行較為平衡，整體健康狀況良好")

    # 養生建議
    element_foods = {
        '木': '綠色蔬菜、酸味食物、枸杞、菊花茶',
        '火': '紅色食物、苦味蔬菜、蓮子、百合',
        '土': '黃色食物、甜味適量、山藥、薏仁',
        '金': '白色食物、辛味適量、白蘿蔔、銀耳',
        '水': '黑色食物、鹹味適量、黑豆、海帶'
    }

    for elem in lacking:
        foods = element_foods.get(elem, '')
        if foods:
            health_tips.append(f"補{elem}食物：{foods}")

    # 運動建議
    exercise_map = {
        '木': '適合戶外活動、伸展運動、太極拳',
        '火': '適合有氧運動、瑜伽、游泳降火',
        '土': '適合散步、八段錦、腹部按摩',
        '金': '適合呼吸練習、爬山、武術',
        '水': '適合游泳、慢跑、冥想靜坐'
    }

    exercise_tips = []
    for elem in lacking:
        tip = exercise_map.get(elem, '')
        if tip:
            exercise_tips.append(f"補{elem}運動：{tip}")

    if not exercise_tips:
        exercise_tips.append(f"根據日主{day_element}：{exercise_map.get(day_element, '規律運動，保持健康')}")

    return {
        'organ_focus': organ_map.get(day_element, {}).get('organs', ''),
        'health_warnings': health_warnings,
        'health_tips': health_tips,
        'exercise_tips': exercise_tips,
        'excess': excess,
        'lacking': lacking
    }

# --- 4.6 大運流年分析 ---

def analyze_dayun_liunian(bazi, birth_date, five_elem_result, pattern_result):
    """分析大運與流年"""
    gender = bazi.gender
    year_stem = bazi.stems[0]
    month_pillar = bazi.pillars[1]
    xi_shen = pattern_result['xi_shen']
    yong_shen = pattern_result['yong_shen']

    # 判斷大運順逆
    yang_stems = ['甲', '丙', '戊', '庚', '壬']
    is_yang = year_stem in yang_stems
    is_forward = (is_yang and gender == "男") or (not is_yang and gender == "女")

    direction = "順行" if is_forward else "逆行"

    # 計算大運起始年齡（簡化計算）
    month_branch = bazi.branches[1]
    month_idx = BRANCHES.index(month_branch)

    # 生成未來六步大運
    dayun_list = []
    month_stem = bazi.stems[1]
    stem_idx = STEMS.index(month_stem)
    branch_idx = BRANCHES.index(month_branch)

    for i in range(1, 7):
        if is_forward:
            new_stem_idx = (stem_idx + i) % 10
            new_branch_idx = (branch_idx + i) % 12
        else:
            new_stem_idx = (stem_idx - i) % 10
            new_branch_idx = (branch_idx - i) % 12

        dayun_stem = STEMS[new_stem_idx]
        dayun_branch = BRANCHES[new_branch_idx]
        dayun_pillar = dayun_stem + dayun_branch

        # 判斷大運五行
        dayun_elem = ELEMENTS_MAP.get(dayun_stem, '')

        # 判斷大運吉凶
        if dayun_elem == xi_shen or dayun_elem == yong_shen:
            luck = "吉"
            luck_desc = f"大運走{dayun_elem}，為喜用神，運勢較佳"
        elif dayun_elem in pattern_result.get('ji_shen', []):
            luck = "凶"
            luck_desc = f"大運走{dayun_elem}，為忌神，宜謹慎行事"
        else:
            luck = "平"
            luck_desc = f"大運走{dayun_elem}，運勢平穩"

        start_age = i * 10  # 簡化計算

        dayun_list.append({
            'pillar': dayun_pillar,
            'element': dayun_elem,
            'luck': luck,
            'luck_desc': luck_desc,
            'age_range': f"{start_age}-{start_age+9}歲"
        })

    # 當前流年分析
    current_year = birth_date.year if hasattr(birth_date, 'year') else 2024
    analysis_year = 2024  # 分析年份

    # 計算流年干支（簡化）
    year_offset = (analysis_year - 4) % 60
    liunian_stem = STEMS[year_offset % 10]
    liunian_branch = BRANCHES[year_offset % 12]
    liunian_pillar = liunian_stem + liunian_branch
    liunian_elem = ELEMENTS_MAP.get(liunian_stem, '')

    if liunian_elem == xi_shen or liunian_elem == yong_shen:
        liunian_luck = "今年運勢較佳，宜積極把握機會"
    elif liunian_elem in pattern_result.get('ji_shen', []):
        liunian_luck = "今年運勢起伏，宜保守穩健"
    else:
        liunian_luck = "今年運勢平穩，順勢而為"

    return {
        'direction': direction,
        'dayun_list': dayun_list,
        'liunian_pillar': liunian_pillar,
        'liunian_luck': liunian_luck,
        'analysis_year': analysis_year
    }

# --- 4.7 人生建議與開運方法 ---

def get_life_advice(five_elem_result, pattern_result, career_result, marriage_result, health_result):
    """綜合人生建議"""
    strength = five_elem_result['strength']
    xi_shen = pattern_result['xi_shen']
    yong_shen = pattern_result['yong_shen']

    advice_list = []

    # 事業建議
    advice_list.append({
        'category': '事業發展',
        'advice': career_result['career_advice'],
        'detail': f"適合行業：{'、'.join(career_result['suitable_industries'][:4])}"
    })

    # 財運建議
    advice_list.append({
        'category': '財富理財',
        'advice': career_result['wealth_analysis'][0] if career_result['wealth_analysis'] else '穩健理財',
        'detail': '建議：量入為出，適當投資，分散風險'
    })

    # 感情建議
    advice_list.append({
        'category': '感情婚姻',
        'advice': marriage_result['marriage_advice'],
        'detail': marriage_result['spouse_desc']
    })

    # 健康建議
    health_advice = health_result['health_warnings'][0] if health_result['health_warnings'] else '注意養生'
    advice_list.append({
        'category': '健康養生',
        'advice': health_advice,
        'detail': health_result['health_tips'][0] if health_result['health_tips'] else '均衡飲食，規律作息'
    })

    return advice_list

def get_lucky_elements(pattern_result, five_elem_result):
    """獲取開運方法"""
    xi_shen = pattern_result['xi_shen']
    yong_shen = pattern_result['yong_shen']

    # 五行對應開運物
    lucky_items = {
        '木': {
            'colors': '綠色、青色、翠色',
            'directions': '東方',
            'numbers': '3、8',
            'items': '植物盆栽、木質飾品、書籍',
            'foods': '蔬菜、水果、酸味食物'
        },
        '火': {
            'colors': '紅色、紫色、橙色',
            'directions': '南方',
            'numbers': '2、7',
            'items': '燈飾、電子產品、紅色飾品',
            'foods': '紅色食物、苦味蔬菜'
        },
        '土': {
            'colors': '黃色、棕色、米色',
            'directions': '中央、東北、西南',
            'numbers': '5、0',
            'items': '陶瓷器皿、玉石、水晶',
            'foods': '穀物、甜食、根莖類'
        },
        '金': {
            'colors': '白色、金色、銀色',
            'directions': '西方',
            'numbers': '4、9',
            'items': '金屬飾品、鐘錶、汽車',
            'foods': '白色食物、辛辣調味'
        },
        '水': {
            'colors': '黑色、藍色、灰色',
            'directions': '北方',
            'numbers': '1、6',
            'items': '水族缸、噴泉、流動物品',
            'foods': '海鮮、黑色食物、鹹味'
        }
    }

    result = {}

    if xi_shen and xi_shen in lucky_items:
        result['喜神開運'] = lucky_items[xi_shen]
        result['喜神'] = xi_shen

    if yong_shen and yong_shen in lucky_items and yong_shen != xi_shen:
        result['用神開運'] = lucky_items[yong_shen]
        result['用神'] = yong_shen

    return result

def get_overall_rating(five_elem_result, pattern_result, all_shen_sha):
    """命格總評"""
    scores = {
        '格局評分': 0,
        '財運評分': 0,
        '事業評分': 0,
        '婚姻評分': 0,
        '健康評分': 0
    }

    # 格局評分
    patterns = pattern_result['patterns']
    if any(p in patterns for p in ['正官格', '正財格', '正印格']):
        scores['格局評分'] = 85
    elif any(p in patterns for p in ['食神格', '偏財格']):
        scores['格局評分'] = 80
    elif any(p in patterns for p in ['建祿格', '七殺格']):
        scores['格局評分'] = 75
    else:
        scores['格局評分'] = 70

    # 神煞加成
    good_sha = ['天乙貴人', '天德貴人', '月德貴人', '文昌貴人', '太極貴人', '祿神', '將星', '紅鸞', '天喜']
    bad_sha = ['羊刃', '劫煞', '災煞', '空亡', '血刃', '孤辰', '寡宿']

    good_count = sum(1 for sha in all_shen_sha if sha in good_sha)
    bad_count = sum(1 for sha in all_shen_sha if sha in bad_sha)

    sha_bonus = good_count * 2 - bad_count * 2

    # 其他評分
    ten_gods = pattern_result['ten_gods']

    # 財運
    scores['財運評分'] = min(90, 65 + ten_gods.get('正財', 0) * 8 + ten_gods.get('偏財', 0) * 6 + sha_bonus)

    # 事業
    scores['事業評分'] = min(90, 65 + ten_gods.get('正官', 0) * 8 + ten_gods.get('七殺', 0) * 5 + sha_bonus)

    # 婚姻
    scores['婚姻評分'] = min(90, 70 + sha_bonus)
    if '紅鸞' in all_shen_sha or '天喜' in all_shen_sha:
        scores['婚姻評分'] += 5
    if '孤辰' in all_shen_sha or '寡宿' in all_shen_sha or '孤鸞煞' in all_shen_sha:
        scores['婚姻評分'] -= 5

    # 健康
    scores['健康評分'] = min(90, 75 + sha_bonus)
    if '血刃' in all_shen_sha or '流霞' in all_shen_sha:
        scores['健康評分'] -= 3

    # 計算總評
    total = sum(scores.values()) / len(scores)

    if total >= 85:
        overall = "上上格局，命帶貴氣，一生順遂"
    elif total >= 75:
        overall = "上等格局，福祿兼備，事業有成"
    elif total >= 65:
        overall = "中上格局，平穩發展，小富即安"
    elif total >= 55:
        overall = "中等格局，需要努力，可期成就"
    else:
        overall = "普通格局，逆境求存，貴在堅持"

    return {
        'scores': scores,
        'total': round(total, 1),
        'overall': overall,
        'good_sha_count': good_count,
        'bad_sha_count': bad_count
    }


# --- 5. 深度交互分析引擎 ---

def analyze_all_interactions(bazi):
    s, b = bazi.stems, bazi.branches
    p_names = ["年", "月", "日", "時"]
    res = {"天干合衝": [], "地支合化": [], "地支刑衝害": []}
    
    s_combos = {tuple(sorted(('甲','己'))): '甲己合土', tuple(sorted(('乙','庚'))): '乙庚合金', tuple(sorted(('丙','辛'))): '丙辛合水', tuple(sorted(('丁','壬'))): '丁壬合木', tuple(sorted(('戊','癸'))): '戊癸合火'}
    s_clashes = {tuple(sorted(('甲','庚'))): '甲庚相衝', tuple(sorted(('乙','辛'))): '乙辛相衝', tuple(sorted(('丙','壬'))): '丙壬相衝', tuple(sorted(('丁','癸'))): '丁癸相衝'}
    
    # 地支六合 (重要修復點)
    b_6_combos = {tuple(sorted(('子','丑'))): '子丑合土', tuple(sorted(('寅','亥'))): '寅亥合木', tuple(sorted(('卯','戌'))): '卯戌合火', tuple(sorted(('辰','酉'))): '辰酉合金', tuple(sorted(('巳','申'))): '巳申合水', tuple(sorted(('午','未'))): '午未合火'}
    
    b_clashes = {tuple(sorted(('子','午'))): '子午相衝', tuple(sorted(('丑','未'))): '丑未相衝', tuple(sorted(('寅','申'))): '寅申相衝', tuple(sorted(('卯','酉'))): '卯酉相衝', tuple(sorted(('辰','戌'))): '辰戌相衝', tuple(sorted(('巳','亥'))): '巳亥相衝'}
    
    semi_list = {tuple(sorted(('申','子'))): '申子半合水局', tuple(sorted(('子','辰'))): '子辰半合水局', tuple(sorted(('寅','午'))): '寅午半合火局', tuple(sorted(('午','戌'))): '午戌半合火局', tuple(sorted(('亥','卯'))): '亥卯半合木局', tuple(sorted(('卯','未'))): '卯未半合木局', tuple(sorted(('巳','酉'))): '巳酉半合金局', tuple(sorted(('酉','丑'))): '酉丑半合金局'}

    for i in range(4):
        for j in range(i+1, 4):
            ps, pb = tuple(sorted((s[i], s[j]))), tuple(sorted((b[i], b[j])))
            if ps in s_combos: res["天干合衝"].append(f"{p_names[i]}{p_names[j]} {s_combos[ps]}")
            if ps in s_clashes: res["天干合衝"].append(f"{p_names[i]}{p_names[j]} {s_clashes[ps]}")
            
            # 修復：比對六合與半合
            if pb in b_6_combos: res["地支合化"].append(f"{p_names[i]}{p_names[j]} {b_6_combos[pb]}")
            if pb in semi_list: res["地支合化"].append(f"{p_names[i]}{p_names[j]} {semi_list[pb]}")
            
            if pb in b_clashes: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b_clashes[pb]}")
            if b[i] == b[j] and b[i] in ['辰', '午', '酉', '亥']: res["地支刑衝害"].append(f"{p_names[i]}{p_names[j]} {b[i]}自刑")
    return res

# --- 6. 渲染 ---

def render_chart(bazi, birth_date=None):
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

    # 執行所有分析
    five_elem_result = analyze_five_elements(bazi)
    pattern_result = determine_pattern_and_yongshen(bazi, five_elem_result)
    personality_result = analyze_personality(bazi, five_elem_result, pattern_result)
    career_result = analyze_career_wealth(bazi, five_elem_result, pattern_result)
    marriage_result = analyze_marriage(bazi, five_elem_result, pattern_result)
    health_result = analyze_health(bazi, five_elem_result)
    dayun_result = analyze_dayun_liunian(bazi, birth_date, five_elem_result, pattern_result)
    life_advice = get_life_advice(five_elem_result, pattern_result, career_result, marriage_result, health_result)
    lucky_result = get_lucky_elements(pattern_result, five_elem_result)
    rating_result = get_overall_rating(five_elem_result, pattern_result, list(all_found_ss))

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
            <div><h4 style="color: #d35400;">【天干合衝】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['天干合衝']]) if rels['天干合衝'] else "<li>無顯著合衝</li>"}</ul></div>
            <div><h4 style="color: #27ae60;">【地支合化】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['地支合化']]) if rels['地支合化'] else "<li>無顯著合化</li>"}</ul><h4 style="color: #c0392b;">【地支刑衝害】</h4><ul>{"".join([f"<li>{x}</li>" for x in rels['地支刑衝害']]) if rels['地支刑衝害'] else "<li>無顯著刑衝害</li>"}</ul></div>
        </div>
    </div>"""

    detail_rows = []
    for ss in sorted(list(all_found_ss)):
        info = SHEN_SHA_INFO.get(ss, {'feature': '暫無資料', 'effect': '暫無資料'})
        detail_rows.append(f"""<tr><td style='border:1px solid #ccc;padding:10px;font-weight:bold;color:#8e44ad;width:150px;'>{ss}</td><td style='border:1px solid #ccc;padding:10px;'>{info['feature']}</td><td style='border:1px solid #ccc;padding:10px;color:#d35400;'>{info['effect']}</td></tr>""")

    ss_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; text-align: center; padding: 25px; border: 2.5px solid #8e44ad; border-radius: 15px; background: #fdfbff;">
        <h2 style="color: #8e44ad; border-bottom: 2px solid #8e44ad; padding-bottom: 10px;">🔮 命盤神煞深度解析</h2>
        <table style="width:100%; border-collapse: collapse; margin-top: 15px;">
            <tr style="background: #f4f0ff; font-weight: bold;">
                <td style="border: 1px solid #ccc; padding: 10px;">神煞名稱</td>
                <td style="border: 1px solid #ccc; padding: 10px;">綜合特徵</td>
                <td style="border: 1px solid #ccc; padding: 10px;">實際作用</td>
            </tr>
            {"".join(detail_rows) if detail_rows else "<tr><td colspan='3' style='padding:20px;'>本命盤無特殊神煞解析</td></tr>"}
        </table>
    </div>"""

    # === 一、基本資料 ===
    basic_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #3498db; border-radius: 15px; background: #f8fbff;">
        <h2 style="color: #3498db; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📋 一、基本資料</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            <div style="padding: 15px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <p><strong>性別：</strong>{bazi.gender}</p>
                <p><strong>日主：</strong>{bazi.stems[2]}（{five_elem_result['day_element']}）</p>
                <p><strong>日主陰陽：</strong>{STEM_PROPS[bazi.stems[2]]['polarity']}{five_elem_result['day_element']}</p>
            </div>
            <div style="padding: 15px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <p><strong>身強身弱：</strong>{five_elem_result['strength']}</p>
                <p><strong>格局：</strong>{'、'.join(pattern_result['patterns'])}</p>
                <p><strong>納音：</strong>{NAYIN_DATA.get(bazi.pillars[2], '')}</p>
            </div>
        </div>
    </div>"""

    # === 二、完整八字命盤 ===
    full_bazi_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #9b59b6; border-radius: 15px; background: #fdf8ff;">
        <h2 style="color: #9b59b6; text-align: center; border-bottom: 2px solid #9b59b6; padding-bottom: 10px;">🔍 二、完整八字命盤</h2>
        <div style="text-align: center; margin-top: 20px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #f0e6f6;">
                    <th style="border: 1px solid #ccc; padding: 12px;">柱位</th>
                    <th style="border: 1px solid #ccc; padding: 12px;">年柱</th>
                    <th style="border: 1px solid #ccc; padding: 12px;">月柱</th>
                    <th style="border: 1px solid #ccc; padding: 12px;">日柱</th>
                    <th style="border: 1px solid #ccc; padding: 12px;">時柱</th>
                </tr>
                <tr>
                    <td style="border: 1px solid #ccc; padding: 10px; font-weight: bold;">干支</td>
                    <td style="border: 1px solid #ccc; padding: 10px; font-size: 24px; font-weight: bold;">{bazi.pillars[0]}</td>
                    <td style="border: 1px solid #ccc; padding: 10px; font-size: 24px; font-weight: bold;">{bazi.pillars[1]}</td>
                    <td style="border: 1px solid #ccc; padding: 10px; font-size: 24px; font-weight: bold; color: #c0392b;">{bazi.pillars[2]}</td>
                    <td style="border: 1px solid #ccc; padding: 10px; font-size: 24px; font-weight: bold;">{bazi.pillars[3]}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ccc; padding: 10px; font-weight: bold;">納音</td>
                    <td style="border: 1px solid #ccc; padding: 10px;">{NAYIN_DATA.get(bazi.pillars[0], '')}</td>
                    <td style="border: 1px solid #ccc; padding: 10px;">{NAYIN_DATA.get(bazi.pillars[1], '')}</td>
                    <td style="border: 1px solid #ccc; padding: 10px;">{NAYIN_DATA.get(bazi.pillars[2], '')}</td>
                    <td style="border: 1px solid #ccc; padding: 10px;">{NAYIN_DATA.get(bazi.pillars[3], '')}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #ccc; padding: 10px; font-weight: bold;">五行</td>
                    <td style="border: 1px solid #ccc; padding: 10px;">{ELEMENTS_MAP.get(bazi.stems[0], '')}、{ELEMENTS_MAP.get(bazi.branches[0], '')}</td>
                    <td style="border: 1px solid #ccc; padding: 10px;">{ELEMENTS_MAP.get(bazi.stems[1], '')}、{ELEMENTS_MAP.get(bazi.branches[1], '')}</td>
                    <td style="border: 1px solid #ccc; padding: 10px;">{ELEMENTS_MAP.get(bazi.stems[2], '')}、{ELEMENTS_MAP.get(bazi.branches[2], '')}</td>
                    <td style="border: 1px solid #ccc; padding: 10px;">{ELEMENTS_MAP.get(bazi.stems[3], '')}、{ELEMENTS_MAP.get(bazi.branches[3], '')}</td>
                </tr>
            </table>
        </div>
    </div>"""

    # === 三、五行旺衰分析 ===
    scores = five_elem_result['scores']
    max_score = max(scores.values()) if scores.values() else 1

    element_bars = ""
    element_colors = {'木': '#27ae60', '火': '#e74c3c', '土': '#f39c12', '金': '#bdc3c7', '水': '#3498db'}
    for elem in ['木', '火', '土', '金', '水']:
        score = scores.get(elem, 0)
        percentage = (score / max_score) * 100 if max_score > 0 else 0
        color = element_colors.get(elem, '#95a5a6')
        element_bars += f"""
            <div style="margin: 10px 0;">
                <div style="display: flex; align-items: center;">
                    <span style="width: 40px; font-weight: bold;">{elem}</span>
                    <div style="flex: 1; background: #eee; border-radius: 10px; height: 25px; margin: 0 10px;">
                        <div style="width: {percentage}%; background: {color}; height: 100%; border-radius: 10px; transition: width 0.5s;"></div>
                    </div>
                    <span style="width: 60px; text-align: right;">{score:.1f}分</span>
                </div>
            </div>"""

    five_elem_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #27ae60; border-radius: 15px; background: #f8fff8;">
        <h2 style="color: #27ae60; text-align: center; border-bottom: 2px solid #27ae60; padding-bottom: 10px;">⚖️ 三、五行旺衰分析</h2>
        <div style="margin-top: 20px;">
            {element_bars}
        </div>
        <div style="margin-top: 20px; padding: 15px; background: #fff; border-radius: 10px;">
            <p><strong>日主五行：</strong>{five_elem_result['day_element']} | <strong>身強身弱：</strong><span style="color: #c0392b; font-weight: bold;">{five_elem_result['strength']}</span></p>
            <p><strong>分析：</strong>{five_elem_result['strength_desc']}</p>
            <p><strong>扶助力量：</strong>{five_elem_result['help_score']:.1f}分 | <strong>剋洩力量：</strong>{five_elem_result['weaken_score']:.1f}分</p>
            {f"<p><strong>過旺五行：</strong>{'、'.join(five_elem_result['excess'])}</p>" if five_elem_result['excess'] else ""}
            {f"<p><strong>不足五行：</strong>{'、'.join(five_elem_result['lacking'])}</p>" if five_elem_result['lacking'] else ""}
        </div>
    </div>"""

    # === 四、格局與用神 ===
    pattern_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #e74c3c; border-radius: 15px; background: #fff8f8;">
        <h2 style="color: #e74c3c; text-align: center; border-bottom: 2px solid #e74c3c; padding-bottom: 10px;">🎯 四、格局與用神</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #c0392b; margin-bottom: 15px;">【命格格局】</h4>
                <p style="font-size: 20px; font-weight: bold; color: #2c3e50;">{'、'.join(pattern_result['patterns'])}</p>
                <p style="margin-top: 10px; color: #666;">{pattern_result['pattern_desc']}</p>
            </div>
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #27ae60; margin-bottom: 15px;">【喜用神】</h4>
                <p><strong>喜神：</strong><span style="font-size: 18px; color: #27ae60; font-weight: bold;">{pattern_result['xi_shen']}</span></p>
                <p><strong>用神：</strong><span style="font-size: 18px; color: #3498db; font-weight: bold;">{pattern_result['yong_shen']}</span></p>
                <p><strong>忌神：</strong><span style="color: #e74c3c;">{'、'.join(pattern_result['ji_shen']) if pattern_result['ji_shen'] else '無明顯忌神'}</span></p>
                <p style="margin-top: 10px; color: #666;">{pattern_result['advice']}</p>
            </div>
        </div>
    </div>"""

    # === 五、性格特質深度分析 ===
    god_traits_html = "".join([f"<li>{t}</li>" for t in personality_result['god_traits']]) if personality_result['god_traits'] else "<li>十神分佈平均</li>"

    personality_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #f39c12; border-radius: 15px; background: #fffef8;">
        <h2 style="color: #f39c12; text-align: center; border-bottom: 2px solid #f39c12; padding-bottom: 10px;">🌟 五、性格特質深度分析</h2>
        <div style="margin-top: 15px;">
            <div style="padding: 20px; background: #fff; border-radius: 10px; margin-bottom: 15px;">
                <h4 style="color: #d35400;">【日主 {personality_result['day_master']} 的基本性格】</h4>
                <p style="font-size: 18px; font-weight: bold; color: #2c3e50;">{personality_result['base_trait']}</p>
                <p style="margin-top: 10px;"><strong>優點：</strong>{personality_result['positive']}</p>
                <p><strong>缺點：</strong>{personality_result['negative']}</p>
            </div>
            <div style="padding: 20px; background: #fff; border-radius: 10px; margin-bottom: 15px;">
                <h4 style="color: #8e44ad;">【身強身弱影響】</h4>
                <p>{personality_result['strength_trait']}</p>
            </div>
            <div style="padding: 20px; background: #fff; border-radius: 10px;">
                <h4 style="color: #16a085;">【十神性格特點】</h4>
                <ul>{god_traits_html}</ul>
            </div>
        </div>
    </div>"""

    # === 六、事業財運分析 ===
    industries_html = "、".join(career_result['suitable_industries']) if career_result['suitable_industries'] else "需結合大運流年分析"
    wealth_html = "".join([f"<li>{w}</li>" for w in career_result['wealth_analysis']])

    career_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #2980b9; border-radius: 15px; background: #f8faff;">
        <h2 style="color: #2980b9; text-align: center; border-bottom: 2px solid #2980b9; padding-bottom: 10px;">💼 六、事業財運分析</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #2c3e50;">【事業發展】</h4>
                <p>{career_result['career_advice']}</p>
                <h4 style="color: #27ae60; margin-top: 15px;">【適合行業】</h4>
                <p>{industries_html}</p>
            </div>
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #f39c12;">【財運分析】</h4>
                <ul>{wealth_html}</ul>
                <p style="margin-top: 10px;"><strong>喜用五行行業：</strong>{career_result['xi_shen']}、{career_result['yong_shen']}</p>
            </div>
        </div>
    </div>"""

    # === 七、婚姻感情分析 ===
    marriage_traits_html = "".join([f"<li>{t}</li>" for t in marriage_result['marriage_traits']])

    marriage_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #e91e63; border-radius: 15px; background: #fff8fa;">
        <h2 style="color: #e91e63; text-align: center; border-bottom: 2px solid #e91e63; padding-bottom: 10px;">💑 七、婚姻感情分析</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #c2185b;">【感情特質】</h4>
                <ul>{marriage_traits_html}</ul>
                <p style="margin-top: 10px;"><strong>配偶星：</strong>{marriage_result['spouse_star']}</p>
            </div>
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #8e44ad;">【配偶特質】</h4>
                <p>{marriage_result['spouse_desc']}</p>
                <h4 style="color: #27ae60; margin-top: 15px;">【婚姻建議】</h4>
                <p>{marriage_result['marriage_advice']}</p>
            </div>
        </div>
    </div>"""

    # === 八、健康養生指南 ===
    warnings_html = "".join([f"<li>{w}</li>" for w in health_result['health_warnings']])
    tips_html = "".join([f"<li>{t}</li>" for t in health_result['health_tips']]) if health_result['health_tips'] else "<li>五行平衡，注意日常保健即可</li>"
    exercise_html = "".join([f"<li>{e}</li>" for e in health_result['exercise_tips']])

    health_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #00bcd4; border-radius: 15px; background: #f8ffff;">
        <h2 style="color: #00bcd4; text-align: center; border-bottom: 2px solid #00bcd4; padding-bottom: 10px;">🏥 八、健康養生指南</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; margin-top: 15px;">
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #e74c3c;">【健康注意】</h4>
                <ul>{warnings_html}</ul>
                <p style="margin-top: 10px;"><strong>重點臟腑：</strong>{health_result['organ_focus']}</p>
            </div>
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #27ae60;">【飲食建議】</h4>
                <ul>{tips_html}</ul>
            </div>
            <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #3498db;">【運動養生】</h4>
                <ul>{exercise_html}</ul>
            </div>
        </div>
    </div>"""

    # === 九、大運流年分析 ===
    dayun_rows = ""
    for dy in dayun_result['dayun_list']:
        luck_color = {'吉': '#27ae60', '凶': '#e74c3c', '平': '#f39c12'}.get(dy['luck'], '#666')
        dayun_rows += f"""
            <tr>
                <td style="border: 1px solid #ccc; padding: 10px;">{dy['age_range']}</td>
                <td style="border: 1px solid #ccc; padding: 10px; font-size: 18px; font-weight: bold;">{dy['pillar']}</td>
                <td style="border: 1px solid #ccc; padding: 10px;">{dy['element']}</td>
                <td style="border: 1px solid #ccc; padding: 10px; color: {luck_color}; font-weight: bold;">{dy['luck']}</td>
                <td style="border: 1px solid #ccc; padding: 10px;">{dy['luck_desc']}</td>
            </tr>"""

    dayun_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #673ab7; border-radius: 15px; background: #faf8ff;">
        <h2 style="color: #673ab7; text-align: center; border-bottom: 2px solid #673ab7; padding-bottom: 10px;">🔮 九、大運流年分析</h2>
        <div style="margin-top: 15px;">
            <p style="text-align: center; margin-bottom: 15px;"><strong>大運方向：</strong><span style="color: #673ab7; font-weight: bold;">{dayun_result['direction']}</span></p>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #ede7f6;">
                    <th style="border: 1px solid #ccc; padding: 10px;">年齡段</th>
                    <th style="border: 1px solid #ccc; padding: 10px;">大運</th>
                    <th style="border: 1px solid #ccc; padding: 10px;">五行</th>
                    <th style="border: 1px solid #ccc; padding: 10px;">吉凶</th>
                    <th style="border: 1px solid #ccc; padding: 10px;">運勢說明</th>
                </tr>
                {dayun_rows}
            </table>
            <div style="margin-top: 20px; padding: 15px; background: #fff; border-radius: 10px;">
                <h4 style="color: #d35400;">【{dayun_result['analysis_year']}年流年分析】</h4>
                <p><strong>流年干支：</strong>{dayun_result['liunian_pillar']}</p>
                <p>{dayun_result['liunian_luck']}</p>
            </div>
        </div>
    </div>"""

    # === 十、人生總體建議 ===
    advice_cards = ""
    for adv in life_advice:
        advice_cards += f"""
            <div style="padding: 15px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h4 style="color: #2c3e50; margin-bottom: 10px;">{adv['category']}</h4>
                <p style="font-weight: bold;">{adv['advice']}</p>
                <p style="color: #666; font-size: 14px; margin-top: 5px;">{adv['detail']}</p>
            </div>"""

    life_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #009688; border-radius: 15px; background: #f8fffd;">
        <h2 style="color: #009688; text-align: center; border-bottom: 2px solid #009688; padding-bottom: 10px;">💡 十、人生總體建議</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            {advice_cards}
        </div>
    </div>"""

    # === 十一、開運方法 ===
    lucky_content = ""
    for key in ['喜神開運', '用神開運']:
        if key in lucky_result:
            shen_type = '喜神' if key == '喜神開運' else '用神'
            shen_elem = lucky_result.get(shen_type, '')
            items = lucky_result[key]
            lucky_content += f"""
                <div style="padding: 20px; background: #fff; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <h4 style="color: #ff5722;">{shen_type}（{shen_elem}）開運法</h4>
                    <p><strong>幸運顏色：</strong>{items['colors']}</p>
                    <p><strong>吉利方位：</strong>{items['directions']}</p>
                    <p><strong>幸運數字：</strong>{items['numbers']}</p>
                    <p><strong>開運物品：</strong>{items['items']}</p>
                    <p><strong>補運食物：</strong>{items['foods']}</p>
                </div>"""

    if not lucky_content:
        lucky_content = "<div style='padding: 20px; text-align: center;'>命局中和，各類開運方法皆可嘗試</div>"

    lucky_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #ff5722; border-radius: 15px; background: #fffaf8;">
        <h2 style="color: #ff5722; text-align: center; border-bottom: 2px solid #ff5722; padding-bottom: 10px;">🌈 十一、開運方法</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            {lucky_content}
        </div>
    </div>"""

    # === 十二、命格總評 ===
    score_bars = ""
    for category, score in rating_result['scores'].items():
        color = '#27ae60' if score >= 80 else '#f39c12' if score >= 70 else '#e74c3c'
        score_bars += f"""
            <div style="margin: 8px 0;">
                <div style="display: flex; align-items: center;">
                    <span style="width: 80px;">{category}</span>
                    <div style="flex: 1; background: #eee; border-radius: 10px; height: 20px; margin: 0 10px;">
                        <div style="width: {score}%; background: {color}; height: 100%; border-radius: 10px;"></div>
                    </div>
                    <span style="width: 50px; text-align: right; font-weight: bold;">{score:.0f}</span>
                </div>
            </div>"""

    rating_html = f"""<div style="margin-top: 35px; font-family: '標楷體'; padding: 25px; border: 2.5px solid #795548; border-radius: 15px; background: #faf8f5;">
        <h2 style="color: #795548; text-align: center; border-bottom: 2px solid #795548; padding-bottom: 10px;">📊 十二、命格總評</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px;">
            <div style="padding: 20px; background: #fff; border-radius: 10px;">
                <h4 style="color: #5d4037;">【各項評分】</h4>
                {score_bars}
            </div>
            <div style="padding: 20px; background: #fff; border-radius: 10px;">
                <h4 style="color: #5d4037;">【綜合評價】</h4>
                <div style="text-align: center; margin: 20px 0;">
                    <span style="font-size: 48px; font-weight: bold; color: #ff5722;">{rating_result['total']}</span>
                    <span style="font-size: 20px; color: #666;">分</span>
                </div>
                <p style="text-align: center; font-size: 18px; color: #2c3e50; font-weight: bold;">{rating_result['overall']}</p>
                <p style="margin-top: 15px; text-align: center; color: #666;">
                    吉神：{rating_result['good_sha_count']}個 | 凶煞：{rating_result['bad_sha_count']}個
                </p>
            </div>
        </div>
    </div>"""

    return html + rel_html + ss_html + basic_html + full_bazi_html + five_elem_html + pattern_html + personality_html + career_html + marriage_html + health_html + dayun_html + life_html + lucky_html + rating_html

# --- 6. 主程式 ---
st.set_page_config(page_title="專業 AI 八字解析", layout="wide")
st.title("🔮 專業 AI 八字全方位解析系統")

c1, c2, c3, c4 = st.columns(4)
with c1: birth_date = st.date_input("選擇日期", value=datetime.date(1990, 1, 1), min_value=datetime.date(1900, 1, 1), max_value=datetime.date(2100, 12, 31))
with c4: gender = st.radio("性別", ["男", "女"], horizontal=True)
birth_hour = st.selectbox("小時", range(24), format_func=lambda x: f"{x:02d}:00")

if st.button("🔮 開始精確排盤"):
    solar = Solar.fromYmdHms(birth_date.year, birth_date.month, birth_date.day, birth_hour, 0, 0)
    eight_char = solar.getLunar().getEightChar()
    y_p, m_p, d_p = eight_char.getYear(), eight_char.getMonth(), eight_char.getDay()
    h_p = getattr(eight_char, 'getHour', getattr(eight_char, 'getTime', lambda: "時柱錯誤"))()
    st.markdown(render_chart(Bazi(y_p, m_p, d_p, h_p, gender), birth_date), unsafe_allow_html=True)







