# HeartGuard AI ❤️

HeartGuard AI is a comprehensive cardiovascular health assistant that uses Machine Learning to assess heart disease risk and Generative AI to provide personalized health insights.

## ✨ Features

- **Risk Prediction**: Uses advanced ML models (Random Forest, Gradient Boosting) to estimate cardiovascular risk based on clinical data.
- **AI Assistant**: A built-in chatbot powered by Google's Gemini models (1.5 Flash) that understands your medical profile and answers health queries.
- **Interactive Dashboard**: Visualize your health trends over time with dynamic charts.
- **Secure Profile**: Manage your vital statistics, lifestyle factors, and history securely.

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML5, Tailwind CSS, JavaScript (Chart.js)
- **AI/ML**: Scikit-Learn, Google GenAI SDK (Gemini)
- **Database**: SQLite
- **Deployment**: Gunicorn (Ready for Render/Heroku)

## 🚀 Getting Started Locally

1. **Clone the repository**
   ```bash
   git clone https://github.com/AvaniPatel75/HeartGuard-AI.git
   cd HeartGuard-AI
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your_secret_key
   DATABASE_URL=sqlite:///heartguard.db
   GOOGLE_API_KEY=your_google_gemini_api_key
   EMAIL_USER=optional_email_for_alerts
   EMAIL_PASS=optional_email_password
   ```

4. **Run the App**
   ```bash
   python app.py
   ```
   Visit `http://127.0.0.1:5000` in your browser.

## 🌐 Deployment (Render.com)

1. Create a new Web Service on Render connected to this repo.
2. Set Build Command: `pip install -r requirements.txt`
3. Set Start Command: `gunicorn app:app`
4. Add Environment Variables (`GOOGLE_API_KEY`, etc.) in the Render dashboard.

## 📄 License
This project is for educational and health awareness purposes.
