class FlaskApp:
    def handle_error(self) -> dict:
        return {'status': 500, 'cors': '*'}
