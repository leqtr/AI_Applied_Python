from aiogram.fsm.state import State, StatesGroup

### вводная информация пользователя
class ProfileSetup(StatesGroup):
    age = State()
    height = State()
    current_weight = State()
    target_weight = State()
    # activity = State()
    city = State()

class FoodLogging(StatesGroup):
    food_name = State()
    food_weight = State()

# class CustomGoal(StatesGroup):
#     water_goal = State()
#     calorie_goal = State()