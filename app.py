import streamlit as st
import os
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
import plotly.express as px
import pandas as pd

# Load environment variables
load_dotenv()

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Custom CSS for vibrant design
st.markdown("""
    <style>
        body {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            font-family: 'Arial', sans-serif;
        }
        .stButton>button {
            background: #ff6b6b;
            border: 2px solid #404040;
            color: white;
            padding: 10px 20px;
            border-radius: 15px;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            transform: scale(1.05);
            background: #ff4d4d;
            box-shadow: 0 0 10px rgba(255, 107, 107, 0.5);
        }
        .header {
            font-size: 36px;
            text-align: center;
            margin: 20px 0;
            color: #ffe600;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        .confetti {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 1000;
        }
    </style>
""", unsafe_allow_html=True)

# Session State Management
class QuizState:
    def __init__(self):
        self.user_data = {
            'nickname': '',
            'score': 0,
            'correct_answers': 0,
            'avatar': '🤖',
            'badges': [],
            'history': [],
            'streak': 0,
            'power_ups': {'hints': 3, 'freeze': 1, 'double': 1}
        }
        self.current_question = None
        self.question_start_time = None
        self.leaderboard = []
        self.category = "General Knowledge"

def initialize_session():
    if 'quiz' not in st.session_state:
        st.session_state.quiz = QuizState()

initialize_session()

# Enhanced AI Question Generation with Categories
def generate_ai_question(category: str = "General Knowledge", difficulty: str = "medium"):
    prompt = f"""Generate a {difficulty} difficulty {category} question in JSON format with:
    - question
    - type (multiple_choice/true_false)
    - options (array for multiple_choice)
    - correct_answer
    - explanation
    - difficulty (1-5)
    - hint (short clue)
    Example format:
    {{
        "question": "What is the capital of France?",
        "type": "multiple_choice",
        "options": ["London", "Berlin", "Paris", "Madrid"],
        "correct_answer": "Paris",
        "explanation": "Paris has been the capital of France since the 5th century.",
        "difficulty": 2,
        "hint": "Known as the City of Light"
    }}"""
    try:
        completion = groq_client.chat.completions.create(
            messages=[{
                "role": "user",
                "content": prompt
            }],
            model="llama3-70b-8192",
            response_format={"type": "json_object"},
            temperature=0.7
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        st.error(f"AI Error: {str(e)}")
        return None

# Interactive Question Display with Power-ups
def display_question():
    if st.session_state.quiz.current_question is None:
        return

    # Check time remaining
    elapsed_time = (datetime.now() - st.session_state.quiz.question_start_time).total_seconds()
    time_left = max(20 - elapsed_time, 0)

    if time_left <= 0:
        handle_timeout()
        return

    q = st.session_state.quiz.current_question

    with st.form("question_form"):
        # Question text
        st.markdown(f"""
            <div style="font-size: 24px; padding: 20px; background: rgba(255, 255, 255, 0.1); 
            border-radius: 10px; margin: 20px 0;">
                {q['question']}
            </div>
        """, unsafe_allow_html=True)

        # Answer options
        if q['type'] == 'multiple_choice':
            answer = st.radio("Select your answer:", q['options'])
        else:
            answer = st.selectbox("True/False", ["True", "False"])

        # Timer display
        st.markdown(f"""
            <div class="timer" style="
                font-size: 24px;
                color: {'#ff4444' if time_left < 10 else '#4CAF50'};
                padding: 10px;
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.1);
                text-align: center;
                margin: 10px 0;
            ">⏳ {int(time_left // 60):02d}:{int(time_left % 60):02d}</div>
        """, unsafe_allow_html=True)

        # Form submit button
        submit = st.form_submit_button("Submit Answer")
        if submit:
            handle_answer(answer, q)

    # Power-ups section
    power_col1, power_col2, power_col3 = st.columns(3)
    with power_col1:
        if st.session_state.quiz.user_data['power_ups']['hints'] > 0:
            if st.button(f"Hint 🧠 ({st.session_state.quiz.user_data['power_ups']['hints']})", 
                        use_container_width=True):
                st.toast(q.get('hint', 'No hint available'))
                st.session_state.quiz.user_data['power_ups']['hints'] -= 1

    # Add similar blocks for other power-ups...

# Enhanced Answer Handling with Timeout Support
def handle_answer(user_answer, question):
    # Check time again in case of race conditions
    elapsed_time = (datetime.now() - st.session_state.quiz.question_start_time).total_seconds()
    if elapsed_time > 20:
        handle_timeout()
        return

    is_correct = user_answer == question['correct_answer']
    score = 10 * question['difficulty']

    # Update streak and apply power-ups
    if is_correct:
        st.session_state.quiz.user_data['streak'] += 1
        if st.session_state.quiz.user_data['streak'] % 3 == 0:
            st.session_state.quiz.user_data['power_ups']['hints'] += 1
    else:
        st.session_state.quiz.user_data['streak'] = 0

    # Update user data
    st.session_state.quiz.user_data['score'] += score if is_correct else 0
    st.session_state.quiz.user_data['correct_answers'] += 1 if is_correct else 0
    st.session_state.quiz.user_data['history'].append({
        'question': question['question'],
        'correct': is_correct,
        'timestamp': datetime.now().isoformat()
    })

    # Update leaderboard
    st.session_state.quiz.leaderboard.append({
        'nickname': st.session_state.quiz.user_data['nickname'],
        'score': st.session_state.quiz.user_data['score'],
        'avatar': st.session_state.quiz.user_data['avatar'],
        'category': st.session_state.quiz.category
    })

    # Visual feedback
    if is_correct:
        st.markdown("""
            <div class="confetti">
                <script>
                    const confettiSettings = { target: '.confetti', max: 150, size: 1, animate: true, 
                    props: ['circle', 'square'], colors: [[16,185,129], [239,68,68], [255,206,86]] };
                    const confetti = new Confetti(confettiSettings);
                    confetti.render();
                    setTimeout(() => confetti.clear(), 3000);
                </script>
            </div>
        """, unsafe_allow_html=True)
        st.success(f"✅ Correct! {question['explanation']}")
        st.audio("https://www.soundjay.com/button/sounds/beep-07.mp3", format='audio/mp3')
    else:
        st.error(f"❌ Incorrect. {question['explanation']}")
        st.audio("https://www.soundjay.com/button/sounds/beep-05.mp3", format='audio/mp3')

    # Proceed to next question
    next_question()

def handle_timeout():
    st.error("⏰ Time's up!")
    st.audio("https://www.soundjay.com/button/sounds/beep-05.mp3", format='audio/mp3')
    # Add timeout handling to history
    st.session_state.quiz.user_data['history'].append({
        'question': st.session_state.quiz.current_question['question'],
        'correct': False,
        'timestamp': datetime.now().isoformat()
    })
    next_question()

def next_question():
    check_achievements()
    st.session_state.quiz.current_question = None
    time.sleep(2)
    st.rerun()

# Registration Form and Other Components...
# (Keep existing registration_form, check_achievements, display_leaderboard, etc.)

# Main App Flow
def main():
    st.title("🚀 AI-Powered Quiz Arena")
    
    if not st.session_state.quiz.user_data['nickname']:
        registration_form()
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.quiz.current_question is None:
                with st.spinner('Generating question...'):
                    q = generate_ai_question(st.session_state.quiz.category)
                    if q:
                        st.session_state.quiz.current_question = q
                        st.session_state.quiz.question_start_time = datetime.now()
                    else:
                        st.error("Failed to generate question. Please try again!")
            display_question()
        
        with col2:
            # Sidebar content (keep existing implementation)
            pass

        # Keep existing analytics, feedback, and social sharing sections

    display_leaderboard()

if __name__ == "__main__":
    main()
