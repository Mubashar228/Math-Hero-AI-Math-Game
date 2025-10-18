# Math Hero - Streamlit Complete Prototype
# File: math_hero_streamlit_full.py
# Run: streamlit run math_hero_streamlit_full.py

import streamlit as st
import random
import time
from PIL import Image, ImageDraw, ImageFont
import io
import math

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="Math Hero",
    page_icon="🦸‍♂️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# -------------------------
# Helpers: session state init
# -------------------------

def init_state():
    defaults = {
        'grade': 3,
        'mode': 'Math Quiz',
        'score': 0,
        'level': 1,
        'question_index': 0,
        'started': False,
        'history': [],
        'current_question': None,
        'current_answer': None,
        'current_choices': None,
        'question_start_time': None,
        'time_limit': 30,  # seconds per question
        'consecutive_correct': 0,
        'weak_topics': {},  # track topic errors
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# -------------------------
# Utility: simple math question generators by topic
# -------------------------

def gen_addition(grade):
    a = random.randint(1, 10 * grade)
    b = random.randint(1, 10 * grade)
    q = f"{a} + {b} = ?"
    return q, a + b, None


def gen_subtraction(grade):
    a = random.randint(1, 10 * grade)
    b = random.randint(1, a)
    q = f"{a} - {b} = ?"
    return q, a - b, None


def gen_multiplication(grade):
    a = random.randint(1, grade + 5)
    b = random.randint(1, 12)
    q = f"{a} × {b} = ?"
    return q, a * b, None


def gen_division(grade):
    b = random.randint(1, min(12, grade + 6))
    c = random.randint(1, 12)
    a = b * c
    q = f"{a} ÷ {b} = ?"
    return q, c, None


def gen_fraction_add(grade):
    # simple fraction addition with same denominator
    d = random.choice([2,3,4,5,6])
    a = random.randint(1, d-1)
    b = random.randint(1, d-1)
    numerator = a + b
    q = f"{a}/{d} + {b}/{d} = ? (Answer as fraction simplified)"
    return q, f"{numerator}/{d}", None


def gen_algebra_linear(grade):
    x = random.randint(1, 10)
    m = random.randint(1, 5)
    c = random.randint(0, 10)
    a = m * x + c
    q = f"Solve for x: {m}x + {c} = {a}"
    return q, x, None


def gen_area_rectangle(grade):
    l = random.randint(1, 10 + grade)
    w = random.randint(1, 10 + grade)
    q = f"Area of rectangle with length {l} and width {w} = ?"
    return q, l*w, None


def choose_math_topic(grade):
    # choose topics based on grade
    if grade <= 4:
        topics = ['addition','subtraction','multiplication']
    elif grade <= 6:
        topics = ['addition','subtraction','multiplication','division']
    elif grade <= 8:
        topics = ['multiplication','division','fractions','area']
    else:
        topics = ['algebra','fractions','area','division']
    return random.choice(topics)


def generate_math_question(grade):
    topic = choose_math_topic(grade)
    if topic == 'addition':
        q, ans, meta = gen_addition(grade)
    elif topic == 'subtraction':
        q, ans, meta = gen_subtraction(grade)
    elif topic == 'multiplication':
        q, ans, meta = gen_multiplication(grade)
    elif topic == 'division':
        q, ans, meta = gen_division(grade)
    elif topic == 'fractions':
        q, ans, meta = gen_fraction_add(grade)
    elif topic == 'algebra':
        q, ans, meta = gen_algebra_linear(grade)
    elif topic == 'area':
        q, ans, meta = gen_area_rectangle(grade)
    else:
        q, ans, meta = gen_addition(grade)
    return {'type':'math','topic':topic,'question':q,'answer':ans,'meta':meta}

# -------------------------
# Shape challenge generator (draw with PIL)
# -------------------------

def draw_shape_image(shape, params):
    size = 300
    img = Image.new('RGB', (size, size), color=(255,255,255))
    draw = ImageDraw.Draw(img)
    margin = 30
    if shape == 'square':
        s = params.get('side', 100)
        x0 = (size - s)//2
        y0 = (size - s)//2
        draw.rectangle([x0,y0,x0+s,y0+s], outline='black', width=4)
    elif shape == 'rectangle':
        l = params.get('length', 160)
        w = params.get('width', 100)
        x0 = (size - l)//2
        y0 = (size - w)//2
        draw.rectangle([x0,y0,x0+l,y0+w], outline='black', width=4)
    elif shape == 'circle':
        r = params.get('radius', 70)
        cx, cy = size//2, size//2
        draw.ellipse([cx-r,cy-r,cx+r,cy+r], outline='black', width=4)
    elif shape == 'triangle':
        base = params.get('base', 160)
        h = params.get('height', 120)
        cx = size//2
        points = [(cx, (size-h)//2), (cx-base//2, (size+h)//2), (cx+base//2, (size+h)//2)]
        draw.polygon(points, outline='black')
    else:
        draw.text((20,20), 'Unknown shape', fill='black')
    return img


def generate_shape_question(grade):
    # select a shape based on grade
    shapes = ['square','rectangle','circle','triangle']
    shape = random.choice(shapes)
    if shape == 'square':
        side = random.randint(3 + grade, 6 + grade)
        question = f"A square has side = {side} cm. What is its area?"
        answer = side*side
        params = {'side': int(side*15/ (6+grade) * 6) if grade<6 else side*10}
    elif shape == 'rectangle':
        l = random.randint(4+grade, 8+grade)
        w = random.randint(2+grade, 5+grade)
        question = f"A rectangle has length = {l} cm and width = {w} cm. What is its perimeter?"
        answer = 2*(l+w)
        params = {'length': int(l*10), 'width': int(w*8)}
    elif shape == 'circle':
        r = random.randint(3+grade, 6+grade)
        question = f"A circle has radius = {r} cm. Approximate circumference (use π≈3.14)."
        answer = round(2*3.14*r,1)
        params = {'radius': int(r*6)}
    elif shape == 'triangle':
        b = random.randint(4+grade, 8+grade)
        h = random.randint(3+grade, 7+grade)
        question = f"A triangle has base = {b} cm and height = {h} cm. What is its area?"
        answer = round(0.5*b*h,1)
        params = {'base': int(b*10), 'height': int(h*8)}
    # create choices (4 options)
    choices = []
    if isinstance(answer, (int, float)):
        correct = answer
        choices.append(correct)
        for _ in range(3):
            # nearby wrong answers
            delta = random.randint(1, max(2, int(abs(correct)*0.2)+1))
            wrong = correct + random.choice([-1,1])*delta*random.randint(1,3)
            if isinstance(correct,float):
                wrong = round(wrong,1)
            choices.append(wrong)
        random.shuffle(choices)
    else:
        choices = None
    img = draw_shape_image(shape, params)
    return {'type':'shape','shape':shape,'question':question,'answer':answer,'choices':choices,'image':img}

# -------------------------
# Hints generator (simple rule-based)
# -------------------------

def generate_hint(qdict):
    if qdict['type'] == 'math':
        topic = qdict.get('topic')
        if topic == 'addition':
            return 'Try adding units first, then tens. Use carry if needed.'
        if topic == 'subtraction':
            return 'Try subtracting smaller digit from larger; borrow if necessary.'
        if topic == 'multiplication':
            return 'Multiply one number by each digit of the other, or use repeated addition.'
        if topic == 'division':
            return 'Think how many times divisor fits into dividend.'
        if topic == 'fractions':
            return 'Make denominators same, add numerators.'
        if topic == 'algebra':
            return 'Isolate x: subtract constant then divide by coefficient.'
        if topic == 'area':
            return 'Area = length × width (for rectangle).'
    elif qdict['type'] == 'shape':
        if 'area' in qdict['question'].lower():
            if 'triangle' in qdict['question'].lower():
                return 'Area of triangle = 1/2 × base × height.'
            else:
                return 'Multiply dimensions for area (or use π for circles).'
        if 'perimeter' in qdict['question'].lower():
            return 'Perimeter is sum of all sides.'
        if 'circumference' in qdict['question'].lower():
            return 'Use circumference = 2 × π × r (π≈3.14).'
    return 'Try to break the problem into smaller steps.'

# -------------------------
# Question lifecycle
# -------------------------

def start_new_question():
    # create new question based on mode and grade
    grade = st.session_state.grade
    if st.session_state.mode == 'Math Quiz':
        q = generate_math_question(grade)
    else:
        q = generate_shape_question(grade)
    st.session_state.current_question = q
    st.session_state.current_answer = q['answer']
    if q['type'] == 'shape':
        st.session_state.current_choices = q['choices']
    else:
        st.session_state.current_choices = None
    st.session_state.question_start_time = time.time()


def check_answer(user_input):
    q = st.session_state.current_question
    correct = st.session_state.current_answer
    topic = q.get('topic', q.get('shape'))
    # convert user_input if numeric
    try:
        if isinstance(correct, str):
            is_correct = str(user_input).strip() == str(correct).strip()
        elif isinstance(correct, float):
            val = float(user_input)
            is_correct = abs(val - correct) <= 0.5
        else:
            val = float(user_input)
            is_correct = abs(val - float(correct)) < 1e-6
    except Exception:
        is_correct = False
    return is_correct

# -------------------------
# UI: Sidebar settings
# -------------------------
with st.sidebar:
    st.header("Player Setup")
    grade = st.selectbox("Select Grade (3 - 10)", options=list(range(3, 11)), index=st.session_state.grade-3)
    st.session_state.grade = grade

    mode = st.radio("Choose Mode", options=["Math Quiz", "Shape Challenge"], index=0 if st.session_state.mode=='Math Quiz' else 1)
    st.session_state.mode = mode

    st.markdown("---")
    st.write(f"**Current Grade:** {st.session_state.grade}")
    st.write(f"**Mode:** {st.session_state.mode}")
    st.write(f"**Level:** {st.session_state.level}")
    st.write(f"**Score:** {st.session_state.score}")
    st.write(f"**Consecutive Correct:** {st.session_state.consecutive_correct}")

    st.markdown("---")
    st.write("Time limit per question (seconds)")
    tlim = st.slider("Time limit", min_value=10, max_value=90, value=st.session_state.time_limit)
    st.session_state.time_limit = tlim

    if st.button("Reset Progress"):
        for k in ['score','level','question_index','started','history','current_question','current_answer','current_choices','question_start_time','consecutive_correct','weak_topics']:
            if k in st.session_state:
                del st.session_state[k]
        init_state()
        st.rerun()

# -------------------------
# Main UI
# -------------------------
st.title("Math Hero 🦸‍♂️ — Learn. Play. Level Up.")
st.markdown("<div style='background: linear-gradient(90deg,#A6C0FE,#F68084); padding:12px; border-radius:10px'>\
<h3 style='color:white; margin:0'>Welcome to Math Hero!</h3>\
<p style='color:#fff; margin:0'>Solve problems, identify shapes, and move through levels. Grades 3-10.</p></div>", unsafe_allow_html=True)

st.write("\n")


# Controls: Start / Next / Hint
col1, col2, col3 = st.columns([1,1,1])
with col1:
    if st.button("Start Game ▶️"):
        st.session_state.started = True
        st.session_state.score = 0
        st.session_state.level = 1
        st.session_state.question_index = 0
        st.session_state.consecutive_correct = 0
        st.session_state.history = []
        start_new_question()
        st.rerun()

with col2:
    if st.button("Next Question ⏭️"):
        start_new_question()
        st.rerun()
with col3:
    if st.button("Give Hint 💡"):
        if st.session_state.current_question:
            st.info(generate_hint(st.session_state.current_question))

st.write("---")

if not st.session_state.started:
    st.write("Press **Start Game** to begin. You can configure grade and time limit on the left.")
    st.write("Features: level progression, shape visuals, timed questions, hints, and adaptive practice.")
    st.write("Recommended: Start with Grade 3 and try a few rounds to see how leveling works.")
    st.write("---")
else:
    q = st.session_state.current_question
    if not q:
        start_new_question()
        q = st.session_state.current_question

    # show progress
    st.progress(min(100, st.session_state.consecutive_correct * 20))
    st.markdown(f"**Level:** {st.session_state.level} &nbsp;&nbsp; **Score:** {st.session_state.score}")

    # show question depending on type
    if q['type'] == 'math':
        st.subheader("Math Question")
        st.write(f"**Topic:** {q.get('topic', 'General')}")
        st.write(q['question'])
        # show input
        ans = st.text_input("Your answer", key='answer_input')
        # show elapsed time
        elapsed = time.time() - st.session_state.question_start_time
        remaining = max(0, int(st.session_state.time_limit - elapsed))
        st.write(f"Time left: {remaining} seconds")
        if remaining == 0:
            st.warning("Time's up! Try the next question.")
            st.session_state.history.append({'question':q['question'],'correct':False,'given':None})
            st.session_state.consecutive_correct = 0
            start_new_question()
            st.rerun()

        if st.button("Submit Answer"):
            correct = check_answer(ans)
            if correct:
                st.success("Correct! 🎉")
                st.session_state.score += 10
                st.session_state.consecutive_correct += 1
                st.session_state.history.append({'question':q['question'],'correct':True,'given':ans})
                # update weak topics
                topic = q.get('topic')
                if topic and topic in st.session_state.weak_topics:
                    st.session_state.weak_topics[topic] = max(0, st.session_state.weak_topics[topic]-1)
            else:
                st.error(f"Not quite. The correct answer was: {st.session_state.current_answer}")
                st.session_state.consecutive_correct = 0
                st.session_state.history.append({'question':q['question'],'correct':False,'given':ans})
                topic = q.get('topic')
                if topic:
                    st.session_state.weak_topics[topic] = st.session_state.weak_topics.get(topic,0)+1
            # level up condition
            if st.session_state.consecutive_correct >= 5:
                st.session_state.level += 1
                st.balloons()
                st.success(f"Level up! You reached level {st.session_state.level} 🎉")
                st.session_state.consecutive_correct = 0
            start_new_question()
            st.rerun()


    else:  # shape
        st.subheader("Shape Challenge")
        img = q['image']
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        st.image(buf)
        st.write(q['question'])
        choices = q['choices']
        if choices:
            choice = st.radio("Choose:", options=[str(c) for c in choices], key='shape_choice')
            if st.button("Submit Shape Answer"):
                correct_val = st.session_state.current_answer
                try:
                    user_val = float(choice)
                except:
                    user_val = None
                if isinstance(correct_val, float):
                    ok = abs(user_val - correct_val) <= 0.5
                else:
                    ok = user_val == correct_val
                if ok:
                    st.success("Correct! 🎉")
                    st.session_state.score += 10
                    st.session_state.consecutive_correct += 1
                else:
                    st.error(f"Wrong. Correct answer: {correct_val}")
                    st.session_state.consecutive_correct = 0
                # record
                st.session_state.history.append({'question':q['question'],'correct':ok,'given':choice})
                if st.session_state.consecutive_correct >= 5:
                    st.session_state.level += 1
                    st.balloons()
                    st.success(f"Level up! You reached level {st.session_state.level} 🎉")
                    st.session_state.consecutive_correct = 0
                start_new_question()
                st.rerun()
        else:
            st.write("No multiple choices available for this question.")

    st.write('---')
    st.subheader('Session Summary')
    st.write(f"Total Score: {st.session_state.score}")
    st.write(f"Questions attempted: {len(st.session_state.history)}")
    if st.session_state.history:
        last = st.session_state.history[-5:]
        for i, h in enumerate(last[::-1],1):
            st.write(f"{i}. {h['question']} — {'✅' if h['correct'] else '❌'} (You: {h['given']})")
    if st.session_state.weak_topics:
        st.markdown('**Weak topics (more practice needed):**')
        sorted_weak = sorted(st.session_state.weak_topics.items(), key=lambda x: -x[1])
        for t, cnt in sorted_weak:
            if cnt>0:
                st.write(f"- {t}: {cnt} mistakes")

# Footer notes
st.write('---')
st.caption('Math Hero — Prototype. Next steps: add persistent leaderboard, audio feedback, and LLM hints.')
