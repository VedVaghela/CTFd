import re
import uuid

from CTFd.plugins import register_plugin_assets_directory
from flask import session
from CTFd.models import db,  Challenges, Users



class FlagException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class BaseFlag(object):
    name = None
    templates = {}

    @staticmethod
    def compare(self, saved, provided):
        return True


class CTFdStaticFlag(BaseFlag):
    name = "static"
    templates = {  # Nunjucks templates used for key editing & viewing
        "create": "/plugins/flags/assets/static/create.html",
        "update": "/plugins/flags/assets/static/edit.html",
    }

    @staticmethod
    def compare(chal_key_obj, provided):
        saved = chal_key_obj.content
        data = chal_key_obj.data

        if len(saved) != len(provided):
            return False
        result = 0

        if data == "case_insensitive":
            for x, y in zip(saved.lower(), provided.lower()):
                result |= ord(x) ^ ord(y)
        else:
            for x, y in zip(saved, provided):
                result |= ord(x) ^ ord(y)
        return result == 0


class CTFdRegexFlag(BaseFlag):
    name = "regex"
    templates = {  # Nunjucks templates used for key editing & viewing
        "create": "/plugins/flags/assets/regex/create.html",
        "update": "/plugins/flags/assets/regex/edit.html",
    }

    @staticmethod
    def compare(chal_key_obj, provided):
        saved = chal_key_obj.content
        data = chal_key_obj.data

        try:
            if data == "case_insensitive":
                res = re.match(saved, provided, re.IGNORECASE)
            else:
                res = re.match(saved, provided)
        # TODO: this needs plugin improvements. See #1425.
        except re.error as e:
            raise FlagException("Regex parse error occured") from e

        return res and res.group() == provided


# Define the model for the unique flags
class UserFlags(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'))
    flag = db.Column(db.String(64))

    def __init__(self, user_id, challenge_id, flag):
        self.user_id = user_id
        self.challenge_id = challenge_id
        self.flag = flag

def save_user_flag(user_id, challenge_id, flag):
    user_flag = UserFlags(user_id=user_id, challenge_id=challenge_id, flag=flag)
    db.session.add(user_flag)
    db.session.commit()

def get_user_flag(user_id, challenge_id):
    user_flag = UserFlags.query.filter_by(user_id=user_id, challenge_id=challenge_id).first()
    return user_flag.flag if user_flag else None

#Class of User-specific Flags for each challenge
class CTFDynamicFlag(BaseFlag):
    name="dynamic"
    templates = {
        "create": "/plugins/flags/assets/dynamic/create.html",
        "update": "/plugins/flags/assets/dynamic/edit.html",
    }

    #Generate a unique flag for each user
    @staticmethod
    def generate_flag(user_id, challenge_id):
        unique_flag = f"flag{{{user_id}-{challenge_id}-{uuid.uuid4()}}}"
        save_user_flag(user_id, challenge_id, unique_flag)
        return unique_flag

    # @staticmethod
    # def compare(chal_key_obj, provided, user_id):
    #     saved = get_user_flag(user_id, chal_key_obj.challenge_id)
    #     if saved is None:
    #         return False
    #     return saved == provided
    @staticmethod
    def compare(chal_key_obj, provided):
        saved = chal_key_obj.content
        data = chal_key_obj.data

        if len(saved) != len(provided):
            return False
        result = 0

        if data == "case_insensitive":
            for x, y in zip(saved.lower(), provided.lower()):
                result |= ord(x) ^ ord(y)
        else:
            for x, y in zip(saved, provided):
                result |= ord(x) ^ ord(y)
        return result == 0


FLAG_CLASSES = {"static": CTFdStaticFlag, "regex": CTFdRegexFlag, "dynamic": CTFDynamicFlag}


def get_flag_class(class_id):
    cls = FLAG_CLASSES.get(class_id)
    if cls is None:
        raise KeyError
    return cls

def get_current_user_id():
    return session.get('user_id')

def get_challenge_id():
    return session.get('challenge_id')


def load(app):
    register_plugin_assets_directory(app, base_path="/plugins/flags/assets/")
