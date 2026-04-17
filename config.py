import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "9f3c77d8d8S36e7c19fc1e99Fa8a3d672a5c8fb0f28c8f2a46807faPdc6aabc4")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:kosmaZ1572@localhost/machinerental_flask",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
