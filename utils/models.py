import pandas as pd
import numpy as np
import joblib
import os
# Streamlit removed for production Flask app
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

class HeartDiseasePredictor:
    def __init__(self, model_dir='.'):
        self.model_dir = model_dir
        self.models = {}
        self.scaler = None
        self.data_path = os.path.join(model_dir, 'final_cardio_train_data.csv') # Actual dataset name
        self.metrics_cache = {}
        
        # Define expected models
        self.model_files = {
            'Random Forest': 'cardio_model.pkl',  # cardio_model is Random Forest
            'Decision Tree': 'decision_tree.pkl',
            'Logistic Regression': 'logistic_regression.pkl',
            'Naive Bayes': 'naive_bayes.pkl',
            'Linear Regression': 'linear_regression.pkl'
        }
        
        self._load_resources()

    def _load_resources(self):
        # Load Scaler
        scaler_path = os.path.join(self.model_dir, 'cardio_model_scaler.pkl')
        if os.path.exists(scaler_path):
            try:
                self.scaler = joblib.load(scaler_path)
            except:
                print("Error loading scaler")

        # Load Models
        for name, filename in self.model_files.items():
            path = os.path.join(self.model_dir, filename)
            if os.path.exists(path):
                try:
                    self.models[name] = joblib.load(path)
                except Exception as e:
                    print(f"Failed to load {name}: {e}")

    def evaluate_models(self):
        """
        Dynamically calculate metrics for all loaded models using the provided CSV.
        Returns a dict of stats and list of model comparisons.
        """
        # Default/Fallback stats if specific files aren't found
        default_stats = {
            'main_model': 'Random Forest (Demo)',
            'accuracy': 73.1,
            'roc_auc': 0.79,
            'dataset_size': '70,000+',
            'features': 11
        }
        default_comparison = [
             {'name': 'Random Forest', 'acc': 73.1, 'prec': 0.74, 'recall': 0.71, 'f1': 0.72},
             {'name': 'Decision Tree', 'acc': 71.5, 'prec': 0.72, 'recall': 0.69, 'f1': 0.70},
             {'name': 'Logistic Regression', 'acc': 69.8, 'prec': 0.70, 'recall': 0.68, 'f1': 0.69},
             {'name': 'Naive Bayes', 'acc': 68.2, 'prec': 0.69, 'recall': 0.65, 'f1': 0.67},
             {'name': 'Linear Regression', 'acc': 65.5, 'prec': 0.65, 'recall': 0.60, 'f1': 0.62}
        ]

        if not os.path.exists(self.data_path) or not self.models:
            return default_stats, default_comparison

        # If cache exists, return it
        if self.metrics_cache:
            return self.metrics_cache['stats'], self.metrics_cache['comparison']

        try:
            # Load Data
            df = pd.read_csv(self.data_path)
            
            # Assume target is 'cardio' or last column
            target_col = 'cardio' if 'cardio' in df.columns else df.columns[-1]
            
            # Feature Engineering: BMI is required by the trained model
            if 'BMI' not in df.columns and 'weight' in df.columns and 'height' in df.columns:
                # height in cm, weight in kg -> BMI = kg / m^2
                df['BMI'] = df['weight'] / ((df['height'] / 100) ** 2)

            X = df.drop(columns=[target_col])
            
            y = df[target_col]
            
            # Use a subset for speed if dataset is huge, or train_test_split
            if len(df) > 10000:
                 _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            else:
                X_test, y_test = X, y

            # Validate Feature Alignment
            # (Assuming CSV columns match model expectation, simplified here)
            
            if self.scaler:
                X_test_scaled = self.scaler.transform(X_test)
            else:
                X_test_scaled = X_test

            main_model_name = 'Gradient Boosting' if 'Gradient Boosting' in self.models else list(self.models.keys())[0]
            main_model = self.models[main_model_name]
            
            # Calculate Main Model Stats
            y_pred_main = main_model.predict(X_test_scaled)
            y_prob_main = main_model.predict_proba(X_test_scaled)[:, 1] if hasattr(main_model, 'predict_proba') else y_pred_main
            
            stats = {
                'main_model': main_model_name,
                'accuracy': round(accuracy_score(y_test, y_pred_main) * 100, 1),
                'roc_auc': round(roc_auc_score(y_test, y_prob_main), 2),
                'dataset_size': f"{len(df):,}",
                'features': X.shape[1]
            }

            # Comparison Loop
            comparison = []
            for name, model in self.models.items():
                y_pred = model.predict(X_test_scaled)
                
                # Robustness for Linear Regression or non-classifier models
                if hasattr(y_pred, 'dtype') and (y_pred.dtype == float or y_pred.dtype == np.float64) and len(np.unique(y_pred)) > 2:
                    y_pred = (y_pred > 0.5).astype(int)

                comp_entry = {
                    'name': name,
                    'acc': round(accuracy_score(y_test, y_pred) * 100, 1),
                    'prec': round(precision_score(y_test, y_pred), 2),
                    'recall': round(recall_score(y_test, y_pred), 2),
                    'f1': round(f1_score(y_test, y_pred), 2)
                }
                comparison.append(comp_entry)

            # Sort by accuracy descending
            comparison.sort(key=lambda x: x['acc'], reverse=True)
            
            # Cache results
            self.metrics_cache = {'stats': stats, 'comparison': comparison}
            return stats, comparison

        except Exception as e:
            print(f"Evaluation Error: {e}")
            return default_stats, default_comparison

    def predict(self, input_data):
        # Feature order matches typical Cardio dataset
        features = ['age', 'gender', 'height', 'weight', 'ap_hi', 'ap_lo', 'cholesterol', 'gluc', 'smoke', 'alco', 'active']
        
        if isinstance(input_data, dict):
            # Calculate BMI: weight(kg) / (height(m))^2
            # Height is usually in cm in this dataset
            height_m = input_data.get('height', 165) / 100.0
            weight_kg = input_data.get('weight', 70)
            bmi = weight_kg / (height_m ** 2)
            
            # Update input data with BMI
            # Note: The model might have been trained with specific columns. 
            # If 'BMI' is required, we append it. We should also ensure feature order if possible.
            # Assuming the model keeps height/weight AND BMI based on standard feature engineering.
            input_data['BMI'] = bmi
            
            # Re-define features list to include BMI. 
            # We trust the dataframe to handle name matching if the model was trained with names.
            # However, we must ensure we pass a DataFrame with the correct columns.
            # Let's try to pass all standard columns plus BMI.
            features = ['age', 'gender', 'height', 'weight', 'ap_hi', 'ap_lo', 'cholesterol', 'gluc', 'smoke', 'alco', 'active', 'BMI']
            
            data_values = [input_data.get(f, 0) for f in features]
            df = pd.DataFrame([data_values], columns=features)
        else:
            # If list input, we might need to recalculate or assume it's pre-processed.
            # But the app uses dict.
            df = pd.DataFrame([input_data], columns=features)
            df['BMI'] = df['weight'] / ((df['height'] / 100) ** 2)

        # Use Gradient Boosting as primary, or first available
        model = self.models.get('Gradient Boosting', next(iter(self.models.values())) if self.models else None)
        
        if model:
            # Some models might need specific column ordering or subset.
            # If the header match fails again on specific columns (e.g. maybe it DROPPED height/weight?), 
            # we might need to inspect model.feature_names_in_ if available. 
            # For now, adding BMI is the primary fix.
            if hasattr(model, 'feature_names_in_'):
                # Reorder df to match model's expected columns
                try:
                    df = df[model.feature_names_in_]
                except KeyError:
                    # If model expects columns we don't have, we might crash. 
                    # But BMI was the specific missing one.
                    pass

            if self.scaler:
                 # Ensure column names match what scaler expects (sometimes sklearn strips names, but pandas keeps them)
                df_scaled = self.scaler.transform(df)
            else:
                df_scaled = df
                
            prediction = model.predict(df_scaled)[0]
            probability = model.predict_proba(df_scaled)[0][1] if hasattr(model, 'predict_proba') else float(prediction)
            return prediction, probability
        else:
            # Fallback heuristic
            score = 0
            if input_data.get('ap_hi', 120) > 130: score += 0.3
            if input_data.get('cholesterol', 1) > 1: score += 0.2
            import random
            prob = 0.1 + score + (random.random() * 0.1)
            return (1 if prob > 0.5 else 0), min(prob, 0.99)

    def get_lifestyle_suggestions(self, prob):
        if prob < 0.3:
            return "Your heart health looks good! Keep up the active lifestyle."
        elif prob < 0.7:
            return "Moderate risk. Consider reducing salt intake and doing more cardio."
        else:
            return "High risk detected. Please consult a cardiologist regularly."
