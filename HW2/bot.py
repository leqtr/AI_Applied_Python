from aiogram import Bot, Dispatcher, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.filters import Command
from states import ProfileSetup, FoodLogging #, CustomGoal
from utils import get_city_lat_lon, get_weather, get_food_calories, generate_progress_plot, text_to_emoji, calculate_bmr_with_goal, calculate_water_intake, get_calories_burned
from config import BOT_TOKEN
from middleware import LoggingMiddleware

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
dp.message.middleware(LoggingMiddleware())
dp.callback_query.middleware(LoggingMiddleware())


### хранение данных пользователей в памяти
users = {}

################################################################################################начало работы бота
@dp.message(Command("start"))
async def start(message: Message):
    await message.reply("Hello! I'm your Good Habit Bot. 😊\nI'll help you track your water intake, meals, and exercises. \nUse /set_profile to get started!")

################################################################################################стартовые параметры профиля
### начало заполнения
@dp.message(Command("set_profile"))
async def set_profile(message: Message,
                      state: FSMContext):
    sex_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Female",
                                  callback_data="female")],
            [InlineKeyboardButton(text="Male", callback_data="male")]
        ]
    )
    await message.reply("Please select your sex:", reply_markup=sex_keyboard)

### пол
@dp.callback_query(lambda c: c.data in ["male", "female"])
async def handle_sex_selection(callback: types.CallbackQuery, state: FSMContext):
    sex = callback.data
    await state.update_data(sex=sex)

    await callback.message.answer("Enter your age:")
    await state.set_state(ProfileSetup.age)
    await callback.answer()

### возраст
@dp.message(ProfileSetup.age)
async def process_age(message: Message,
                      state: FSMContext):
    try:
        age = int(message.text)
        if age < 10 or age > 100:  ### возраст от 10 до 100 лет
            raise ValueError
    except ValueError:
        await message.reply("⚠️ Please enter a valid age between 10 and 100 years.")
        return None

    await state.update_data(age=age)
    await message.reply("Enter your height (cm):")
    await state.set_state(ProfileSetup.height)

### рост
@dp.message(ProfileSetup.height)
async def process_height(message: Message,
                         state: FSMContext):
    try:
        height = int(message.text)
        if height < 80 or height > 250:  ### рост от 80 до 250 см
            raise ValueError
    except ValueError:
        await message.reply("⚠️ Please enter a valid height between 80 and 250 cm.")
        return None

    await state.update_data(height=height)
    await message.reply("Enter your current weight:")
    await state.set_state(ProfileSetup.current_weight)

### текущий вес
@dp.message(ProfileSetup.current_weight)
async def process_current_weight(message: Message,
                         state: FSMContext):
    try:
        current_weight = int(message.text)
        if current_weight < 30 or current_weight > 500:  ### вес от 30 до 500 кг
            raise ValueError
    except ValueError:
        await message.reply("⚠️ Please enter a valid weight between 30 and 500 kg.")
        return None

    await state.update_data(current_weight=current_weight)
    await message.reply("Enter your target weight:")
    await state.set_state(ProfileSetup.target_weight)

### целевой вес
@dp.message(ProfileSetup.target_weight)
async def process_target_weight(message: Message,
                      state: FSMContext):
    try:
        target_weight = int(message.text)
        if target_weight < 30 or target_weight > 500:  ### вес от 30 до 500 кг
            raise ValueError
    except ValueError:
        await message.reply("⚠️ Please enter a valid weight between 30 and 500 kg.")
        return None

    await state.update_data(target_weight=target_weight)

    activity_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Minimal Activity - Sedentary lifestyle (no exercise)", callback_data="activity_1")],
            [InlineKeyboardButton(text="Light Activity - 1-3 workouts per week", callback_data="activity_2")],
            [InlineKeyboardButton(text="Moderate Activity - 3-5 workouts per week", callback_data="activity_3")],
            [InlineKeyboardButton(text="High Activity - 6-7 workouts per week", callback_data="activity_4")],
            [InlineKeyboardButton(text="Extreme Activity - Athlete, physical job", callback_data="activity_5")]
        ]
    )
    await message.reply("Please select your activity level:", reply_markup=activity_keyboard)

### уровень активности
@dp.callback_query(lambda c: c.data.startswith("activity_"))
async def handle_activity_selection(callback: types.CallbackQuery, state: FSMContext):
    activity_level = int(callback.data.split("_")[1])
    await state.update_data(activity_level=activity_level)

    await callback.message.answer(f"✅ Activity level saved! Now, enter your city:")
    await state.set_state(ProfileSetup.city)
    await callback.answer()

### город
@dp.message(ProfileSetup.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text
    try:
        ### валидация, что введенный город существует
        lat, lon = get_city_lat_lon(city)
    except Exception as e:
        await message.reply(f"⚠️ The city '{city}' was not found. Please try again.")
        return None

    data = await state.get_data()
    user_id = message.from_user.id
    sex = data['sex']
    age = data['age']
    height = data['height']
    current_weight = data['current_weight']
    target_weight = data['target_weight']
    activity_level = data['activity_level']

    water_goal = calculate_water_intake(current_weight = current_weight,
                                        activity_level = activity_level)
    calorie_goal = calculate_bmr_with_goal(sex = sex,
                                           age = age,
                                           height = height,
                                           current_weight = current_weight,
                                           target_weight = target_weight,
                                           activity_level = activity_level)
    users[user_id] = {
        "sex": sex,
        "age": age,
        "height": height,
        "current_weight": current_weight,
        "target_weight": target_weight,
        "activity_level": activity_level,
        "city": city,
        "logged_water": 0,
        "logged_calories": 0,
        "water_goal": water_goal,
        "calorie_goal": calorie_goal,
        'calories_burned': 0
    }
    await message.reply("✅ Profile saved! Use /help to find out about bot functions.")
    await state.clear()

################################################################################################справка по боту
### справка по боту
@dp.message(Command("help"))
async def help_command(message: Message):
    help_text = (
        "📚 *Bot Commands Guide:*\n\n"
        "1️⃣ */set\\_profile* – Set up your profile by entering your parameters\\.\n\n"
        
        "2️⃣ */set\\_water\\_goal \\<goal\\_in\\_ml\\>* – Set a custom daily water intake goal \\(if not set, bot calculates the norm itself\\)\\. \nExample: `/set_water_goal 3000`\\.\n"
        "3️⃣ */set\\_calorie\\_goal \\<goal\\_in\\_kcal\\>* – Set a custom daily calorie consumption goal \\(if not set, bot calculates the norm itself\\)\\. \nExample: `/set_calorie_goal 2500`\\.\n\n"
        
        "4️⃣ */log\\_food \\<food\\_name\\>* – Log the food you eat and track your calorie intake\\. \nExample: `/log_food banana`\\.\n"
        "5️⃣ */log\\_water \\<amount\\_in\\_ml\\>* – Log the amount of water you drink\\. \nExample: `/log_water 500`\\.\n"
        "6️⃣ */log\\_workout \\<activity\\> \\<duration\\_in\\_minutes\\>* – Log your workout and calories burned\\. \nExample: `/log_workout running 30`\\.\n\n"
        
        "7️⃣ */check\\_progress* – Check your progress for water intake, calorie consumption, and calories burned during workouts\\.\n\n"
        
        "💡 *Note:* Ensure to set up your profile first using /set\\_profile to use most of the features\\.\n"
        "🚀 Stay healthy and hydrated\\! 💧🍽💪"
    )
    await message.reply(help_text, parse_mode="MarkdownV2")

################################################################################################персональные цели по воде и калориям
### изменение цели по воде
@dp.message(Command("set_water_goal"))
async def set_water_goal(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("⚠️ You need to set up your profile first. Use /set_profile.")
        return None

    try:
        water_goal = int(message.text.split(maxsplit=1)[-1])
        if water_goal < 0 or water_goal > 10000:  ### потребляемое кол-во воду больше 0 и меньше 10
            raise ValueError
    except (ValueError, IndexError):
        await message.reply("⚠️ Please enter a valid amount of water (between 0 and 10000 ml). Example: /set_water_goal 5000")
        return None

    users[user_id]["water_goal"] = water_goal
    await message.reply(f"✅ Your daily water goal has been set to {water_goal} ml.")

### изменение цели по калориям
@dp.message(Command("set_calorie_goal"))
async def set_water_goal(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("⚠️ You need to set up your profile first. Use /set_profile.")
        return None

    try:
        calorie_goal = int(message.text.split(maxsplit=1)[-1])
        if calorie_goal < 0 or calorie_goal > 10000:
            raise ValueError
    except (ValueError, IndexError):
        await message.reply("⚠️ Please enter a valid amount between 1000 and 10000 kcal.")
        return None

    users[user_id]["calorie_goal"] = calorie_goal
    await message.reply(f"✅ Your daily calorie goal has been set to {calorie_goal} kcal.")

################################################################################################логирование еды,воды,тренировок
### логирование еды
@dp.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("⚠️ You need to set up your profile first. Use /set_profile.")
        return None

    food_name = message.text.split(maxsplit=1)[-1]
    calories = get_food_calories(food_name)['calories']

    if calories is None:
        await message.reply(f"⚠️ Sorry, I couldn't find any information on '{food_name}'. Please try a different food.")
        return None

    emoji_message = text_to_emoji(food_name) if text_to_emoji(food_name) != '' else '🍽'
    await state.update_data(food_name=food_name, calories=calories)
    await message.reply(emoji_message + f" {food_name} — {calories} kcal per 100g. How many grams did you consume?")
    await state.set_state(FoodLogging.food_weight)

@dp.message(FoodLogging.food_weight)
async def process_food_weight(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    try:
        weight = int(message.text)
    except ValueError:
        await message.reply("Please enter a valid number.")
        return

    total_calories = round((weight / 100) * data["calories"])
    users[user_id]["logged_calories"] += total_calories

    await message.reply(f"✅ Logged: {total_calories:.1f} kcal for {data['food_name']}.")
    await state.clear()

### логирование воды
@dp.message(Command("log_water"))
async def log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("⚠️ You need to set up your profile first. Use /set_profile.")
        return None

    try:
        water_amount = int(message.text.split(maxsplit=1)[-1])
        if water_amount < 0 or water_amount > 10000:  ### потребляемое кол-во воду больше 0 и меньше 10
            raise ValueError
    except (ValueError, IndexError):
        await message.reply("⚠️ Please enter a valid amount of water (between 0 and 10000 ml). Example: /log_water 500")
        return None

    users[user_id]["logged_water"] += water_amount
    total_water = users[user_id]["logged_water"]

    await message.reply(f"✅ Logged {water_amount} ml of water! Total water intake: {total_water} ml.")

### логирование тренировок
@dp.message(Command("log_workout"))
async def log_workout(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("⚠️ You need to set up your profile first. Use /set_profile.")
        return None

    try:
        mess = message.text.split(maxsplit=1)
        parts = mess[1].rsplit(maxsplit=1)
        activity = parts[0].lower()  ### вид тренировки
        duration = int(parts[1])  ### длительность в минутах

        if duration <= 0 or duration > 600:
            raise ValueError

    except (ValueError, IndexError):
        await message.reply("⚠️ Please use the correct format: /log_workout <activity> <duration in minutes>. Example: /log_workout running 30")
        return None

    calories_burned = get_calories_burned(activity, duration)
    if calories_burned is None:
        await message.reply(f"⚠️ Sorry, I couldn't find information for the activity '{activity}'. Please try a different workout.")
        return None

    ### обновляем сженные калории и новую норму воды
    users[user_id]["calories_burned"] = round(users[user_id].get("calories_burned", 0) + calories_burned)
    additional_water = int((duration / 30) * 500)  ### 500 мл воды за каждые 30 минут тренировки
    users[user_id]["water_goal"] += additional_water
    emoji_message = text_to_emoji(activity) if text_to_emoji(activity) != '' else '💪'

    await message.reply(emoji_message + f" {activity} for {duration} minutes — {calories_burned:.0f} kcal burned.\n"
                       f"💧 Stay hydrated! Drink additional {additional_water} ml of water.")

################################################################################################прогресс
### проверка прогресса
@dp.message(Command("check_progress"))
async def check_progress(message: Message):
    user_id = message.from_user.id
    if user_id not in users:
        await message.reply("⚠️ You need to set up your profile first. Use /set_profile.")
        return None

    user = users[user_id]
    temp = get_weather(user["city"])
    temp_water_bonus = 500 if temp and temp > 25 else 0

    water_goal = user["water_goal"] + temp_water_bonus
    calorie_goal = user["calorie_goal"]

    generate_progress_plot(user["logged_water"], water_goal, user["logged_calories"], calorie_goal)
    photo = FSInputFile("progress.png")

    await message.answer_photo(photo, caption=f"🌡 Temperature in the city {user['city']}: {temp}°C\n\n"
                                              f"📈 Progress:\n\n"
                                              f"💧 Water intake:\n"
                                              f"💧 {user['logged_water']} ml out of {water_goal} ml\n"
                                              f"💧 {int(100.0*user['logged_water']/water_goal)}% of the goal\n"
                                              f"💧 {water_goal - user['logged_water']} ml left\n\n"
                                              
                                              f"🍽 Calories consumed:\n"
                                              f"🍽 {user['logged_calories']} kcal out of {calorie_goal} kcal\n"
                                              f"🍽 {int(100.0*user['logged_calories']/calorie_goal)}% of the goal\n"
                                              f"🍽 {calorie_goal - user['logged_calories']} kcal left\n\n"
                                              
                                              f"💪 Calories burned:\n"
                                              f"💪 {user['calories_burned']} kcal burned during workout\n"
                                              )

################################################################################################запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

################################################################################################чеклист
# Критерии оценивания:
# ✅ Реализован телеграм-бот с помощью выбранной библиотеки, который обрабатывает запросы пользователя и как минимум просто работает – 2 балла.
# ✅ Реализована настройка профиля пользователя с сохранением информации в программе – 1 балл.
# ✅ Реализован корректный расчёт воды и калорий – 0.3 балла. Если в задании есть неопределенность, решите ее по своему выбору.
# ✅ Успешное использование OpenWeatherMap или иного API для погоды (это вы умеете из ДЗ 1) и OpenFoodFacts или иного способа расчета калорийности – 0.2 балла.
# ✅ Бот позволяет фиксировать воду, еду и тренировки, и каждый из этих методов корректно обновляет все состояния и данные – по 1.5 балла за каждый, всего 4.5 балла.
# # ✅ воду
# # ✅ еду
# # ✅ тренировки
# ✅ Корректно реализован метод, возвращающий прогресс по воде и калориям – 1 балл.
# ✅ Деплой бота на онлайн-сервер, например, на render.com, выполнен корректно. В качестве подтверждения того, что вы успешно задеплоили бота, необходимо прикрепить скриншот с логами, на котором будет видно, что build был успешен. В идеале, чтобы были показаны все команды, которые отправлял пользователь, которые вы будете логировать с помощью, например, middleware, как на лекции – 1 балл.
# ✅ Графики: Постройте графики прогресса по воде и калориям и реализуйте функциональность бота для пока этих графиков (макс + 2 балла).
# ❌ Рекомендации: Бот может предлагать продукты с низким содержанием калорий или тренировки для достижения целей (макс + 1 балл, логику можете предложить любую).
# ❌ Продвинутое определение калорийности: Можете реализовать какой-то более умный способ определения калорийности продукта (макс + 2 балла).

### ✅ добавить \help и вывод подсказки про help после заполнения профиля
### ✅ внести проверку на существование города
### ✅ вообще подумать над различными валидациями текста со стороны пользователя
### ✅ добавить учет воды
### ✅ добавить учет тренировок - /log_workout <тип тренировки> <время (мин)>:
### ### ✅ учет сожженых калорий / воды?
### ✅ подумать над альтернативным графиком прогресса (динамика, распределение)
### ✅ спрашивать цель по калориям и сделать дефолтную цель
### ✅ спрашивать цель по воде и тоже показывать норму воды как дефолт

### комментарии
### ### заменил активность в день на активность по тренировкам, иначе слишком расплывчато
### ### калораж обычно учитывает активность, тренировка не означает, что можно больше есть в этот день... (но логика изменения параметров в связи с тренировкой реализована с водой)
### ### в логировании воды не указываю, сколько до нормы, так как этот функционал уже есть в чекпрогрессе

### особенности
### ### запрашиваю: пол, возраст, рост, текущий вес, целевой вес, уровень активности, город
### ### можно устанавливать личные цели по калориям и весу, или по дефолту бот считает нормы с учетом запрашиваемых параметров
### ### есть справка
### ### есть справка

# Деплой, оформление и описание