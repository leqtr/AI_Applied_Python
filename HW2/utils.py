import requests
import matplotlib.pyplot as plt
from config import WEATHER_API_KEY, API_NINJAS_KEY
import emoji

LAT_LON_URL = 'http://api.openweathermap.org/geo/1.0/direct'
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
FOOD_API_URL = "https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={}&json=true"
WORKOUT_API_URL = "https://api.api-ninjas.com/v1/caloriesburned?activity={}"


def get_city_lat_lon(city: str):
    """
    Fetch latitude and longitude of the given city using OpenWeatherMap API
    """
    try:

        params = {
            "q": city,
            "appid": WEATHER_API_KEY,
        }
        response = requests.get(LAT_LON_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                return data[0]['lat'], data[0]['lon']
            else:
                raise Exception(f"City not found: {city}")
        else:
            raise Exception(f"Error fetching latitude/longitude: {response.status_code}, {response.text}")
    except:
        raise Exception(f"Error fetching latitude/longitude: {response.status_code}, {response.text}")


def get_weather(city: str):
    """
    Fetch current temperature in the given city by its latitude and longitude
    """
    lat, lon = get_city_lat_lon(city)

    weather_params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric"  # Convert temperature to Celsius
    }
    response = requests.get(WEATHER_URL, params=weather_params)
    if response.status_code == 200:
        data = response.json()
        return data["main"]["temp"]
    else:
        raise Exception(f"Error fetching current temperature: {response.status_code}, {response.text}")

def get_food_calories(food_name: str):
    """
    Fetch calorie content of a given food item using OpenFoodFacts API
    """
    url = FOOD_API_URL.format(food_name.replace(" ", "-"))
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:  ### проверяем, есть ли найденные продукты
            first_product = products[0] ### для простоты берем первый продукт
            return {
                'name': first_product.get('product_name', 'unknown'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
        else:
            return None
    else:
        raise Exception(f"Error fetching food calorie content: {response.status_code}, {response.text}")

def generate_progress_plot(water_logged, water_goal, calories_consumed, calories_goal):
    """
    Generate a progress bar chart for water intake and calorie consumption
    """
    labels = ['Water (ml)', 'Calories (kcal)']
    values = [
        water_logged / water_goal if water_goal > 0 else 0,
        calories_consumed / calories_goal if calories_goal > 0 else 0
    ]

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(labels, values, color=['blue', 'red'])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Progress (%)")
    ax.set_title("Your progress")

    plt.savefig("progress.png", bbox_inches="tight")
    plt.close()

def text_to_emoji(word):
    """
    Text to emoji translator (if possible)
    """
    emojified = emoji.emojize(f":{word}:", language="alias")
    return emojified if emojified != f":{word}:" else ''

def calculate_bmr_with_goal(sex: str,
                            age: int,
                            height: float,
                            current_weight: float,
                            target_weight: float,
                            activity_level: int):
    """
    Calculate daily calorie requirement using BMR (Mifflin-St Jeor Equation) and adjust for activity level and target weight
    """
    if sex == "male":
        bmr = 10 * current_weight + 6.25 * height - 5 * age + 5
    elif sex == "female":
        bmr = 10 * current_weight + 6.25 * height - 5 * age - 161
    else:
        raise ValueError("Invalid sex. Please specify 'male' or 'female'.")

    activity_multipliers = {
        1: 1.2,   ### minimal activity
        2: 1.375, ### light activity
        3: 1.55,  ### moderate activity
        4: 1.725, ### high activity
        5: 1.9    ### extreme activity
    }
    activity_factor = activity_multipliers.get(activity_level, 1.2)
    total_calories = bmr * activity_factor

    ### поправка дневных калорий на целевой вес
    total_calories += (target_weight - current_weight) * 100

    return round(total_calories)


def calculate_water_intake(current_weight: float,
                           activity_level: int):
    """
    Calculate the daily water intake norm in milliliters.
    """
    base_water = current_weight * 30

    ### доп вода в жаркую погожу
    activity_water = {
        1: 0,    ### minimal activity
        2: 300,  ### light activity
        3: 500,  ### moderate activity
        4: 700,  ### high activity
        5: 1000  ### extreme activity
    }.get(activity_level, 0)

    total_water = base_water + activity_water

    return round(total_water)

def get_calories_burned(activity: str,
                        duration: int):
    """
    Fetch calories burned for a given activity and duration using the API Ninjas
    """
    url = WORKOUT_API_URL.format(activity)
    headers = {"X-Api-Key": API_NINJAS_KEY}

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            calories_per_min = data[0].get("calories_per_hour", 0)/60.0
            return round(calories_per_min * duration)
    return None