from db.schemas.comments_schema import CommentInDB 

def generate_notification(soruce:str, destination:str, is_follow:False, is_comment:False):
    notification = ""