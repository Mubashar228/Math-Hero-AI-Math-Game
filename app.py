# math_hero_v7.py
"""
Math Hero v7 — Gamified AI Math Challenge (complete)
- Grades 2-10, 20 levels per grade, 10 questions per level
- Math Quiz + Shape Challenge
- Grade 4-5 extra topics: Factors & Multiples, Decimals, Time Measurement
- Detailed per-question results saved and appended to CSV leaderboard
- Enter-to-submit for text answers; radio + Submit for shape answers (placeholder + unique key)
- Save/Load progress (JSON) + export leaderboard CSV
"""

import streamlit as st
import random
import math
import json
import csv
import os
import time
from PIL import Image, ImageDraw
import io
from datetime import datetime
import pandas as pd

# ---------------------------
# Config
# ---------------------------
APP_TITLE = "Math Hero v7 — Gamified AI Math Challenge"
PAGE_ICON = "🦸‍♂️"
LEVELS_PER_GRADE = 20
QUESTIONS_PER_LEVEL = 10
PASS_PERCENT = 70
SAVE_FILE = "math_hero_progress_v7.json"
LEADERBOARD_FILE = "math_hero_leaderboard_v7.csv"

st.set_page_config(page_title=APP_TITLE, page_icon=PAGE_ICON, layout="wide")

# ---------------------------
# Utilities: persistence & leaderboard append
# ---------------------------
def load_progress(path=SAVE_FILE):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_progress(data, path=SAVE_FILE):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def append_leaderboard_rows(rows, path=LEADERBOARD_FILE):
    """
    rows: list of dicts with columns:
    timestamp, player, grade, level, q_no, question, given, correct_answer, is_correct, time_taken, percent_level
    """
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
        print("Leaderboard append error:", e)
        return False

# ---------------------------
# Session state init
# ---------------------------
def init_state():
    defaults = {
        "player": "Player",
        "grade": 5,
        "mode": "Math Quiz",
        "current_level": 1,
        "level_unlocked": {g:1 for g in range(2,11)},
        "level_progress": {str(g):{} for g in range(2,11)},
        "started": False,
        "question_in_level": 0,
        "correct_in_level": 0,
        "current_q": None,
        "current_ans": None,
        "current_choices": None,
        "question_start_time": None,
        "time_limit": 45,
        "score": 0,
        "history": [],
        "weak_topics": {},
        "show_result": False,
        "last_result": None,
        "ui_input": "",
        "shape_choice_key": None,
        "auto_clear_flag": False,
        # per-level detailed question list (list of dicts)
        "level_results": []
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Load saved progress if present (merge safely)
_progress_store = load_progress()
if _progress_store:
    # merge only if keys present — keep current session_state values where present
    st.session_state["level_progress"] = _progress_store.get("level_progress", st.session_state["level_progress"])
    st.session_state["level_unlocked"] = _progress_store.get("level_unlocked", st.session_state["level_unlocked"])

# ---------------------------
# Question generators
# ---------------------------
# Basic operations (grades 2-4)
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
    a = random.randint(0, 20)
    b = random.randint(0, 20)
    ans = ">" if a > b else "<" if a < b else "="
    return f"Which is greater: {a} or {b}? Write '>' or '<' or '='.", ans

def gen_simple_story(grade):
    a = random.randint(5, 30)
    b = random.randint(1, 10)
    return f"Ali had {a} apples. He gave {b} to Ahmed. How many left?", a - b

# Fractions & related
def gen_fractions_add(grade):
    d = random.randint(2,8)
    a = random.randint(1, d-1)
    b = random.randint(1, d-1)
    num = a+b
    den = d
    g = math.gcd(num, den)
    frac_s = f"{num//g}/{den//g}"
    dec = round(num/den, 3)
    return f"{a}/{d} + {b}/{d} = ? (fraction or decimal)", {"fraction":frac_s, "decimal":dec}

def gen_fraction_to_mixed(grade):
    num = random.randint(5, 20)
    den = random.randint(2, 8)
    whole = num // den
    rem = num % den
    if rem == 0:
        return f"Write {num}/{den} as a mixed number.", str(whole)
    else:
        return f"Write {num}/{den} as a mixed number.", f"{whole} {rem}/{den}"

# LCM/HCF
def gen_lcm(grade):
    a = random.randint(2,20)
    b = random.randint(2,20)
    return f"Find LCM of {a} and {b}.", (a*b)//math.gcd(a,b)

def gen_hcf(grade):
    a = random.randint(2,50)
    b = random.randint(2,50)
    return f"Find HCF (GCD) of {a} and {b}.", math.gcd(a,b)

# Percent/profit/area
def gen_percentage(grade):
    base = random.randint(10,200)
    pct = random.choice([5,10,15,20,25])
    return f"What is {pct}% of {base}?", round(base*pct/100,2)

def gen_profit_loss(grade):
    cp = random.randint(50,500)
    pct = random.choice([5,10,15,20,25])
    sp = round(cp*(1 + pct/100), 2)
    return f"Cost price = {cp}, profit = {pct}%. What is selling price?", sp

def gen_area_rectangle(grade):
    l = random.randint(2,20)
    w = random.randint(1,15)
    return f"Area of rectangle length={l} and width={w} = ?", l*w

def gen_perimeter_rectangle(grade):
    l = random.randint(2,20)
    w = random.randint(1,15)
    return f"Perimeter of rectangle length={l} and width={w} = ?", 2*(l+w)

# Advanced grade 9-10
def gen_function_eval(grade):
    a = random.randint(1,5)
    b = random.randint(0,10)
    x = random.randint(1,10)
    return f"If f(x) = {a}x + {b}, find f({x}).", a*x + b

def gen_set_membership(grade):
    A = set(random.sample(range(1,20),5))
    x = random.choice(list(A))
    return f"Given A = {sorted(A)}. Is {x} in A? Answer 'yes' or 'no'.", "yes"

def gen_trig_basic(grade):
    choice = random.choice([(30,0.5),(45, round(math.sqrt(2)/2,3)), (60, round(math.sqrt(3)/2,3))])
    ang, val = choice
    return f"What is sin({ang}°)? (approx)", val

def gen_slope(grade):
    x1 = random.randint(0,5)
    y1 = random.randint(0,5)
    x2 = x1 + random.randint(1,6)
    y2 = y1 + random.randint(-3,6)
    s = round((y2-y1)/(x2-x1),3)
    return f"Find slope of line through ({x1},{y1}) and ({x2},{y2}).", s

def gen_matrix_add(grade):
    a,b,c,d = [random.randint(0,5) for _ in range(4)]
    e,f_,g,h = [random.randint(0,5) for _ in range(4)]
    q = f"Add matrices [[{a},{b}],[{c},{d}]] + [[{e},{f_}],[{g},{h}]]. Write result [[x,y],[z,w]]."
    ans = f"[[{a+e},{b+f_}],[{c+g},{d+h}]]"
    return q, ans

# ---------------------------
# New Grade 4-5 generators: Factors & Multiples, Decimals, Time Measurement
# ---------------------------
def gen_factors_multiples(grade):
    kind = random.choice(['factor_check','common_multiple','gcf_simple'])
    if kind == 'factor_check':
        base = random.randint(2, 12)
        multiple = base * random.randint(2,6)
        q = f"Is {base} a factor of {multiple}? Answer 'yes' or 'no'."
        ans = 'yes'
        return q, ans
    elif kind == 'common_multiple':
        a = random.randint(2, 8)
        b = random.randint(2, 8)
        # find a small common multiple
        m = a
        while m % b != 0:
            m += a
        q = f"Find a common multiple of {a} and {b} (small)."
        return q, m
    else:
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        g = math.gcd(a,b)
        q = f"Find the GCF (HCF) of {a} and {b}."
        return q, g

def gen_decimals_question(grade):
    kind = random.choice(['add','sub','mul'])
    if kind == 'add':
        a = round(random.uniform(0.1, 9.9), 2)
        b = round(random.uniform(0.1, 9.9), 2)
        q = f"{a} + {b} = ? (round to 2 decimals)"
        ans = round(a + b, 2)
        return q, ans
    elif kind == 'sub':
        a = round(random.uniform(1.0, 15.0), 2)
        b = round(random.uniform(0.1, min(9.9, a-0.1)), 2)
        q = f"{a} - {b} = ? (round to 2 decimals)"
        ans = round(a - b, 2)
        return q, ans
    else:
        a = round(random.uniform(0.5, 5.0), 2)
        b = round(random.uniform(0.5, 5.0), 2)
        q = f"{a} × {b} = ? (round to 2 decimals)"
        ans = round(a * b, 2)
        return q, ans

def gen_time_measurement(grade):
    kind = random.choice(['convert_minutes','add_time','read_clock'])
    if kind == 'convert_minutes':
        mins = random.choice([15,30,45,60,90,120,75,135])
        q = f"Convert {mins} minutes into hours and minutes (format H:M)."
        hours = mins // 60
        rem = mins % 60
        ans = f"{hours}:{rem:02d}"
        return q, ans
    elif kind == 'add_time':
        h1 = random.randint(0,3)
        m1 = random.choice([0,15,30,45])
        h2 = random.randint(0,3)
        m2 = random.choice([0,15,30,45])
        total_mins = (h1*60 + m1) + (h2*60 + m2)
        q = f"Add times {h1}:{m1:02d} + {h2}:{m2:02d}. Give answer as H:M."
        ans = f"{total_mins//60}:{total_mins%60:02d}"
        return q, ans
    else:
        h = random.randint(1,12)
        m = random.choice([0,15,30,45])
        q = f"What time is shown: {h}:{m:02d}? (Write H:M)"
        ans = f"{h}:{m:02d}"
        return q, ans

# ---------------------------
# Shape drawing & question
# ---------------------------
def draw_shape(shape, params):
    size = 320
    img = Image.new("RGB", (size,size), color=(255,255,255))
    draw = ImageDraw.Draw(img)
    if shape == "square":
        s = params.get("s_px", 120)
        x0 = (size-s)//2
        y0 = (size-s)//2
        draw.rectangle([x0,y0,x0+s,y0+s], outline="black", width=4)
    elif shape == "rectangle":
        l = params.get("l_px",160)
        w = params.get("w_px",100)
        x0 = (size-l)//2
        y0 = (size-w)//2
        draw.rectangle([x0,y0,x0+l,y0+w], outline="black", width=4)
    elif shape == "circle":
        r = params.get("r_px",70)
        cx = size//2
        cy = size//2
        draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline="black", width=4)
    elif shape == "triangle":
        base = params.get("base_px",160)
        h = params.get("h_px",120)
        cx = size//2
        pts = [(cx, (size-h)//2), (cx-base//2, (size+h)//2), (cx+base//2, (size+h)//2)]
        draw.polygon(pts, outline="black")
    return img

def gen_shape_question(grade):
    shape = random.choice(["square","rectangle","circle","triangle"])
    if shape == "square":
        side = random.randint(3+grade, 8+grade)
        q = f"A square has side = {side} cm. What is its area?"
        ans = side*side
        params = {"s_px": int(side*6)}
    elif shape == "rectangle":
        l = random.randint(4+grade, 10+grade)
        w = random.randint(2+grade, 6+grade)
        q = f"A rectangle has length = {l} cm and width = {w} cm. What is its perimeter?"
        ans = 2*(l+w)
        params = {"l_px": int(l*10), "w_px": int(w*8)}
    elif shape == "circle":
        r = random.randint(3+grade, 7+grade)
        q = f"A circle has radius = {r} cm. Approximate circumference (π≈3.14)."
        ans = round(2*3.14*r,1)
        params = {"r_px": int(r*6)}
    else:
        b = random.randint(4+grade, 9+grade)
        h = random.randint(3+grade, 8+grade)
        q = f"A triangle has base = {b} cm and height = {h} cm. What is its area?"
        ans = round(0.5*b*h,1)
        params = {"base_px": int(b*10), "h_px": int(h*8)}
    img = draw_shape(shape, params)
    choices = []
    if isinstance(ans, (int, float)):
        choices.append(ans)
        for _ in range(3):
            delta = max(1, int(abs(ans)*0.15) or 1)
            wrong = ans + random.choice([-1,1])*random.randint(1, delta+3)
            if isinstance(ans, float):
                wrong = round(wrong,1)
            choices.append(wrong)
        random.shuffle(choices)
    return {"type":"shape","question":q,"answer":ans,"choices":choices,"image":img}

# ---------------------------
# Topic chooser & generator
# ---------------------------
def choose_topic(grade):
    # note: you can tune which grades use which topics
    if grade <= 3:
        return random.choice(["addition","subtraction","multiplication","division","comparison","story"])
    elif grade in (4,5):
        return random.choice([
            "addition","subtraction","multiplication","division","comparison","story",
            "fractions_add","fraction_mixed","lcm","hcf","percentage","profit",
            "area_rect","perimeter_rect","mul_basic",
            "factors_multiples","decimals","time_measurement"
        ])
    elif grade <= 8:
        return random.choice(["fractions_add","fraction_mixed","lcm","hcf","percentage","profit","area_rect","perimeter_rect","mul_basic"])
    else:
        return random.choice(["function","sets","trig","slope","fraction_mixed","matrix"])

def generate_math_question(grade):
    topic = choose_topic(grade)
    if topic == "addition":
        q,a = gen_addition(grade); return {"type":"math","topic":"addition","question":q,"answer":a}
    if topic == "subtraction":
        q,a = gen_subtraction(grade); return {"type":"math","topic":"subtraction","question":q,"answer":a}
    if topic == "multiplication" or topic=="mul_basic":
        q,a = gen_multiplication(grade); return {"type":"math","topic":"multiplication","question":q,"answer":a}
    if topic == "division":
        q,a = gen_division(grade); return {"type":"math","topic":"division","question":q,"answer":a}
    if topic == "comparison":
        q,a = gen_comparison(grade); return {"type":"math","topic":"comparison","question":q,"answer":a}
    if topic == "story":
        q,a = gen_simple_story(grade); return {"type":"math","topic":"story","question":q,"answer":a}
    if topic == "fractions_add":
        q,a = gen_fractions_add(grade); return {"type":"math","topic":"fractions","question":q,"answer":a}
    if topic == "fraction_mixed":
        q,a = gen_fraction_to_mixed(grade); return {"type":"math","topic":"fractions_mixed","question":q,"answer":a}
    if topic == "lcm":
        q,a = gen_lcm(grade); return {"type":"math","topic":"lcm","question":q,"answer":a}
    if topic == "hcf":
        q,a = gen_hcf(grade); return {"type":"math","topic":"hcf","question":q,"answer":a}
    if topic == "percentage":
        q,a = gen_percentage(grade); return {"type":"math","topic":"percentage","question":q,"answer":a}
    if topic == "profit":
        q,a = gen_profit_loss(grade); return {"type":"math","topic":"profit","question":q,"answer":a}
    if topic == "area_rect":
        q,a = gen_area_rectangle(grade); return {"type":"math","topic":"area","question":q,"answer":a}
    if topic == "perimeter_rect":
        q,a = gen_perimeter_rectangle(grade); return {"type":"math","topic":"perimeter","question":q,"answer":a}
    if topic == "function":
        q,a = gen_function_eval(grade); return {"type":"math","topic":"function","question":q,"answer":a}
    if topic == "sets":
        q,a = gen_set_membership(grade); return {"type":"math","topic":"sets","question":q,"answer":a}
    if topic == "trig":
        q,a = gen_trig_basic(grade); return {"type":"math","topic":"trig","question":q,"answer":a}
    if topic == "slope":
        q,a = gen_slope(grade); return {"type":"math","topic":"slope","question":q,"answer":a}
    if topic == "matrix":
        q,a = gen_matrix_add(grade); return {"type":"math","topic":"matrix","question":q,"answer":a}
    if topic == "factors_multiples":
        q,a = gen_factors_multiples(grade); return {"type":"math","topic":"factors_multiples","question":q,"answer":a}
    if topic == "decimals":
        q,a = gen_decimals_question(grade); return {"type":"math","topic":"decimals","question":q,"answer":a}
    if topic == "time_measurement":
        q,a = gen_time_measurement(grade); return {"type":"math","topic":"time","question":q,"answer":a}
    # fallback
    q,a = gen_addition(grade); return {"type":"math","topic":"addition","question":q,"answer":a}

# ---------------------------
# Core gameplay: start/next/record
# ---------------------------
def start_level(grade, level):
    unlocked = st.session_state["level_unlocked"].get(grade,1)
    if level > unlocked:
        return False
    st.session_state.update({
        "started": True,
        "question_in_level": 0,
        "correct_in_level": 0,
        "current_q": None,
        "current_ans": None,
        "current_choices": None,
        "history": [],
        "weak_topics": st.session_state.get("weak_topics", {}),
        "show_result": False,
        "last_result": None,
        "score": st.session_state.get("score", 0),
        "level_results": []
    })
    next_q()
    return True

def next_q():
    # generate question and store time
    if st.session_state["mode"] == "Math Quiz":
        qdict = generate_math_question(st.session_state["grade"])
    else:
        qdict = gen_shape_question(st.session_state["grade"])
    st.session_state["current_q"] = qdict
    st.session_state["current_ans"] = qdict["answer"]
    st.session_state["current_choices"] = qdict.get("choices")
    st.session_state["question_start_time"] = time.time()
    # unique key for radio widgets
    st.session_state["shape_choice_key"] = f"shape_choice_{random.randint(100000,999999)}"
    # request clearing text input on next render (no on_change triggered)
    st.session_state["auto_clear_flag"] = True
    # ensure ui_input is empty (we will clear safely in UI rendering)
    # Do NOT set st.session_state["ui_input"] here to avoid triggering on_change

def record_answer(given):
    """
    given: raw answer provided by user (string/number). This function is called only
    when user explicitly submits (Enter in text_input or Submit button for shapes).
    It records per-question details, updates counters, and either moves to next question
    or finishes level and saves details to CSV/JSON.
    """
    q = st.session_state.get("current_q")
    correct = st.session_state.get("current_ans")
    topic = q.get("topic") if q else None
    time_taken = None
    if st.session_state.get("question_start_time"):
        time_taken = round(time.time() - st.session_state["question_start_time"], 2)

    # Normalize given: try convert numeric answers to float/int when appropriate
    given_norm = given
    # if given is empty string treat as None
    if isinstance(given, str) and given.strip() == "":
        given_norm = ""
    # evaluation
    is_correct = False
    try:
        if isinstance(correct, dict):
            frac = correct.get("fraction")
            dec = correct.get("decimal")
            if isinstance(given_norm, str) and given_norm.strip() == frac:
                is_correct = True
            else:
                try:
                    if abs(float(given_norm) - float(dec)) <= 0.05:
                        is_correct = True
                except:
                    is_correct = False
        elif isinstance(correct, (int, float)):
            try:
                if abs(float(given_norm) - float(correct)) <= 0.05:
                    is_correct = True
            except:
                # try comparing as strings lowercase
                try:
                    if str(given_norm).strip().lower() == str(correct).strip().lower():
                        is_correct = True
                except:
                    is_correct = False
        else:
            if str(given_norm).strip().lower() == str(correct).strip().lower():
                is_correct = True
    except Exception:
        is_correct = False

    # build per-question detail dict
    q_text = q.get("question") if q else ""
    q_no = st.session_state.get("question_in_level",0) + 1
    detail = {
        "q_no": q_no,
        "question": q_text,
        "given": given_norm,
        "correct_answer": correct,
        "is_correct": is_correct,
        "time_taken": time_taken,
        "topic": topic,
        "timestamp": datetime.utcnow().isoformat()
    }
    st.session_state["level_results"].append(detail)

    # update counters
    st.session_state["question_in_level"] += 1
    if is_correct:
        st.session_state["correct_in_level"] += 1
        st.session_state["score"] = st.session_state.get("score",0) + 10
    else:
        # track weak topic
        if topic:
            st.session_state["weak_topics"][topic] = st.session_state["weak_topics"].get(topic,0) + 1

    # append short history for UI
    st.session_state["history"].append({
        "q": q_text,
        "given": given_norm,
        "correct": is_correct
    })

    # check level end
    if st.session_state["question_in_level"] >= QUESTIONS_PER_LEVEL:
        total = st.session_state["question_in_level"]
        correct_cnt = st.session_state["correct_in_level"]
        percent = int(correct_cnt/total*100) if total>0 else 0
        passed = percent >= PASS_PERCENT
        # prepare last_result including details
        st.session_state["last_result"] = {
            "total": total,
            "correct": correct_cnt,
            "percent": percent,
            "passed": passed,
            "details": st.session_state["level_results"][:]
        }
        # save into level_progress
        g = st.session_state["grade"]
        lvl = st.session_state["current_level"]
        st.session_state["level_progress"].setdefault(str(g), {})[str(lvl)] = st.session_state["last_result"]
        # unlock next level if passed
        if passed and lvl < LEVELS_PER_GRADE:
            st.session_state["level_unlocked"][g] = max(st.session_state["level_unlocked"].get(g,1), lvl+1)
        st.session_state["show_result"] = True

        # persist JSON progress
        save_progress({"level_progress": st.session_state["level_progress"], "level_unlocked": st.session_state["level_unlocked"]})

        # append per-question rows to CSV leaderboard
        # compose rows with percent info
        rows = []
        for d in st.session_state["level_results"]:
            rows.append({
                "timestamp": d["timestamp"],
                "player": st.session_state.get("player","Player"),
                "grade": st.session_state.get("grade"),
                "level": st.session_state.get("current_level"),
                "q_no": d["q_no"],
                "question": d["question"],
                "given": d["given"],
                "correct_answer": d["correct_answer"],
                "is_correct": int(d["is_correct"]),
                "time_taken": d["time_taken"],
                "percent_level": percent
            })
        append_leaderboard_rows(rows)

    else:
        # move to next question (only called when user submitted explicitly)
        next_q()

# ---------------------------
# UI: header & sidebar
# ---------------------------
def render_header():
    st.markdown(f"<h1 style='margin:0'>{APP_TITLE} {PAGE_ICON}</h1>", unsafe_allow_html=True)
    st.markdown("<div style='background:linear-gradient(90deg,#A6C0FE,#F68084); padding:6px; border-radius:8px;'>"
                "<b style='color:white'>Play, Learn and Level Up — Grades 2 to 10</b></div>", unsafe_allow_html=True)

def render_sidebar():
    st.sidebar.header("Player & Settings")
    player = st.sidebar.text_input("Player name", value=st.session_state.get("player","Player"))
    st.session_state["player"] = player

    grade = st.sidebar.selectbox("Grade", options=list(range(2,11)), index=st.session_state["grade"]-2)
    st.session_state["grade"] = grade

    mode = st.sidebar.radio("Mode", options=["Math Quiz","Shape Challenge"], index=0 if st.session_state["mode"]=="Math Quiz" else 1)
    st.session_state["mode"] = mode

    st.sidebar.markdown("---")
    st.sidebar.write(f"Level: {st.session_state['current_level']} (Unlocked: {st.session_state['level_unlocked'].get(st.session_state['grade'],1)})")
    st.sidebar.write(f"Score (session): {st.session_state.get('score',0)}")
    st.sidebar.write(f"Weak topics: {st.session_state.get('weak_topics',{})}")

    tlim = st.sidebar.slider("Time limit per question (seconds)", min_value=10, max_value=120, value=st.session_state["time_limit"])
    st.session_state["time_limit"] = tlim

    if st.sidebar.button("Save Progress Now"):
        ok = save_progress({"level_progress": st.session_state["level_progress"], "level_unlocked": st.session_state["level_unlocked"]})
        if ok:
            st.sidebar.success("Progress saved.")
        else:
            st.sidebar.error("Save failed.")

    if st.sidebar.button("Export Progress JSON"):
        st.sidebar.download_button("Download progress JSON", data=json.dumps({"level_progress": st.session_state["level_progress"], "level_unlocked": st.session_state["level_unlocked"]}), file_name="math_hero_progress_export.json")

    st.sidebar.markdown("---")
    st.sidebar.write("Leaderboard & Reports")
    if st.sidebar.button("Export Leaderboard CSV"):
        if os.path.exists(LEADERBOARD_FILE):
            with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
                st.sidebar.download_button("Download leaderboard", data=f.read(), file_name="leaderboard.csv")
        else:
            st.sidebar.info("No leaderboard yet.")

# ---------------------------
# Main UI
# ---------------------------
def main_ui():
    render_header()
    render_sidebar()

    col1, col2 = st.columns([3,1])
    with col1:
        lvl = st.number_input("Choose Level", min_value=1, max_value=LEVELS_PER_GRADE, value=st.session_state["current_level"])
        lvl = int(lvl)
        st.session_state["current_level"] = lvl
        if lvl > st.session_state["level_unlocked"].get(st.session_state["grade"],1):
            st.warning(f"Level {lvl} is locked. Complete previous levels to unlock.")
    with col2:
        if st.button("Start Level"):
            if st.session_state["current_level"] <= st.session_state["level_unlocked"].get(st.session_state["grade"],1):
                ok = start_level(st.session_state["grade"], st.session_state["current_level"])
                if not ok:
                    st.error("Cannot start locked level.")
                else:
                    st.experimental_rerun = getattr(st, "rerun", None)
                    st.rerun()
            else:
                st.error("This level is locked.")

    st.markdown("---")
    if not st.session_state["started"]:
        st.info(f"Press Start Level. Each level: {QUESTIONS_PER_LEVEL} questions. Pass = {PASS_PERCENT}%")
        sample = generate_math_question(st.session_state["grade"])
        st.write("Sample:", sample["question"])
        st.stop()

    # progress display
    st.write(f"Grade {st.session_state['grade']} — Level {st.session_state['current_level']} | Q {st.session_state['question_in_level']+1}/{QUESTIONS_PER_LEVEL}")
    st.progress(min(100, int((st.session_state['question_in_level']/QUESTIONS_PER_LEVEL)*100)))

    # ensure question exists
    if st.session_state["current_q"] is None:
        next_q()
        st.rerun()

    # show result screen when level ends
    if st.session_state["show_result"]:
        res = st.session_state["last_result"]
        st.markdown("---")
        if res["passed"]:
            st.balloons()
            st.success(f"Level Passed! {res['correct']}/{res['total']} ({res['percent']}%)")
        else:
            st.error(f"Level Failed. {res['correct']}/{res['total']} ({res['percent']}%)")

        st.markdown("**Level Summary**")
        st.write(f"- Correct: {res['correct']}")
        st.write(f"- Total: {res['total']}")
        st.write(f"- Percentage: {res['percent']}%")

        st.markdown("**Question-wise Details**")
        details = res.get("details", st.session_state.get("level_results", []))
        rows = []
        for i,d in enumerate(details, start=1):
            rows.append({
                "Q#": i,
                "Question": d.get("question"),
                "Your Answer": d.get("given"),
                "Correct Answer": d.get("correct_answer"),
                "Result": "✅" if d.get("is_correct") else "❌",
                "Time(s)": d.get("time_taken")
            })
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)
        else:
            st.write("No question details available.")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Retry Level"):
                start_level(st.session_state["grade"], st.session_state["current_level"])
                st.rerun()
        with c2:
            if res["passed"]:
                if st.button("Go to Next Level"):
                    if st.session_state["current_level"] < LEVELS_PER_GRADE:
                        st.session_state["current_level"] += 1
                        start_level(st.session_state["grade"], st.session_state["current_level"])
                        st.rerun()
                    else:
                        st.success("You completed all levels for this grade!")

        st.markdown("---")
        name = st.text_input("Save to leaderboard — player name", value=st.session_state.get("player","Player"))
        if st.button("Save to Leaderboard (CSV)"):
            # we already appended rows to csv at level end, but allow explicit save (re-append)
            # we'll append one more set with current timestamp if needed
            appended = append_leaderboard_rows([{
                "timestamp": datetime.utcnow().isoformat(),
                "player": name,
                "grade": st.session_state.get("grade"),
                "level": st.session_state.get("current_level"),
                "q_no": 0,
                "question": "Level summary save",
                "given": "",
                "correct_answer": "",
                "is_correct": "",
                "time_taken": "",
                "percent_level": res["percent"]
            }])
            if appended:
                st.success("Saved to leaderboard.")
            else:
                st.error("Save failed.")
        st.stop()

    # render current question
    qdict = st.session_state["current_q"]
    st.markdown("---")
    if qdict["type"] == "math":
        st.subheader("Math Question")
        st.write("Topic:", qdict.get("topic","General"))
        st.write(qdict["question"])

        # clear input safely if requested (setting ui_input to "" will NOT trigger on_change)
        if st.session_state.get("auto_clear_flag"):
            st.session_state["ui_input"] = ""
            st.session_state["auto_clear_flag"] = False

        # text input: Enter submits answer -> on_change triggers record_answer
        st.text_input("Type your answer and press Enter", key="ui_input",
                      on_change=lambda: record_answer(st.session_state.get("ui_input","")))

        # show time left
        elapsed = time.time() - st.session_state["question_start_time"] if st.session_state.get("question_start_time") else 0
        remaining = max(0, int(st.session_state.get("time_limit",45) - elapsed))
        st.write(f"Time left: {remaining} seconds")
        if remaining <= 0:
            # timeout -> record empty and proceed
            record_answer("")
            st.rerun()

    else:
        # shape challenge area
        st.subheader("Shape Challenge")
        buf = io.BytesIO()
        qdict["image"].save(buf, format="PNG")
        st.image(buf)
        st.write(qdict["question"])

        if qdict.get("choices"):
            # placeholder + unique key to avoid pre-selection bug
            options = ["Select an answer"] + [str(c) for c in qdict["choices"]]
            unique_key = st.session_state.get("shape_choice_key") or f"shape_choice_{random.randint(100000,999999)}"
            selected = st.radio("Choose your answer 👇", options=options, index=0, key=unique_key)
            if selected != "Select an answer":
                if st.button("Submit Answer"):
                    # convert numeric if possible
                    try:
                        val = float(selected)
                        # convert integers to int for nicer comparisons
                        if val.is_integer():
                            val = int(val)
                    except:
                        val = selected
                    record_answer(val)
                    st.rerun()
            else:
                st.info("👆 Please select an answer then press Submit.")
        else:
            # typed answer fallback
            if st.session_state.get("auto_clear_flag"):
                st.session_state["ui_input"] = ""
                st.session_state["auto_clear_flag"] = False
            st.text_input("Type answer and press Enter", key="ui_input", on_change=lambda: record_answer(st.session_state.get("ui_input","")))

    # footer: recent history
    st.markdown("---")
    st.subheader("Recent History (last 5)")
    history = st.session_state.get("history", [])
    for h in history[-5:][::-1]:
        st.write(f"- {h['q']} — {'✅' if h['correct'] else '❌'} (You: {h['given']})")

# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    main_ui()
    # ensure if started and no current question we generate one (rare)
    if st.session_state.get("started") and not st.session_state.get("current_q") and not st.session_state.get("show_result"):
        next_q()
        st.rerun()
