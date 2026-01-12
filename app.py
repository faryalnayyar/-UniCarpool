from flask import Flask, render_template, redirect, url_for
from config import Config
from database import Database
from routes.user_routes import user_bp
from routes.ride_routes import ride_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Database
    with app.app_context():
        Database.initialize()

    # Register Blueprints
    app.register_blueprint(user_bp, url_prefix='/api/v1')
    
    # Note: frontend calls /api/ride/... sometimes, but we standardized on /api/v1
    # However, ride_routes now uses /v1/... extensively.
    # The blueprint in ride_routes.py is defined as: ride_bp = Blueprint('ride_bp', __name__)
    # Inside it, routes are like @ride_bp.route('/v1/rides/nearby') or @ride_bp.route('/ride/create')
    # If we register with url_prefix='/api', then it becomes /api/v1/rides/nearby.
    # If we register with url_prefix='/api/v1', then it might become /api/v1/v1/... which is bad.
    # Let's check ride_routes again. 
    # ride_routes Step 26: @ride_bp.route('/v1/rides/nearby')
    # So if we register as url_prefix='/api', we get /api/v1/rides/nearby. THIS IS CORRECT.
    app.register_blueprint(ride_bp, url_prefix='/api')

    # Frontend Routes (serving the HTML)
    @app.route('/')
    def index():
        return render_template('base.html') # Landing page

    @app.route('/auth')
    def auth_page():
        return render_template('auth.html')

    @app.route('/dashboard')
    def dashboard_page():
        return render_template('dashboard.html')

    return app
