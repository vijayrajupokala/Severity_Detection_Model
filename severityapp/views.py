from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings
import pymysql
import pandas as pd
from joblib import load

import os
import pickle
import joblib
import numpy as np
from collections import Counter
from scipy.special import expit  # sigmoid


import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud


import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag
from nltk.util import ngrams


from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import SGDClassifier, PassiveAggressiveClassifier


from ngboost import NGBClassifier
from ngboost.distns import Bernoulli


import tensorflow as tf
from tensorflow.keras.models import Sequential, Model, load_model
from tensorflow.keras.layers import Dense, Input, Embedding, Conv1D, GlobalMaxPooling1D, LSTM, Dropout
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.utils import to_categorical


from transformers import (
    AutoTokenizer, AutoModel,
    RobertaTokenizer, RobertaModel,
    BertTokenizer, BertForSequenceClassification,
    XLNetTokenizer, XLNetForSequenceClassification
)
import torch
from torch.optim import AdamW

ng_final = joblib.load("severityapp/model/ngboost_dnn_model1.pkl")
DENSE_MODEL_PATH = r"severityapp/model/dense_feature_model.h5"


MODEL_DIR = r"severityapp\model"
os.makedirs(MODEL_DIR, exist_ok=True)

import nltk

# Tokenizer
nltk.download('punkt', quiet=True)

# Stopwords
nltk.download('stopwords', quiet=True)

# WordNet for lemmatizer
nltk.download('wordnet', quiet=True)

#  POS tagging for better lemmatization
nltk.download('averaged_perceptron_tagger', quiet=True)

def get_db_connection():
    """Reusable MySQL connection (always returns DictCursor)"""
    return pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='root',
        password='root',
        database='mydb',
        cursorclass=pymysql.cursors.DictCursor  
    )



def ensure_single_admin():
    try:
        con = get_db_connection()
        with con:
            cur = con.cursor()

            cur.execute("SELECT id FROM emp_details3 WHERE role='admin'")
            admin = cur.fetchone()

            if not admin:
                cur.execute("""
                    INSERT INTO emp_details3
                    (username, email, password, role, approved, address, mobile)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    "admin",
                    "admin@gmail.com",
                    "admin",
                    "admin",
                    1,
                    "hyderabad",
                    "1234567890"
                ))
                con.commit()
    except Exception as e:
        print("Error ensuring admin:", e)



def index(request):
    return render(request, 'index.html')

def user_page(request):
    user = request.session.get('user')
    if not user:
        return redirect('login')  
    return render(request, 'user.html', {'user': user})


@csrf_exempt
def approve_user(request, username):
    user = request.session.get('user')
    if not user or user['role'] != 'admin':
        return redirect('login')

    try:
        con = get_db_connection()
        with con:
            cur = con.cursor()
            cur.execute("UPDATE emp_details3 SET approved = 1 WHERE username = %s", (username,))
            con.commit()

    except Exception as e:
        print("Error approving user:", e)

    return redirect('admin_page')


def admin_page(request):
    user = request.session.get('user')
    if not user:
        return redirect('login')

    if user['role'] != 'admin':
        return redirect('user_page')

    try:
        con = get_db_connection()
        with con:
            cur = con.cursor()
            cur.execute("SELECT * FROM emp_details3 WHERE role='user'")
            users_list = cur.fetchall()

    except Exception as e:
        return render(request, 'admin.html', {
            'user': user,
            'error': f'Database error: {str(e)}'
        })

    return render(request, 'admin.html', {'user': user, 'users_list': users_list})



def register_view(request):

    ensure_single_admin()

    message = None

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        mobile = request.POST.get('mobile')          
        address = request.POST.get('address')        
        role = "user"                               

        if password != confirm_password:
            message = {'error': 'Passwords do not match'}

        else:
            try:
                con = get_db_connection()

                with con:
                    cur = con.cursor()

                    cur.execute("SELECT username FROM emp_details3 WHERE username=%s", (username,))
                    if cur.fetchone():
                        message = {'error': 'Username already exists'}


                    else:
                        cur.execute("SELECT email FROM emp_details3 WHERE email=%s", (email,))
                        if cur.fetchone():
                            message = {'error': 'Email already exists'}
                        cur.execute("SELECT mobile FROM emp_details3 WHERE mobile=%s", (mobile,))
                        if cur.fetchone():
                            message = {'error': 'mobile already exists'}
                        else:
                            cur.execute("""
                                INSERT INTO emp_details3
                                (username, email, password, role, approved, mobile, address)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (username, email, password, role, 0, mobile, address))

                            con.commit()
                            message = {'success': 'Account created successfully! Awaiting admin approval.'}

            except Exception as e:
                message = {'error': f'Database error: {str(e)}'}

    return render(request, 'register.html', message)


def login_view(request):
    context = {}

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        try:
            con = get_db_connection()
            with con:
                cur = con.cursor()

                cur.execute(
                    "SELECT * FROM emp_details3 WHERE username=%s AND password=%s",
                    (username, password)
                )
                user = cur.fetchone()

                if user:
                    if not user['approved']:
                        context['error'] = 'Your account is awaiting admin approval.'
                    else:
                        request.session['user'] = user
                        role = user['role']

                        if role == 'admin':
                            return redirect('admin_page')
                        elif role == 'user':
                            return redirect('user_page')
                        else:
                            context['error'] = 'Invalid role assigned to this user.'
                else:
                    context['error'] = 'Invalid login credentials'

        except Exception as e:
            context['error'] = f'Database error: {str(e)}'

    return render(request, 'login.html', context)



def preprocess_data(df, save_path=None, target_col=None):
    """
    Preprocess text columns, combine into a single list of text samples (X_text),
    append non-text features, and encode Y (if target_col is given).

    Parameters:
        df (pd.DataFrame): Input data.
        save_path (str or None): Path to save/load preprocessed CSV. If None, skip file I/O.
        target_col (str or None): Target label column to encode.

    Returns:
        X (list of str + numerical features), Y (label encoded or None)
    """
    global le
    if save_path and os.path.exists(save_path):
        print(f"Loading existing preprocessed file: {save_path}")
        df = pd.read_csv(save_path)
    else:
        print("Preprocessing data" + (f" and saving to: {save_path}" if save_path else " (no saving)"))
        lemmatizer = WordNetLemmatizer()
        stop_words = set(stopwords.words('english'))

        def clean_text(text):
            text = str(text).lower()
            tokens = word_tokenize(text)
            tokens = [lemmatizer.lemmatize(t) for t in tokens if t.isalnum() and t not in stop_words]
            return ' '.join(tokens)

        # Separate target column
        target_series = None
        if target_col and target_col in df.columns:
            target_series = df[target_col]
            df = df.drop(columns=[target_col])

        # Process text columns
        text_columns = df.select_dtypes(include='object').columns
        for col in text_columns:
            df[f'processed_{col}'] = df[col].apply(clean_text)

        # Drop original text columns
        df.drop(columns=text_columns, inplace=True)

        # Reattach target column if it was dropped
        if target_series is not None:
            df[target_col] = target_series

        # Save only if path is specified
        if save_path:
            df.to_csv(save_path, index=False)

    # Select processed and numerical columns
    processed_text_cols = [col for col in df.columns if col.startswith('processed_')]
    non_text_cols = [col for col in df.columns if col not in processed_text_cols + ([target_col] if target_col else [])]

    # Join text columns into a single string
    X_text = df[processed_text_cols].astype(str).agg(' '.join, axis=1)

    # Numeric features
    X_numeric = df[non_text_cols].values if non_text_cols else None

    # Combine text and numeric
    if X_numeric is not None and len(X_numeric) > 0:
        X = [f"{text} {' '.join(map(str, numeric))}" for text, numeric in zip(X_text, X_numeric)]
    else:
        X = X_text.tolist()

    # Label encode target
    Y = None
    if target_col and target_col in df.columns:
        le = LabelEncoder()
        Y = le.fit_transform(df[target_col])

    return X, Y
    


def Lightweight_RoBERT_feature_extraction(texts, model_name='sentence-transformers/all-MiniLM-L6-v2'):
    """Extract Lightweight_RoBERT features from texts."""
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)

    encoded_input = tokenizer(texts, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        model_output = model(**encoded_input)

    token_embeddings = model_output.last_hidden_state
    attention_mask = encoded_input['attention_mask']
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()

    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, dim=1)
    sum_mask = input_mask_expanded.sum(dim=1)
    embeddings = sum_embeddings / sum_mask

    X = embeddings.cpu().numpy()
    return X, model



def feature_extraction(X_text, method='Lightweight_RoBERT', model_dir=r'severity\model', is_train=True):
    """
    Extract features from X_text using Lightweight RoBERTa model from Sentence-Transformers.
    - Train: Load from cache if available, else compute and save.
    - Test: Always compute, don't save.
    """
    if method != 'Lightweight_RoBERT':
        raise ValueError(f"[ERROR] Only 'Lightweight_RoBERT' is supported in this version.")

    x_file = os.path.join(model_dir, f'X_{method}.pkl')

    print(f"[INFO] Feature extraction method: {method}, Train mode: {is_train}")
    model_name = 'sentence-transformers/all-distilroberta-v1'

    if is_train:
        if os.path.exists(x_file):
            print(f"[INFO] Loading cached Lightweight RoBERTa features from {x_file}")
            X = joblib.load(x_file)
        else:
            print("[INFO] Computing Lightweight RoBERTa features...")
            X, model = Lightweight_RoBERT_feature_extraction(X_text, model_name=model_name)
            joblib.dump(X, x_file)
    else:
        print("[INFO] Performing Lightweight RoBERTa feature extraction for testing...")
        X, model = Lightweight_RoBERT_feature_extraction(X_text, model_name=model_name)

    return X

   

def prediction_page(request):
    prediction_table = None
    uploaded_filename = None

    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        uploaded_filename = file.name

        # Load uploaded CSV
        df_test1 = pd.read_csv(file)
        df_result = df_test1.copy()

        # 1. PREPROCESS
        df_test, _ = preprocess_data(df_test1)

        # 2. FEATURE EXTRACTION
        features_test = feature_extraction(
            df_test,
            method='Lightweight_RoBERT',
            is_train=False
        )

        # 3. PREDICT
        y_pred = ng_final.predict(features_test)

        # 4. MANUAL LABEL MAPPING
        label_map = {0: "non-severe", 1: "severe"}
        y_labels = [label_map[int(i)] for i in y_pred]

        # Add predictions
        df_result["Predicted_Label"] = y_labels
        df_result.insert(0, "Sl.No", range(1, len(df_result) + 1))

        # Convert to HTML
        prediction_table = df_result.to_html(
            classes="table table-bordered table-striped table-hover",
            index=False
        )

        messages.success(request, f"Predictions generated successfully for {uploaded_filename}")

    return render(
        request,
        "prediction.html",
        {
            "prediction_table": prediction_table,
            "uploaded_filename": uploaded_filename
        }
    )


def test_extract_features_from_dense_model(X_test, model_path=r"severityapp\model\dense_feature_model.h5"):
    print(f"✅ Loading model from: {model_path}")
    model = load_model(model_path)

    # Extract output from the intermediate 'feature_layer'
    feature_extractor = Model(inputs=model.input,
                              outputs=model.get_layer("feature_layer").output)

    print("🚀 Extracting features from test data...")
    features_test = feature_extractor.predict(X_test)

    return features_test

def user_prediction(request):
    prediction = None

    if request.method == "POST":
        text = request.POST.get("text")

        df = pd.DataFrame({"Short Description": [text]})

        # Preprocess
        df_test, _ = preprocess_data(df)

        # Correct Feature extraction (same as training)
        features = feature_extraction(
            df_test,
            method='Lightweight_RoBERT',
            is_train=False
        )

        
        # Predict
        y_pred = ng_final.predict(features)

        # Correct mapping
        label_map = {0: "non-severe", 1: "severe"}
        prediction = label_map[int(y_pred[0])]

    return render(request, "user.html", {
        "prediction": prediction,
        "user": request.session.get("user")
    })


