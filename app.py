from flask import Flask, render_template, redirect, url_for
from flask_cors import CORS
from config import Config
from database import Database
from routes.user_routes import user_bp
from routes.ride_routes import ride_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Enable CORS for all routes
    CORS(app)

    # Initialize Database
    with app.app_context():
        Database.initialize()

    # Register Blueprints
    # Standardizing to /api/v1 for both
    app.register_blueprint(user_bp, url_prefix='/api/v1')
    app.register_blueprint(ride_bp, url_prefix='/api/v1')

   
    @app.route('/')
    def index():
        return render_template('base.html') # Landing page

    @app.route('/auth')
    def auth_page():
        return render_template('auth.html')

    @app.route('/dashboard')
    def dashboard_page():
        return render_template('dashboard.html')

    # -------------------------
    # PWA Support
    # -------------------------
    @app.route('/manifest.json')
    def serve_manifest():
        return app.send_static_file('manifest.json')

    @app.route('/sw.js')
    def serve_sw():
        return app.send_static_file('sw.js')

    return app
