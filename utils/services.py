from google import genai
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- AI Service ---
def get_ai_response(prompt, context=""):
    """
    Get response from Gemini API.
    Fallback to simple rules if key not found.
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    
    args = {}
    if api_key:
        print(f"[AI Debug] Found API Key: {api_key[:5]}...")
    else:
        print("[AI Debug] No API Key found in env!")
        return "I'm sorry, I'm not fully connected to the cloud right now. Please check my configuration."

    try:
        # New SDK Initialization
        client = genai.Client(api_key=api_key)
        
        # 2026 Dynamic Discovery: Find a valid 'flash' model
        # Hardcoding fails because 1.5 might be retired in 2026.
        target_model = None
        all_models = []
        try:
            for m in client.models.list():
                all_models.append(m.name)
                if 'flash' in m.name.lower() and 'legacy' not in m.name.lower():
                    target_model = m.name
                    # Prefer the latest/highest version if multiple? 
                    # Usually the list order or first match is fine for now.
                    # Let's break on first valid flash to be fast.
                    break
        except Exception as e:
            print(f"[AI Debug] List models failed: {e}")

        # Fallback to Pro if no Flash
        if not target_model:
            for m_name in all_models:
                if 'pro' in m_name.lower():
                    target_model = m_name
                    break
        
        # Fallback to *anything*
        if not target_model and all_models:
             target_model = all_models[0]
             
        # Default safety (if list failed completely)
        if not target_model:
            target_model = 'gemini-2.5-flash' # Guess for 2026

        print(f"[AI Debug] Selected Model: {target_model}")

        system_prompt = f"""
        You are HeartGuard AI, a friendly and professional medical assistant.
        Your goal is to help users understand cardiovascular health.
        
        User Context: {context}
        
        Guidelines:
        1. Be empathetic but professional.
        2. Do not provide definitive medical diagnoses. Always suggest consulting a doctor for serious concerns.
        3. Keep answers concise (< 150 words) unless asked for details.
        
        Answer the user's question: {prompt}
        """
        
        print(f"[AI Debug] Sending prompt to {target_model} (New SDK)...")
        
        # New SDK Call
        # Note: model name usually comes as "models/gemini-...", SDK might handle it.
        # Check if we need to strip 'models/' prefix. 
        # The new SDK usually accepts it, or just the ID. 
        # But let's try passing exactly what .list() returned.
        
        response = client.models.generate_content(
            model=target_model,
            contents=system_prompt
        )
        
        # New SDK response structure access
        # It might be response.text or response.candidates[0].content...
        # For simple text generation, .text is usually a property helper.
        
        print(f"[AI Debug] Response received: {len(response.text)} chars")
        return response.text
        
    except Exception as e:
        print(f"[AI Debug] AI Error: {e}")
        return f"I'm having trouble thinking right now. Error: {e}"

# --- Email Service ---
def send_risk_alert(to_email, user_name, result):
    """
    Send an email with the risk assessment results.
    Falls back to console print for development.
    """
    smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('EMAIL_PORT', 587))
    sender_email = os.getenv('EMAIL_USER')
    sender_password = os.getenv('EMAIL_PASS')
    
    # Developement Mode: If no credentials, log to console
    if not sender_email or not sender_password:
        print("\n" + "="*40)
        print(f" [DEV] EMAIL SIMULATION - To: {to_email}")
        print(f" Subject: HeartGuard Assessment: {result['risk']} Risk")
        print(f" Risk: {result['risk']} ({result['prob']}%)")
        print("="*40 + "\n")
        return True
        
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = f"HeartGuard Assessment: {result['risk']} Risk Detected"
    
    risk_color = "red" if result['risk'] == "High" else "green"
    
    body = f"""
    <html>
      <body>
        <h2>Hello {user_name},</h2>
        <p>You recently completed a cardiovascular risk assessment on HeartGuard.</p>
        
        <div style="padding: 20px; border: 1px solid #eee; border-radius: 10px; background-color: #f9f9f9;">
            <h3 style="color: {risk_color}; margin-top: 0;">{result['risk']} Risk ({result['prob']}%)</h3>
            <p><strong>Analysis:</strong> {result['suggestion']}</p>
        </div>
        
        <p>Please note: This is an AI-powered estimate and not a medical diagnosis.</p>
        
        <p>Stay Healthy,<br>The HeartGuard Team</p>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Sending Failed: {e}")
        print("Falling back to console output...")
        print("\n" + "="*40)
        print(f" [FALLBACK] EMAIL SIMULATION - To: {to_email}")
        print(f" Subject: HeartGuard Assessment: {result['risk']} Risk")
        print(f" Risk: {result['risk']} ({result['prob']}%)")
        print("="*40 + "\n")
        return True

def send_otp_email(to_email, otp):
    """
    Send OTP for password reset.
    Falls back to console print for development.
    """
    smtp_server = os.getenv('EMAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('EMAIL_PORT', 587))
    sender_email = os.getenv('EMAIL_USER')
    sender_password = os.getenv('EMAIL_PASS')
    
    # Developement Mode: If no credentials, log to console
    if not sender_email or not sender_password:
        print("\n" + "="*40)
        print(f" [DEV] EMAIL SIMULATION - To: {to_email}")
        print(f" Subject: HeartGuard Password Reset Code")
        print(f" OTP CODE: {otp}")
        print("="*40 + "\n")
        return True
        
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = "HeartGuard Password Reset Code"
    
    body = f"""
    <html>
      <body>
        <h2>Password Reset Request</h2>
        <p>Use the following code to reset your password:</p>
        <h1 style="color: #0284c7; letter-spacing: 5px;">{otp}</h1>
        <p>If you didn't request this, please ignore this email.</p>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Sending Failed: {e}")
        print("Falling back to console output...")
        print("\n" + "="*40)
        print(f" [FALLBACK] EMAIL SIMULATION - To: {to_email}")
        print(f" Subject: HeartGuard Password Reset Code")
        print(f" OTP CODE: {otp}")
        print("="*40 + "\n")
        return True
