from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime
import json
from dotenv import load_dotenv
from flask_moment import Moment


load_dotenv()

app = Flask(__name__)
moment = Moment(app)
app.secret_key = os.getenv('SECRET_KEY')  # Change this to a random secret key
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')


# Google Sheets Configuration
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_google_sheet_client():
    """Initialize Google Sheets client"""
    try:
        # You'll need to add your service account JSON file
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return None

def get_images_from_sheet():
    """Fetch images data from Google Sheets"""
    try:
        client = get_google_sheet_client()
        if not client:
            return []
        
        # Replace with your Google Sheet ID
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet('Images')
        records = sheet.get_all_records()
        return records
    except Exception as e:
        print(f"Error fetching images: {e}")
        return []

def get_albums_from_sheet():
    """Fetch albums data from Google Sheets"""
    try:
        client = get_google_sheet_client()
        if not client:
            return []
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet('Albums')
        records = sheet.get_all_records()
        return records
    except Exception as e:
        print(f"Error fetching albums: {e}")
        return []

def get_testimonials_from_sheet():
    """Fetch reviews data from Google Sheets"""
    try:
        client = get_google_sheet_client()
        if not client:
            return []
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet('Testimonials')
        records = sheet.get_all_records()
        testimonials = sorted(records, key=lambda x: x["date"], reverse=True)
        return testimonials
    except Exception as e:
        print(f"Error fetching albums: {e}")
        return []

def save_contact_to_sheet(name, email, phone, project_type, budget, event_date, message):
    """Save contact form data to Google Sheets"""
    try:
        client = get_google_sheet_client()
        if not client:
            return False
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet('Contacts')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([timestamp, name, email, phone, project_type, budget, event_date, message, 'New'])
        return True
    except Exception as e:
        print(f"Error saving contact: {e}")
        return False

@app.route('/')
def home():
    """Home page with image gallery"""
    images = get_images_from_sheet()
    albums = get_albums_from_sheet()
    return render_template('home.html', images=images, albums=albums)

@app.route('/about')
def about():
    """About me page"""
    return render_template('about.html')

@app.route('/about')
def about():
    testimonials = get_testimonials_from_sheet()
    return render_template("about.html", testimonials=testimonials)

@app.route('/connect', methods=['GET', 'POST'])
def connect():
    """Contact form page"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        project_type = request.form.get('project_type')
        budget = request.form.get('budget')
        event_date = request.form.get('event_date')
        message = request.form.get('message')
        
        if name and email and message:
            if save_contact_to_sheet(name, email, phone, project_type, budget, event_date, message):
                flash('Thank you for your message! I\'ll get back to you soon.', 'success')
            else:
                flash('Sorry, there was an error sending your message. Please try again.', 'error')
        else:
            flash('Please fill in all fields.', 'error')
        
        return redirect(url_for('connect'))
    
    return render_template('connect.html')

@app.route('/album/<album_name>')
def album(album_name):
    """Display specific album"""
    images = get_images_from_sheet()
    album_images = [img for img in images if img.get('Album', '').lower() == album_name.lower()]
    return render_template('album.html', images=album_images, album_name=album_name)

@app.route('/api/images')
def api_images():
    """API endpoint for images (for dynamic loading)"""
    images = get_images_from_sheet()
    return jsonify(images)

@app.route('/api/album/<album_name>')
def api_album(album_name):
    """API endpoint for specific album"""
    images = get_images_from_sheet()
    album_images = [img for img in images if img.get('Album', '').lower() == album_name.lower()]
    return jsonify(album_images)

if __name__ == '__main__':
    app.run(debug=True)
