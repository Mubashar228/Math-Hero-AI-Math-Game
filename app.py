# math_hero_complete.py
import streamlit as st
import random
import time
import math
from PIL import Image, ImageDraw
import io

# ---------------- APP CONFIG ----------------
APP_TITLE = "Math Hero – AI Math Game"
LEVELS_PER_GRADE = 20
QUESTIONS_PER_LEVEL = 10
PASS_PERCENTAGE = 70  # percent required to pass a level

st.set_page_config(page_title=APP_TITLE, page_icon="🦸‍♂️", layout="centered")

# ---------------- SAFE INITIALIZATION ----------------
defaults = {
    "grade": 3,
    "mode": "Math Quiz",            # or "Shape Challenge"
    "current_level": 1,
    "level_unlocked": {g: 1 for g in range(2, 11)},     # which level is unlocked per grade
    "level_progress": {g: {} for g in range(2, 11)},    # store pass/fail per level
    "started": False,
    "current_question": None,
    "current_answer": None,
    "current_choices": None,
    "question_start_time": None,
    "time_limit": 45,
    "question_in_level": 0,
    "correct_in_level": 0,
    "history": [],
    "user_answer": "",
    "show_level_result": False,
    "last_result": None,
    "score": 0,   # overall score for session
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ---------------- HELPERS: question generators ----------------

# Basic ops for early grades
def gen_addition(maxv):
    a = random.randint(1, maxv)
    b = random.randint(1, maxv)
    return f"{a} + {b} = ?", a + b

def gen_subtraction(maxv):
    a = random.randint(1, maxv)
    b = random.randint(1, a)
    return f"{a} - {b} = ?", a - b

def gen_multiplication(maxv):
    a = random.randint(1, maxv)
    b = random.randint(1, maxv)
    return f"{a} × {b} = ?", a * b

def gen_division(maxv):
    b = random.randint(1, maxv)
    c = random.randint(1, maxv)
    a = b * c
    return f"{a} ÷ {b} = ?", c

def gen_comparison(maxv):
    a = random.randint(0, maxv)
    b = random.randint(0, maxv)
    q = f"Which is greater: {a} or {b}? Write '>' or '<' or '='."
    ans = ">" if a > b else "<" if a < b else "="
    return q, ans

def gen_simple_statement(grade):
    a = random.randint(1, 10*grade)
    b = random.randint(1, 5*grade)
    q = f"Ali had {a} apples. He gave {b} apples to Ahmed. How many apples left?"
    return q, a - b

# Fractions (returns numeric approx for checking or simplified string)
def gen_fraction_add(grade):
    # generate with common denom for simplicity
    d = random.randint(2, 8)
    a = random.randint(1, d-1)
    b = random.randint(1, d-1)
    num = a + b
    den = d
    # simplify
    g = math.gcd(num, den)
    simp_num = num // g
    simp_den = den // g
    q = f"{a}/{d} + {b}/{d} = ? (Answer as simplified fraction or decimal)"
    # we will accept both simplified fraction string and decimal approx
    return q, {"fraction": f"{simp_num}/{simp_den}", "decimal": round(num/den, 3)}

def gen_fraction_to_mixed(grade):
    a = random.randint(5, 20)
    b = random.randint(2, 8)
    q = f"Write {a}/{b} as a mixed number."
    whole = a // b
    rem = a % b
    if rem == 0:
        ans = f"{whole}"
    else:
        ans = f"{whole} {rem}/{b}"
    return q, ans

def gen_lcm(grade):
    a = random.randint(2, 20)
    b = random.randint(2, 20)
    return f"Find LCM of {a} and {b}.", (a * b) // math.gcd(a, b)

def gen_hcf(grade):
    a = random.randint(2, 50)
    b = random.randint(2, 50)
    return f"Find HCF (GCD) of {a} and {b}.", math.gcd(a, b)

def gen_percentage(grade):
    base = random.randint(10, 200)
    per = random.choice([5,10,15,20,25,30])
    q = f"What is {per}% of {base}?"
    return q, round(base * per / 100, 2)

def gen_profit_loss(grade):
    cp = random.randint(50, 500)
    pct = random.choice([5,10,15,20,25,30])
    sp = round(cp * (1 + pct/100), 2)
    q = f"Cost price = {cp}, profit = {pct}%. What is selling price?"
    return q, sp

def gen_area_rectangle(grade):
    l = random.randint(1, 20)
    w = random.randint(1, 20)
    return f"Area of rectangle (length={l}, width={w}) = ?", l * w

def gen_perimeter_rectangle(grade):
    l = random.randint(1, 20)
    w = random.randint(1, 20)
    return f"Perimeter of rectangle (length={l}, width={w}) = ?", 2*(l + w)

# Higher grade topics
def gen_function_eval(grade):
    a = random.randint(1,5)
    b = random.randint(0,5)
    x = random.randint(1,10)
    q = f"If f(x) = {a}x + {b}, find f({x})."
    return q, a*x + b

def gen_set_membership(grade):
    A = set(random.sample(range(1,20), 5))
    x = random.choice(list(A))
    q = f"Given set A = {sorted(A)}. Is {x} in A? Answer 'yes' or 'no'."
    return q, "yes"

def gen_trig_basic(grade):
    choices = [(30, 0.5), (45, round(math.sqrt(2)/2,3)), (60, round(math.sqrt(3)/2,3))]
    ang, val = random.choice(choices)
    q = f"What is sin({ang}°)? (approx)"
    return q, val

def gen_slope(grade):
    x1 = random.randint(0,5)
    y1 = random.randint(0,5)
    x2 = x1 + random.randint(1,5)
    y2 = y1 + random.randint(-3,5)
    q = f"Find slope of line through ({x1},{y1}) and ({x2},{y2})."
    slope = round((y2 - y1) / (x2 - x1), 3)
    return q, slope

def gen_matrix_add(grade):
    a,b,c,d = [random.randint(0,5) for _ in range(4)]
    e,f_,g,h = [random.randint(0,5) for _ in range(4)]
    q = f"Add matrices [[{a},{b}],[{c},{d}]] + [[{e},{f_}],[{g},{h}]]. Write result as [[x,y],[z,w]]."
    ans = f"[[{a+e},{b+f_}],[{c+g},{d+h}]]"
    return q, ans

# ---------------- SHAPE DRAWING ----------------
def draw_shape(shape, params):
    size = 300
    img = Image.new('RGB', (size, size), color=(255,255,255))
    draw = ImageDraw.Draw(img)
    if shape == "square":
        s = params.get("s_px", 120)
        x0 = (size - s)//2
        y0 = (size - s)//2
        draw.rectangle([x0,y0,x0+s,y0+s], outline="black", width=4)
    elif shape == "rectangle":
        l = params.get("l_px", 160)
        w = params.get("w_px", 100)
        x0 = (size - l)//2
        y0 = (size - w)//2
        draw.rectangle([x0,y0,x0+l,y0+w], outline="black", width=4)
    elif shape == "circle":
        r = params.get("r_px", 70)
        cx, cy = size//2, size//2
        draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline="black", width=4)
    elif shape == "triangle":
        base = params.get("base_px", 160)
        h = params.get("h_px", 120)
        cx = size//2
        pts = [(cx, (size-h)//2), (cx-base//2, (size+h)//2), (cx+base//2, (size+h)//2)]
        draw.polygon(pts, outline="black")
    return img

def gen_shape_question(grade):
    shape = random.choice(["square","rectangle","circle","triangle"])
    if shape == "square":
        side = random.randint(3+grade, 6+grade)
        q = f"A square has side = {side} cm. What is its area?"
        ans = side * side
        params = {"s_px": int(side * 6)}
    elif shape == "rectangle":
        l = random.randint(4+grade, 8+grade)
        w = random.randint(2+grade, 5+grade)
        q = f"A rectangle has length = {l} cm and width = {w} cm. What is its perimeter?"
        ans = 2 * (l + w)
        params = {"l_px": int(l * 10), "w_px": int(w * 8)}
    elif shape == "circle":
        r = random.randint(3+grade, 6+grade)
        q = f"A circle has radius = {r} cm. Approximate circumference (π≈3.14)."
        ans = round(2 * 3.14 * r, 1)
        params = {"r_px": int(r * 6)}
    else:
        b = random.randint(4+grade, 8+grade)
        h = random.randint(3+grade, 7+grade)
        q = f"A triangle has base = {b} cm and height = {h} cm. What is its area?"
        ans = round(0.5 * b * h, 1)
        params = {"base_px": int(b * 10), "h_px": int(h * 8)}
    img = draw_shape(shape, params)
    # prepare choices
    choices = []
    if isinstance(ans, (int, float)):
        choices.append(ans)
        for _ in range(3):
            delta = max(1, int(abs(ans) * 0.15) or 1)
            wrong = ans + random.choice([-1,1]) * random.randint(1, delta+3)
            if isinstance(ans, float):
                wrong = round(wrong, 1)
            choices.append(wrong)
        random.shuffle(choices)
    return {"type":"shape", "question": q, "answer": ans, "choices": choices, "image": img}

# ---------------- TOPIC SELECTION ----------------
def choose_topic_by_grade(grade):
    if grade <= 4:
        return random.choice(["addition","subtraction","multiplication","division","comparison","simple_statement"])
    elif grade <= 8:
        return random.choice(["fractions_add","fraction_mixed","lcm","hcf","percentage","profit","area_rect","perimeter_rect","mul_basic"])
    else:
        return random.choice(["function","sets","trig","slope","fraction_mixed","matrix"])

def generate_math_question_for_grade(grade):
    topic = choose_topic_by_grade(grade)
    # single call pattern: call generator once and return both q & a
    if topic == "addition":
        q,a = gen_addition(10 * grade)
        return {"type":"math","topic":"addition","question":q,"answer":a}
    if topic == "subtraction":
        q,a = gen_subtraction(10 * grade)
        return {"type":"math","topic":"subtraction","question":q,"answer":a}
    if topic == "multiplication" or topic == "mul_basic":
        q,a = gen_multiplication(max(12, grade+2))
        return {"type":"math","topic":"multiplication","question":q,"answer":a}
    if topic == "division":
        q,a = gen_division(min(12, grade+6))
        return {"type":"math","topic":"division","question":q,"answer":a}
    if topic == "comparison":
        q,a = gen_comparison(20)
        return {"type":"math","topic":"comparison","question":q,"answer":a}
    if topic == "simple_statement":
        q,a = gen_simple_statement(grade)
        return {"type":"math","topic":"word_problem","question":q,"answer":a}
    if topic == "fractions_add":
        q,a = gen_fraction_add(grade)
        return {"type":"math","topic":"fractions","question":q,"answer":a}
    if topic == "fraction_mixed":
        q,a = gen_fraction_to_mixed(grade)
        return {"type":"math","topic":"fractions_mixed","question":q,"answer":a}
    if topic == "lcm":
        q,a = gen_lcm(grade)
        return {"type":"math","topic":"lcm","question":q,"answer":a}
    if topic == "hcf":
        q,a = gen_hcf(grade)
        return {"type":"math","topic":"hcf","question":q,"answer":a}
    if topic == "percentage":
        q,a = gen_percentage(grade)
        return {"type":"math","topic":"percentage","question":q,"answer":a}
    if topic == "profit":
        q,a = gen_profit_loss(grade)
        return {"type":"math","topic":"profit_loss","question":q,"answer":a}
    if topic == "area_rect":
        q,a = gen_area_rectangle(grade)
        return {"type":"math","topic":"area","question":q,"answer":a}
    if topic == "perimeter_rect":
        q,a = gen_perimeter_rectangle(grade)
        return {"type":"math","topic":"perimeter","question":q,"answer":a}
    if topic == "function":
        q,a = gen_function_eval(grade)
        return {"type":"math","topic":"function","question":q,"answer":a}
    if topic == "sets":
        q,a = gen_set_membership(grade)
        return {"type":"math","topic":"sets","question":q,"answer":a}
    if topic == "trig":
        q,a = gen_trig_basic(grade)
        return {"type":"math","topic":"trigonometry","question":q,"answer":a}
    if topic == "slope":
        q,a = gen_slope(grade)
        return {"type":"math","topic":"slope","question":q,"answer":a}
    if topic == "matrix":
        q,a = gen_matrix_add(grade)
        return {"type":"math","topic":"matrix","question":q,"answer":a}

    # fallback
    q,a = gen_addition(10 * grade)
    return {"type":"math","topic":"addition","question":q,"answer":a}

# ---------------- QUESTION LIFECYCLE ----------------
def start_new_question():
    # if current level is locked, do nothing
    grade = st.session_state.grade
    lvl = st.session_state.current_level
    if lvl > st.session_state.level_unlocked.get(grade, 1):
        return
    # generate either math or shape question based on mode
    if st.session_state.mode == "Math Quiz":
        qdict = generate_math_question_for_grade(grade)
    else:
        qdict = gen_shape_question(grade)
    # store question and answer once
    st.session_state.current_question = qdict
    st.session_state.current_answer = qdict["answer"]
    st.session_state.current_choices = qdict.get("choices")
    st.session_state.question_start_time = time.time()
    # clear user_answer safely
    st.session_state.update({"user_answer": ""})

def safe_increment_and_continue(correct_flag, given):
    # record
    st.session_state.question_in_level += 1
    if correct_flag:
        st.session_state.correct_in_level += 1
        st.session_state.score += 10
    st.session_state.history.append({"q": st.session_state.current_question["question"], "correct": correct_flag, "given": given})
    # clear current question
    st.session_state.update({"user_answer": ""})
    st.session_state.current_question = None
    st.session_state.current_answer = None
    st.session_state.current_choices = None
    # decide next step
    if st.session_state.question_in_level >= QUESTIONS_PER_LEVEL:
        # finalize level
        total = st.session_state.question_in_level
        correct = st.session_state.correct_in_level
        percent = int(correct / total * 100) if total > 0 else 0
        passed = percent >= PASS_PERCENTAGE
        st.session_state.last_result = {"total": total, "correct": correct, "percent": percent, "passed": passed}
        # store progress
        grade = st.session_state.grade
        level = st.session_state.current_level
        st.session_state.level_progress.setdefault(grade, {})[level] = {"passed": passed, "percent": percent, "score": st.session_state.score}
        if passed and level < LEVELS_PER_GRADE:
            st.session_state.level_unlocked[grade] = max(st.session_state.level_unlocked.get(grade, 1), level + 1)
        st.session_state.show_level_result = True
    else:
        # next question
        start_new_question()
        st.rerun()

# Callback for Enter in text_input for math
def on_enter_submit():
    q = st.session_state.current_question
    if q is None:
        return
    user_raw = st.session_state.user_answer
    given = user_raw.strip()
    correct_flag = False
    # answer checking logic: handles numeric, float tolerance, fractions (dict), and strings
    correct = st.session_state.current_answer
    try:
        if isinstance(correct, dict):
            # fraction answer dict: accept fraction string or decimal approx
            frac_expected = correct.get("fraction")
            dec_expected = correct.get("decimal")
            # try normalized string comparison
            if given == frac_expected:
                correct_flag = True
            else:
                try:
                    if abs(float(given) - float(dec_expected)) <= 0.01:
                        correct_flag = True
                except:
                    correct_flag = False
        elif isinstance(correct, (int, float)):
            # numeric comparison with tolerance for floats
            try:
                if abs(float(given) - float(correct)) <= 0.5:
                    correct_flag = True
            except:
                correct_flag = False
        else:
            # string comparison (case-insensitive)
            if str(given).lower() == str(correct).lower():
                correct_flag = True
    except Exception:
        correct_flag = False
    # record and continue
    safe_increment_and_continue(correct_flag, given)

# Callback for shape choice (radio)
def on_shape_choice():
    choice = st.session_state.shape_choice
    try:
        user_val = float(choice)
    except:
        user_val = None
    correct = st.session_state.current_answer
    ok = False
    if isinstance(correct, float):
        if user_val is not None and abs(user_val - correct) <= 0.5:
            ok = True
    else:
        try:
            ok = float(choice) == float(correct)
        except:
            ok = False
    safe_increment_and_continue(ok, choice)

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("Player Setup")
    new_grade = st.selectbox("Select Grade (2 - 10)", options=list(range(2,11)), index=st.session_state.grade-2)
    if new_grade != st.session_state.grade:
        # reset grade progress view but keep stored progress
        st.session_state.update({
            "grade": new_grade,
            "current_level": 1,
            "question_in_level": 0,
            "correct_in_level": 0,
            "history": [],
            "show_level_result": False,
            "last_result": None,
            "started": False
        })
        # generate a question for the new grade
        start_new_question()
        st.rerun()

    mode = st.radio("Mode", options=["Math Quiz", "Shape Challenge"], index=0 if st.session_state.mode=="Math Quiz" else 1)
    st.session_state.mode = mode

    st.markdown("---")
    st.write(f"Grade: {st.session_state.grade}")
    st.write(f"Current Level: {st.session_state.current_level}/{LEVELS_PER_GRADE}")
    st.write(f"Unlocked Level: {st.session_state.level_unlocked.get(st.session_state.grade,1)}")
    passed_ct = sum(1 for v in st.session_state.level_progress.get(st.session_state.grade, {}).values() if v.get("passed"))
    st.write(f"Levels passed: {passed_ct}/{LEVELS_PER_GRADE}")
    st.write(f"Score (session): {st.session_state.score}")

    st.markdown("---")
    new_time = st.slider("Time limit (sec) per question", min_value=15, max_value=120, value=st.session_state.time_limit)
    st.session_state.time_limit = new_time

    if st.button("Reset Grade Progress"):
        st.session_state.level_progress[st.session_state.grade] = {}
        st.session_state.level_unlocked[st.session_state.grade] = 1
        st.session_state.update({
            "current_level": 1,
            "question_in_level": 0,
            "correct_in_level": 0,
            "history": [],
            "show_level_result": False,
            "last_result": None
        })
        start_new_question()
        st.rerun()

# ---------------- MAIN UI ----------------
st.title(APP_TITLE)
st.markdown("<div style='background: linear-gradient(90deg,#A6C0FE,#F68084); padding:10px; border-radius:8px'>\
<h4 style='color:white; margin:0'>Learn, practice and level up! (Grades 2 - 10)</h4></div>", unsafe_allow_html=True)
st.write("---")

# Level selection and start
col1, col2 = st.columns([3,1])
with col1:
    chosen_lvl = st.number_input("Choose Level", min_value=1, max_value=LEVELS_PER_GRADE, value=st.session_state.current_level, step=1)
    chosen_lvl = int(chosen_lvl)
    if chosen_lvl > st.session_state.level_unlocked.get(st.session_state.grade, 1):
        st.warning(f"Level {chosen_lvl} is locked. Complete previous levels to unlock.")
    else:
        st.session_state.current_level = chosen_lvl

with col2:
    if st.button("Start Level"):
        if st.session_state.current_level <= st.session_state.level_unlocked.get(st.session_state.grade, 1):
            st.session_state.update({
                "started": True,
                "question_in_level": 0,
                "correct_in_level": 0,
                "history": [],
                "show_level_result": False,
                "last_result": None
            })
            start_new_question()
            st.rerun()
        else:
            st.error("This level is locked.")

st.write(f"**Level {st.session_state.current_level} / {LEVELS_PER_GRADE}**")

if not st.session_state.started:
    st.info(f"Press Start Level to begin. You must score at least {PASS_PERCENTAGE}% to pass a level. Each level has {QUESTIONS_PER_LEVEL} questions.")
    st.stop()

# Show progress in the level
st.write(f"Question {st.session_state.question_in_level + 1} of {QUESTIONS_PER_LEVEL}")
if st.session_state.current_question is None:
    start_new_question()

qdict = st.session_state.current_question
if not qdict:
    st.write("Generating question...")
    start_new_question()
    st.rerun()
else:
    if qdict["type"] == "math":
        st.subheader("Math Question")
        st.write(f"Topic: {qdict.get('topic','General')}")
        st.write(qdict["question"])
        # text input with Enter-to-submit: on_change => on_enter_submit
        st.text_input("Your answer (press Enter):", key="user_answer", on_change=on_enter_submit, placeholder="Type answer and press Enter")
        # show time left
        elapsed = time.time() - st.session_state.question_start_time
        remaining = max(0, int(st.session_state.time_limit - elapsed))
        st.write(f"Time left: {remaining} seconds")
        if remaining == 0:
            # treat as wrong and advance
            safe_increment_and_continue(False, None)
            st.rerun()

    else:
        st.subheader("Shape Challenge")
        buf = io.BytesIO()
        qdict["image"].save(buf, format="PNG")
        st.image(buf)
        st.write(qdict["question"])
        if qdict.get("choices"):
            st.radio("Choose answer:", options=[str(c) for c in qdict["choices"]], key="shape_choice", on_change=on_shape_choice)
        else:
            st.write("No multiple choice available for this question.")
            st.text_input("Type answer (press Enter):", key="user_answer", on_change=on_enter_submit)

# Show level result if ready
if st.session_state.show_level_result:
    res = st.session_state.last_result
    st.write("---")
    if res["passed"]:
        st.balloons()
        st.success(f"Level Passed! Score: {res['correct']}/{res['total']} ({res['percent']}%)")
    else:
        st.error(f"Level Failed. Score: {res['correct']}/{res['total']} ({res['percent']}%).")

    st.markdown("**Level Summary**")
    st.write(f"- Correct: {res['correct']}")
    st.write(f"- Total: {res['total']}")
    st.write(f"- Percentage: {res['percent']}%")

    colA, colB = st.columns(2)
    with colA:
        if st.button("Retry Level"):
            st.session_state.update({
                "question_in_level": 0,
                "correct_in_level": 0,
                "history": [],
                "show_level_result": False,
                "last_result": None
            })
            start_new_question()
            st.rerun()
    with colB:
        if res["passed"]:
            if st.button("Go to Next Level"):
                if st.session_state.current_level < LEVELS_PER_GRADE:
                    st.session_state.current_level += 1
                    st.session_state.update({
                        "question_in_level": 0,
                        "correct_in_level": 0,
                        "history": [],
                        "show_level_result": False,
                        "last_result": None
                    })
                    start_new_question()
                    st.rerun()
                else:
                    st.success("You completed all levels for this grade! 🎉")

# recent history
st.write("---")
st.subheader("Recent Questions")
for h in st.session_state.history[-5:][::-1]:
    st.write(f"- {h['q']} — {'✅' if h['correct'] else '❌'} (You: {h['given']})")

st.caption("Math Hero — Stable full version. Questions generated once per prompt; Enter submits answers; input cleared safely; level locking implemented.")
