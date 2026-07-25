class UserRouter:
    def get_user(self, user_id: int) -> dict:
        return {'id': user_id}
