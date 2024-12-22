import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from sklearn.linear_model import LinearRegression
import datetime

API_KEY_PLACEHOLDER = "Enter your OpenWeatherMap API key here"
LAT_LON_URL = 'http://api.openweathermap.org/geo/1.0/direct'
TEMP_URL = "https://api.openweathermap.org/data/2.5/weather"
two_sigmas = 2  ### интервал для аномалий
window = 30  ### окно скользящего среднего

month_to_season = {12: "winter", 1: "winter", 2: "winter",
                   3: "spring", 4: "spring", 5: "spring",
                   6: "summer", 7: "summer", 8: "summer",
                   9: "autumn", 10: "autumn", 11: "autumn"}

current_date = datetime.date.today()
current_season = month_to_season[current_date.month]


def analyze_city(city_df: pd.DataFrame,  ### должны подавать только отсортированные по дате данные (для rolling)
                 window: int = 30):
    city_df = city_df.sort_values(by="timestamp")
    ### скользящее среднее и стандартное отклонение по всему городу
    city_df["rolling_mean"] = city_df["temperature"].rolling(window=window).mean()
    city_df["rolling_std"] = city_df["temperature"].rolling(window=window).std()

    ### аномалии по скользящему среднему
    city_df["is_anomaly"] = city_df.apply(lambda row:
                                          row['temperature'] > row["rolling_mean"] + two_sigmas * row["rolling_std"]
                                          or
                                          row['temperature'] < row["rolling_mean"] - two_sigmas * row["rolling_std"],
                                          axis=1)

    ### avg, min, max температуры по городу за все время
    avg_temp = city_df["temperature"].mean()
    min_temp = city_df["temperature"].min()
    max_temp = city_df["temperature"].max()

    ### статистика по сезонам
    city_season_df = city_df.groupby("season")["temperature"].agg(season_avg_temp="mean",
                                                                  season_std_temp="std").reset_index()

    ### тренд
    X = pd.DataFrame((city_df["timestamp"] - city_df["timestamp"].min()).dt.days)
    y = city_df["temperature"]

    model = LinearRegression()
    model.fit(X, y)
    # y_pred = model.predict(X)
    trend = "positive" if model.coef_[0] > 0 else "negative"

    return {
        "avg_temp": avg_temp,
        "min_temp": min_temp,
        "max_temp": max_temp,
        "seasonal_profile": city_season_df,
        "trend": trend,
        "anomalies": city_df[city_df.is_anomaly == True]
    }


### хотим делать все запросы внутри одной сессии, чтобы сократить накладные расходы на переподключения
def get_city_lat_lon(city: str,
                     session: requests.Session,
                     api_key: str):
    '''
    Получаем широту и долготу города по его названию
    '''
    params = {
        "q": city,
        "appid": api_key,
    }
    response = session.get(LAT_LON_URL, params=params)
    if response.status_code == 200:
        result = response.json()
        return result[0]['lat'], result[0]['lon']
    else:
        raise Exception(f"Error fetching latitude/longitude: {response.status_code}, {response.text}")


def get_city_current_temperature(lat: float,
                                 lon: float,
                                 session: requests.Session,
                                 api_key: str):
    '''
    Получаем текущую температуру по широте и долготе города
    '''
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric"  ### переводим в градусы Цельсия
    }
    response = session.get(TEMP_URL, params=params)
    if response.status_code == 200:
        result = response.json()
        return result["main"]["temp"]
    else:
        raise Exception(f"Error fetching current temperature: {response.status_code}, {response.text}")


### проверяем на аномальность текущую температуру с профилем сезона
def anomality_check(current_temp: float,
                    seasonal_profile: pd.DataFrame,
                    season: str):
    '''
    Определяем, является ли текущая температура аномальной.
    '''
    season_df = seasonal_profile[seasonal_profile["season"] == season]
    mean_temp = season_df["season_avg_temp"].values[0]
    std_temp = season_df["season_std_temp"].values[0]

    return current_temp < mean_temp - two_sigmas * std_temp or current_temp > mean_temp + two_sigmas * std_temp


def main():
    ### сайдбар для вводных
    st.sidebar.title("Temperature App Settings")
    uploaded_file = st.sidebar.file_uploader("Upload historical temperature data (CSV)", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file, parse_dates=["timestamp"])

        cities = df["city"].unique()
        city = st.sidebar.selectbox("Select a city for analysis", cities)

        min_date = df[df.city == city]["timestamp"].min().date()
        max_date = df[df.city == city]["timestamp"].max().date()

        st.sidebar.write(f"**Data Range:** {min_date} to {max_date}")

        start_date = st.sidebar.date_input("Start Date", value=min_date)
        end_date = st.sidebar.date_input("End Date", value=max_date)

        api_key = st.sidebar.text_input("OpenWeatherMap API Key", type="password")

        current_temp = None
        ### Нынешняя температура
        if api_key:
            with requests.Session() as session:
                try:
                    lat, lon = get_city_lat_lon(city, session, api_key)
                    current_temp = get_city_current_temperature(lat, lon, session, api_key)
                except Exception as e:
                    st.error(str(e))
        else:
            st.warning("Please enter a valid OpenWeatherMap API key to fetch current temperature.")

        if st.sidebar.button("Analyze") and current_temp:
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            city_data = df[(df["city"] == city) & (df["timestamp"].between(start_date, end_date))]

            result = analyze_city(city_data)
            seasonal_profile = result["seasonal_profile"]
            anomalies = result["anomalies"]

            ### Общая статистика
            st.subheader(f"Temperature Analysis for {city}")

            anomaly_status = "not normal" if anomality_check(current_temp, seasonal_profile,
                                                             current_season) else "normal"
            if anomaly_status == 'normal':
                st.success(
                    f"**Current temperature** of {current_temp:.2f}°C in {city} is {anomaly_status} for the {current_season}.")
            elif anomaly_status == 'not normal':
                st.warning(
                    f"**Current temperature** of {current_temp:.2f}°C in {city} is {anomaly_status} for the {current_season}.")

            st.write(f"**Average Temperature:** {result['avg_temp']:.2f}°C")
            st.write(f"**Minimum Temperature:** {result['min_temp']:.2f}°C")
            st.write(f"**Maximum Temperature:** {result['max_temp']:.2f}°C")
            st.write(f"**Temperature Trend throughout chosen period:** {result['trend']}")

            ### Описательная статистика
            st.subheader("Descriptive Statistics")

            st.write(f"**Summary**")
            st.dataframe(city_data.describe())
            st.dataframe(city_data.describe(include='object'))

            histogram = px.histogram(
                city_data,
                x="temperature",
                nbins=30,
                histnorm="probability",
                title="Temperature Distribution",
                labels={"temperature": "Temperature (°C)"},
                color_discrete_sequence=['#80b1d3']
            )
            st.plotly_chart(histogram)

            ### Профиль сезона
            st.subheader("Seasonal Profile")
            st.write(f"**Seasonal statistics**")
            st.dataframe(seasonal_profile)
            fig = px.box(
                city_data,
                x="season",
                y="temperature",
                color="season",
                title="Seasonal Temperature Distribution",
                labels={"season": "Season", "temperature": "Temperature (°C)"},
                color_discrete_sequence=['#80b1d3','#ffffb3','#ccebc5','#fb8072']
            )
            st.plotly_chart(fig)

            ### Температурный временной ряд
            st.subheader("Temperature Time Series with Anomalies")
            fig = px.line(city_data,
                          x="timestamp",
                          y="temperature",
                          title="Temperature Time Series",
                          labels={"timestamp": "Date", "temperature": "Temperature (°C)"},
                          color_discrete_sequence=['#80b1d3']
                          )
            fig.add_scatter(x=anomalies["timestamp"],
                            y=anomalies["temperature"],
                            mode="markers",
                            marker=dict(color="red", size=6),
                            name="Anomalies")
            st.plotly_chart(fig)

            ### Датафрейм с аномалиями
            st.write(f"**Anomalies**")
            st.dataframe(anomalies)

if __name__ == "__main__":
    main()