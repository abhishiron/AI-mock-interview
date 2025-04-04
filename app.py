import streamlit as st
import pyttsx3
import speech_recognition as sr
import os
from dotenv import load_dotenv
import google.generativeai as genai
import threading
import queue


load_dotenv()


genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


recognizer = sr.Recognizer()

def speak_text(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)
    engine.say(text)
    engine.runAndWait()

def get_feedback(answer, context):
    prompt = f"""
    Context: {context}
    Answer: {answer}
    Provide feedback on the answer and suggest areas of improvement.
    Limit your response to 50 words. Be concise.
    """
    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
    response = model.generate_content(prompt)
    return ' '.join(response.text.split()[:100])  

def generate_followup_question(previous_answer):
    prompt = f"""
    Based on the following answer, generate a follow-up question.
    Answer: {previous_answer}
    Limit the question to 20 words.
    """
    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
    response = model.generate_content(prompt)
    return ' '.join(response.text.split()[:50])  

def get_audio_response(q):
    with sr.Microphone() as source:
        recognizer.energy_threshold = 300
        recognizer.adjust_for_ambient_noise(source, duration=1)
        st.write("🎙 Listening for your response...")
        audio = recognizer.listen(source)
        try:
            response = recognizer.recognize_google(audio)
            q.put(response)
        except sr.UnknownValueError:
            q.put("Could not understand audio")
        except sr.RequestError as e:
            q.put(f"Could not request results; {e}")


def generate_initial_questions(job_type, experience_level, interview_format, focus_areas):
    return [
        f"Tell me about your experience in {job_type}.",
        f"What are your strengths and weaknesses as a {experience_level} professional?",
        f"How do you prepare for a {interview_format} interview?",
        f"What are the key focus areas in {focus_areas}?"
    ]


st.set_page_config(page_title="Mock Interview with AI Feedback", layout="wide")
st.title("💼 Mock Interview with AI Feedback")


st.header("Tell us about yourself")
job_type = st.text_area("Job or Industry", placeholder="e.g., software engineering, marketing, finance")
experience_level = st.text_area("Current Level of Experience", placeholder="e.g., entry-level, mid-level, senior-level")
interview_format = st.text_area("Preferred Interview Format", placeholder="e.g., behavioral, technical")
focus_areas = st.text_area("Specific Focus Areas", placeholder="e.g., communication, problem-solving")


if 'questions' not in st.session_state:
    st.session_state.questions = []
    st.session_state.current_question = 0
    st.session_state.responses = []
    st.session_state.current_response = ""
    st.session_state.recording = False
    st.session_state.total_feedback = []
    st.session_state.interview_started = False

if st.button("Start Mock Interview"):
    if job_type and experience_level and interview_format and focus_areas:
        st.session_state.questions = generate_initial_questions(job_type, experience_level, interview_format, focus_areas)
        st.session_state.current_question = 0
        st.session_state.responses = []
        st.session_state.current_response = ""
        st.session_state.recording = False
        st.session_state.total_feedback = []
        st.session_state.interview_started = True


def handle_question():
    if st.session_state.current_question < len(st.session_state.questions):
        question = st.session_state.questions[st.session_state.current_question]
        st.subheader(f"🧠 Question {st.session_state.current_question + 1}")
        st.write(question)

        q = queue.Queue()
        if st.session_state.recording:
            st.write("🎙 Recording...")
            response_thread = threading.Thread(target=get_audio_response, args=(q,))
            response_thread.start()
            response_thread.join()
            if not q.empty():
                st.session_state.current_response = q.get()
            st.session_state.recording = False
        else:
            if st.button("🎤 Double click to Start Recording Your Answer", key=f"record_{st.session_state.current_question}"):
                st.session_state.recording = True

        if st.session_state.current_response:
            st.write(f"🗣 Your Answer: {st.session_state.current_response}")
            feedback = get_feedback(st.session_state.current_response, question)
            st.write(f"📝 Feedback: {feedback}")
            speak_text(feedback)

            score = min(max(len(st.session_state.current_response.split()) // 5, 1), 10)
            st.session_state.total_feedback.append(score)

            followup_question = generate_followup_question(st.session_state.current_response)
            st.session_state.questions.append(followup_question)
            st.session_state.current_question += 1
            st.session_state.current_response = ""
            handle_question()


if st.session_state.interview_started:
    handle_question()


finish_button_placeholder = st.empty()
if finish_button_placeholder.button("Finish"):
    st.session_state.current_question = len(st.session_state.questions)
    st.session_state.interview_started = False
    st.write("✅ Mock Interview Finished!")

    if st.session_state.total_feedback:
        total_score = sum(st.session_state.total_feedback) // len(st.session_state.total_feedback)
    else:
        total_score = 0

    st.subheader(f"📊 Overall Feedback Score: {total_score}/10")

    if total_score >= 7:
        st.success("Great job! Keep it up!")
    elif 4 <= total_score < 7:
        st.warning("Good effort! There are some areas to improve.")
    else:
        st.error("Needs improvement. Focus on the feedback provided.")


st.sidebar.header("🧭 Navigation")
st.sidebar.info("Use the main area to interact with the interview. Responses are transcribed and scored in real time.")
