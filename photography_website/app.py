from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, make_response
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
import uuid

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
visitor_sessions = defaultdict(float)  # Track visitor sessions

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
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        return None

def get_client_ip():
    """Get the real client IP address"""
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def get_location_from_ip(ip_address):
    """Get location info from IP address using fallback: ipinfo → ip-api → ipapi"""
    
    def try_ipinfo(ip):
        try:
            resp = requests.get(f"https://ipinfo.io/{ip}/json", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                loc = data.get('loc', ',').split(',')
                return {
                    'country': data.get('country', 'Unknown'),
                    'region': data.get('region', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown'),
                    'isp': data.get('org', 'Unknown'),
                    'latitude': loc[0] if len(loc) > 1 else 'Unknown',
                    'longitude': loc[1] if len(loc) > 1 else 'Unknown',
                    'source': 'ipinfo.io'
                }
        except Exception as e:
            print(f"[ipinfo.io] Error: {e}")
        return None

    def try_ipapi_com(ip):
        try:
            resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'country': data.get('country', 'Unknown'),
                    'region': data.get('regionName', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown'),
                    'isp': data.get('isp', 'Unknown'),
                    'latitude': str(data.get('lat', 'Unknown')),
                    'longitude': str(data.get('lon', 'Unknown')),
                    'source': 'ip-api.com'
                }
        except Exception as e:
            print(f"[ip-api.com] Error: {e}")
        return None

    def try_ipapi_co(ip):
        try:
            resp = requests.get(f"https://ipapi.co/{ip}/json/", timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'country': data.get('country_name', 'Unknown'),
                    'region': data.get('region', 'Unknown'),
                    'city': data.get('city', 'Unknown'),
                    'timezone': data.get('timezone', 'Unknown'),
                    'isp': data.get('org', 'Unknown'),
                    'latitude': str(data.get('latitude', 'Unknown')),
                    'longitude': str(data.get('longitude', 'Unknown')),
                    'source': 'ipapi.co'
                }
        except Exception as e:
            print(f"[ipapi.co] Error: {e}")
        return None

    # Ignore local/private IPs
    if not ip_address or ip_address.startswith(('127.', '192.168.', '10.', '172.')):
        return {
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'timezone': 'Unknown',
            'isp': 'Unknown',
            'latitude': 'Unknown',
            'longitude': 'Unknown',
            'source': 'invalid_local_ip'
        }

    return (
        try_ipinfo(ip_address)
        or try_ipapi_com(ip_address)
        or try_ipapi_co(ip_address)
        or {
            'country': 'Unknown',
            'region': 'Unknown',
            'city': 'Unknown',
            'timezone': 'Unknown',
            'isp': 'Unknown',
            'latitude': 'Unknown',
            'longitude': 'Unknown',
            'source': 'fallback_failed'
        }
    )

def get_or_create_visitor_id():
    """Get existing visitor ID from cookie or create new one"""
    visitor_id = request.cookies.get('visitor_id')
    if not visitor_id:
        visitor_id = str(uuid.uuid4())
    return visitor_id

def should_log_visitor(visitor_id, ip_address):
    """Check if we should log this visitor based on cookie and rate limiting"""
    current_time = time.time()
    
    # Check if this visitor_id has been logged recently
    last_logged = visitor_sessions.get(visitor_id, 0)
    if current_time - last_logged >= RATE_LIMIT_SECONDS:
        visitor_sessions[visitor_id] = current_time
        return True
    
    # Fallback to IP-based rate limiting for visitors without cookies
    if not request.cookies.get('visitor_id'):
        last_logged_ip = ip_last_logged.get(ip_address, 0)
        if current_time - last_logged_ip >= RATE_LIMIT_SECONDS:
            ip_last_logged[ip_address] = current_time
            return True
    
    return False

def log_visitor_async(visitor_id, ip_address, user_agent, referrer, location_data, is_returning):
    """Log visitor data to Google Sheets asynchronously"""
    def log_to_sheet():
        try:
            client = get_google_sheet_client()
            if not client:
                print("Failed to get Google Sheets client")
                return
            
            try:
                spreadsheet = client.open_by_key(GOOGLE_ANALYTIC_SHEET_ID)
                sheet = spreadsheet.worksheet('UserLogs')
            except gspread.exceptions.SpreadsheetNotFound:
                print(f"Spreadsheet not found: {GOOGLE_ANALYTIC_SHEET_ID}")
                return
            except gspread.exceptions.WorksheetNotFound:
                print("UserLogs worksheet not found")
                return
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Prepare row data with safe defaults
            row_data = [
                timestamp,
                visitor_id or 'Unknown',
                ip_address or 'Unknown',
                location_data.get('country', 'Unknown'),
                location_data.get('region', 'Unknown'), 
                location_data.get('city', 'Unknown'),
                location_data.get('timezone', 'Unknown'),
                location_data.get('isp', 'Unknown'),
                user_agent or 'Unknown',
                referrer or 'Direct',
                location_data.get('latitude','Unknown'),
                location_data.get('longitude','Unknown'),
                location_data.get('source','Unknown'),
                'Returning' if is_returning else 'New'
            ]
            
            sheet.append_row(row_data)
            print(f"Successfully logged visitor: {visitor_id} ({ip_address}) from {location_data.get('city', 'Unknown')}, {location_data.get('country', 'Unknown')} - {'Returning' if is_returning else 'New'}")
            
        except Exception as e:
            print(f"Error logging visitor to sheet: {e}")
    
    thread = threading.Thread(target=log_to_sheet)
    thread.daemon = True
    thread.start()

def track_visitor():
    """Track visitor information with cookie-based unique identification"""
    try:
        ip_address = get_client_ip()
        visitor_id = get_or_create_visitor_id()
        is_returning = bool(request.cookies.get('visitor_id'))
        
        # Skip localhost and private IPs for testing
        if ip_address in ['127.0.0.1', 'localhost'] or ip_address.startswith('192.168.'):
            print(f"Skipping tracking for local IP: {ip_address}")
            return
        
        # Rate limiting check
        if not should_log_visitor(visitor_id, ip_address):
            print(f"Rate limited for visitor: {visitor_id}")
            return
        
        user_agent = request.headers.get('User-Agent', 'Unknown')
        referrer = request.headers.get('Referer')
        
        print(f"Tracking visitor: {visitor_id} (IP: {ip_address}) - {'Returning' if is_returning else 'New'}")
        
        # Get location data
        location_data = get_location_from_ip(ip_address)
        
        # Log asynchronously to avoid blocking the response
        log_visitor_async(visitor_id, ip_address, user_agent, referrer, location_data, is_returning)
        
        # Set visitor cookie in the response (will be handled in after_request)
        if not is_returning:
            session['new_visitor_id'] = visitor_id
        
    except Exception as e:
        print(f"Error in track_visitor: {e}")

def is_visitor_blocked(visitor_id):
    try:
        client = get_google_sheet_client()
        if not client:
            return False
        sheet = client.open_by_key(GOOGLE_ANALYTIC_SHEET_ID).worksheet('Blacklist')
        blocked_ids = sheet.col_values(1)[1:]  # Assuming visitor IDs are in column A and skipping A1
        return visitor_id in blocked_ids
    except Exception as e:
        print(f"Error checking blocked visitors: {e}")
        return False

@app.after_request
def after_request(response):
    """Set visitor cookie after request"""
    if 'new_visitor_id' in session:
        visitor_id = session.pop('new_visitor_id')
        response.set_cookie('visitor_id', visitor_id, max_age=365*24*60*60)  # 1 year
    return response

def get_images_from_sheet():
    """Fetch images data from Google Sheets"""
    try:
        client = get_google_sheet_client()
        if not client:
            return []
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet('Images')
        records = sheet.get_all_records()
        return records
    except Exception as e:
        print(f"Error fetching images: {e}")
        return []

# def get_albums_from_sheet():
#     """Fetch albums data from Google Sheets"""
#     try:
#         client = get_google_sheet_client()
#         if not client:
#             return []
        
#         sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet('Albums')
#         records = sheet.get_all_records()
#         return records
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

@app.before_request
def before_request():
    """Track visitor before each request"""
    # Skip tracking for static files and analytics routes
    if request.endpoint and (
        request.endpoint.startswith('static') or 
        request.endpoint.startswith('analytics') or
        request.path.startswith('/analytics')
    ):
        return None
    # Block specific visitors
    visitor_id = get_or_create_visitor_id()
    if is_visitor_blocked(visitor_id):
        return render_template('blocked.html'), 403
    
    # Track the visitor
    track_visitor()

@app.route('/')
def home():
    """Home page with image gallery"""
    images = get_images_from_sheet()
    albums = get_albums_from_sheet()
    return render_template('home.html', images=images, albums=albums)

@app.route('/about')
def about():
    """About me page"""
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

# Analytics routes
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
        unique_visitors = len(set(record.get('Visitor_ID', record.get('IP', '')) for record in records))
        new_visitors = len([r for r in records if r.get('Visitor_Type') == 'New'])
        returning_visitors = len([r for r in records if r.get('Visitor_Type') == 'Returning'])
        
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
            'unique_visitors': unique_visitors,
            'new_visitors': new_visitors,
            'returning_visitors': returning_visitors,
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
            app.permanent_session_lifetime = timedelta(hours=24)
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
def analytics_api():
    """JSON API endpoint for analytics data"""
    try:
        client = get_google_sheet_client()
        if not client:
            return jsonify({'error': 'Could not connect to analytics data'})
        
        try:
            spreadsheet = client.open_by_key(GOOGLE_ANALYTIC_SHEET_ID)
            sheet = spreadsheet.worksheet('UserLogs')
        except gspread.exceptions.SpreadsheetNotFound:
            return jsonify({'error': 'Analytics spreadsheet not found'})
        except gspread.exceptions.WorksheetNotFound:
            return jsonify({'error': 'UserLogs worksheet not found'})
        
        records = sheet.get_all_records()
        
        if not records:
            return jsonify({
                'total_visits': 0,
                'unique_visitors': 0,
                'top_countries': {},
                'recent_visits': []
            })
        
        # Basic analytics
        total_visits = len(records)
        unique_visitors = len(set(record.get('Visitor_ID', record.get('IP', '')) for record in records))
        countries = {}
        
        for record in records:
            country = record.get('Country', 'Unknown')
            if country and country != '':
                countries[country] = countries.get(country, 0) + 1
        
        analytics_data = {
            'total_visits': total_visits,
            'unique_visitors': unique_visitors,
            'top_countries': dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]),
            'recent_visits': records[-10:] if len(records) >= 10 else records
        }
        
        return jsonify(analytics_data)
        
    except Exception as e:
        print(f"Analytics API error: {e}")
        return jsonify({'error': f'Analytics error: {e}'})
    
@app.route('/test-analytics')
def test_analytics():
    """Test endpoint to manually add analytics data"""
    if app.debug:
        test_location = {
            'country': 'India',
            'region': 'Rajasthan', 
            'city': 'Jaipur',
            'timezone': 'Asia/Kolkata',
            'isp': 'Test ISP'
        }
        visitor_id = get_or_create_visitor_id()
        log_visitor_async(visitor_id, '192.168.1.100', 'Test User Agent', 'Test Referrer', test_location, False)
        return jsonify({'message': 'Test analytics data added'})
    else:
        return jsonify({'error': 'Not available in production'})
    
def get_blog_posts_from_sheet():
    """Fetch blog posts from Google Sheets"""
    try:
        client = get_google_sheet_client()
        if not client:
            return []
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).worksheet('Blog')
        records = sheet.get_all_records()
        # Sort by date, newest first
        return sorted(records, key=lambda x: x.get('Date', ''), reverse=True)
    except Exception as e:
        print(f"Error fetching blog posts: {e}")
        return []

@app.route('/blog')
def blog():
    """Blog listing page"""
    posts = get_blog_posts_from_sheet()
    return render_template('blog.html', posts=posts)

@app.route('/blog/<slug>')
def blog_post(slug):
    """Individual blog post"""
    posts = get_blog_posts_from_sheet()
    post = next((p for p in posts if p.get('Slug') == slug), None)
    if not post:
        flash('Blog post not found', 'error')
        return redirect(url_for('blog'))
    return render_template('blog_post.html', post=post)

if __name__ == '__main__':
    app.run(debug=True)
