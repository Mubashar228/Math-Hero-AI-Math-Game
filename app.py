# math_hero_pro.py
"""
Math Hero — Professional Streamlit app (complete)
Features:
- Grades 2-10, 20 levels per grade, 10 questions per level
- Math Quiz + Shape Challenge
- Per-question recording and CSV leaderboard
- Unlock next level automatically on passing
- Detailed level results & CSV download
- Enter to submit for typed answers; safe radio for shape answers
- Progress save/load (JSON)
- Clean UI and helpful messages
"""

import streamlit as st
import random
import math
import json
import csv
import os
import time
from PIL import Image, ImageDraw, ImageFont
import io
from datetime import datetime
import pandas as pd

# ---------------------------
# App configuration
# ---------------------------
APP_TITLE = "Math Hero — Gamified AI Math Challenge"
PAGE_ICON = "🦸‍♂️"
LEVELS_PER_GRADE = 20
QUESTIONS_PER_LEVEL = 10
PASS_PERCENT = 70  # percent needed to pass a level
SAVE_FILE = "math_hero_progress.json"
LEADERBOARD_FILE = "math_hero_leaderboard.csv"
THEME_PRIMARY = "#4f46e5"  # indigo-ish
FONT_FAMILY = "Inter, Arial, sans-serif"

st.set_page_config(page_title=APP_TITLE, page_icon=PAGE_ICON, layout="wide")

# small CSS to make it look nicer
st.markdown(
    f"""
    <style>
    .app-title {{ font-family: {FONT_FAMILY}; font-size:32px; color:{THEME_PRIMARY}; font-weight:700 }}
    .subtitle {{ font-family: {FONT_FAMILY}; font-size:14px; color:#374151; }}
    .card {{ padding:12px; border-radius:10px; background:linear-gradient(180deg, #ffffff, #f8fafc); box-shadow: 0 4px 18px rgba(15,23,42,0.06); }}
    .small-muted {{ color: #6b7280; font-size:13px; }}
    .big-button {{ background:{THEME_PRIMARY}; color:white; padding:8px 14px; border-radius:8px; }}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------
# Utilities: persistence
# ---------------------------
def load_json(path=SAVE_FILE):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json(data, path=SAVE_FILE):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# Append rows (list of dicts) to CSV leaderboard with consistent columns
def append_leaderboard(rows, path=LEADERBOARD_FILE):
    # expected keys: timestamp, player, grade, level, q_no, question, given, correct_answer, is_correct, time_taken, percent_level
    fieldnames = ["timestamp","player","grade","level","q_no","question","given","correct_answer","is_correct","time_taken","percent_level"]
    first = not os.path.exists(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if first:
                writer.writeheader()
            for r in rows:
                writer.writerow(r)
        return True
    except Exception as e:
        print("Error writing leaderboard:", e)
        return False

# Allow downloading CSV content from in-memory rows
def make_csv_bytes(rows):
    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")

# ---------------------------
# Session defaults & init
# ---------------------------
def init_session():
    defaults = {
        "player_name": "Player",
        "grade": 5,
        "mode": "Math Quiz",  # "Math Quiz" or "Shape Challenge"
        "current_level": 1,
        "level_unlocked": {str(g): [1] for g in range(2, 11)},  # unlocked list per grade (strings)
        "level_progress": {str(g): {} for g in range(2, 11)},  # store results per grade->level
        "started": False,
        "question_index": 0,
        "correct_in_level": 0,
        "current_q": None,
        "current_ans": None,
        "current_choices": None,
        "question_start_time": None,
        "time_limit": 45,
        "score": 0,
        "recent_history": [],
        "weak_topics": {},
        "show_result": False,
        "last_result": None,
        "ui_input": "",
        "shape_key": None,
        "auto_clear": False,
        "level_results": [],  # per-question details for current level
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# initialize
init_session()

# if saved progress exists, load unlocked & level_progress (merge)
_saved = load_json()
if _saved:
    # merge unlocked lists
    locked = _saved.get("level_unlocked", {})
    if isinstance(locked, dict):
        for g, lst in locked.items():
            # ensure list type and unique
            st.session_state["level_unlocked"].setdefault(str(g), [])
            for lvl in lst:
                if lvl not in st.session_state["level_unlocked"][str(g)]:
                    st.session_state["level_unlocked"][str(g)].append(lvl)
    # merge level_progress
    lp = _saved.get("level_progress", {})
    if isinstance(lp, dict):
        for g, obj in lp.items():
            st.session_state["level_progress"].setdefault(str(g), {})
            for lvl, data in obj.items():
                st.session_state["level_progress"][str(g)][str(lvl)] = data

# ---------------------------
# Question Generators
# ---------------------------
# basic 2-4
def gen_addition(grade):
    a = random.randint(1, 10*grade)
    b = random.randint(1, 10*grade)
    return f"{a} + {b} = ?", a + b

def gen_subtraction(grade):
    a = random.randint(1, 10*grade)
    b = random.randint(1, a)
    return f"{a} - {b} = ?", a - b

def gen_multiplication(grade):
    a = random.randint(1, max(3, grade+2))
    b = random.randint(1, 12)
    return f"{a} × {b} = ?", a*b

def gen_division(grade):
    b = random.randint(1, min(12, grade+6))
    c = random.randint(1, 12)
    a = b*c
    return f"{a} ÷ {b} = ?", c

def gen_comparison(grade):
    a = random.randint(0, 50)
    b = random.randint(0, 50)
    ans = ">" if a > b else "<" if a < b else "="
    return f"Which is greater: {a} or {b}? Write '>' or '<' or '='.", ans

def gen_story(grade):
    a = random.randint(5, 50)
    b = random.randint(1, min(10, a))
    return f"Ali had {a} apples. He gave {b} apples. How many left?", a - b

# fractions
def gen_fraction_add(grade):
    d = random.randint(2,8)
    a = random.randint(1, d-1)
    b = random.randint(1, d-1)
    num = a + b
    den = d
    g = math.gcd(num, den)
    frac = f"{num//g}/{den//g}"
    dec = round(num/den, 3)
    return f"{a}/{d} + {b}/{d} = ? (fraction or decimal)", {"fraction":frac, "decimal":dec}

def gen_fraction_mixed(grade):
    num = random.randint(5, 20)
    den = random.randint(2, 8)
    whole = num // den
    rem = num % den
    if rem == 0:
        return f"Write {num}/{den} as mixed number.", str(whole)
    else:
        return f"Write {num}/{den} as mixed number.", f"{whole} {rem}/{den}"

# LCM/HCF
def gen_lcm(grade):
    a = random.randint(2, 20)
    b = random.randint(2, 20)
    return f"Find LCM of {a} and {b}.", (a*b)//math.gcd(a,b)

def gen_hcf(grade):
    a = random.randint(2, 40)
    b = random.randint(2, 40)
    return f"Find HCF (GCD) of {a} and {b}.", math.gcd(a,b)

# percentage / profit-loss
def gen_percentage(grade):
    base = random.randint(10,300)
    p = random.choice([5,10,15,20,25])
    return f"What is {p}% of {base}?", round(base * p/100, 2)

def gen_profit(grade):
    cp = random.randint(50,600)
    p = random.choice([5,10,15,20,25])
    sp = round(cp * (1 + p/100), 2)
    return f"Cost price = {cp}. Profit = {p}%. Find selling price.", sp

# geometry basics
def gen_area_rectangle(grade):
    l = random.randint(2, 20)
    w = random.randint(1, 15)
    return f"Area of rectangle length={l} and width={w} = ?", l*w

def gen_perimeter_rectangle(grade):
    l = random.randint(2, 20)
    w = random.randint(1, 15)
    return f"Perimeter of rectangle length={l} and width={w} = ?", 2*(l+w)

# advanced
def gen_function_eval(grade):
    a = random.randint(1,5)
    b = random.randint(0,10)
    x = random.randint(1,10)
    return f"If f(x) = {a}x + {b}, find f({x}).", a*x + b

def gen_set_membership(grade):
    A = set(random.sample(range(1,25), 5))
    x = random.choice(list(A))
    return f"Given set A = {sorted(A)}. Is {x} in A? Answer 'yes' or 'no'.", "yes"

def gen_trig_basic(grade):
    choices = [(30,0.5),(45, round(math.sqrt(2)/2,3)), (60, round(math.sqrt(3)/2,3))]
    ang, val = random.choice(choices)
    return f"What is sin({ang}°)? (approx)", val

def gen_slope(grade):
    x1 = random.randint(0,5); y1 = random.randint(0,5)
    x2 = x1 + random.randint(1,6); y2 = y1 + random.randint(-3,6)
    s = round((y2-y1)/(x2-x1), 3)
    return f"Find slope of line through ({x1},{y1}) and ({x2},{y2}).", s

def gen_matrix_add(grade):
    a,b,c,d = [random.randint(0,5) for _ in range(4)]
    e,f_,g,h = [random.randint(0,5) for _ in range(4)]
    return f"Add matrices [[{a},{b}],[{c},{d}]] + [[{e},{f_}],[{g},{h}]]. Write result [[x,y],[z,w]].", f"[[{a+e},{b+f_}],[{c+g},{d+h}]]"

# ---------------------------
# Grade 4-5 special generators
# ---------------------------
def gen_factors_multiples(grade):
    typ = random.choice(['factor_check','common_multiple','gcf'])
    if typ == 'factor_check':
        a = random.randint(2,12)
        m = a * random.randint(2,6)
        return f"Is {a} a factor of {m}? Answer 'yes' or 'no'.", "yes"
    elif typ == 'common_multiple':
        a = random.randint(2,8); b = random.randint(2,8)
        m = a
        while m % b != 0:
            m += a
        return f"Find a small common multiple of {a} and {b}.", m
    else:
        a = random.randint(2, 12); b = random.randint(2, 12)
        return f"Find the GCF (HCF) of {a} and {b}.", math.gcd(a,b)

def gen_decimals(grade):
    typ = random.choice(['add','sub','mul'])
    if typ == 'add':
        a = round(random.uniform(0.1, 9.9),2); b = round(random.uniform(0.1, 9.9),2)
        return f"{a} + {b} = ? (round to 2 decimals)", round(a+b,2)
    if typ == 'sub':
        a = round(random.uniform(1, 15),2); b = round(random.uniform(0.1, min(9.9, a-0.1)),2)
        return f"{a} - {b} = ? (round to 2 decimals)", round(a-b,2)
    return f"{round(random.uniform(0.5,5),2)} × {round(random.uniform(0.5,5),2)} = ? (round to 2 decimals)", round(random.uniform(0.5,5)*random.uniform(0.5,5),2)

def gen_time_measurement(grade):
    typ = random.choice(['convert','add','read'])
    if typ == 'convert':
        mins = random.choice([15,30,45,60,75,90,120])
        h = mins//60; r = mins%60
        return f"Convert {mins} minutes to hours:minutes (H:M).", f"{h}:{r:02d}"
    if typ == 'add':
        h1 = random.randint(0,3); m1 = random.choice([0,15,30,45])
        h2 = random.randint(0,3); m2 = random.choice([0,15,30,45])
        tot = (h1*60+m1)+(h2*60+m2)
        return f"Add times {h1}:{m1:02d} + {h2}:{m2:02d} (H:M).", f"{tot//60}:{tot%60:02d}"
    h = random.randint(1,12); m = random.choice([0,15,30,45])
    return f"What time is shown: {h}:{m:02d}? (Write H:M)", f"{h}:{m:02d}"

# ---------------------------
# Shapes & shape-questions
# ---------------------------
def draw_shape_image(shape, params, size=360):
    img = Image.new("RGBA", (size,size), (255,255,255,255))
    draw = ImageDraw.Draw(img)
    if shape == 'square':
        s = params.get('s_px', 120)
        x0 = (size - s)//2; y0 = (size - s)//2
        draw.rectangle([x0,y0,x0+s,y0+s], outline="black", width=4)
    elif shape == 'rectangle':
        l = params.get('l_px', 160); w = params.get('w_px', 100)
        x0 = (size - l)//2; y0 = (size - w)//2
        draw.rectangle([x0,y0,x0+l,y0+w], outline="black", width=4)
    elif shape == 'circle':
        r = params.get('r_px', 70); cx = size//2; cy = size//2
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline="black", width=4)
    else:  # triangle
        base = params.get('base_px',160); h = params.get('h_px',120); cx = size//2
        pts = [(cx, (size-h)//2), (cx-base//2, (size+h)//2), (cx+base//2, (size+h)//2)]
        draw.polygon(pts, outline="black")
    return img

def gen_shape_question(grade):
    shape = random.choice(['square','rectangle','circle','triangle'])
    if shape == 'square':
        side = random.randint(3+grade, 8+grade)
        q = f"A square has side = {side} cm. What is its area?"
        ans = side*side; params = {'s_px': int(side*6)}
    elif shape == 'rectangle':
        l = random.randint(4+grade, 10+grade); w = random.randint(2+grade, 6+grade)
        q = f"A rectangle has length = {l} cm and width = {w} cm. What is its perimeter?"
        ans = 2*(l+w); params = {'l_px':int(l*10),'w_px':int(w*8)}
    elif shape == 'circle':
        r = random.randint(3+grade, 7+grade)
        q = f"A circle has radius = {r} cm. Approximate circumference (π≈3.14)."
        ans = round(2*3.14*r,1); params = {'r_px':int(r*6)}
    else:
        b = random.randint(4+grade, 9+grade); h = random.randint(3+grade, 8+grade)
        q = f"A triangle has base = {b} cm and height = {h} cm. What is its area?"
        ans = round(0.5*b*h,1); params = {'base_px':int(b*10),'h_px':int(h*8)}
    img = draw_shape_image(shape, params)
    # build choices for MCQ
    choices = []
    if isinstance(ans, (int,float)):
        choices.append(ans)
        for _ in range(3):
            delta = max(1, int(abs(ans)*0.15) or 1)
            wrong = ans + random.choice([-1,1])*random.randint(1, delta+3)
            if isinstance(ans, float): wrong = round(wrong,1)
            choices.append(wrong)
        random.shuffle(choices)
    return {"type":"shape","question":q,"answer":ans,"choices":choices,"image":img}

# ---------------------------
# Topic chooser per grade & unified generator
# ---------------------------
def choose_topic(grade):
    if grade <= 3:
        return random.choice(['addition','subtraction','multiplication','division','comparison','story'])
    elif grade in (4,5):
        return random.choice(['addition','subtraction','multiplication','division','comparison','story',
                              'fractions_add','fraction_mixed','lcm','hcf','percentage','profit',
                              'area_rect','perimeter_rect','mul_basic','factors_multiples','decimals','time_measurement'])
    elif grade <= 8:
        return random.choice(['fractions_add','fraction_mixed','lcm','hcf','percentage','profit','area_rect','perimeter_rect','mul_basic'])
    else:
        return random.choice(['function','sets','trig','slope','fraction_mixed','matrix'])

def generate_question_for_grade(grade):
    topic = choose_topic(grade)
    # mapping
    if topic == 'addition':
        q,a = gen_addition(grade); return {'type':'math','topic':'addition','question':q,'answer':a}
    if topic == 'subtraction':
        q,a = gen_subtraction(grade); return {'type':'math','topic':'subtraction','question':q,'answer':a}
    if topic == 'multiplication' or topic == 'mul_basic':
        q,a = gen_multiplication(grade); return {'type':'math','topic':'multiplication','question':q,'answer':a}
    if topic == 'division':
        q,a = gen_division(grade); return {'type':'math','topic':'division','question':q,'answer':a}
    if topic == 'comparison':
        q,a = gen_comparison(grade); return {'type':'math','topic':'comparison','question':q,'answer':a}
    if topic == 'story':
        q,a = gen_story(grade); return {'type':'math','topic':'story','question':q,'answer':a}
    if topic == 'fractions_add':
        q,a = gen_fraction_add(grade); return {'type':'math','topic':'fractions','question':q,'answer':a}
    if topic == 'fraction_mixed':
        q,a = gen_fraction_mixed(grade); return {'type':'math','topic':'fractions_mixed','question':q,'answer':a}
    if topic == 'lcm':
        q,a = gen_lcm(grade); return {'type':'math','topic':'lcm','question':q,'answer':a}
    if topic == 'hcf':
        q,a = gen_hcf(grade); return {'type':'math','topic':'hcf','question':q,'answer':a}
    if topic == 'percentage':
        q,a = gen_percentage(grade); return {'type':'math','topic':'percentage','question':q,'answer':a}
    if topic == 'profit':
        q,a = gen_profit(grade); return {'type':'math','topic':'profit','question':q,'answer':a}
    if topic == 'area_rect':
        q,a = gen_area_rectangle(grade); return {'type':'math','topic':'area','question':q,'answer':a}
    if topic == 'perimeter_rect':
        q,a = gen_perimeter_rectangle(grade); return {'type':'math','topic':'perimeter','question':q,'answer':a}
    if topic == 'function':
        q,a = gen_function_eval(grade); return {'type':'math','topic':'function','question':q,'answer':a}
    if topic == 'sets':
        q,a = gen_set_membership(grade); return {'type':'math','topic':'sets','question':q,'answer':a}
    if topic == 'trig':
        q,a = gen_trig_basic(grade); return {'type':'math','topic':'trig','question':q,'answer':a}
    if topic == 'slope':
        q,a = gen_slope(grade); return {'type':'math','topic':'slope','question':q,'answer':a}
    if topic == 'matrix':
        q,a = gen_matrix_add(grade); return {'type':'math','topic':'matrix','question':q,'answer':a}
    if topic == 'factors_multiples':
        q,a = gen_factors_multiples(grade); return {'type':'math','topic':'factors_multiples','question':q,'answer':a}
    if topic == 'decimals':
        q,a = gen_decimals(grade); return {'type':'math','topic':'decimals','question':q,'answer':a}
    if topic == 'time_measurement':
        q,a = gen_time_measurement(grade); return {'type':'math','topic':'time','question':q,'answer':a}
    # fallback
    q,a = gen_addition(grade); return {'type':'math','topic':'addition','question':q,'answer':a}

# ---------------------------
# Core game control: start level, next question, record answer
# ---------------------------
def start_level(grade, level):
    # ensure unlocked
    unlocked = st.session_state['level_unlocked'].get(str(grade), [1])
    if level not in unlocked:
        return False
    # reset counters
    st.session_state['started'] = True
    st.session_state['question_index'] = 0
    st.session_state['correct_in_level'] = 0
    st.session_state['current_q'] = None
    st.session_state['current_ans'] = None
    st.session_state['current_choices'] = None
    st.session_state['question_start_time'] = None
    st.session_state['score'] = st.session_state.get('score', 0)
    st.session_state['recent_history'] = []
    st.session_state['level_results'] = []
    st.session_state['show_result'] = False
    st.session_state['last_result'] = None
    st.session_state['auto_clear'] = False
    next_question()
    return True

def next_question():
    if st.session_state['mode'] == 'Math Quiz':
        qdict = generate_question_for_grade(st.session_state['grade'])
    else:
        qdict = gen_shape_question(st.session_state['grade'])
    st.session_state['current_q'] = qdict
    st.session_state['current_ans'] = qdict['answer']
    st.session_state['current_choices'] = qdict.get('choices', None)
    st.session_state['question_start_time'] = time.time()
    st.session_state['shape_key'] = f"shape_{random.randint(100000,999999)}"
    # set flag to clear input safely on render
    st.session_state['auto_clear'] = True

def record_answer(given_raw):
    """
    given_raw: can be string, int, float or empty string
    This function should be called only when user explicitly submits (Enter or Submit).
    """
    qdict = st.session_state.get('current_q', {})
    correct = st.session_state.get('current_ans')
    topic = qdict.get('topic', None)
    time_taken = None
    try:
        if st.session_state.get('question_start_time'):
            time_taken = round(time.time() - st.session_state['question_start_time'], 2)
    except:
        time_taken = None

    given = given_raw
    # normalize blanks
    if isinstance(given, str) and given.strip() == '':
        given = ''

    # Evaluate correctness robustly
    is_correct = False
    try:
        if isinstance(correct, dict):
            # fraction dict with 'fraction' and 'decimal'
            frac = correct.get('fraction')
            dec = correct.get('decimal')
            if isinstance(given, str) and given.strip() == frac:
                is_correct = True
            else:
                try:
                    if abs(float(given) - float(dec)) <= 0.05:
                        is_correct = True
                except:
                    is_correct = False
        elif isinstance(correct, (int, float)):
            try:
                if abs(float(given) - float(correct)) <= 0.05:
                    is_correct = True
            except:
                # compare strings
                try:
                    if str(given).strip().lower() == str(correct).strip().lower():
                        is_correct = True
                except:
                    is_correct = False
        else:
            if str(given).strip().lower() == str(correct).strip().lower():
                is_correct = True
    except Exception:
        is_correct = False

    # question serial in level is current index + 1
    q_no = st.session_state['question_index'] + 1

    detail = {
        "q_no": q_no,
        "question": qdict.get('question', ''),
        "given": given,
        "correct_answer": correct,
        "is_correct": bool(is_correct),
        "time_taken": time_taken,
        "topic": topic,
        "timestamp": datetime.utcnow().isoformat()
    }
    # append detail
    st.session_state['level_results'].append(detail)

    # update counters
    st.session_state['question_index'] += 1
    if is_correct:
        st.session_state['correct_in_level'] += 1
        st.session_state['score'] = st.session_state.get('score',0) + 10
    else:
        if topic:
            st.session_state['weak_topics'][topic] = st.session_state['weak_topics'].get(topic, 0) + 1

    # append short history
    st.session_state['recent_history'].append({'q': detail['question'], 'given': detail['given'], 'correct': detail['is_correct']})

    # level finished?
    if st.session_state['question_index'] >= QUESTIONS_PER_LEVEL:
        # compute result
        total = st.session_state['question_index']
        correct = st.session_state['correct_in_level']
        percent = int(correct/total*100) if total > 0 else 0
        passed = percent >= PASS_PERCENT
        last = {
            "total": total,
            "correct": correct,
            "percent": percent,
            "passed": passed,
            "details": st.session_state['level_results'][:]
        }
        st.session_state['last_result'] = last
        st.session_state['show_result'] = True

        # save in session level_progress
        g = str(st.session_state['grade'])
        lvl = str(st.session_state['current_level'])
        st.session_state['level_progress'].setdefault(g, {})[lvl] = last

        # unlock next level if passed
        if passed:
            # ensure uniqueness
            unlocked = st.session_state['level_unlocked'].setdefault(str(st.session_state['grade']), [1])
            next_lvl = st.session_state['current_level'] + 1
            if next_lvl <= LEVELS_PER_GRADE and next_lvl not in unlocked:
                unlocked.append(next_lvl)
                st.session_state['level_unlocked'][str(st.session_state['grade'])] = unlocked

        # persist progress JSON
        save_json({'level_unlocked': st.session_state['level_unlocked'], 'level_progress': st.session_state['level_progress']})

        # append to CSV leaderboard: one row per question
        rows = []
        for d in st.session_state['level_results']:
            rows.append({
                "timestamp": d['timestamp'],
                "player": st.session_state.get('player_name','Player'),
                "grade": st.session_state.get('grade'),
                "level": st.session_state.get('current_level'),
                "q_no": d['q_no'],
                "question": d['question'],
                "given": d['given'],
                "correct_answer": d['correct_answer'],
                "is_correct": int(d['is_correct']),
                "time_taken": d['time_taken'],
                "percent_level": percent
            })
        append_leaderboard(rows)
    else:
        # go to next question
        next_question()

# ---------------------------
# UI rendering: header & sidebar
# ---------------------------
def render_header():
    st.markdown(f"<div class='app-title'>{APP_TITLE} {PAGE_ICON}</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Interactive AI-assisted math practice — gamified & graded (Grades 2–10)</div>", unsafe_allow_html=True)

def render_sidebar():
    st.sidebar.header("Player & Settings")
    name = st.sidebar.text_input("Player name", value=st.session_state.get('player_name','Player'))
    st.session_state['player_name'] = name

    grade = st.sidebar.selectbox("Grade", options=list(range(2,11)), index=st.session_state.get('grade',5)-2)
    st.session_state['grade'] = grade

    mode = st.sidebar.radio("Mode", options=["Math Quiz","Shape Challenge"], index=0 if st.session_state.get('mode','Math Quiz')=='Math Quiz' else 1)
    st.session_state['mode'] = mode

    st.sidebar.markdown("---")
    st.sidebar.write(f"Current Level: {st.session_state.get('current_level',1)}")
    st.sidebar.write(f"Score (session): {st.session_state.get('score',0)}")
    st.sidebar.write(f"Weak topics: {st.session_state.get('weak_topics',{})}")

    tlim = st.sidebar.slider("Time limit (seconds)", min_value=10, max_value=120, value=st.session_state.get('time_limit',45))
    st.session_state['time_limit'] = tlim

    if st.sidebar.button("Save Progress"):
        ok = save_json({'level_unlocked': st.session_state['level_unlocked'], 'level_progress': st.session_state['level_progress']})
        if ok:
            st.sidebar.success("Progress saved to JSON.")
        else:
            st.sidebar.error("Save failed.")

    if st.sidebar.button("Export Leaderboard CSV"):
        if os.path.exists(LEADERBOARD_FILE):
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                st.sidebar.download_button("Download Leaderboard", data=f.read(), file_name="leaderboard.csv")
        else:
            st.sidebar.info("Leaderboard empty.")

# ---------------------------
# Level selector UI (shows all 20 levels and lock status)
# ---------------------------
def render_level_selector():
    st.markdown("### 🎯 Choose Grade & Level")
    col1, col2 = st.columns([3,1])
    with col1:
        # show grade and choose level number via number_input but also visually show lock/unlock grid
        lvl = st.number_input("Level (1–20)", min_value=1, max_value=LEVELS_PER_GRADE, value=st.session_state.get('current_level',1))
        st.session_state['current_level'] = int(lvl)
    with col2:
        if st.button("Start Level"):
            g = st.session_state['grade']
            lvl = st.session_state['current_level']
            unlocked = st.session_state['level_unlocked'].get(str(g), [1])
            if lvl in unlocked:
                ok = start_level(g, lvl)
                if not ok:
                    st.error("Cannot start: level locked.")
                else:
                    st.experimental_rerun = getattr(st, "rerun", None)
                    st.rerun()
            else:
                st.error("Level locked. Please pass previous levels to unlock.")

    st.markdown("#### Levels")
    grade_str = str(st.session_state.get('grade'))
    unlocked = st.session_state['level_unlocked'].get(grade_str, [1])
    cols = st.columns(5)
    for i in range(1, LEVELS_PER_GRADE+1):
        col = cols[(i-1) % 5]
        with col:
            if i in unlocked:
                if st.button(f"Level {i}", key=f"lv_{grade_str}_{i}"):
                    st.session_state['current_level'] = i
                    ok = start_level(st.session_state['grade'], i)
                    if ok:
                        st.experimental_rerun = getattr(st, "rerun", None)
                        st.rerun()
            else:
                st.button(f"🔒 Level {i}", key=f"lv_locked_{grade_str}_{i}", disabled=True)

# ---------------------------
# Main UI: question rendering and result screens
# ---------------------------
def render_game_ui():
    # progress header
    st.markdown("---")
    st.write(f"Grade {st.session_state['grade']} — Level {st.session_state['current_level']} | Question {min(st.session_state['question_index']+1, QUESTIONS_PER_LEVEL)}/{QUESTIONS_PER_LEVEL}")
    st.progress(min(100, int((st.session_state['question_index']/QUESTIONS_PER_LEVEL)*100)))

    # ensure a question exists
    if not st.session_state.get('current_q'):
        next_question()
        st.rerun()

    # if level ended show result summary
    if st.session_state.get('show_result'):
        res = st.session_state['last_result']
        st.markdown("---")
        if res.get('passed'):
            st.balloons()
            st.success(f"🎉 Level Passed — {res['correct']}/{res['total']} ({res['percent']}%)")
        else:
            st.error(f"Level Ended — {res['correct']}/{res['total']} ({res['percent']}%)")

        st.markdown("### Level Summary")
        st.write(f"- Correct: {res['correct']}")
        st.write(f"- Total: {res['total']}")
        st.write(f"- Percentage: {res['percent']}%")
        st.write("")

        st.markdown("#### Question-wise details")
        details = res.get('details', [])
        if details:
            df_rows = []
            for d in details:
                df_rows.append({
                    "Q#": d['q_no'],
                    "Question": d['question'],
                    "Your Answer": d['given'],
                    "Correct Answer": d['correct_answer'],
                    "Result": "✅" if d['is_correct'] else "❌",
                    "Time(s)": d['time_taken']
                })
            df = pd.DataFrame(df_rows)
            st.dataframe(df, use_container_width=True)
            # provide download button for this level results
            csv_bytes = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Level Results (CSV)", data=csv_bytes, file_name=f"mathhero_grade{st.session_state['grade']}_level{st.session_state['current_level']}.csv")
        else:
            st.write("No details recorded for this level.")

        # buttons: retry or next
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Retry Level"):
                start_level(st.session_state['grade'], st.session_state['current_level'])
                st.rerun()
        with c2:
            if res.get('passed'):
                if st.button("Go to Next Level"):
                    # unlock and start next level
                    current = st.session_state['current_level']
                    if current < LEVELS_PER_GRADE:
                        st.session_state['current_level'] = current + 1
                        # ensure unlocked
                        unlocked = st.session_state['level_unlocked'].setdefault(str(st.session_state['grade']), [1])
                        if (current+1) not in unlocked:
                            unlocked.append(current+1)
                            st.session_state['level_unlocked'][str(st.session_state['grade'])] = unlocked
                        start_level(st.session_state['grade'], st.session_state['current_level'])
                        st.rerun()
                    else:
                        st.success("You've completed all levels!")
        # leader-board save already done on level end, but expose button to export entire CSV
        st.markdown("---")
        if os.path.exists(LEADERBOARD_FILE):
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                data = f.read()
            st.download_button("Download Full Leaderboard CSV", data=data, file_name="math_hero_leaderboard.csv")
        st.stop()

    # Normal question rendering
    qdict = st.session_state['current_q']

    st.markdown("### Question")
    if qdict['type'] == 'math':
        st.subheader("Math Question")
        st.write(f"Topic: {qdict.get('topic','General')}")
        st.write(qdict['question'])

        # safe clear text input
        if st.session_state.get('auto_clear'):
            st.session_state['ui_input'] = ""
            st.session_state['auto_clear'] = False

        # text input — Enter triggers on_change which calls record_answer()
        st.text_input("Type your answer and press Enter", key="ui_input", on_change=lambda: handle_text_submit())

        # time left indicator
        elapsed = time.time() - st.session_state.get('question_start_time', time.time())
        remaining = max(0, int(st.session_state.get('time_limit',45) - elapsed))
        st.write(f"Time left: {remaining} seconds")
        if remaining <= 0:
            # timed out
            record_answer("")
            st.rerun()
    else:
        st.subheader("Shape Challenge")
        # show image
        buf = io.BytesIO()
        img = qdict['image']
        img.save(buf, format="PNG")
        st.image(buf)
        st.write(qdict['question'])
        # if MCQ choices exist, show radio with placeholder + Submit button
        if qdict.get('choices'):
            options = ["Select an answer"] + [str(c) for c in qdict.get('choices',[])]
            key = st.session_state.get('shape_key') or f"shape_{random.randint(100000,999999)}"
            selected = st.radio("Choose your answer 👇", options=options, index=0, key=key)
            if selected != "Select an answer":
                if st.button("Submit Answer"):
                    # try numeric conversion
                    try:
                        val = float(selected)
                        if val.is_integer(): val = int(val)
                    except:
                        val = selected
                    record_answer(val)
                    st.rerun()
            else:
                st.info("Select an answer and press Submit.")
        else:
            # fallback to typed answer with Enter
            if st.session_state.get('auto_clear'):
                st.session_state['ui_input'] = ""
                st.session_state['auto_clear'] = False
            st.text_input("Type answer and press Enter", key="ui_input", on_change=lambda: handle_text_submit())

    # recent history
    st.markdown("---")
    st.subheader("Recent History")
    for h in st.session_state.get('recent_history', [])[-5:][::-1]:
        st.write(f"- {h['q']} — {'✅' if h['correct'] else '❌'} (You: {h['given']})")

# wrapper to call record_answer from text_input on_change safely
def handle_text_submit():
    # the text input field key is 'ui_input'. We should capture value and clear manually.
    val = st.session_state.get('ui_input','')
    # for numeric answers try conversion
    v = val
    try:
        # allow integer conversion
        if v.strip() == "":
            v2 = ""
        else:
            if '.' in v:
                v2 = float(v)
            else:
                v2 = int(v)
            v = v2
    except:
        v = val  # leave as string
    # call record function
    record_answer(v)
    # after recording, we do NOT immediately set ui_input to "" here because changing session_state key inside callback is safe.
    st.session_state['ui_input'] = ""

# ---------------------------
# Top-level main function
# ---------------------------
def main():
    render_header()
    render_sidebar()

    # layout: left column for main content, right column for a progress card
    left, right = st.columns([3,1])

    with left:
        render_level_selector()
        st.markdown("---")
        if not st.session_state.get('started'):
            st.info("Start a level to begin. Each level has 10 questions. You must score at least 70% to pass.")
            st.stop()
        render_game_ui()

    with right:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown(f"**Player:** {st.session_state.get('player_name','Player')}")
        st.markdown(f"**Grade:** {st.session_state.get('grade')}")
        st.markdown(f"**Level:** {st.session_state.get('current_level')}")
        st.markdown(f"**Score:** {st.session_state.get('score',0)}")
        st.markdown("---")
        st.markdown("**Progress**")
        # show unlocked levels for current grade
        unlocked = st.session_state['level_unlocked'].get(str(st.session_state.get('grade')), [1])
        st.write(f"Unlocked levels: {sorted(unlocked)}")
        st.markdown("---")
        if st.button("Export Progress (JSON)"):
            data = {'level_unlocked': st.session_state['level_unlocked'], 'level_progress': st.session_state['level_progress']}
            st.download_button("Download JSON", data=json.dumps(data, indent=2), file_name="math_hero_progress_export.json")
        st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
