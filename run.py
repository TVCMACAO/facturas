from app import create_app, db # Import db

app = create_app()

if __name__ == '__main__':
    try:
        app.run(debug=True)
    except Exception as e:
        print(f"Error al iniciar el servidor: {e}")
        import traceback
        traceback.print_exc()
