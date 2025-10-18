# Math Hero v3 - Streamlit Complete Game (Grades 2-10)
# File: math_hero_streamlit_v3.py
# Run: streamlit run math_hero_streamlit_v3.py

import streamlit as st
import random
import time
from PIL import Image, ImageDraw
import io

# -------------------------
# Config
# -------------------------
APP_TITLE = "Math Hero v3"
LEVELS_PER_GRADE = 20
QUESTIONS_PER_LEVEL = 10
PASS_PERCENTAGE = 70  # 70% to pass

st.set_page_config(page_title=APP_TITLE, page_icon="🦸‍♂️", layout="centered")

# -------------------------
# Session state init helper
# -------------------------

def init_state():
    defaults = {
        'grade': 3,
        'mode': 'Math Quiz',
        'current_level': 1,
        'level_unlocked': {g:1 for g in range(2,11)},  # unlocked level per grade
        'level_progress': {g: {} for g in range(2,11)},  # store pass/fail per level
        'started': False,
        'current_question': None,
        'current_answer': None,
        'current_choices': None,
        'question_start_time': None,
        'time_limit': 45,
        'question_in_level': 0,
        'correct_in_level': 0,
        'history': [],
        'user_answer': '',
        'show_level_result': False,
        'last_result': None,  # dict with stats
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# -------------------------
# Question generators grouped by topic
# -------------------------

def gen_addition(maxv=100):
    a = random.randint(1, maxv)
    b = random.randint(1, maxv)
    return f"{a} + {b} = ?", a + b


def gen_subtraction(maxv=100):
    a = random.randint(1, maxv)
    b = random.randint(1, a)
    return f"{a} - {b} = ?", a - b


def gen_multiplication(maxv=12):
    a = random.randint(1, maxv)
    b = random.randint(1, maxv)
    return f"{a} × {b} = ?", a * b


def gen_division(maxv=12):
    b = random.randint(1, maxv)
    c = random.randint(1, maxv)
    a = b * c
    return f"{a} ÷ {b} = ?", c

# comparison
def gen_comparison(maxv=50):
    a = random.randint(0, maxv)
    b = random.randint(0, maxv)
    q = f"Which is greater: {a} or {b}? Write '>' or '<' or '='."
    if a > b:
        ans = '>'
    elif a < b:
        ans = '<'
    else:
        ans = '='
    return q, ans

# simple word problems
def gen_simple_statement(grade):
    a = random.randint(1, 10*grade)
    b = random.randint(1, 5*grade)
    q = f"Ali had {a} apples. He gave {b} apples to Ahmed. How many apples left?"
    return q, a - b

# fractions
def gen_fraction_proper(grade):
    d = random.randint(2, 8)
    a = random.randint(1, d-1)
    b = random.randint(1, d-1)
    q = f"{a}/{d} + {b}/{d} = ? (simplify)"
    num = a + b
    den = d
    # simplify
    def gcd(x,y):
        while y:
            x,y = y, x%y
        return x
    g = gcd(num, den)
    return q, f"{num//g}/{den//g}"

def gen_fraction_improper(grade):
    a = random.randint(5, 15)
    b = random.randint(2, 8)
    q = f"Write {a}/{b} as a mixed number."
    whole = a // b
    rem = a % b
    if rem == 0:
        ans = str(whole)
    else:
        ans = f"{whole} {rem}/{b}"
    return q, ans

# lcm and hcf
def gen_lcm(grade):
    a = random.randint(2, 20)
    b = random.randint(2, 20)
    def lcm(x,y):
        import math
        return x*y//math.gcd(x,y)
    q = f"Find LCM of {a} and {b}."
    return q, lcm(a,b)

def gen_hcf(grade):
    a = random.randint(2, 50)
    b = random.randint(2, 50)
    import math
    q = f"Find HCF (GCD) of {a} and {b}."
    return q, math.gcd(a,b)

# percentage, profit/loss
def gen_percentage(grade):
    base = random.randint(10,200)
    per = random.choice([5,10,15,20,25])
    q = f"What is {per}% of {base}?"
    return q, round(base*per/100,2)

def gen_profit_loss(grade):
    cost = random.randint(50,500)
    profit_pct = random.choice([10,20,25,30])
    sell = int(cost*(1+profit_pct/100))
    q = f"Cost price {cost}, selling price {sell}. What is profit %?"
    return q, profit_pct

# area/perimeter
def gen_area_rectangle(grade):
    l = random.randint(2, 20)
    w = random.randint(1, 15)
    q = f"Area of rectangle length={l} cm and width={w} cm = ?"
    return q, l*w

def gen_perimeter_rectangle(grade):
    l = random.randint(2, 20)
    w = random.randint(1, 15)
    q = f"Perimeter of rectangle length={l} cm and width={w} cm = ?"
    return q, 2*(l+w)

# higher grade topics
def gen_functions(grade):
    a = random.randint(1,5)
    b = random.randint(0,10)
    x = random.randint(1,10)
    q = f"Given f(x) = {a}x + {b}. Find f({x})."
    return q, a*x + b

def gen_sets(grade):
    # simple membership question
    A = set(random.sample(range(1,20), 5))
    x = random.choice(list(A))
    q = f"Given set A = {sorted(A)}. Is {x} in set A? Answer 'yes' or 'no'."
    return q, 'yes'

def gen_trigonometry(grade):
    # basic common angles
    angles = {30:0.5,45:math.sqrt(2)/2,60:math.sqrt(3)/2}
    ang = random.choice(list(angles.keys()))
    func = random.choice(['sin','cos','tan'])
    q = f"What is {func}({ang}°)? (approx if needed)"
    if func == 'sin':
        ans = round(angles[ang],3) if ang in angles else None
    elif func == 'cos':
        # cos(30)=sqrt3/2 etc
        if ang==30: ans = round(math.sqrt(3)/2,3)
        elif ang==45: ans = round(math.sqrt(2)/2,3)
        elif ang==60: ans = round(0.5,3)
    else:
        if ang==30: ans = round(1/math.sqrt(3),3)
        elif ang==45: ans = 1.0
        elif ang==60: ans = round(math.sqrt(3),3)
    return q, ans

def gen_slope(grade):
    x1,y1 = random.randint(0,5), random.randint(0,5)
    x2,y2 = x1+random.randint(1,5), y1+random.randint(-3,5)
    q = f"Find slope of line through ({x1},{y1}) and ({x2},{y2})."
    slope = (y2-y1)/(x2-x1)
    return q, round(slope,3)

def gen_matrices(grade):
    # 2x2 addition
    a = random.randint(0,5)
    b = random.randint(0,5)
    c = random.randint(0,5)
    d = random.randint(0,5)
    e = random.randint(0,5)
    f_ = random.randint(0,5)
    g = random.randint(0,5)
    h = random.randint(0,5)
    q = f"Add matrices: [[{a},{b}],[{c},{d}]] + [[{e},{f_}],[{g},{h}]]. Write result as [[x,y],[z,w]]."
    ans = f"[[{a+e},{b+f_}],[{c+g},{d+h}]]"
    return q, ans

# choose topic per grade
import math

def choose_topic_for_grade(grade):
    if grade <= 4:
        pool = ['addition','subtraction','multiplication','division','comparison','simple_statement']
    elif grade <= 8:
        pool = ['fractions_proper','fractions_improper','lcm','hcf','percentage','profit_loss','area_rect','perimeter_rect']
    else:
        pool = ['functions','sets','trigonometry','slope','fractions_proper','matrices']
    return random.choice(pool)

# generate a math question based on chosen topic

def generate_math_question_for_grade(grade):
    topic = choose_topic_for_grade(grade)
    if topic == 'addition':
        return {'type':'math','topic':topic,'question':gen_addition(10*grade)[0],'answer':gen_addition(10*grade)[1]}
    if topic == 'subtraction':
        return {'type':'math','topic':topic,'question':gen_subtraction(10*grade)[0],'answer':gen_subtraction(10*grade)[1]}
    if topic == 'multiplication':
        return {'type':'math','topic':topic,'question':gen_multiplication(12)[0],'answer':gen_multiplication(12)[1]}
    if topic == 'division':
        return {'type':'math','topic':topic,'question':gen_division(12)[0],'answer':gen_division(12)[1]}
    if topic == 'comparison':
        q,a = gen_comparison(20)
        return {'type':'math','topic':topic,'question':q,'answer':a}
    if topic == 'simple_statement':
        q,a = gen_simple_statement(grade)
        return {'type':'math','topic':topic,'question':q,'answer':a}
    if topic == 'fractions_proper':
        q,a = gen_fraction_proper(grade)
        return {'type':'math','topic':'fractions','question':q,'answer':a}
    if topic == 'fractions_improper':
        q,a = gen_fraction_improper(grade)
        return {'type':'math','topic':'fractions','question':q,'answer':a}
    if topic == 'lcm':
        q,a = gen_lcm(grade)
        return {'type':'math','topic':'lcm','question':q,'answer':a}
    if topic == 'hcf':
        q,a = gen_hcf(grade)
        return {'type':'math','topic':'hcf','question':q,'answer':a}
    if topic == 'percentage':
        q,a = gen_percentage(grade)
        return {'type':'math','topic':'percentage','question':q,'answer':a}
    if topic == 'profit_loss':
        q,a = gen_profit_loss(grade)
        return {'type':'math','topic':'profit_loss','question':q,'answer':a}
    if topic == 'area_rect':
        q,a = gen_area_rectangle(grade)
        return {'type':'math','topic':'area','question':q,'answer':a}
    if topic == 'perimeter_rect':
        q,a = gen_perimeter_rectangle(grade)
        return {'type':'math','topic':'perimeter','question':q,'answer':a}
    if topic == 'functions':
        q,a = gen_functions(grade)
        return {'type':'math','topic':'functions','question':q,'answer':a}
    if topic == 'sets':
        q,a = gen_sets(grade)
        return {'type':'math','topic':'sets','question':q,'answer':a}
    if topic == 'trigonometry':
        q,a = gen_trigonometry(grade)
        return {'type':'math','topic':'trigonometry','question':q,'answer':a}
    if topic == 'slope':
        q,a = gen_slope(grade)
        return {'type':'math','topic':'slope','question':q,'answer':a}
    if topic == 'matrices':
        q,a = gen_matrices(grade)
        return {'type':'math','topic':'matrices','question':q,'answer':a}
    # fallback
    q,a = gen_addition(10*grade)
    return {'type':'math','topic':'addition','question':q,'answer':a}

# -------------------------
# Shape generators (kept similar)
# -------------------------

def draw_shape_image(shape, params):
    size = 300
    img = Image.new('RGB', (size, size), color=(255,255,255))
    draw = ImageDraw.Draw(img)
    if shape == 'square':
        s = params.get('side_px', 120)
        x0 = (size - s)//2
        y0 = (size - s)//2
        draw.rectangle([x0,y0,x0+s,y0+s], outline='black', width=4)
    elif shape == 'rectangle':
        l = params.get('length_px', 160)
        w = params.get('width_px', 100)
        x0 = (size - l)//2
        y0 = (size - w)//2
        draw.rectangle([x0,y0,x0+l,y0+w], outline='black', width=4)
    elif shape == 'circle':
        r = params.get('radius_px', 70)
        cx, cy = size//2, size//2
        draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline='black', width=4)
    elif shape == 'triangle':
        base = params.get('base_px', 160)
        h = params.get('height_px', 120)
        cx = size//2
        points = [(cx, (size-h)//2), (cx-base//2, (size+h)//2), (cx+base//2, (size+h)//2)]
        draw.polygon(points, outline='black')
    return img


def generate_shape_question(grade):
    shapes = ['square','rectangle','circle','triangle']
    shape = random.choice(shapes)
    if shape == 'square':
        side = random.randint(3 + grade, 6 + grade)
        question = f"A square has side = {side} cm. What is its area?"
        answer = side*side
        params = {'side_px': int(side*6)}
    elif shape == 'rectangle':
        l = random.randint(4+grade, 8+grade)
        w = random.randint(2+grade, 5+grade)
        question = f"A rectangle has length = {l} cm and width = {w} cm. What is its perimeter?"
        answer = 2*(l+w)
        params = {'length_px': int(l*10), 'width_px': int(w*8)}
    elif shape == 'circle':
        r = random.randint(3+grade, 6+grade)
        question = f"A circle has radius = {r} cm. Approximate circumference (use π≈3.14)."
        answer = round(2*3.14*r,1)
        params = {'radius_px': int(r*6)}
    elif shape == 'triangle':
        b = random.randint(4+grade, 8+grade)
        h = random.randint(3+grade, 7+grade)
        question = f"A triangle has base = {b} cm and height = {h} cm. What is its area?"
        answer = round(0.5*b*h,1)
        params = {'base_px': int(b*10), 'height_px': int(h*8)}
    choices = []
    if isinstance(answer, (int, float)):
        correct = answer
        choices.append(correct)
        for _ in range(3):
            delta = max(1, int(abs(correct)*0.15))
            wrong = correct + random.choice([-1,1])*random.randint(1, delta+3)
            if isinstance(correct, float):
                wrong = round(wrong,1)
            choices.append(wrong)
        random.shuffle(choices)
    img = draw_shape_image(shape, params)
    return {'type':'shape','shape':shape,'question':question,'answer':answer,'choices':choices,'image':img}

# -------------------------
# Lifecycle: start question, check answers
# -------------------------

def start_level_question():
    # Guard: if level locked, do nothing
    grade = st.session_state.grade
    level = st.session_state.current_level
    if level > st.session_state.level_unlocked.get(grade,1):
        return
    # generate question according to mode
    if st.session_state.mode == 'Math Quiz':
        q = generate_math_question_for_grade(grade)
    else:
        q = generate_shape_question(grade)
    st.session_state.current_question = q
    st.session_state.current_answer = q['answer']
    st.session_state.current_choices = q.get('choices')
    st.session_state.question_start_time = time.time()
    st.session_state.user_answer = ''


def check_answer_auto():
    q = st.session_state.current_question
    if q is None:
        return
    user = st.session_state.user_answer
    # increment question counter even if wrong
    st.session_state.question_in_level += 1
    correct_flag = False
    try:
        if isinstance(st.session_state.current_answer, str):
            correct_flag = str(user).strip().lower() == str(st.session_state.current_answer).strip().lower()
        elif isinstance(st.session_state.current_answer, float):
            correct_flag = abs(float(user) - st.session_state.current_answer) <= 0.5
        else:
            correct_flag = abs(float(user) - float(st.session_state.current_answer)) < 1e-6
    except Exception:
        correct_flag = False

    if correct_flag:
        st.session_state.correct_in_level += 1
        st.session_state.score += 10
        st.success("Correct!")
    else:
        st.error(f"Incorrect. Correct answer: {st.session_state.current_answer}")

    st.session_state.history.append({'q':q['question'],'correct':correct_flag,'given':user})
    st.session_state.user_answer = ''

    # after QUESTIONS_PER_LEVEL -> show result
    if st.session_state.question_in_level >= QUESTIONS_PER_LEVEL:
        show_level_result()
    else:
        start_level_question()
        st.rerun()


def submit_shape_choice():
    choice = st.session_state.shape_choice
    st.session_state.question_in_level += 1
    correct_val = st.session_state.current_answer
    user_val = None
    try:
        user_val = float(choice)
    except Exception:
        pass
    ok = False
    if isinstance(correct_val, float):
        if user_val is not None and abs(user_val - correct_val) <= 0.5:
            ok = True
    else:
        try:
            ok = float(choice) == float(correct_val)
        except Exception:
            ok = False
    if ok:
        st.session_state.correct_in_level += 1
        st.session_state.score += 10
        st.success("Correct!")
    else:
        st.error(f"Wrong. Correct answer: {correct_val}")
    st.session_state.history.append({'q':st.session_state.current_question['question'],'correct':ok,'given':choice})
    st.session_state.shape_choice = None
    if st.session_state.question_in_level >= QUESTIONS_PER_LEVEL:
        show_level_result()
    else:
        start_level_question()
        st.rerun()


def show_level_result():
    total = st.session_state.question_in_level
    correct = st.session_state.correct_in_level
    percent = int(correct/total*100) if total>0 else 0
    passed = percent >= PASS_PERCENTAGE
    st.session_state.last_result = {'total':total,'correct':correct,'percent':percent,'passed':passed}
    # record progress
    grade = st.session_state.grade
    level = st.session_state.current_level
    st.session_state.level_progress.setdefault(grade, {})[level] = {'passed':passed,'score':st.session_state.score,'percent':percent}
    if passed:
        # unlock next level if exists
        if level < LEVELS_PER_GRADE:
            st.session_state.level_unlocked[grade] = max(st.session_state.level_unlocked.get(grade,1), level+1)
    # mark show flag
    st.session_state.show_level_result = True

# -------------------------
# Sidebar UI
# -------------------------
with st.sidebar:
    st.header("Player Setup")
    new_grade = st.selectbox("Select Grade (2 - 10)", options=list(range(2, 11)), index=st.session_state.grade-2)
    if new_grade != st.session_state.grade:
        st.session_state.grade = new_grade
        # reset level counters for new grade view
        st.session_state.current_level = 1
        st.session_state.question_in_level = 0
        st.session_state.correct_in_level = 0
        st.session_state.history = []
        st.session_state.show_level_result = False
        start_level_question()
        st.rerun()

    mode = st.radio("Mode", options=["Math Quiz","Shape Challenge"], index=0 if st.session_state.mode=='Math Quiz' else 1)
    st.session_state.mode = mode

    st.markdown("---")
    st.write(f"**Progress for Grade {st.session_state.grade}:**")
    prog = st.session_state.level_progress.get(st.session_state.grade, {})
    passed_levels = sum(1 for v in prog.values() if v.get('passed'))
    st.write(f"Levels passed: {passed_levels}/{LEVELS_PER_GRADE}")

    st.write(f"Unlocked level: {st.session_state.level_unlocked.get(st.session_state.grade,1)}")
    st.write(f"Current level: {st.session_state.current_level}")
    st.write(f"Score: {st.session_state.score if 'score' in st.session_state else 0}")

    st.markdown("---")
    st.write("Settings")
    tlim = st.slider("Time limit (seconds)", min_value=15, max_value=120, value=st.session_state.time_limit)
    st.session_state.time_limit = tlim
    if st.button("Reset Grade Progress"):
        st.session_state.level_progress[st.session_state.grade] = {}
        st.session_state.level_unlocked[st.session_state.grade] = 1
        st.session_state.current_level = 1
        st.session_state.history = []
        st.session_state.question_in_level = 0
        st.session_state.correct_in_level = 0
        st.session_state.show_level_result = False
        start_level_question()
        st.rerun()

# -------------------------
# Main UI
# -------------------------
st.title(APP_TITLE + " 🦸‍♂️")
st.markdown("<div style='background: linear-gradient(90deg,#A6C0FE,#F68084); padding:10px; border-radius:8px'>\
<h4 style='color:white; margin:0'>Learn, practice and level up! (Grades 2 - 10)</h4></div>", unsafe_allow_html=True)
st.write("---")

# Level selector and lock logic
col1, col2 = st.columns([3,1])
with col1:
    lvl = st.number_input("Choose Level (locked until passed previous)", min_value=1, max_value=LEVELS_PER_GRADE, value=st.session_state.current_level, step=1)
    lvl = int(lvl)
    # lock check
    if lvl > st.session_state.level_unlocked.get(st.session_state.grade,1):
        st.warning(f"Level {lvl} is locked. Complete previous levels to unlock.")
    else:
        st.session_state.current_level = lvl
with col2:
    if st.button("Start Level"):
        if st.session_state.current_level <= st.session_state.level_unlocked.get(st.session_state.grade,1):
            st.session_state.started = True
            st.session_state.question_in_level = 0
            st.session_state.correct_in_level = 0
            st.session_state.history = []
            st.session_state.show_level_result = False
            start_level_question()
            st.rerun()
        else:
            st.error("This level is locked.")

st.write(f"**Level {st.session_state.current_level} / {LEVELS_PER_GRADE}**")

# If not started, show instructions
if not st.session_state.started:
    st.info("Press Start Level to begin. You must get at least {}% to pass a level. Each level has {} questions.".format(PASS_PERCENTAGE, QUESTIONS_PER_LEVEL))
    st.stop()

# show current question number
st.write(f"Question {st.session_state.question_in_level + 1} of {QUESTIONS_PER_LEVEL}")

q = st.session_state.current_question
if not q:
    start_level_question()
    q = st.session_state.current_question

if q['type'] == 'math':
    st.subheader('Math')
    st.write(f"Topic: {q.get('topic','')}")
    st.write(q['question'])
    # text input auto-submit with Enter
    st.text_input('Your answer (press Enter to submit):', key='user_answer', on_change=check_answer_auto, placeholder='Type answer and press Enter')
    # time left
    elapsed = time.time() - st.session_state.question_start_time
    remaining = max(0, int(st.session_state.time_limit - elapsed))
    st.write(f"Time left: {remaining} seconds")
    if remaining == 0:
        st.warning("Time's up - moving to next question.")
        # treat as wrong and advance
        st.session_state.question_in_level += 1
        st.session_state.history.append({'q':q['question'],'correct':False,'given':None})
        if st.session_state.question_in_level >= QUESTIONS_PER_LEVEL:
            show_level_result()
        else:
            start_level_question()
            st.rerun()

else:
    st.subheader('Shape Challenge')
    buf = io.BytesIO()
    q['image'].save(buf, format='PNG')
    st.image(buf)
    st.write(q['question'])
    if q.get('choices'):
        # use radio with on_change to auto-submit selection
        st.radio('Choose answer:', options=[str(c) for c in q['choices']], key='shape_choice', on_change=submit_shape_choice)
    else:
        st.write('No choices for this shape question.')

# If level result ready show modal-like area
if st.session_state.show_level_result:
    res = st.session_state.last_result
    st.write('---')
    if res['passed']:
        st.balloons()
        st.success(f"Level Passed! Score: {res['correct']}/{res['total']} ({res['percent']}%)")
    else:
        st.error(f"Level Failed. Score: {res['correct']}/{res['total']} ({res['percent']}%). Try again to unlock next level.")
    st.markdown("**Level Summary:**")
    st.write(f"Correct: {res['correct']}")
    st.write(f"Total: {res['total']}")
    st.write(f"Percentage: {res['percent']}%")
    # offer retry or continue (if passed)
    colA, colB = st.columns(2)
    with colA:
        if st.button('Retry Level'):
            st.session_state.question_in_level = 0
            st.session_state.correct_in_level = 0
            st.session_state.history = []
            st.session_state.show_level_result = False
            start_level_question()
            st.rerun()
    with colB:
        if res['passed']:
            if st.button('Go to Next Level'):
                if st.session_state.current_level < LEVELS_PER_GRADE:
                    st.session_state.current_level += 1
                    st.session_state.question_in_level = 0
                    st.session_state.correct_in_level = 0
                    st.session_state.history = []
                    st.session_state.show_level_result = False
                    start_level_question()
                    st.rerun()
                else:
                    st.success('You completed all levels for this grade! Well done!')

# show small history
st.write('---')
st.subheader('Recent Questions')
for h in st.session_state.history[-5:][::-1]:
    st.write(f"- {h['q']} — {'✅' if h['correct'] else '❌'} (You: {h['given']})")

# footer
st.write('---')
st.caption('Math Hero v3 — Levels, locks, grade-wise topics, and Enter-to-submit implemented. Save progress by exporting level_progress if needed.')
