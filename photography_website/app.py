from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import gspread
from google.oauth2.service_account import Credentials
import os
from datetime import datetime,timedelta
import json
from dotenv import load_dotenv
from flask_moment import Moment
import requests
import threading
from collections import defaultdict
import time
import hashlib
from functools import wraps

load_dotenv()

app = Flask(__name__)
moment = Moment(app)
app.secret_key = os.getenv('SECRET_KEY')  
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')
GOOGLE_ANALYTIC_SHEET_ID = os.getenv('GOOGLE_ANALYTIC_SHEET_ID')
ANALYTICS_PASSWORD = os.getenv('ANALYTICS_PASSWORD')

RATE_LIMIT_SECONDS = 300  # 5 minutes
ip_last_logged = defaultdict(float)

# Authentication decorator
def requires_auth(f):
    """Decorator to require authentication for analytics routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('analytics_authenticated'):
            return redirect(url_for('analytics_login'))
        return f(*args, **kwargs)
    return decorated_function

def verify_password(password):
    """Verify the analytics password"""
    return password == ANALYTICS_PASSWORD


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

def get_client_ip():
    """Get the real client IP address"""
    # Check for forwarded IP (common with proxies/load balancers)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def get_location_from_ip(ip_address):
    """Get location information from IP address using free API"""
    try:
        # Using ipapi.co - free tier allows 1000 requests/day
        if ip_address and ip_address != '127.0.0.1' and not ip_address.startswith('192.168.'):
            response = requests.get(f'https://ipapi.co/{ip_address}/json/', timeout=3)
            if response.status_code == 200:
                data = response.json()
                return {
                    'country': data.get('country_name', 'Unknown'),
                    'region': data.get('region', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown'),
                    'isp': data.get('org', 'Unknown')
                }
    except Exception as e:
        print(f"Error getting location for IP {ip_address}: {e}")
    
    return {
        'country': 'Unknown',
        'region': 'Unknown', 
        'city': 'Unknown',
        'timezone': 'Unknown',
        'isp': 'Unknown'
    }

def should_log_visitor(ip_address):
    """Check if we should log this visitor based on rate limiting"""
    current_time = time.time()
    last_logged = ip_last_logged.get(ip_address, 0)
    if current_time - last_logged >= RATE_LIMIT_SECONDS:
        ip_last_logged[ip_address] = current_time
        return True
    return False

def log_visitor_async(ip_address, user_agent, referrer, location_data):
    """Log visitor data to Google Sheets asynchronously"""
    def log_to_sheet():
        try:
            client = get_google_sheet_client()
            if not client:
                return
            
            sheet = client.open_by_key(GOOGLE_ANALYTIC_SHEET_ID).worksheet('UserLogs')
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare row data
            row_data = [
                timestamp,
                ip_address,
                location_data['country'],
                location_data['region'],
                location_data['city'],
                location_data['timezone'],
                location_data['isp'],
                user_agent,
                referrer or 'Direct'
            ]
            
            sheet.append_row(row_data)
            print(f"Logged visitor: {ip_address} from {location_data['city']}, {location_data['country']}")
            
        except Exception as e:
            print(f"Error logging visitor: {e}")
    
    # Run in background thread to avoid blocking the main request
    thread = threading.Thread(target=log_to_sheet)
    thread.daemon = True
    thread.start()

def track_visitor():
    """Track visitor information"""
    try:
        ip_address = get_client_ip()
        
        # Rate limiting check
        if not should_log_visitor(ip_address):
            return
        
        user_agent = request.headers.get('User-Agent', 'Unknown')
        referrer = request.headers.get('Referer')
        
        # Get location data
        location_data = get_location_from_ip(ip_address)
        
        # Log asynchronously to avoid blocking the response
        log_visitor_async(ip_address, user_agent, referrer, location_data)
        
    except Exception as e:
        print(f"Error in track_visitor: {e}")

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

# def get_testimonials_from_sheet():
#     """Fetch reviews data from Google Sheets"""
#     try:
#         client = get_google_sheet_client()
#         if not client:
#             return []
        
#         sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet('Testimonials')
#         records = sheet.get_all_records()
#         testimonials = sorted(records, key=lambda x: x["date"], reverse=True)
#         return testimonials
#     except Exception as e:
#         print(f"Error fetching albums: {e}")
#         return []

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

# @app.route('/about')
# def about():
#     """About me page"""
#     return render_template('about.html')

@app.route('/about')
def about():
    # testimonials = get_testimonials_from_sheet() (add this (, testimonials=testimonials) to the return function
    return render_template("about.html")

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

#Routing for Analytics side
@app.route('/analytics')
@requires_auth
def analytics():
    """Simple analytics dashboard - now protected with authentication"""
    try:
        client = get_google_sheet_client()
        if not client:
            return jsonify({'error': 'Could not connect to analytics data'})
        
        sheet = client.open_by_key(GOOGLE_ANALYTIC_SHEET_ID).worksheet('UserLogs')
        records = sheet.get_all_records()
        
        # Basic analytics
        total_visits = len(records)
        unique_ips = len(set(record['IP'] for record in records if 'IP' in record))
        countries = {}
        cities = {}
        daily_visits = {}
        
        for record in records:
            # Country stats
            country = record.get('Country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
            
            # City stats
            city = f"{record.get('City', 'Unknown')}, {record.get('Country', 'Unknown')}"
            cities[city] = cities.get(city, 0) + 1
            
            # Daily visits
            timestamp = record.get('Timestamp', '')
            if timestamp:
                date = timestamp.split(' ')[0]  # Get date part
                daily_visits[date] = daily_visits.get(date, 0) + 1
        
        analytics_data = {
            'total_visits': total_visits,
            'unique_visitors': unique_ips,
            'top_countries': dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]),
            'top_cities': dict(sorted(cities.items(), key=lambda x: x[1], reverse=True)[:10]),
            'daily_visits': dict(sorted(daily_visits.items(), reverse=True)[:30]),
            'recent_visits': records[-20:] if records else []
        }
        
        return render_template('analytics.html', data=analytics_data)
    except Exception as e:
        return jsonify({'error': f'Analytics error: {e}'})

@app.route('/analytics/login', methods=['GET', 'POST'])
def analytics_login():
    """Login page for analytics access"""
    if request.method == 'POST':
        password = request.form.get('password')
        if verify_password(password):
            session['analytics_authenticated'] = True
            session.permanent = True
            app.permanent_session_lifetime = timedelta(hours=24)  # Stay logged in for 24 hours
            flash('Successfully logged in to analytics dashboard', 'success')
            return redirect(url_for('analytics'))
        else:
            flash('Invalid password', 'error')
    
    return render_template('analytics_login.html')

@app.route('/analytics/logout')
def analytics_logout():
    """Logout from analytics"""
    session.pop('analytics_authenticated', None)
    flash('Successfully logged out from analytics', 'success')
    return redirect(url_for('home'))

@app.route('/analytics/api')
@requires_auth
def analytics_api():
    """JSON API endpoint for analytics data"""
    try:
        client = get_google_sheet_client()
        if not client:
            return jsonify({'error': 'Could not connect to analytics data'})
        
        sheet = client.open_by_key(GOOGLE_ANALYTIC_SHEET_ID).worksheet('UserLogs')
        records = sheet.get_all_records()
        
        # Basic analytics
        total_visits = len(records)
        unique_ips = len(set(record['IP'] for record in records if 'IP' in record))
        countries = {}
        for record in records:
            country = record.get('Country', 'Unknown')
            countries[country] = countries.get(country, 0) + 1
        
        analytics_data = {
            'total_visits': total_visits,
            'unique_visitors': unique_ips,
            'top_countries': dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]),
            'recent_visits': records[-10:] if records else []
        }
        
        return jsonify(analytics_data)
    except Exception as e:
        return jsonify({'error': f'Analytics error: {e}'})
    
if __name__ == '__main__':
    app.run(debug=True)
