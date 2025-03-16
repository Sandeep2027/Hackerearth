from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_file
from database import (init_db, add_user, get_user, save_content, get_content_by_user,
                      get_content_by_topic, save_feedback, get_feedback_stats, log_interaction,
                      get_user_recommendations, get_user_analytics, categorize_content, export_content_to_csv)
from transformers import pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'  


init_db()


generator = pipeline("text-generation", model="distilgpt2")
sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")

def generate_content(topic, experience_level):
    prompt = f"Explain {topic} in DeFi for a {experience_level} audience."
    result = generator(prompt, max_length=150, num_return_sequences=1, truncation=True)[0]['generated_text']
    title = f"{experience_level.capitalize()} Guide to {topic}"
    return title, result

def analyze_sentiment(comment):
    result = sentiment_analyzer(comment)[0]
    return result['score'] if result['label'] == 'POSITIVE' else -result['score']

def recommend_content(user_interests, all_content):
    if not all_content:
        return []
    vectorizer = TfidfVectorizer()
    content_bodies = [c[3] for c in all_content]  
    tfidf_matrix = vectorizer.fit_transform(content_bodies + [user_interests])
    similarity = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])
    top_indices = np.argsort(similarity[0])[-3:][::-1]
    return [all_content[i] for i in top_indices]


def login_required(f):
    def wrap(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('register'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        experience_level = request.form['experience_level']
        interests = request.form['interests']
        add_user(username, experience_level, interests)
        session['username'] = username
        return redirect(url_for('content'))
    return render_template('register.html')

@app.route('/content', methods=['GET', 'POST'])
@login_required
def content():
    user = get_user(session['username'])
    if user is None:
        session.pop('username', None)
        return redirect(url_for('register'))
    content = get_content_by_user(user[0])
    recommendations = recommend_content(user[3], get_content_by_topic(''))
    
    if request.method == 'POST':
        topic = request.form['topic']
        category = request.form.get('category', 'General')
        title, body = generate_content(topic, user[2])
        save_content(user[0], title, body, topic, category)
        log_interaction(user[0], len(get_content_by_user(user[0])), 'generate')
        return redirect(url_for('content'))
    
    categories = categorize_content(user[0])
    return render_template('content.html', user=user, content=content, recommendations=recommendations, categories=categories)

@app.route('/feedback/<int:content_id>', methods=['GET', 'POST'])
@login_required
def feedback(content_id):
    user = get_user(session['username'])
    if user is None:
        session.pop('username', None)
        return redirect(url_for('register'))
    content_item = next((c for c in get_content_by_user(user[0]) if c[0] == content_id), None)
    if not content_item:
        return redirect(url_for('content'))
    
    if request.method == 'POST':
        rating = int(request.form['rating'])
        comment = request.form['comment']
        sentiment = analyze_sentiment(comment)
        save_feedback(content_id, rating, comment, sentiment)
        log_interaction(user[0], content_id, 'feedback')
        return redirect(url_for('content'))
    
    stats = get_feedback_stats(content_id)
    return render_template('feedback.html', content=content_item, stats=stats)

@app.route('/analytics')
@login_required
def analytics():
    user = get_user(session['username'])
    if user is None:
        session.pop('username', None)
        return redirect(url_for('register'))
    analytics = get_user_analytics(user[0])
    recommendations = get_user_recommendations(user[0])
    return render_template('analytics.html', user=user, analytics=analytics, recommendations=recommendations)

@app.route('/export')
@login_required
def export_page():
    user = get_user(session['username'])
    if user is None:
        session.pop('username', None)
        return redirect(url_for('register'))
    content = get_content_by_user(user[0])
    return render_template('export.html', user=user, content=content)

@app.route('/download_export')
@login_required
def download_export():
    user = get_user(session['username'])
    if user is None:
        session.pop('username', None)
        return redirect(url_for('register'))
    file_path = export_content_to_csv(user[0])
    return send_file(file_path, as_attachment=True, download_name=f"{user[1]}_content.csv")

@app.route('/search', methods=['POST'])
@login_required
def search():
    topic = request.form['topic']
    content = get_content_by_topic(topic)
    return jsonify({"content": [{"id": c[0], "title": c[2], "body": c[3]} for c in content]})

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('register'))

if __name__ == '__main__':
    app.run(debug=True)