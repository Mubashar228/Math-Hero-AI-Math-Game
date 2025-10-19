# math_hero_v6.py
"""
Math Hero v6 — Full production-ready Streamlit app
- Grades 2-10, 20 levels per grade, 10 questions per level
- Math Quiz + Shape Challenge
- Fixes: shape radio auto-select bug solved (placeholder + unique key + explicit submit)
- Safe session_state updates and no NameError
- Save/Load progress, leaderboard, weak-topic tracking, hints, shapes drawn with PIL

Run:
    pip install streamlit pillow
    streamlit run math_hero_v6.py
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

# ---------------------------
# App configuration
# ---------------------------
APP_TITLE = "Math Hero v6 — Gamified AI Math Challenge"
PAGE_ICON = "🦸‍♂️"
LEVELS_PER_GRADE = 20
QUESTIONS_PER_LEVEL = 10
PASS_PERCENT = 70  # percent to pass a level
SAVE_FILE = "math_hero_progress_v6.json"
LEADERBOARD_FILE = "math_hero_leaderboard_v6.csv"

st.set_page_config(page_title=APP_TITLE, page_icon=PAGE_ICON, layout="wide")

# ---------------------------
# Utilities: persistence
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

def append_leaderboard_row(row, path=LEADERBOARD_FILE):
    header = ["timestamp","player","grade","level","score","percent"]
    first = not os.path.exists(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if first:
                writer.writerow(header)
            writer.writerow(row)
        return True
    except Exception:
        return False

# ---------------------------
# session state defaults
# ---------------------------
def init_state():
    defaults = {
        "player": "Player",
        "grade": 5,
        "mode": "Math Quiz",  # or "Shape Challenge"
        "current_level": 1,
        "level_unlocked": {g:1 for g in range(2,11)},
        "level_progress": {str(g):{} for g in range(2,11)},
        "started": False,
        "question_in_level": 0,
        "correct_in_level": 0,
        "current_q": None,     # dict with question
        "current_ans": None,
        "current_choices": None,
        "question_start_time": None,
        "time_limit": 45,
        "score": 0,
        "history": [],
        "weak_topics": {},
        "show_result": False,
        "last_result": None,
        "ui_input": "",        # used for text_input key
        "shape_choice_key": None,
        "auto_clear_flag": False
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# Load stored progress (if any)
progress_store = load_progress()
if progress_store:
    # only load if state still default/empty
    if not any(progress_store.get("level_progress", {})):
        st.session_state["level_progress"] = progress_store.get("level_progress", st.session_state["level_progress"])
        st.session_state["level_unlocked"] = progress_store.get("level_unlocked", st.session_state["level_unlocked"])

# ---------------------------
# Question Generators
# Each function returns (question_text, answer)
# For fraction answers sometimes return dict {'fraction':..., 'decimal':...}
# ---------------------------

# --- Grade 2-4 basic
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

# --- Grades 5-8 intermediate
def gen_fractions_add(grade):
    d = random.randint(2,8)
    a = random.randint(1, d-1)
    b = random.randint(1, d-1)
    num = a+b
    den = d
    g = math.gcd(num, den)
    frac_s = f"{num//g}/{den//g}"
    dec = round(num/den, 3)
    return f"{a}/{d} + {b}/{d} = ? (answer as fraction or decimal)", {"fraction":frac_s, "decimal":dec}

def gen_fraction_to_mixed(grade):
    num = random.randint(5, 20)
    den = random.randint(2, 8)
    whole = num // den
    rem = num % den
    if rem == 0:
        return f"Write {num}/{den} as a mixed number.", str(whole)
    else:
        return f"Write {num}/{den} as a mixed number.", f"{whole} {rem}/{den}"

def gen_lcm(grade):
    a = random.randint(2,20)
    b = random.randint(2,20)
    return f"Find LCM of {a} and {b}.", (a*b)//math.gcd(a,b)

def gen_hcf(grade):
    a = random.randint(2,50)
    b = random.randint(2,50)
    return f"Find HCF (GCD) of {a} and {b}.", math.gcd(a,b)

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

# --- Grades 9-10 advanced
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
# Topic chooser & unified generator
# ---------------------------
def choose_topic(grade):
    if grade <=4:
        return random.choice(["addition","subtraction","multiplication","division","comparison","story"])
    elif grade <=8:
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
    # fallback
    q,a = gen_addition(grade); return {"type":"math","topic":"addition","question":q,"answer":a}

# ---------------------------
# Core gameplay functions
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
        "score": st.session_state.get("score", 0)
    })
    next_q()
    return True

def next_q():
    if st.session_state["mode"] == "Math Quiz":
        qdict = generate_math_question(st.session_state["grade"])
    else:
        qdict = gen_shape_question(st.session_state["grade"])
    st.session_state["current_q"] = qdict
    st.session_state["current_ans"] = qdict["answer"]
    st.session_state["current_choices"] = qdict.get("choices")
    st.session_state["question_start_time"] = time.time()
    # set a unique radio key base to avoid persisted selection between questions
    st.session_state["shape_choice_key"] = f"shape_choice_{random.randint(100000,999999)}"
    # request clear of ui input next render
    st.session_state["auto_clear_flag"] = True

def record_answer(given):
    # given can be string, number, or None
    q = st.session_state["current_q"]
    correct = st.session_state["current_ans"]
    topic = q.get("topic") if q else None
    ok = False
    # handle fractions dict
    try:
        if isinstance(correct, dict):
            frac = correct.get("fraction")
            dec = correct.get("decimal")
            if isinstance(given, str) and given.strip() == frac:
                ok = True
            else:
                try:
                    if abs(float(given) - float(dec)) <= 0.05:
                        ok = True
                except:
                    ok = False
        elif isinstance(correct, (int, float)):
            try:
                if abs(float(given) - float(correct)) <= 0.5:
                    ok = True
            except:
                ok = False
        else:
            if str(given).strip().lower() == str(correct).strip().lower():
                ok = True
    except Exception:
        ok = False

    # update counters
    st.session_state["question_in_level"] += 1
    if ok:
        st.session_state["correct_in_level"] += 1
        st.session_state["score"] = st.session_state.get("score",0) + 10
    else:
        # track weak topics
        if topic:
            st.session_state["weak_topics"][topic] = st.session_state["weak_topics"].get(topic,0) + 1

    # append history
    st.session_state["history"].append({
        "q": q.get("question") if q else "N/A",
        "given": given,
        "correct": ok
    })

    # end of level?
    if st.session_state["question_in_level"] >= QUESTIONS_PER_LEVEL:
        total = st.session_state["question_in_level"]
        correct_count = st.session_state["correct_in_level"]
        percent = int(correct_count/total*100) if total>0 else 0
        passed = percent >= PASS_PERCENT
        st.session_state["last_result"] = {"total": total, "correct": correct_count, "percent": percent, "passed": passed}
        # save progress
        g = st.session_state["grade"]
        lvl = st.session_state["current_level"]
        st.session_state["level_progress"].setdefault(str(g), {})[str(lvl)] = st.session_state["last_result"]
        if passed and lvl < LEVELS_PER_GRADE:
            st.session_state["level_unlocked"][g] = max(st.session_state["level_unlocked"].get(g,1), lvl+1)
        st.session_state["show_result"] = True
        # persist to file
        save_progress({"level_progress": st.session_state["level_progress"], "level_unlocked": st.session_state["level_unlocked"]})
    else:
        # continue
        next_q()

# ---------------------------
# UI pieces
# ---------------------------
def header_section():
    st.markdown(f"<h1 style='margin:0'>{APP_TITLE} {PAGE_ICON}</h1>", unsafe_allow_html=True)
    st.markdown("<div style='background:linear-gradient(90deg,#A6C0FE,#F68084); padding:8px; border-radius:8px; margin-bottom:8px'>"
                "<b style='color:white'>Play, Learn and Level Up — Grades 2 to 10</b></div>", unsafe_allow_html=True)

def sidebar_section():
    st.sidebar.header("Player & Settings")
    name = st.sidebar.text_input("Player name", value=st.session_state.get("player","Player"))
    st.session_state["player"] = name

    grade = st.sidebar.selectbox("Grade", options=list(range(2,11)), index=st.session_state["grade"]-2)
    st.session_state["grade"] = grade

    mode = st.sidebar.radio("Mode", options=["Math Quiz","Shape Challenge"], index=0 if st.session_state["mode"]=="Math Quiz" else 1)
    st.session_state["mode"] = mode

    st.sidebar.markdown("---")
    st.sidebar.write(f"Level: {st.session_state['current_level']} (Unlocked: {st.session_state['level_unlocked'].get(st.session_state['grade'],1)})")
    st.sidebar.write(f"Score (session): {st.session_state.get('score',0)}")
    st.sidebar.write(f"Weak topics: {st.session_state.get('weak_topics',{})}")

    tlim = st.sidebar.slider("Time limit (seconds)", min_value=10, max_value=120, value=st.session_state["time_limit"])
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
    st.sidebar.write("Leaderboard")
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
    header_section()
    sidebar_section()

    # Level chooser and start
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
                    st.rerun()
            else:
                st.error("This level is locked.")

    st.markdown("---")
    if not st.session_state["started"]:
        st.info(f"Press Start Level. Each level: {QUESTIONS_PER_LEVEL} questions. Pass = {PASS_PERCENT}%")
        # preview sample
        sample = generate_math_question(st.session_state["grade"])
        st.write("Sample:", sample["question"])
        st.stop()

    # show progress within level
    st.write(f"Grade {st.session_state['grade']} — Level {st.session_state['current_level']} | Q {st.session_state['question_in_level']+1}/{QUESTIONS_PER_LEVEL}")
    st.progress(min(100, int((st.session_state['question_in_level']/QUESTIONS_PER_LEVEL)*100)))

    # ensure question exists
    if st.session_state["current_q"] is None:
        next_q()
        st.rerun()

    # if show_result true, show summary
    if st.session_state["show_result"]:
        res = st.session_state["last_result"]
        st.markdown("---")
        if res["passed"]:
            st.balloons()
            st.success(f"Level Passed! {res['correct']}/{res['total']} ({res['percent']}%)")
        else:
            st.error(f"Level Failed. {res['correct']}/{res['total']} ({res['percent']}%)")
        st.write("Level Summary:")
        st.write("- Correct:", res["correct"])
        st.write("- Total:", res["total"])
        st.write("- Percent:", res["percent"])
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
        # leaderboard save
        st.markdown("---")
        name = st.text_input("Save to leaderboard — enter name", value=st.session_state.get("player","Player"))
        if st.button("Save to Leaderboard"):
            row = [datetime.utcnow().isoformat(), name, st.session_state["grade"], st.session_state["current_level"], st.session_state["score"], res["percent"]]
            ok = append_leaderboard_row(row)
            if ok:
                st.success("Saved.")
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

        # ensure ui_input cleared if requested
        if st.session_state.get("auto_clear_flag"):
            st.session_state["ui_input"] = ""
            st.session_state["auto_clear_flag"] = False

        # text input with on_change: send the current ui_input value
        st.text_input("Type answer and press Enter", key="ui_input", on_change=lambda: record_answer(st.session_state.get("ui_input","")))
        # timer display
        elapsed = time.time() - st.session_state["question_start_time"] if st.session_state["question_start_time"] else 0
        remaining = max(0, int(st.session_state["time_limit"] - elapsed))
        st.write(f"Time left: {remaining} seconds")
        if remaining <= 0:
            record_answer("")  # treat as wrong
            st.rerun()

    else:
        # SHAPE CHALLENGE — FIXED SECTION
        st.subheader("Shape Challenge")
        buf = io.BytesIO()
        qdict["image"].save(buf, format="PNG")
        st.image(buf)
        st.write(qdict["question"])

        # If there are choices, show radio with placeholder + unique key + Submit button
        if qdict.get("choices"):
            # placeholder option to avoid auto-selecting the first real choice
            options = ["Select an answer"] + [str(c) for c in qdict["choices"]]
            # unique key ensures radio does not preserve previous selection
            unique_key = st.session_state.get("shape_choice_key") or f"shape_choice_{random.randint(100000,999999)}"
            # render radio with default index 0
            selected = st.radio("Choose your answer 👇", options=options, index=0, key=unique_key)

            # Submit button triggers recording
            if selected != "Select an answer":
                if st.button("Submit Answer"):
                    # record numeric or string accordingly
                    # convert to float if possible (so record_answer handles numeric)
                    val = None
                    try:
                        val = float(selected)
                    except:
                        val = selected
                    record_answer(val)
                    st.rerun()
            else:
                st.info("👆 Please select an answer then press Submit.")
        else:
            # fallback to typed input
            if st.session_state.get("auto_clear_flag"):
                st.session_state["ui_input"] = ""
                st.session_state["auto_clear_flag"] = False
            st.text_input("Type answer and press Enter", key="ui_input", on_change=lambda: record_answer(st.session_state.get("ui_input","")))

    # recent history
    st.markdown("---")
    st.subheader("Recent History (last 5)")
    for h in st.session_state["history"][-5:][::-1]:
        st.write(f"- {h['q']} — {'✅' if h['correct'] else '❌'} (You: {h['given']})")

# ---------------------------
# run
# ---------------------------
if __name__ == "__main__":
    main_ui()
    # ensure question exists if started
    if st.session_state["started"] and not st.session_state["current_q"] and not st.session_state["show_result"]:
        next_q()
        st.rerun()

