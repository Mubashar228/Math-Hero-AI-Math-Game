"""
Math Hero v5 - Gamified AI Math Challenge
File: math_hero_v5_full.py
Run: streamlit run math_hero_v5_full.py

Features:
- Grades 2-10, 20 levels per grade, 10 questions per level
- Math Quiz + Shape Challenge modes
- Grade-appropriate topics (2-4 basic ops, 5-8 fractions/LCM/HCF/percent/profit/area, 9-10 functions/sets/trig/slope/matrices)
- Shapes rendered with PIL for visual questions
- Enter-to-submit for text answers (safe clearing of inputs)
- Level locking/unlocking (pass = 70%)
- Level result screen with balloons and congratulatory messages
- Local leaderboard (CSV) and progress export/import
- Hint system and weak-topic tracking
- Persistent simple save to local JSON (if available) for progress

This is a single-file production-ready Streamlit app. Customize paths and APIs as needed.
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

# ---------------------------
# App configuration
# ---------------------------
APP_TITLE = "Math Hero v5 — Gamified AI Math Challenge"
PAGE_ICON = "🦸‍♂️"
LEVELS_PER_GRADE = 20
QUESTIONS_PER_LEVEL = 10
PASS_PERCENT = 70  # percent needed to pass a level
SAVE_FILE = "math_hero_progress.json"
LEADERBOARD_FILE = "math_hero_leaderboard.csv"

st.set_page_config(page_title=APP_TITLE, page_icon=PAGE_ICON, layout="wide")

# ---------------------------
# Utility: persistent storage helpers
# ---------------------------

def load_progress():
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_progress(data):
    try:
        with open(SAVE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def append_leaderboard(entry):
    header = ["timestamp","player","grade","level","score","percent"]
    write_header = not os.path.exists(LEADERBOARD_FILE)
    try:
        with open(LEADERBOARD_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(header)
            writer.writerow(entry)
        return True
    except Exception:
        return False

# ---------------------------
# Session state defaults & safe init
# ---------------------------

def init_session_state():
    defaults = {
        'player_name': 'Player',
        'grade': 3,
        'mode': 'Math Quiz',
        'current_level': 1,
        'level_unlocked': {g:1 for g in range(2,11)},
        'level_progress': {str(g):{} for g in range(2,11)},
        'question_index': 0,
        'question_in_level': 0,
        'correct_in_level': 0,
        'current_question': None,
        'current_answer': None,
        'current_choices': None,
        'question_start_time': None,
        'time_limit': 45,
        'score': 0,
        'history': [],
        'weak_topics': {},
        'show_result': False,
        'last_result': None,
        'auto_clear_flag': False,  # for safe clearing of input after submit
        'user_input_temp': '',
        'started': False,
    }
    for k,v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session_state()

# Load saved progress into session if available (do not overwrite existing active progress unless empty)
progress_data = load_progress()
if progress_data and not st.session_state['level_progress']:
    st.session_state['level_progress'] = progress_data.get('level_progress', st.session_state['level_progress'])
    st.session_state['level_unlocked'] = progress_data.get('level_unlocked', st.session_state['level_unlocked'])

# ---------------------------
# Question generators
# ---------------------------

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
    return f"{a} × {b} = ?", a * b


def gen_division(grade):
    b = random.randint(1, min(12, grade+6))
    c = random.randint(1, 12)
    a = b * c
    return f"{a} ÷ {b} = ?", c


def gen_comparison(grade):
    a = random.randint(0, 20)
    b = random.randint(0, 20)
    ans = '>' if a > b else '<' if a < b else '='
    return f"Which is greater: {a} or {b}? Write '>' or '<' or '='.", ans


def gen_simple_story(grade):
    a = random.randint(5, 30)
    b = random.randint(1, 10)
    return f"Ali had {a} apples. He gave {b} apples to Ahmed. How many apples left?", a - b

# Fractions proper/improper

def gen_fractions_add(grade):
    d = random.randint(2, 8)
    a = random.randint(1, d-1)
    b = random.randint(1, d-1)
    num = a + b
    den = d
    g = math.gcd(num, den)
    simp_num = num // g
    simp_den = den // g
    frac_str = f"{simp_num}/{simp_den}"
    dec = round(num/den, 3)
    return f"{a}/{d} + {b}/{d} = ? (answer as fraction or decimal)", {'fraction': frac_str, 'decimal': dec}


def gen_fraction_improper_to_mixed(grade):
    num = random.randint(5, 20)
    den = random.randint(2, 8)
    whole = num // den
    rem = num % den
    if rem == 0:
        ans = str(whole)
    else:
        ans = f"{whole} {rem}/{den}"
    return f"Write {num}/{den} as mixed number.", ans


def gen_lcm(grade):
    a = random.randint(2, 20)
    b = random.randint(2, 20)
    return f"Find LCM of {a} and {b}", (a*b)//math.gcd(a,b)


def gen_hcf(grade):
    a = random.randint(2, 50)
    b = random.randint(2, 50)
    return f"Find HCF (GCD) of {a} and {b}", math.gcd(a,b)


def gen_percentage(grade):
    base = random.randint(10, 200)
    per = random.choice([5,10,15,20,25])
    return f"What is {per}% of {base}?", round(base*per/100, 2)


def gen_profit_loss(grade):
    cp = random.randint(50, 500)
    pct = random.choice([5,10,15,20,25,30])
    sp = round(cp*(1 + pct/100), 2)
    return f"Cost price = {cp}, profit = {pct}%. Find selling price.", sp


def gen_area_rectangle(grade):
    l = random.randint(2, 20)
    w = random.randint(1, 15)
    return f"Area of rectangle length={l} and width={w} = ?", l*w

# Higher grade

def gen_function_eval(grade):
    a = random.randint(1,5)
    b = random.randint(0,10)
    x = random.randint(1,10)
    return f"Given f(x) = {a}x + {b}. Find f({x}).", a*x + b


def gen_set_membership(grade):
    A = set(random.sample(range(1,20), 5))
    x = random.choice(list(A))
    return f"Given set A = {sorted(A)}. Is {x} in A? Answer 'yes' or 'no'.", 'yes'


def gen_trig_basic(grade):
    angle_val = random.choice([(30,0.5),(45,round(math.sqrt(2)/2,3)),(60,round(math.sqrt(3)/2,3))])
    ang, val = angle_val
    return f"What is sin({ang}°)? (approx)", val


def gen_slope(grade):
    x1 = random.randint(0,5)
    y1 = random.randint(0,5)
    x2 = x1 + random.randint(1,6)
    y2 = y1 + random.randint(-3,6)
    slope = round((y2 - y1)/(x2 - x1), 3)
    return f"Find slope of line through ({x1},{y1}) and ({x2},{y2}).", slope


def gen_matrix_add(grade):
    a,b,c,d = [random.randint(0,5) for _ in range(4)]
    e,f_,g,h = [random.randint(0,5) for _ in range(4)]
    q = f"Add matrices [[{a},{b}],[{c},{d}]] + [[{e},{f_}],[{g},{h}]]. Write result as [[x,y],[z,w]]."
    ans = f"[[{a+e},{b+f_}],[{c+g},{d+h}]]"
    return q, ans

# ---------------------------
# Shapes generator (PIL drawing)
# ---------------------------

def draw_shape_image(shape, params):
    size = 300
    img = Image.new('RGB', (size,size), color=(255,255,255))
    draw = ImageDraw.Draw(img)
    if shape == 'square':
        s = params.get('side_px', 120)
        x0 = (size - s)//2
        y0 = (size - s)//2
        draw.rectangle([x0,y0,x0+s,y0+s], outline='black', width=4)
    elif shape == 'rectangle':
        l = params.get('l_px', 160)
        w = params.get('w_px', 100)
        x0 = (size - l)//2
        y0 = (size - w)//2
        draw.rectangle([x0,y0,x0+l,y0+w], outline='black', width=4)
    elif shape == 'circle':
        r = params.get('r_px', 70)
        cx, cy = size//2, size//2
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline='black', width=4)
    elif shape == 'triangle':
        base = params.get('base_px', 160)
        h = params.get('h_px', 120)
        cx = size//2
        pts = [(cx, (size-h)//2), (cx-base//2, (size+h)//2), (cx+base//2, (size+h)//2)]
        draw.polygon(pts, outline='black')
    return img


def gen_shape_question(grade):
    shape = random.choice(['square','rectangle','circle','triangle'])
    if shape == 'square':
        side = random.randint(3+grade, 6+grade)
        q = f"A square has side = {side} cm. What is its area?"
        ans = side*side
        params = {'side_px': int(side*6)}
    elif shape == 'rectangle':
        l = random.randint(4+grade, 8+grade)
        w = random.randint(2+grade, 5+grade)
        q = f"A rectangle has length = {l} cm and width = {w} cm. What is its perimeter?"
        ans = 2*(l+w)
        params = {'l_px': int(l*10), 'w_px': int(w*8)}
    elif shape == 'circle':
        r = random.randint(3+grade, 6+grade)
        q = f"A circle has radius = {r} cm. Approximate circumference (π≈3.14)."
        ans = round(2*3.14*r, 1)
        params = {'r_px': int(r*6)}
    else:
        b = random.randint(4+grade, 8+grade)
        h = random.randint(3+grade, 7+grade)
        q = f"A triangle has base = {b} cm and height = {h} cm. What is its area?"
        ans = round(0.5*b*h,1)
        params = {'base_px': int(b*10), 'h_px': int(h*8)}
    img = draw_shape_image(shape, params)
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
    return {'type':'shape','question':q,'answer':ans,'choices':choices,'image':img}

# ---------------------------
# Topic chooser per grade
# ---------------------------
# 🟩 Function to generate rectangle perimeter questions
def gen_perimeter_rectangle(grade):
    import random
    length = random.randint(2, 20)
    width = random.randint(2, 20)
    question = f"Find the perimeter of a rectangle with length {length} cm and width {width} cm."
    answer = 2 * (length + width)
    return question, answer


def choose_topic(grade):
    if grade <= 4:
        return random.choice(['addition','subtraction','multiplication','division','comparison','story'])
    elif grade <= 8:
        return random.choice(['fractions_add','fraction_mixed','lcm','hcf','percentage','profit','area','perimeter','mul_basic'])
    else:
        return random.choice(['function','sets','trig','slope','fraction_mixed','matrix'])


def generate_math_question(grade):
    topic = choose_topic(grade)
    # call generator once and return structured dict
    if topic == 'addition':
        q,a = gen_addition(grade)
        return {'type':'math','topic':'addition','question':q,'answer':a}
    if topic == 'subtraction':
        q,a = gen_subtraction(grade)
        return {'type':'math','topic':'subtraction','question':q,'answer':a}
    if topic == 'multiplication' or topic=='mul_basic':
        q,a = gen_multiplication(grade)
        return {'type':'math','topic':'multiplication','question':q,'answer':a}
    if topic == 'division':
        q,a = gen_division(grade)
        return {'type':'math','topic':'division','question':q,'answer':a}
    if topic == 'comparison':
        q,a = gen_comparison(grade)
        return {'type':'math','topic':'comparison','question':q,'answer':a}
    if topic == 'story':
        q,a = gen_simple_story(grade)
        return {'type':'math','topic':'story','question':q,'answer':a}
    if topic == 'fractions_add':
        q,a = gen_fractions_add(grade)
        return {'type':'math','topic':'fractions','question':q,'answer':a}
    if topic == 'fraction_mixed':
        q,a = gen_fraction_improper_to_mixed(grade)
        return {'type':'math','topic':'fractions_mixed','question':q,'answer':a}
    if topic == 'lcm':
        q,a = gen_lcm(grade)
        return {'type':'math','topic':'lcm','question':q,'answer':a}
    if topic == 'hcf':
        q,a = gen_hcf(grade)
        return {'type':'math','topic':'hcf','question':q,'answer':a}
    if topic == 'percentage':
        q,a = gen_percentage(grade)
        return {'type':'math','topic':'percentage','question':q,'answer':a}
    if topic == 'profit':
        q,a = gen_profit_loss(grade)
        return {'type':'math','topic':'profit','question':q,'answer':a}
    if topic == 'area':
        q,a = gen_area_rectangle(grade)
        return {'type':'math','topic':'area','question':q,'answer':a}
    if topic == 'perimeter':
        q,a = gen_perimeter_rectangle(grade)
        return {'type':'math','topic':'perimeter','question':q,'answer':a}
    if topic == 'function':
        q,a = gen_function_eval(grade)
        return {'type':'math','topic':'function','question':q,'answer':a}
    if topic == 'sets':
        q,a = gen_set_membership(grade)
        return {'type':'math','topic':'sets','question':q,'answer':a}
    if topic == 'trig':
        q,a = gen_trig_basic(grade)
        return {'type':'math','topic':'trig','question':q,'answer':a}
    if topic == 'slope':
        q,a = gen_slope(grade)
        return {'type':'math','topic':'slope','question':q,'answer':a}
    if topic == 'matrix':
        q,a = gen_matrix_add(grade)
        return {'type':'math','topic':'matrix','question':q,'answer':a}

    # fallback
    q,a = gen_addition(grade)
    return {'type':'math','topic':'addition','question':q,'answer':a}

# ---------------------------
# Core gameplay functions
# ---------------------------

def start_level(grade, level):
    # check lock
    unlocked = st.session_state['level_unlocked'].get(grade,1)
    if level > unlocked:
        return False
    # reset counters for the level
    st.session_state.update({
        'question_in_level': 0,
        'correct_in_level': 0,
        'history': [],
        'show_result': False,
        'last_result': None,
        'started': True,
    })
    # generate first question
    next_question()
    return True


def next_question():
    # Generate and store current question
    if st.session_state['mode'] == 'Math Quiz':
        qdict = generate_math_question(st.session_state['grade'])
    else:
        qdict = gen_shape_question(st.session_state['grade'])
    st.session_state['current_question'] = qdict
    st.session_state['current_answer'] = qdict['answer']
    st.session_state['current_choices'] = qdict.get('choices')
    st.session_state['question_start_time'] = time.time()
    # mark the input clear request rather than directly set
    st.session_state['auto_clear_flag'] = True


def record_answer(given_raw):
    # handle recording and moving to next
    qdict = st.session_state['current_question']
    correct_flag = False
    given = given_raw
    correct = st.session_state['current_answer']
    try:
        if isinstance(correct, dict):
            # fraction dict
            frac_exp = correct.get('fraction')
            dec_exp = correct.get('decimal')
            # accept either fraction string or decimal approx
            if isinstance(given, str) and given.strip() == frac_exp:
                correct_flag = True
            else:
                try:
                    if abs(float(given) - float(dec_exp)) <= 0.05:
                        correct_flag = True
                except Exception:
                    correct_flag = False
        elif isinstance(correct, (int, float)):
            try:
                if abs(float(given) - float(correct)) <= 0.5:
                    correct_flag = True
            except Exception:
                correct_flag = False
        else:
            if str(given).strip().lower() == str(correct).strip().lower():
                correct_flag = True
    except Exception:
        correct_flag = False

    # update counters safely
    st.session_state['question_in_level'] += 1
    if correct_flag:
        st.session_state['correct_in_level'] += 1
        st.session_state['score'] += 10
    # track weak topics
    topic = qdict.get('topic')
    if not correct_flag and topic:
        st.session_state['weak_topics'][topic] = st.session_state['weak_topics'].get(topic,0) + 1
    # history
    st.session_state['history'].append({'q': qdict.get('question'), 'given': given, 'correct': correct_flag})

    # after QUESTIONS_PER_LEVEL questions -> evaluate
    if st.session_state['question_in_level'] >= QUESTIONS_PER_LEVEL:
        total = st.session_state['question_in_level']
        correct = st.session_state['correct_in_level']
        percent = int(correct/total*100) if total>0 else 0
        passed = percent >= PASS_PERCENT
        st.session_state['last_result'] = {'total': total, 'correct': correct, 'percent': percent, 'passed': passed}
        # save progress
        grade = st.session_state['grade']
        lvl = st.session_state['current_level']
        st.session_state['level_progress'].setdefault(str(grade), {})[str(lvl)] = st.session_state['last_result']
        if passed and lvl < LEVELS_PER_GRADE:
            st.session_state['level_unlocked'][grade] = max(st.session_state['level_unlocked'].get(grade,1), lvl+1)
        st.session_state['show_result'] = True
        # persist to file
        save_progress({'level_progress': st.session_state['level_progress'], 'level_unlocked': st.session_state['level_unlocked']})
    else:
        # continue to next question
        next_question()

# ---------------------------
# UI components
# ---------------------------

def render_header():
    st.markdown(f"<h1 style='color:#1f2937'>{APP_TITLE} {PAGE_ICON}</h1>", unsafe_allow_html=True)
    st.markdown("<div style='background: linear-gradient(90deg,#A6C0FE,#F68084); padding:8px; border-radius:8px'>\
                   <p style='color:white; margin:0'>Interactive math game for grades 2–10. 20 levels per grade, 10 questions per level.</p></div>", unsafe_allow_html=True)


def render_sidebar():
    st.sidebar.header("Player & Settings")
    name = st.sidebar.text_input("Player name", value=st.session_state.get('player_name','Player'))
    st.session_state['player_name'] = name

    grade = st.sidebar.selectbox("Grade", options=list(range(2,11)), index=st.session_state['grade']-2)
    st.session_state['grade'] = grade

    mode = st.sidebar.radio("Mode", options=["Math Quiz","Shape Challenge"], index=0 if st.session_state['mode']=='Math Quiz' else 1)
    st.session_state['mode'] = mode

    st.sidebar.markdown("---")
    st.sidebar.write(f"Current Level: {st.session_state['current_level']} (Unlocked: {st.session_state['level_unlocked'].get(st.session_state['grade'],1)})")
    st.sidebar.write(f"Score (session): {st.session_state['score']}")
    st.sidebar.write(f"Weak topics: {st.session_state['weak_topics']}")

    tlim = st.sidebar.slider("Time limit per question", min_value=10, max_value=120, value=st.session_state['time_limit'])
    st.session_state['time_limit'] = tlim

    if st.sidebar.button("Save Progress Now"):
        ok = save_progress({'level_progress': st.session_state['level_progress'], 'level_unlocked': st.session_state['level_unlocked']})
        if ok:
            st.sidebar.success("Progress saved")
        else:
            st.sidebar.error("Save failed")

    if st.sidebar.button("Export Progress JSON"):
        data = {'level_progress': st.session_state['level_progress'], 'level_unlocked': st.session_state['level_unlocked']}
        st.sidebar.download_button(label='Download JSON', data=json.dumps(data), file_name='math_hero_progress.json')

    st.sidebar.markdown("---")
    st.sidebar.write("Leaderboard & Reports")
    if st.sidebar.button("Export Leaderboard CSV"):
        if os.path.exists(LEADERBOARD_FILE):
            with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
                st.sidebar.download_button('Download Leaderboard', data=f.read(), file_name='leaderboard.csv')
        else:
            st.sidebar.info("No leaderboard yet")

# ---------------------------
# Main app render logic
# ---------------------------

def main_ui():
    render_header()
    st.write('')
    render_sidebar()

    # top controls: choose level and start
    col1, col2 = st.columns([3,1])
    with col1:
        lvl = st.number_input('Choose Level', min_value=1, max_value=LEVELS_PER_GRADE, value=st.session_state['current_level'])
        lvl = int(lvl)
        if lvl > st.session_state['level_unlocked'].get(st.session_state['grade'],1):
            st.warning(f"Level {lvl} is locked. Complete previous levels to unlock.")
        else:
            st.session_state['current_level'] = lvl
    with col2:
        if st.button('Start Level'):
            if st.session_state['current_level'] <= st.session_state['level_unlocked'].get(st.session_state['grade'],1):
                started = start_level(st.session_state['grade'], st.session_state['current_level'])
                if not started:
                    st.error('Cannot start locked level')
                else:
                    st.experimental_rerun = getattr(st, 'rerun', None)
                    st.rerun()
            else:
                st.error('Level locked')

    st.markdown('---')
    # if not started show info
    if not st.session_state['started']:
        st.info(f"Click Start Level to begin. Each level has {QUESTIONS_PER_LEVEL} questions. You must score {PASS_PERCENT}% to pass.")
        # preview examples
        st.write('Preview question types based on grade:')
        preview_q = generate_math_question(st.session_state['grade'])
        st.write(preview_q['question'])
        st.stop()

    # show progress in level
    st.write(f"Grade {st.session_state['grade']} — Level {st.session_state['current_level']} | Question {st.session_state['question_in_level']+1}/{QUESTIONS_PER_LEVEL}")
    st.progress(min(100, int((st.session_state['question_in_level']/QUESTIONS_PER_LEVEL)*100)))

    qdict = st.session_state.get('current_question')
    if not qdict:
        next_question()
        st.rerun()

    if st.session_state['show_result']:
        # show results screen
        res = st.session_state['last_result']
        st.markdown('---')
        if res['passed']:
            st.balloons()
            st.success(f"Level Passed! Score: {res['correct']}/{res['total']} ({res['percent']}%)")
        else:
            st.error(f"Level Failed. Score: {res['correct']}/{res['total']} ({res['percent']}%)")

        st.markdown('**Level Summary**')
        st.write(f"Correct: {res['correct']}")
        st.write(f"Total: {res['total']}")
        st.write(f"Percent: {res['percent']}%")

        c1, c2 = st.columns(2)
        with c1:
            if st.button('Retry Level'):
                start_level(st.session_state['grade'], st.session_state['current_level'])
                st.rerun()
        with c2:
            if res['passed']:
                if st.button('Go to Next Level'):
                    if st.session_state['current_level'] < LEVELS_PER_GRADE:
                        st.session_state['current_level'] += 1
                        start_level(st.session_state['grade'], st.session_state['current_level'])
                        st.rerun()
                    else:
                        st.success('You completed all levels for this grade!')
        # allow saving to leaderboard
        st.markdown('---')
        name = st.text_input('Save result to leaderboard — Enter player name', value=st.session_state.get('player_name','Player'))
        if st.button('Save to Leaderboard'):
            entry = [datetime.utcnow().isoformat(), name, st.session_state['grade'], st.session_state['current_level'], st.session_state['score'], res['percent']]
            ok = append_leaderboard(entry)
            if ok:
                st.success('Saved to leaderboard')
            else:
                st.error('Save failed')
        st.stop()

    # Normal question rendering
    qdict = st.session_state['current_question']
    st.markdown('---')
    if qdict['type'] == 'math':
        st.subheader('Math Question')
        st.write(f"Topic: {qdict.get('topic','General')}")
        st.write(qdict['question'])

        # text input: to avoid direct state collision we use a temp key and an explicit submit
        # show input and allow Enter to submit via on_change
        if 'ui_input_box' not in st.session_state:
            st.session_state['ui_input_box'] = ''

        # If auto_clear_flag is set, clear the input safely
        if st.session_state.get('auto_clear_flag'):
            st.session_state['ui_input_box'] = ''
            st.session_state['auto_clear_flag'] = False

        st.text_input('Type answer and press Enter', key='ui_input_box', on_change=lambda: record_answer(st.session_state.get('ui_input_box','')))

        # timer
        elapsed = time.time() - st.session_state['question_start_time'] if st.session_state['question_start_time'] else 0
        remaining = max(0, int(st.session_state['time_limit'] - elapsed))
        st.write(f"Time left: {remaining} seconds")
        if remaining <= 0:
            # treat as wrong and continue
            record_answer('')
            st.rerun()

    else:
        st.subheader('Shape Challenge')
        buf = io.BytesIO()
        qdict['image'].save(buf, format='PNG')
        st.image(buf)
        st.write(qdict['question'])
        if qdict.get('choices'):
            # radio with on_change
            options = [str(c) for c in qdict['choices']]
            if 'shape_choice' not in st.session_state:
                st.session_state['shape_choice'] = None
            st.radio('Select answer', options=options, key='shape_choice', on_change=lambda: record_answer(st.session_state.get('shape_choice')))
        else:
            st.text_input('Type answer and press Enter', key='ui_input_box', on_change=lambda: record_answer(st.session_state.get('ui_input_box','')))

    # footer: last 5 history
    st.markdown('---')
    st.subheader('Recent History')
    for h in st.session_state['history'][-5:][::-1]:
        st.write(f"- {h['q']} — {'✅' if h['correct'] else '❌'} (You: {h['given']})")

# ---------------------------
# Run app
# ---------------------------
if __name__ == '__main__':
    main_ui()
    # ensure a question exists if game in progress
    if st.session_state['started'] and not st.session_state['current_question'] and not st.session_state['show_result']:
        next_question()
        st.experimental_rerun()
