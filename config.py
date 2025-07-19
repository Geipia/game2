import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey')
    SESSION_TYPE = 'filesystem'
    UPLOAD_FOLDER = 'static/uploads'
    DATABASE = 'data.db'
    STRIPE_PUBLISHABLE_KEY = 'pk_live_51Rb21ICOWsHWoBEGmAY8BEDjuDe7KjsHoTY4hzhve9aiZd0tUaQoaIEG3aoGHHnwjtc8VrEBDJrIZReI0CTVLYqQ00fikEjr67'
    STRIPE_BUY_BUTTON_ID = 'buy_btn_1RlodyCOWsHWoBEGAMGyrBcx'
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_12345')
