

#pip install streamlit pandas requests plotly pillow streamlit-autorefresh


import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION ---
API_BASE_URL = 'https://ll.thespacedevs.com/2.3.0/launches/'
API_KEY      = 'add api key'
HEADERS      = {'Authorization': f'Token {API_KEY}'}
DATA_PATH    = r'C:\Users\HP\scripts\NZSPOClaunches_next_past_month.csv'
IMAGE_PATH   = 'rockets.png'  # Update as needed

# --- Country flag mapper ---
def country_flag_emoji(country):
    flags = {
        'United States': '🇺🇸', 'USA': '🇺🇸',
        'New Zealand': '🇳🇿', 'NZ': '🇳🇿',
        'Australia': '🇦🇺',
        'Russia': '🇷🇺', 'Russian Federation': '🇷🇺',
        'China': '🇨🇳',
        'India': '🇮🇳',
        'Japan': '🇯🇵',
        'South Korea': '🇰🇷',
        'France': '🇫🇷',
        'United Kingdom': '🇬🇧', 'UK': '🇬🇧',
        'Europe': '🇪🇺',
        # Add more as needed
    }
    return flags.get(country, "🌐")

# --- WX Probability mapper ---
def map_wx_prob(prob):
    try:
        prob = float(prob)
    except (TypeError, ValueError):
        return "Unknown"
    if prob >= 80:
        return "High"
    if prob >= 50:
        return "Medium"
    if prob >= 0:
        return "Low"
    return "Unknown"

# --- Download and deduplicate launches ---
def download_and_update_launch_csv(
    csv_path=DATA_PATH,
    start_date=datetime(2025,1,1),
    end_date=datetime(2025,12,31,23,59,59),
    limit=100
):
    params = {
        'net__gte': start_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'net__lte': end_date.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'include_suborbital': 'false',
        'mode': 'normal',
        'limit': limit,
        'ordering': 'net'
    }

    all_rows = []
    url = API_BASE_URL
    first_page = True
    while url:
        resp = requests.get(url, headers=HEADERS, params=params if first_page else None)
        if resp.status_code != 200:
            st.warning(f"Error fetching launches: {resp.status_code}")
            break
        data = resp.json()
        for launch in data.get('results', []):
            net = launch.get('net', '')
            date, _, time = net.partition('T')
            time = time.rstrip('Z')
            name = launch.get('name', '')
            if '|' in name:
                rocket, mission = [s.strip() for s in name.split('|', 1)]
            else:
                rocket, mission = name, ''
            pad_loc = launch.get('pad', {}).get('location', {}).get('name', '')
            country = launch.get('pad', {}).get('country', {}).get('name', '')
            status = launch.get('status', {}).get('name', '')
            prob = launch.get('probability')  # May be None
            details_url = launch.get('infoURLs', [None])
            details_url = details_url[0] if details_url and len(details_url) > 0 else None

            all_rows.append([
                launch.get('id', ''), date, time, rocket, mission, pad_loc,
                country, status, prob, details_url
            ])
        url = data.get('next')
        first_page = False

    # Load previous data if exists
    columns=[
        'launch_id', 'date', 'time', 'rocket', 'mission', 'pad_location',
        'location', 'status', 'wx_probability', 'details_url'
    ]
    if os.path.exists(csv_path):
        prev = pd.read_csv(csv_path, dtype=str)
    else:
        prev = pd.DataFrame(columns=columns)
    new = pd.DataFrame(all_rows, columns=columns)

    # Deduplicate by launch_id, keep latest entry
    merged = pd.concat([prev, new], ignore_index=True)
    merged = merged.drop_duplicates(subset='launch_id', keep='last')
    merged = merged.sort_values(['date', 'time']).reset_index(drop=True)
    merged.to_csv(csv_path, index=False, encoding='utf-8')
    return merged

# --- Data Loading (cached for 12h or on update) ---
@st.cache_data(ttl=60*60*12)
def load_launch_data():
    if not os.path.exists(DATA_PATH):
        st.warning("No local CSV found, run an update first.")
        return pd.DataFrame()
    return pd.read_csv(DATA_PATH, dtype=str)

# --- Card Renderer ---
def render_launch_card(
    date, time, rocket, mission, pad_location, location, status, countdown,
    wx_prob="Unknown", details_url=None, country="", launch_id=None
):
    wx_map = {
        "Low":   ("🟢", "Low"),
        "Medium":("🟠", "Medium"),
        "High":  ("🔴", "High"),
        "Unknown": ("❓", "Unknown")
    }
    wx_icon, wx_label = wx_map.get(wx_prob, ("❓", wx_prob))
    flag = country_flag_emoji(country)

    status_colors = {
        "Go for Launch": "green",
        "Launch Success": "green",
        "Go": "green",
        "Success": "green",
        "Launch Successful": "green",
        "To Be Confirmed": "orange",
        "TBD": "orange",
        "Hold": "orange",
        "Partial Failure": "orange",
        "Failure": "red",
        "Unknown": "gray"
    }
    status_color = status_colors.get(status, "blue")

    # Build details_url using launch_id if possible (preferred: Space Launch Now frontend)
    if launch_id:
        details_url_final = f"https://spacelaunchnow.me/launch/{launch_id}"
    elif details_url and isinstance(details_url, str) and details_url.startswith("http"):
        details_url_final = details_url
    else:
        details_url_final = None

    with st.container():
        cols = st.columns([3, 2, 2, 2, 1])
        with cols[0]:
            st.markdown(f"**Date:** {date}T{time}Z")
            st.markdown(f"**Mission:** {mission}")
            st.markdown(f"**Rocket:** {rocket}")
            st.markdown(f"**Site:** {pad_location}")
            st.markdown(f"**Location:** {location} {flag}")
        with cols[1]:
            st.markdown(f"**WX Probability**")
            st.markdown(f"{wx_icon} {wx_label}")
        with cols[2]:
            st.markdown(f"#### Status")
            st.markdown(
                f"<span style='color:{status_color}; font-size: 1.3em;'><b>{status}</b></span>",
                unsafe_allow_html=True
            )
        with cols[3]:
            st.markdown(f"#### Countdown")
            st.markdown(
                f"<span style='color:#228be6; font-size: 1.7em;'><b>{countdown}</b></span>",
                unsafe_allow_html=True
            )
        with cols[4]:
            if details_url_final:
                st.link_button("Details", details_url_final)
            else:
                st.button("Details", key=f"details_{date}_{time}")
        st.markdown("---")

# --- App Layout ---
st.set_page_config(page_title="Rocket Launches", layout="wide")
st.title("🚀 Rocket Launches Dashboard")

tab1, tab2, tab3, tab4 = st.tabs(["Upcoming Launches", "Past Launches", "Analytics", "About"])

with st.sidebar:
    st.subheader("Data Controls")
    st.markdown("**Download Date Range**")
    default_start = datetime(2025, 1, 1)
    default_end   = datetime(2025, 12, 31)
    date_range = st.date_input(
        "Select date range to download launches:",
        value=(default_start, default_end),
        min_value=datetime(2000, 1, 1),
        max_value=datetime(2100, 12, 31)
    )

    if st.button("Update Launch Data (API Download)"):
        start_date = pd.to_datetime(date_range[0])
        end_date = pd.to_datetime(date_range[1])
        end_date = end_date.replace(hour=23, minute=59, second=59)
        with st.spinner(f"Downloading launches from {start_date.date()} to {end_date.date()}..."):
            updated = download_and_update_launch_csv(
                start_date=start_date,
                end_date=end_date
            )
            st.success(f"Data updated. {len(updated)} total launches in local database.")
        st.cache_data.clear()

# --- Data for Tabs ---
df = load_launch_data()
if not df.empty:
    df['datetime'] = pd.to_datetime(df['date'] + 'T' + df['time'], errors='coerce')
    now_utc = datetime.utcnow()
    df['wx_category'] = df['wx_probability'].apply(map_wx_prob)

with tab1:
    st.header("Upcoming Launches")
    st_autorefresh(interval=300000, key="refresh")  # Animated refresh every 5 seconds

    if df.empty:
        st.info("No data available. Please update launch data.")
    else:
        future_days = st.slider("Show launches for next N days", 1, 60, 14)
        window_end = now_utc + timedelta(days=future_days)
        mask = (df['datetime'] >= now_utc) & (df['datetime'] <= window_end)
        upcoming = df.loc[mask].copy()
        def countdown(row):
            dt = row['datetime']
            diff = dt - datetime.utcnow()
            return str(diff).split('.')[0] if diff.total_seconds() > 0 else "Launched"
        if not upcoming.empty:
            upcoming['Countdown'] = upcoming.apply(countdown, axis=1)
            upcoming = upcoming.sort_values('datetime')
            for _, row in upcoming.iterrows():
                render_launch_card(
                    date=row['date'],
                    time=row['time'],
                    rocket=row['rocket'],
                    mission=row['mission'],
                    pad_location=row['pad_location'],
                    location=row['location'],
                    status=row['status'],
                    countdown=row['Countdown'],
                    wx_prob=row['wx_category'],
                    details_url=row.get('details_url', None),
                    country=row['location'],
                    launch_id=row['launch_id']
                )
        else:
            st.info("No upcoming launches in the selected time window.")

with tab2:
    st.header("Past Launches")
    if df.empty:
        st.info("No data available. Please update launch data.")
    else:
        past = df[df['datetime'] < now_utc].copy()
        rockets = sorted(past['rocket'].dropna().unique())
        locations = sorted(past['location'].dropna().unique())
        sel_rocket = st.selectbox("Rocket Type", ["All"] + rockets)
        sel_location = st.selectbox("Country", ["All"] + locations)
        if sel_rocket != "All":
            past = past[past['rocket'] == sel_rocket]
        if sel_location != "All":
            past = past[past['location'] == sel_location]
        past = past.sort_values('datetime', ascending=False)
        if not past.empty:
            for _, row in past.iterrows():
                render_launch_card(
                    date=row['date'],
                    time=row['time'],
                    rocket=row['rocket'],
                    mission=row['mission'],
                    pad_location=row['pad_location'],
                    location=row['location'],
                    status=row['status'],
                    countdown="Launched",
                    wx_prob=row['wx_category'],
                    details_url=row.get('details_url', None),
                    country=row['location'],
                    launch_id=row['launch_id']
                )
        else:
            st.info("No past launches match the selected filters.")

with tab3:
    st.header("Analytics")
    if df.empty:
        st.info("No data available. Please update launch data.")
    else:
        import plotly.express as px

        # Use only successful launches for most analytics
        success_statuses = ["Success", "Launch Successful"]
        df_success = df[df['status'].isin(success_statuses)].copy()
        st.subheader("Most analytics shown are for successful launches only.")

        # 1. Launches by Country
        st.markdown("### Launches by Country")
        country_count = df_success['location'].value_counts().reset_index()
        country_count.columns = ['Country', 'Launches']
        fig = px.bar(country_count, x='Country', y='Launches', title="Successful Launches by Country")
        st.plotly_chart(fig, use_container_width=True)

        # 2. Mission breakdown by Country (grouping Starlink)
        countries = country_count['Country'].tolist()
        selected_country = st.selectbox("Mission breakdown for country:", countries)
        mission_df = df_success[
            (df_success['location'] == selected_country) &
            (df_success['mission'].notnull()) & (df_success['mission'] != "")
        ]
        if not mission_df.empty:
            # Group all Starlink launches under a single 'Starlink' mission
            missions_norm = mission_df['mission'].str.strip()
            missions_norm = missions_norm.str.replace(r'(?i)starlink.*', 'Starlink', regex=True)
            mission_stats = missions_norm.value_counts().reset_index()
            mission_stats.columns = ['Mission', 'Launches']
            st.markdown(f"**Mission breakdown for {selected_country}:**")
            st.dataframe(mission_stats)
            fig_mis = px.bar(
                mission_stats.head(10), x='Mission', y='Launches',
                title=f"Top Missions in {selected_country} (Starlink grouped)"
            )
            st.plotly_chart(fig_mis, use_container_width=True)
        else:
            st.info(f"No mission data for {selected_country}")

        # 3. Launches by Launch Pad Location
        st.markdown("### Launches by Launch Pad Location")
        pad_count = df_success['pad_location'].value_counts().reset_index()
        pad_count.columns = ['Launch Pad', 'Launches']
        if not pad_count.empty:
            fig3 = px.bar(pad_count, x='Launch Pad', y='Launches', title="Launches by Pad Location")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No pad location data for successful launches.")

        # 4. Monthly Launch Trend
        st.markdown("### Successful Launches Per Month")
        if not df_success.empty:
            df_success['month'] = pd.to_datetime(df_success['date'], errors='coerce').dt.to_period('M').astype(str)
            month_trend = df_success['month'].value_counts().sort_index().reset_index()
            month_trend.columns = ['Month', 'Launches']
            fig_trend = px.line(month_trend, x='Month', y='Launches', markers=True,
                                title="Successful Launches Per Month")
            st.plotly_chart(fig_trend, use_container_width=True)

        # 5. Most Popular Rockets (Top 5)
        st.markdown("### Most Popular Rockets (Top 5)")
        rocket_stats = df_success['rocket'].value_counts().reset_index().head(5)
        rocket_stats.columns = ['Rocket', 'Launches']
        st.dataframe(rocket_stats)
        fig_rocket = px.bar(rocket_stats, x='Rocket', y='Launches', title="Top 5 Most Popular Rockets")
        st.plotly_chart(fig_rocket, use_container_width=True)

        # 6. Success Rate by Country (Pie, selectable)
        st.markdown("### Success Rate by Country")
        all_countries = df['location'].dropna().unique().tolist()
        country_for_pie = st.selectbox("Show success/failure rate for country:", all_countries)
        country_sub = df[df['location'] == country_for_pie]
        status_pie = country_sub['status'].value_counts().reset_index()
        status_pie.columns = ['Status', 'Count']
        fig_pie = px.pie(status_pie, names='Status', values='Count', title=f"Launch Status for {country_for_pie}", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

        # 7. Success Rate by Rocket (Pie, selectable)
        st.markdown("### Success Rate by Rocket")
        all_rockets = df['rocket'].dropna().unique().tolist()
        rocket_for_pie = st.selectbox("Show success/failure rate for rocket:", all_rockets)
        rocket_sub = df[df['rocket'] == rocket_for_pie]
        rocket_status_pie = rocket_sub['status'].value_counts().reset_index()
        rocket_status_pie.columns = ['Status', 'Count']
        fig_rocket_pie = px.pie(rocket_status_pie, names='Status', values='Count', title=f"Launch Status for {rocket_for_pie}", hole=0.4)
        st.plotly_chart(fig_rocket_pie, use_container_width=True)

        # 8. Timeline: Next 10 Scheduled Launches (Upcoming)
        st.markdown("### Timeline: Next 10 Scheduled Launches")
        df_upcoming = df[df['datetime'] > datetime.utcnow()].sort_values('datetime').head(10)
        if not df_upcoming.empty:
            timeline_df = df_upcoming[['date', 'rocket', 'mission', 'pad_location', 'location']]
            timeline_df = timeline_df.rename(columns={'date': 'Launch Date', 'rocket': 'Rocket',
                                                      'mission': 'Mission', 'pad_location': 'Pad Location', 'location': 'Country'})
            st.dataframe(timeline_df)
        else:
            st.info("No upcoming launches found for timeline.")

        # 9. First/Last launch date per country
        st.markdown("### First and Last Launch Date per Country")
        country_dates = df.groupby('location')['datetime'].agg(['min', 'max']).reset_index()
        country_dates.columns = ['Country', 'First Launch', 'Last Launch']
        st.dataframe(country_dates)

        # 10. Failure Reason Breakdown (if present)
        st.markdown("### Failure Reasons (if available)")
        if 'failreason' in df.columns:
            fail_df = df[df['failreason'].notnull() & (df['failreason'] != "")]
            if not fail_df.empty:
                fail_reasons = fail_df['failreason'].value_counts().reset_index()
                fail_reasons.columns = ['Reason', 'Count']
                st.dataframe(fail_reasons)
                fig_fail = px.bar(fail_reasons, x='Reason', y='Count', title="Failure Reasons")
                st.plotly_chart(fig_fail, use_container_width=True)
            else:
                st.info("No failure reasons found in data.")
        else:
            st.info("Failure reasons not included in current data.")

        # 11. Provider Stats (if present)
        st.markdown("### Launch Provider Stats (if available)")
        if 'provider' in df.columns:
            prov_stats = df['provider'].value_counts().reset_index()
            prov_stats.columns = ['Provider', 'Launches']
            st.dataframe(prov_stats)
            fig_prov = px.bar(prov_stats, x='Provider', y='Launches', title="Launches by Provider")
            st.plotly_chart(fig_prov, use_container_width=True)
        else:
            st.info("Launch provider not included in current data.")



with tab4:
    st.header("About")
    st.markdown("""
    **Rocket Launches Dashboard**  
    Displays all orbital launches for any period you select.

    - Data source: [The Space Devs Launch Library 2 API](https://ll.thespacedevs.com/)
    - Weather probability (WX) shown for each launch
    - Analytics for rocket type, country, launch site, and more!
    - "Details" buttons link to public Space Launch Now frontend for each launch.

    _Built with Streamlit, Plotly, and Python._
    """)
    try:
        from PIL import Image
        image = Image.open(IMAGE_PATH)
        st.image(image, use_column_width=True)
    except Exception as e:
        st.info("Rocket dashboard visual not found or failed to load.")

st.caption("Last data update: {}".format(datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')))



'44e9bb0de803f1eca3ac4caa3fbde3bc2e31703a'
