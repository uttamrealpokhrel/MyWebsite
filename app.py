from flask import Flask, render_template, jsonify, request, send_from_directory
import webbrowser
import threading
import time
import os
import subprocess
import json
import requests

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

# In-memory store to avoid repeating identical answers to the same client
last_responses = {}

# Comprehensive system prompt to train ChatGPT about Uttam Pokhrel and the website
UTTAM_SYSTEM_PROMPT = """You are an AI assistant representing Uttam Pokhrel's official website. Here's what you know:

ABOUT UTTAM POKHREL:
- A passionate content creator and B.Sc.CSIT student at Tribhuvan University (Nepal)
- Expertise: AI, Machine Learning, Python programming, Web Development (HTML, CSS, JavaScript)
- YouTube Channel: https://youtube.com/@UttamRealPok - creates educational tech content
- Goal: Inspire and educate others in programming, AI, and technology
- Motto: "If you have something, simply share it with someone"

SKILLS & EXPERTISE:
- Programming: Python, JavaScript, HTML, CSS
- AI/ML: Machine Learning basics, AI tools
- Backend: Flask framework
- Frontend: HTML, CSS, JavaScript
- Tools: Git/GitHub, VS Code, Video editing
- Content Creation: YouTube, online teaching

WEBSITE SERVICES:
- Portfolio showcasing projects and work
- AI Chatbot (you!) for answering questions about Uttam Pokhrel
- Python code runner for educational purposes
- Contact information for collaborations
- Registration form for learning community
- Payment methods for support/donations

CONTACT INFO:
- Email: uttamrealpok@gmail.com
- WhatsApp/Call: +977 9815394998
- YouTube: @UttamRealPok

INSTRUCTIONS:
- Be helpful and educational
- Mention Uttam Pokhrel's background when relevant
- Suggest relevant resources (YouTube, contact methods)
- Answer questions about AI, programming, web development expertly
- Be friendly and encouraging
- If asked about general topics, answer helpfully while connecting to tech/education when possible
- Recommend checking Uttam Pokhrel's YouTube for video tutorials"""


# Serve HTML files directly
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

@app.route("/follow")
def follow():
    return render_template("follow.html")

@app.route("/skills")
def skills():
    skills_list = ["HTML & CSS", "JavaScript", "Python", "Artificial Intelligence", "YouTube Content Creation"]
    return jsonify(skills_list)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "")
    mode = data.get("mode", "local")  # 'local' or 'gpt'

    def client_key():
        # use remote address as a simple client key; falls back to 'anon'
        try:
            return request.remote_addr or 'anon'
        except Exception:
            return 'anon'

    # If user requests GPT and server has OPENAI_API_KEY, forward to OpenAI
    if mode == 'gpt' and os.environ.get('OPENAI_API_KEY'):
        api_key = os.environ.get('OPENAI_API_KEY')
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        # use built-in system prompt trained on Uttam Pokhrel knowledge
        system_prompt = UTTAM_SYSTEM_PROMPT

        # Try once, and if the response equals the last response for this client,
        # retry with a stronger rephrase instruction.
        attempts = 2
        for attempt in range(attempts):
            body = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': message}
                ],
                'temperature': 0.6 if attempt == 0 else 0.95,
                'max_tokens': 800
            }
            try:
                resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, data=json.dumps(body), timeout=15)
            except Exception as e:
                return jsonify({'response': f'Error contacting OpenAI: {str(e)}'}), 500

            if resp.status_code != 200:
                return jsonify({'response': f'OpenAI API error: {resp.status_code}'}), 502

            j = resp.json()
            text = j['choices'][0]['message']['content'].strip()

            key = client_key()
            prev = last_responses.get(key)
            if prev and prev == text and attempt == 0:
                # ask for a rephrasing on second attempt by tweaking system prompt
                system_prompt = (system_prompt or '') + ' If your previous answer repeated, rephrase it differently and include a concise example or code snippet where applicable.'
                continue

            # store and return
            last_responses[key] = text
            return jsonify({'response': text})

    # Fallback to local keyword responder
    response = get_ai_response(message)
    key = client_key()
    prev = last_responses.get(key)
    if prev and prev == response:
        # provide a short alternate hint rather than repeating verbatim
        response = response + ' — Another way to look at this: try asking for an example, a short summary, or a code highlights.'

    last_responses[key] = response
    return jsonify({"response": response})


@app.route('/run-code', methods=['POST'])
def run_code():
    data = request.get_json() or {}
    code = data.get('code', '')
    # Basic safety: limit length
    if not code or len(code) > 2000:
        return jsonify({'ok': False, 'output': 'Code empty or too large.'}), 400

    # Write temp file and execute in subprocess with timeout
    try:
        tmp_path = 'tmp_user_code.py'
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(code)

        proc = subprocess.run(["python", tmp_path], capture_output=True, text=True, timeout=6)
        output = proc.stdout + (('\n' + proc.stderr) if proc.stderr else '')
        return jsonify({'ok': True, 'output': output})
    except subprocess.TimeoutExpired:
        return jsonify({'ok': False, 'output': 'Execution timed out.'}), 408
    except Exception as e:
        return jsonify({'ok': False, 'output': f'Error running code: {str(e)}'}), 500

def get_ai_response(message):
    msg = (message or '').lower().strip()

    # Small, focused knowledge base about Uttam Pokhrel (concise answers)
    kb = {
        'about': "Uttam Pokhrel is a content creator and B.Sc.CSIT student who teaches AI, Python, and web development. He creates tutorials on YouTube and builds practical projects to help learners.",
        'skills': "Key skills: Python, JavaScript, HTML/CSS, Flask, AI/ML, and content creation (YouTube).",
        'youtube': "YouTube: https://youtube.com/@UttamRealPok — tutorials on Python, AI, web development and project walkthroughs.",
        'contact': "Email: uttamrealpok@gmail.com | WhatsApp/Call: +977 9815394998. Use these to reach Uttam for collaborations or questions.",
        'projects': "Works on AI tools, web apps, and educational content. See the website and YouTube channel for project walkthroughs.",
        'register': "Register via the form on the site to join Uttam's learning community and get updates on tutorials and resources.",
        'donate': "Support options include local Nepali gateways and common donation channels; check the Contact page for details.",
        'python': "Uttam teaches Python fundamentals, scripting, and example projects. You can run simple Python code with the code runner on this site.",
        'ai': "AI stands for Artificial Intelligence. It is branch of computer science which involves creating machines that can perform tasks typically requiring human intelligence. Covers AI/ML basics, practical projects, and accessible explanations for beginners and intermediate learners.",
        'web': "Covers frontend (HTML/CSS/JS) and backend (Flask/Python) to build full-stack apps."
    }

    # simple matching: look for keywords and return the short KB answer
    for key, ans in kb.items():
        if key in msg:
            return ans

    if any(w in msg for w in ['hello', 'hi', 'hey', 'greetings']):
        return "Hi — I'm Uttam Pokhrel's AI chatbot assistant. Ask me about Uttam, his skills, projects, contact info, YouTube, or how to join and more."

    if any(w in msg for w in ['contact', 'email', 'phone', 'reach']):
        return kb['contact']

    if any(w in msg for w in ['project', 'portfolio', 'work', 'what do you build']):
        return kb['projects']

    # fallback short answer pointing to site resources
    return "I can answer your questions about Uttam Pokhrel and this website — try asking about 'about', 'skills', 'youtube', 'contact', or 'projects'."

def open_browser():
    time.sleep(1)  # Wait for server to start
    webbrowser.open('http://127.0.0.1:5000/')

if __name__ == "__main__":
    threading.Thread(target=open_browser).start()
    app.run(debug=True)