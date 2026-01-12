from app import create_app
from config import Config

app = create_app()

if __name__ == '__main__':
    print(f"\n🚗 UniCarpool Server running on http://127.0.0.1:{Config.PORT}")
    app.run(debug=True, port=Config.PORT)
