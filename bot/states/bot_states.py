
from aiogram.fsm.state import State, StatesGroup

class BotCreation(StatesGroup):
    waiting_for_token = State()


class AdminPanel(StatesGroup):
    waiting_for_user_action = State()
    subscription_user = State()
    subscription_plan = State()
    subscription_period = State()
    subscription_confirmation = State()
