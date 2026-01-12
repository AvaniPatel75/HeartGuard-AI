from flask import Flask, render_template, request, redirect, url_for, session, flash
from utils.services import get_ai_response, send_risk_alert, send_otp_email
import utils.db as db
import secrets
import os
import datetime
import json
from dotenv import load_dotenv
from utils.models import HeartDiseasePredictor

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Use SECRET_KEY from env, fallback to a random one if not found
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))
app.permanent_session_lifetime = datetime.timedelta(hours=24)

# Initialize DB
db.migrate_from_files()

# Initialize predictor
predictor = HeartDiseasePredictor()

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    user = db.get_user(username)
    
    if user and user['password'] == password:
        session.permanent = True
        session['user'] = username
        session['role'] = user['role']
        # Session email setting removed
        # user_dict = dict(user)
        # session['email'] = user_dict.get('email')
        session['chat_history'] = []
        return redirect(url_for('home'))
            
    return render_template('login.html', error="Invalid username or password")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        # email = request.form.get('email') # Removed
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
             return render_template('register.html', error="Passwords do not match")
        
        if db.get_user(username):
            return render_template('register.html', error="Username already exists")
        
        # Auto-assign admin role if username is strictly 'admin'
        role = 'admin' if username.lower() == 'admin' else 'user'
        
        # Call add_user without email (it defaults to None)
        if db.add_user(username, password, email=None, role=role):
            session.permanent = True
            session['user'] = username
            session['role'] = role
            return redirect(url_for('home'))
        else:
             return render_template('register.html', error="Registration failed")
        
    return render_template('register.html')

# Forgot Password routes removed as per user request to revert authentication
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/onboarding', methods=['GET', 'POST'])
def onboarding():
    # Kept route for logic but flow bypasses it; 
    # Can serve as "Chat Initializer" if linked from header
    return redirect(url_for('chat'))

@app.route('/home')
def home():
    if 'user' not in session: return redirect(url_for('index'))
    
    # Backend Data: Dynamic Model Metrics
    stats, model_comparison = predictor.evaluate_models()
    
    context_data = {
        'mission': "Cardiovascular diseases (CVDs) are the leading cause of death globally, taking an estimated 17.9 million lives each year. I built HeartGuard to democratize access to early detection. By leveraging clinical data patterns, we can identify risks years before symptoms manifest.",
        'global_stats': [
            {'label': 'Global Deaths/Year', 'value': '17.9M'},
            {'label': 'Premature Deaths', 'value': '33%'},
            {'label': 'Preventable Cases', 'value': '80%'}
        ]
    }
    
    guidelines = {
        'dos': [
            'Use this tool for preliminary risk assessment.',
            'Ensure blood pressure readings are recent.',
            'Consult a cardiologist if High Risk is detected.'
        ],
        'donts': [
            'Do not use this as a replacement for professional medical advice.',
            'Do not ignore physical symptoms (chest pain, shortness of breath).',
            'Do not input guessed values for critical metrics like Glucose.'
        ]
    }
    
    return render_template('landing.html', user=session['user'], stats=stats, models=model_comparison, guidelines=guidelines, context=context_data)

@app.route('/about')
def about():
    if 'user' not in session: return redirect(url_for('index'))
    return render_template('about.html', user=session['user'])

@app.route('/admin')
def admin():
    if 'user' not in session: return redirect(url_for('index'))
    if session.get('role') != 'admin':
        return redirect(url_for('home'))
    
    # Fetch Data from DB
    users_data = db.get_all_users()
    logs_data = db.get_all_activity_logs()
    pred_data = db.get_all_predictions()
    
    # Convert and Format
    users_dict = {u['username']: {'role': u['role'], 'created_at': u['created_at']} for u in users_data}
    logs_list = [dict(row) for row in logs_data]
    
    preds_list = []
    for row in pred_data:
        p = dict(row)
        try:
            p['result'] = json.loads(p['result'])
            p['input_data'] = json.loads(p['input_data'])
        except: pass
        preds_list.append(p)

    return render_template('admin.html', user=session['user'], users=users_dict, logs=logs_list, predictions=preds_list)

# --- Predictor Stages ---
@app.route('/predictor/lifestyle', methods=['GET', 'POST'])
def predictor_stage1():
    if 'user' not in session: return redirect(url_for('index'))
    
    if request.method == 'POST':
        session['p_age'] = request.form.get('age')
        session['p_weight'] = request.form.get('weight')
        session['p_height'] = request.form.get('height')
        session['p_smoke'] = 1 if request.form.get('smoke') else 0
        session['p_alco'] = 1 if request.form.get('alco') else 0
        session['p_active'] = 1 if request.form.get('active') else 0
        
        # Risk Logic
        age = float(request.form.get('age', 30))
        is_risk_lifestyle = (age > 45) or (session['p_smoke'] == 1) or (session['p_active'] == 0) or (session['p_alco'] == 1)
        
        if is_risk_lifestyle:
            return redirect(url_for('predictor_stage2'))
        else:
            result = {'risk': 'Low', 'prob': 10.0, 'suggestion': "Your lifestyle markers are healthy. Maintain your activity levels."}
            input_data = {'age': age, 'smoke': session['p_smoke'], 'alco': session['p_alco'], 'active': session['p_active']}
            db.log_prediction(session['user'], input_data, result)
            return render_template('predictor_result.html', user=session['user'], result=result)
            
    return render_template('predictor_step1.html', user=session['user'])

@app.route('/predictor/clinical', methods=['GET', 'POST'])
def predictor_stage2():
    if 'user' not in session: return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            data = {
                'age': float(session.get('p_age', 50)) * 365,
                'gender': int(request.form.get('gender', 1)),
                'height': float(session.get('p_height', 165)),
                'weight': float(session.get('p_weight', 70)),
                'ap_hi': float(request.form.get('ap_hi', 120)),
                'ap_lo': float(request.form.get('ap_lo', 80)),
                'cholesterol': int(request.form.get('cholesterol', 1)),
                'gluc': int(request.form.get('gluc', 1)),
                'smoke': session.get('p_smoke', 0),
                'alco': session.get('p_alco', 0),
                'active': session.get('p_active', 1)
            }
            pred, prob = predictor.predict(data)
            risk = "High" if (pred == 1 or prob > 0.5) else "Low"
            suggestion = predictor.get_lifestyle_suggestions(prob)
            result = {'risk': risk, 'prob': round(prob * 100, 1), 'suggestion': suggestion}
            
            db.log_prediction(session['user'], data, result)
            
            # Send Notification
            user_email = session.get('email')
            if user_email:
                send_risk_alert(user_email, session['user'], result)
            
            return render_template('predictor_result.html', user=session['user'], result=result)
        except Exception as e:
            print(f"Error: {e}")
            
    return render_template('predictor_step2.html', user=session['user'])

# --- Profile ---
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session: return redirect(url_for('index'))
    
    user = session['user']
    
    # Handle Activity Log or Profile Update
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Profile Update
        if action == 'update_profile':
            db.update_user_profile(user, request.form)
            return redirect(url_for('profile'))
        
        # Activity Log
        else:
            activity = request.form.get('activity')
            duration = request.form.get('duration')
            if activity and duration:
                db.log_activity(user, activity, duration, datetime.datetime.now().strftime("%Y-%m-%d"))
            
    # Fetch User Details & Activities
    user_info = db.get_user_details(user)
    activities = [dict(row) for row in db.get_user_activity(user)]
    
    # Calculate streak (simplified)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    streak = 0
    if activities and activities[0]['date'] == today:
        streak = 1
        
    # Valid recent tests for Profile Summary
    recent_tests_raw = db.get_user_history(user)
    recent_tests = []
    
    # Data for Profile Risk Chart
    chart_labels = []
    chart_data = []

    # Iterate in reverse to show oldest to newest on graph if needed, 
    # but get_user_history is usually DESC. Let's reverse for chart to be linear time left-to-right.
    for row in reversed(recent_tests_raw):
        try:
            res = json.loads(row['result'])
            if isinstance(res, str): res = json.loads(res) # Handle double encoding
            
            date_str = datetime.datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S').strftime('%b %d')
            chart_labels.append(date_str)
            
            prob = float(res['prob'])
            # Ensure prob is 0.0-1.0 before scaling, or 0-100 if already scaled
            # Heuristic: if prob > 1, assume it's already %; if <=1, scale it.
            # But the stored format is usually 0.XX. 
            # If user sees 7890, it means prob was 78.9 and we multiplied by 100? Or prob was 7890?
            
            # Use safe scaling
            val = prob * 100 if prob <= 1.0 else prob
            chart_data.append(val) 
        except: pass

    # Re-fetch for table display (clean order)
    highest_risk_test = None
    max_prob = -1.0
    
    for row in recent_tests_raw:
        t = dict(row)
        try:
            # Attempt to parse result
            res_parsed = json.loads(t['result'])
            if isinstance(res_parsed, str):
                res_parsed = json.loads(res_parsed) # Handle double encoding
            t['result'] = res_parsed
            
            # Attempt to parse input_data
            inp_parsed = json.loads(t['input_data'])
            if isinstance(inp_parsed, str):
                inp_parsed = json.loads(inp_parsed) # Handle double encoding
            t['input_data'] = inp_parsed
            
            # Determine Test Type
            if 'ap_hi' in t['input_data']:
                t['type'] = 'Clinical'
            else:
                t['type'] = 'Lifestyle'
            
            # Find highest risk
            if t['result']['prob'] > max_prob:
                max_prob = t['result']['prob']
                highest_risk_test = t
            
            recent_tests.append(t)
        except Exception as e:
             # Skip malformed records
             print(f"Skipping malformed record ID {t.get('id')}: {e}")
             pass

    return render_template('profile.html', user=user, user_info=user_info, activities=activities, streak=streak, recent_tests=recent_tests, chart_labels=chart_labels, chart_data=chart_data, highest_risk_test=highest_risk_test)

@app.route('/tests')
def tests():
    if 'user' not in session: return redirect(url_for('index'))
    
    all_tests_raw = db.get_all_user_predictions(session['user'])
    all_tests = []
    for row in all_tests_raw:
        t = dict(row)
        try:
            t['result'] = json.loads(t['result'])
            t['input_data'] = json.loads(t['input_data'])
        except: pass
        all_tests.append(t)
        
    return render_template('tests.html', user=session['user'], tests=all_tests)

@app.route('/insights')
def insights():
    if 'user' not in session: return redirect(url_for('index'))
    
    # Backend Data: Dynamic Model Metrics
    stats, model_comparison = predictor.evaluate_models()
    
    return render_template('insights.html', user=session['user'], stats=stats, models=model_comparison)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user' not in session: return redirect(url_for('index'))
    
    if 'chat_history' not in session:
        session['chat_history'] = []
        
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        if prompt:
            history = session['chat_history']
            history.append({'role': 'user', 'content': prompt})
            
            # --- Enhanced AI Context ---
            user_info = db.get_user_details(session['user'])
            latest_history = db.get_user_history(session['user'])
            
            context_parts = [f"User: {session['user']}"]
            
            # Add Profile Info
            if user_info:
                u = dict(user_info)
                context_parts.append(f"Profile: Age={u.get('dob','?')}, Blood={u.get('blood_type','?')}, Conditions={u.get('chronic_diseases','None')}, Allergies={u.get('allergies','None')}")
            
            # Add Latest Health Checkup
            if latest_history:
                try:
                    last_test = dict(latest_history[0])
                    # Handle double encoding if necessary (reusing simple logic)
                    res = json.loads(last_test['result'])
                    if isinstance(res, str): res = json.loads(res)
                    
                    inp = json.loads(last_test['input_data'])
                    if isinstance(inp, str): inp = json.loads(inp)

                    context_parts.append(f"Latest Assessment ({last_test['timestamp']}): Risk={res.get('risk')} ({res.get('prob')}%)")
                    context_parts.append(f"Vitals: BP={inp.get('ap_hi')}/{inp.get('ap_lo')}, Cholesterol level={inp.get('cholesterol')}, Glucose level={inp.get('gluc')}")
                except Exception as e:
                    print(f"Context Build Error: {e}")
            
            # Add Recent Chat History
            context_parts.append(f"Recent Conversation: {history[-3:]}")
            
            full_context = " | ".join(context_parts)
            # ---------------------------

            response = get_ai_response(prompt, full_context)
                 
            history.append({'role': 'assistant', 'content': response})
            session['chat_history'] = history
            
    return render_template('chat.html', user=session['user'], messages=session['chat_history'])

if __name__ == '__main__':
    db.init_db()
    db.add_missing_columns()
    app.run(debug=True, port=5000)
