# type: ignore
# pyright: reportGeneralTypeIssues=false
# =================================== IMPORTS ================================= #

import os
import re
pattern = r',(?=(?:[^()]*\([^()]*\))*[^()]*$)'

# import json
import numpy as np 
import pandas as pd 
from datetime import datetime, timedelta
from collections import Counter

# import seaborn as sns 
import plotly.graph_objects as go
import plotly.express as px

import time
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import folium
from folium.plugins import MousePosition

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context
# Google Web Credentials
import json
import base64
import gspread
from google.oauth2.service_account import Credentials

# 'data/~$bmhc_data_2024_cleaned.xlsx'
# print('System Version:', sys.version)
# =================================== DATA ==================================== #

current_dir = os.getcwd()
current_file = os.path.basename(__file__)
script_dir = os.path.dirname(os.path.abspath(__file__))
# data_path = 'data/Navigation_Responses.xlsx'
# file_path = os.path.join(script_dir, data_path)
# data = pd.read_excel(file_path)
# df = data.copy()

# Define the Google Sheets URL
sheet_url = "https://docs.google.com/spreadsheets/d/1Vi5VQWt9AD8nKbO78FpQdm6TrfRmg0o7az77Hku2i7Y/edit#gid=78776635"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

encoded_key = os.getenv("GOOGLE_CREDENTIALS")

if encoded_key:
    json_key = json.loads(base64.b64decode(encoded_key).decode("utf-8"))
    creds = Credentials.from_service_account_info(json_key, scopes=scope)
else:
    creds_path = r"C:\Users\CxLos\OneDrive\Documents\BMHC\Data\bmhc-timesheet-4808d1347240.json"
    if os.path.exists(creds_path):
        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
    else:
        raise FileNotFoundError("Service account JSON file not found and GOOGLE_CREDENTIALS is not set.")

# Authorize and load the sheet
client = gspread.authorize(creds)
sheet = client.open_by_url(sheet_url)
data = pd.DataFrame(client.open_by_url(sheet_url).sheet1.get_all_records())
df = data.copy()
# Trim leading and trailing whitespaces from column names
df.columns = df.columns.str.strip()

# Get the reporting month:
report_month = datetime(2025, 12, 1).strftime("%B")
report_year = datetime(2025, 12, 1).year
int_month = 12

# Filtered df where 'Date of Activity:' is in October
df["Date of Activity"] = pd.to_datetime(df["Date of Activity"], errors='coerce')
# df["Date of Activity"] = df["Date of Activity"].dt.tz_localize('UTC')  # or local timezone first, then convert to UTC
df = df[(df['Date of Activity'].dt.month == int_month) & (df['Date of Activity'].dt.year == report_year)]  # type: ignore
# Sort df from oldest to newest
df = df.sort_values(by='Date of Activity', ascending=True)

# Strip whitespace
df.columns = df.columns.str.strip()

# Strip whitespace from string entries in the whole DataFrame
for col in df.select_dtypes(include='object').columns:
    df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

# df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

# Create Full Name column
df['Full Name'] = df["Individual's First Name:"].astype(str) + " " + df["Individual's Last Name:"].astype(str)

# Define a discrete color sequence
# color_sequence = px.colors.qualitative.Plotly

# -----------------------------------------------
# print(df.head(15))
# print('Total entries: ', len(df))
# print('Column Names: \n', df.columns.tolist())
# print('Column Names: \n', df1.columns)
# print('DF Shape:', df.shape)
# print('Dtypes: \n', df.dtypes)
# print('Info:', df.info())
# print("Amount of duplicate rows:", df.duplicated().sum())

# print('Current Directory:', current_dir)
# print('Script Directory:', script_dir)
# print('Path to data:',file_path)

# ================================= Columns Navigation ================================= #

columns = [
    'Timestamp', 
    'Date of Activity', 
    'Person submitting this form:', 
    'Activity Duration (minutes):', 
    'Location Encountered:',
    "Individual's First Name:", 
    "Individual's Last Name:"
    "Individual's Date of Birth:", 
    "Individual's Insurance Status:", 
    "Individual's street address:", 
    'City:', 
    'ZIP Code:', 
    'County:', 
    'Type of support given:', 
    'Provide brief support description:', 
    "Individual's Status:", 
    'HMIS SPID Number:', 
    'MAP Card Number', 
    'Gender:', 
    'Race/Ethnicity:',
    'Total travel time (minutes):', 
    'Direct Client Assistance Amount:', 
    'Column 21', 
  ]

# ============================== Data Preprocessing ========================== #

# # Fill missing values for numerical columns with a specific value (e.g., -1)
df['HMIS SPID Number:'] = df['HMIS SPID Number:'].fillna(-1)
df['MAP Card Number'] = df['MAP Card Number'].fillna(-1)

df.rename(
    columns={
        "Activity Duration (minutes):" : "Activity Duration",
        "Total travel time (minutes):" : "Travel",
        "Person submitting this form:" : "Person",
        "Location Encountered:" : "Location",
        "Individual's Insurance Status:" : "Insurance",
        "Individual's Status:" : "Status",
        "Type of Coordination/Navigation Provided:" : "Support",
        "Gender:" : "Gender",
        "Race / Ethnicity:" : "Ethnicity",
        "Provide brief support description:" : "Description",
        "Housing Status" : "Housing",
        "Income Level" : "Income",
        # "" : "",
    }, 
inplace=True)

# Search for all duplicates in dataset:
duplicates = df[df.duplicated(keep=False)]
# print("Duplicate entries in dataset:\n", duplicates)

# Find duplicate rows where both first and last names match:
duplicate_rows = df[df.duplicated(subset=["Individual's First Name:", "Individual's Last Name:"], keep=False)][["Individual's First Name:", "Individual's Last Name:", 'Date of Activity']].sort_values(["Individual's Last Name:", "Individual's First Name:"])
# print("Duplicate name entries:\n", duplicate_rows)

# Show duplicate names with their counts
duplicate_counts = df[df.duplicated(subset=["Individual's First Name:", "Individual's Last Name:"], keep=False)].groupby(["Individual's First Name:", "Individual's Last Name:"]).size().reset_index(name='Count').sort_values('Count', ascending=False)
# print("Duplicate name counts:\n", duplicate_counts)

# ========================== SPREADSHEET COMPARISON ========================== #

# Load second spreadsheet for comparison
sheet_url_2 = "https://docs.google.com/spreadsheets/d/1GWnQrLptjkgg8CR1G8OpYaCHZMmW5xOzg0kFtPCkxKw/edit?gid=34671814#gid=34671814"
sheet_2 = client.open_by_url(sheet_url_2)
worksheet_2 = sheet_2.worksheet(f"{report_month}")
data_2 = pd.DataFrame(worksheet_2.get_all_records())
df_2 = data_2.copy()
df_2.columns = df_2.columns.str.strip()

# Find records in df_2 that are NOT in df
missing_in_main = df_2[~df_2['seeker_name'].isin(df['Full Name'])][["seeker_name", 'created_at']].sort_values(['seeker_name', 'created_at'])
# print(f"\nRecords in FH NOT in Navigation ({len(missing_in_main)}):\n", missing_in_main)

# Find records in df that are NOT in df_2
missing_in_comparison = df[~df['Full Name'].isin(df_2['seeker_name'])][['Full Name', 'Date of Activity', 'Person']].sort_values(['Full Name', 'Date of Activity'])
# print(f"\nRecords in Navigation NOT in Findhelp ({len(missing_in_comparison)}):\n", missing_in_comparison)

# ------------------------------- Clients Serviced ---------------------------- #

# # Clients Serviced:
clients_served = len(df)
clients_served = str(clients_served)
# print('Patients Served This Month:', clients_served)

# ------------------------------ Navigation Hours ---------------------------- #

# print("Activity Duration Unique: \n", df['Activity Duration'].unique().tolist())

# # Groupby Activity Duration:
df_duration = df['Activity Duration'].sum()/60
df_duration = round(df_duration) 
# # print('Activity Duration:', df_duration/60, 'hours')

# ------------------------------ Travel Time ---------------------------- #

# 0     124
# 60      3
# 30      3
# 45      1

# print('Travel time unique values:', df['Total travel time (minutes):'].unique())
# print(df['Total travel time (minutes):'].value_counts())

# Clean and replace invalid values
df['Travel'] = (
    df['Travel']
    .astype(str)
    .str.strip()
    .replace({'The Bumgalows': '0'})
)

# Convert to float
df['Travel'] = pd.to_numeric(df['Travel'], errors='coerce')

# Fill NaNs with 0
df['Travel'] = df['Travel'].fillna(0)

# Calculate total travel time in hours
travel_time = round(df['Travel'].sum() / 60)

# print('Travel Time dtype:', df['Total travel time (minutes):'].dtype)
# print('Total Travel Time:', travel_time)

# ------------------------------- Race Graphs ---------------------------- #

df['Ethnicity'] = (
    df['Ethnicity']
        .astype(str)
        .str.strip()
        .replace({
            "Hispanic/Latino": "Hispanic/ Latino", 
            "White": "White/ European Ancestry", 
            "White/ European Ancestry": "White / Caucasian", 
            "Group search": "N/A", 
            "Group search": "N/A", 
        })
)

# Groupby Race/Ethnicity:
df_race = df['Ethnicity'].value_counts().reset_index(name='Count')

# Race Bar Chart
race_bar=px.bar(
    df_race,
    x='Ethnicity',
    y='Count',
    color='Ethnicity',
    text='Count',
).update_layout(
    title=dict(
        text='Race Distribution Bar Chart',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=-20,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        showticklabels=False,  # Hide x-tick labels
        title=dict(
            # text=None,
            text="Race/ Ethnicity",
            font=dict(size=16),  # Font size for the title
        ),
    ),
    yaxis=dict(
        title=dict(
            text='Count',
            font=dict(size=16),  # Font size for the title
        ),
    ),
    legend=dict(
        title='',
        orientation="v",  # Vertical legend
        x=1.05,  # Position legend to the right
        y=1,  # Position legend at the top
        xanchor="left",  # Anchor legend to the left
        yanchor="top",  # Anchor legend to the top
        # visible=False,
        visible=True,
    ),
    hovermode='closest', # Display only one hover label per trace
    bargap=0.07,  # Reduce the space between bars
    bargroupgap=0,  # Reduce space between individual bars in groups
).update_traces(
    textposition='auto',
    hovertemplate='<b>Race:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>'
)

# Race Pie Chart
race_pie=px.pie(
    df_race,
    names='Ethnicity',
    values='Count'
).update_layout(
    title=dict(
        text='Race Distribution Ratio',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    # textinfo='value+percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label}</b>: %{value}<extra></extra>'
)

# ------------------------------- Gender Distribution ---------------------------- #

# print("Gender Unique Before:", df['Gender'].unique().tolist())

gender_unique =[
    'Male', 
    'Transgender', 
    'Female', 
    'Group search ', 
    'Prefer Not to Say'
]

# print("Gender Value Counts Before: \n", df_gender)

df['Gender'] = (
    df['Gender']
        .astype(str)
            .str.strip()
            .replace({
                "Group search": "N/A", 
            })
)

# Groupby 'Gender:'
df_gender = df['Gender'].value_counts().reset_index(name='Count')

# print("Gender Unique After:", df['Gender'].unique().tolist())
# print("Gender Value Counts After: \n", df_gender)

# Gender Bar Chart
gender_bar=px.bar(
    df_gender,
    x='Gender',
    y='Count',
    color='Gender',
    text='Count',
).update_layout(
    title=dict(
        text='Sex Distribution Bar Chart',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=0,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        title=dict(
            # text=None,
            text="Gender",
            font=dict(size=16),  # Font size for the title
        ),
    ),
    yaxis=dict(
        title=dict(
            text='Count',
            font=dict(size=16),  # Font size for the title
        ),
    ),
    legend=dict(
        title='',
        orientation="v",  # Vertical legend
        x=1.05,  # Position legend to the right
        y=1,  # Position legend at the top
        xanchor="left",  # Anchor legend to the left
        yanchor="top",  # Anchor legend to the top
        visible=False
        
    ),
    hovermode='closest', # Display only one hover label per trace
    bargap=0.07,  # Reduce the space between bars
    bargroupgap=0,  # Reduce space between individual bars in groups
).update_traces(
    textposition='auto',
    hovertemplate='<b>Gender</b>: %{label}<br><b>Count</b>: %{y}<extra></extra>'
)

# Gender Pie Chart
gender_pie=px.pie(
    df,
    names='Gender'
).update_layout(
    title=dict(
        text='Ratio of Patient Visits by Sex',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    # textinfo='value+percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label} Visits</b>: %{value}<extra></extra>'
)

# ------------------------------- Age Distribution ---------------------------- #

# # Fill missing values for 'Birthdate' with random dates within a specified range
def random_date(start, end):
    return start + timedelta(days=np.random.randint(0, (end - start).days))

# # Define the date range for random dates
start_date = datetime(1950, 1, 1)
end_date = datetime(2000, 12, 31)

# # Convert 'Individual's Date of Birth:' to datetime, coercing errors to NaT
df['Individual\'s Date of Birth:'] = pd.to_datetime(df['Individual\'s Date of Birth:'], errors='coerce')

# # Fill missing values in 'Individual's Date of Birth:' with random dates
df['Individual\'s Date of Birth:'] = df['Individual\'s Date of Birth:'].apply(
    lambda x: random_date(start_date, end_date) if pd.isna(x) else x
)

# # Calculate 'Client Age' by subtracting the birth year from the current year
df['Client Age'] = pd.to_datetime('today').year - df['Individual\'s Date of Birth:'].dt.year

# # Handle NaT values in 'Client Age' if necessary (e.g., fill with a default value or drop rows)
df['Client Age'] = df['Client Age'].apply(lambda x: "N/A" if x < 0 else x)

# # Define a function to categorize ages into age groups
def categorize_age(age):
    if age == "N/A":
        return "N/A"
    elif 10 <= age <= 19:
        return '10-19'
    elif 20 <= age <= 29:
        return '20-29'
    elif 30 <= age <= 39:
        return '30-39'
    elif 40 <= age <= 49:
        return '40-49'
    elif 50 <= age <= 59:
        return '50-59'
    elif 60 <= age <= 69:
        return '60-69'
    elif 70 <= age <= 79:
        return '70-79'
    else:
        return '80+'

# # Apply the function to create the 'Age_Group' column
df['Age_Group'] = df['Client Age'].apply(categorize_age)

# # Group by 'Age_Group' and count the number of patient visits
df_decades = df.groupby('Age_Group',  observed=True).size().reset_index(name='Patient_Visits')

# # Sort the result by the minimum age in each group
age_order = [
            '10-19',
             '20-29', 
             '30-39', 
             '40-49', 
             '50-59', 
             '60-69', 
             '70-79',
             '80+'
             ]

df_decades['Age_Group'] = pd.Categorical(df_decades['Age_Group'], categories=age_order, ordered=True)
df_decades = df_decades.sort_values('Age_Group')
# print(df_decades.value_counts())

# Age Bar Chart
age_bar=px.bar(
    df_decades,
    x='Age_Group',
    y='Patient_Visits',
    color='Age_Group',
    text='Patient_Visits',
).update_layout(
    title=dict(
        text='Client Age Distribution',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=0,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        title=dict(
            # text=None,
            text="Age Group",
            font=dict(size=16),  # Font size for the title
        ),
    ),
    yaxis=dict(
        title=dict(
            text='Number of Visits',
            font=dict(size=16),  # Font size for the title
        ),
    ),
    legend=dict(
        title_text='',
        orientation="v",  # Vertical legend
        x=1.05,  # Position legend to the right
        y=1,  # Position legend at the top
        xanchor="left",  # Anchor legend to the left
        yanchor="top",  # Anchor legend to the top
        visible=False
    ),
    hovermode='closest', # Display only one hover label per trace
    bargap=0.08,  # Reduce the space between bars
    bargroupgap=0,  # Reduce space between individual bars in groups
).update_traces(
    textposition='auto',
    hovertemplate='<b>Age:</b>: %{label}<br><b>Count</b>: %{y}<extra></extra>'
)

# Pie chart showing values and percentages:

# # Age Pie Chart
age_pie = px.pie(
    df_decades,
    names='Age_Group',
    values='Patient_Visits',
).update_layout(
    title=dict(
        text='Ratio of Client Age Distribution',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    rotation=190,
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label}</b>: %{value}<extra></extra>'
)

# ------------------------------- Insurance Status ------------------------- #

# print("Insurance Unique Before:", df["Insurance"].unique().tolist())

insurance_unique = [
    '',
    'Private Insurance', 
    'MAP',
    'None',
    'Unknown', 
    'MAP 100', 
    '30 Day 100', 
    'NAPHCARE', 
    'MAP Basic', 
    'Medicare', 
    'Just got it!!!', 
    'Medicaid', 
    '30 DAY 100'
]

df["Insurance"] = (
    df["Insurance"]
    .str.strip()
    .replace({
        '': 'Unknown',
        'unknown': 'Unknown',
        'Just got it!!!': 'Private Insurance',
        'Medicare': 'Medicaid',
        'NONE': 'None',
        'Map 000': 'MAP 100',
        '30 Day 100': '30 DAY 100',
        '30 DAY100': '30 DAY 100',
        '30DAY 100': '30 DAY 100',
    })
)

# print("Insurance Unique After:", df["Insurance"].unique().tolist())

df_insurance = df.groupby("Insurance").size().reset_index(name='Count')
# # print(df["Individual's Insurance Status:"].value_counts())

# Insurance Status Bar Chart
insurance_bar=px.bar(
    df_insurance,
    x="Insurance",
    y='Count',
    color="Insurance",
    text='Count',
).update_layout(
    title=dict(
        text='Insurance Status Bar Chart',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=-20, 
        tickfont=dict(size=16),  
        showticklabels=False,  
        # showticklabels=True,  
        title=dict(
            # text=None,
            text="Insurance",
            font=dict(size=16),  
        ),
    ),
    yaxis=dict(
        title=dict(
            text='Count',
            font=dict(size=16),  
        ),
    ),
    legend=dict(
        title='Insurance',
        orientation="v",  # Vertical legend
        x=1.05,  # Position legend to the right
        y=1,  # Position legend at the top
        xanchor="left",  # Anchor legend to the left
        yanchor="top",  # Anchor legend to the top
        # visible=False,
        visible=True,
    ),
    hovermode='closest', # Display only one hover label per trace
    bargap=0.08,  # Reduce the space between bars
    bargroupgap=0,  # Reduce space between individual bars in groups
).update_traces(
    textposition='auto',
    hovertemplate='<b>Insurance:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>'
)

# Insurance Status Pie Chart
insurance_pie=px.pie(
    df_insurance,
    names="Insurance",
    values='Count'
).update_layout(
    title=dict(
        text='Insurance Status Ratio',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    rotation=100,
    # textinfo='value+percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label}</b>: %{value}<extra></extra>'
)

# ------------------------------ Location Encountered --------------------------------- #

# Unique Values:
# print("Locations Unique Before \n:", df['Location'].unique().tolist())

locations_unique = [
"Black Men's Health Clinic", 'Extended Stay America', 'Bungalows', 'Phone call', 'via zoom', 'Cenikor Austin', 'Terrazas Branch Library', 'Cross Creek Hospital', 'Sunrise Navigation Homeless Center', 'Nice project riverside and Montopolis', 'Phone call and visit to 290/35 area where unhoused', 'social security office and DPS (NORTH LAMAR)', 'DPS Meeting (pflugerville locations)', 'GudLife', 'Community First Village', 'Downtown Austin Community Court', 'Trinity Center'
]

location_categories = [
    "Austin Transitional Center",
    "Black Men's Health Clinic",
    "Bungalows",
    "Community First Village",
    "Cross Creek Hospital",
    "Downtown Austin Community Court",
    "Event",
    "Extended Stay America",
    "GudLife",
    "Housing Authority of Travis County",
    "Integral Care - St. John",
    "Kensington",
    "Phone Call",
    "South Bridge",
    "Sunrise Navigation Homeless Center",
    "Terrazas Public Library"
]


df['Location'] = (
    df['Location']
    .str.strip()
    .replace({
        "" : "No Location",
        
        # Terrazas Public Library
        "Terrazas Branch Library": "Terrazas Public Library",
        "Terrezas public Library" : "Terrazas Public Library",
        "Terreaz Public Library" : "Terrazas Public Library",
        
        # Phone
        "Phone call" : "Phone Call",
        "via zoom": "Phone Call",
        "Phone appt" : "Phone Call",
        "over the phone" : "Phone Call",
        "over phone" : "Phone Call",
        "Phone call and visit to 290/35 area where unhoused": "Phone Call",
        
        # Integral Care
        "phone call/Integral care St John location" : "Integral Care - St. John",
        "integral Care- St. John Location" : "Integral Care - St. John",
        
        # Austin Transitional Center
        "Austin transitional Center" : "Austin Transitional Center",
        "Austin Transistional Center" : "Austin Transitional Center",
        "Austin Transitional center" : "Austin Transitional Center",
        "ATC" : "Austin Transitional Center",
        
        # Extended Stay America
        "EXTENDED STAY AMERICA" : "Extended Stay America",
        
        # Capital Villas (not in category list)
        "capital villas apartments" : "Capital Villas Apartments",
        
        # Social Security Office & DPS (not in allowed categories, could be grouped or ignored)
        'ICare and social security office' : "Social Security Office",
        'Social Security office' : "Social Security Office",
        'social security office and DPS (NORTH LAMAR)': "Social Security Office",
        'DPS Meeting (pflugerville locations)': "Social Security Office",
        
        # South Bridge
        "met client at southbridge to complete check in and discussed what options we had for us to be able to obtain missing vital docs" : "South Bridge",
        
        # Encampment Area
        "picking client up from encampment, vital statics appointment and walk in at social security office, then returning client back to encampment area" : "Encampment Area",

        # Other unclear entries
        "Nice project riverside and Montopolis": "Event",
    })
)

location_unexpected = df[~df['Location'].isin(location_categories)]
# print("Location Unexpected: \n", location_unexpected['Location'].unique().tolist())

df_location = df['Location'].value_counts().reset_index(name='Count')
# # print(df['Location Encountered:'].value_counts())

# Location Bar Chart
location_bar=px.bar(
    df_location,
    x="Location",
    y='Count',
    color="Location",
    text='Count',
).update_layout(
    title=dict(
        text='Outreach/ Locations Encountered',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=-20,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        title=dict(
            # text=None,
            text="Location",
            font=dict(size=16),  # Font size for the title
        ),
        # showticklabels=True 
        showticklabels=False  # Hide x-tick labels
    ),
    yaxis=dict(
        title=dict(
            text='Count',
            font=dict(size=16),  # Font size for the title
        ),
    ),
    legend=dict(
        title='',
        orientation="v",  # Vertical legend
        x=1.05,  # Position legend to the right
        y=1,  # Position legend at the top
        xanchor="left",  # Anchor legend to the left
        yanchor="top",  # Anchor legend to the top
        # visible=False
    ),
    hovermode='closest', # Display only one hover label per trace
    bargap=0.08,  # Reduce the space between bars
    bargroupgap=0,  # Reduce space between individual bars in groups
).update_traces(
    textposition=None,
    # textposition='auto',
    hovertemplate='<b>Insurance:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>'
)

# Location Pie Chart
location_pie=px.pie(
    df_location,
    names="Location",
    values='Count'
).update_layout(
    title=dict(
        text='Ratio of Outreach/ Locations Encountered',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    rotation=50,
    # textinfo='percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label}</b>: %{value}<extra></extra>'
)

# ------------------------------- Type of Support Given ---------------------------- #

# print("Support Unique Before: \n", df["Support"].unique().tolist())
# print("Support Value counts: \n", df["Support"].value_counts())

support_unique = [
'Primary Care (dental, vision, physicals, chronic care visits, etc.)', 'Enrollment Assistance (MAP, Medicaid, SNAP, Medicare, insurance, etc.)', 'Behavioral Health (therapy, counseling, psych services, crisis support, etc.), Primary Care (dental, vision, physicals, chronic care visits, etc.)', 'Enrollment Assistance (MAP, Medicaid, SNAP, Medicare, insurance, etc.), Primary Care (dental, vision, physicals, chronic care visits, etc.)', 'Prescription Coverage', 'Population Health Education (cancer related awareness, screenings, prevention info, etc.)', 'Behavioral Health (therapy, counseling, psych services, crisis support, etc.)', 'Social Services (housing, food, utilities, clothing, transportation, etc.)', 'Behavioral Health (therapy, counseling, psych services, crisis support, etc.), Housing and other services for her and her autistic son', 'Behavioral Health (therapy, counseling, psych services, crisis support, etc.), Primary Care (dental, vision, physicals, chronic care visits, etc.), Social Services (housing, food, utilities, clothing, transportation, etc.)', 'Coordinated Assessments (needs assessments, screenings, intake forms, etc.)'
]

support_categories = [
    "Behavioral Health (therapy, counseling, psych services, crisis support, etc.)",
    "Community-Based Preventive Wellness (Movement Is Medicine, fitness programs, health classes, etc.)",
    "Coordinated Assessments (needs assessments, screenings, intake forms, etc.)",
    "Enrollment Assistance (MAP, Medicaid, SNAP, Medicare, insurance, etc.)",
    "Emergency Department (ER follow-up, discharge help, post-ER coordination, etc.)",
    "Nutrition & Cultural Health Education (healthy eating, food demos, SFC programs, etc.)",
    "Pediatrics (child related exams, immunizations, sick visits, wellness visits, etc.)",
    "Permanent Support Housing (PSH related referrals, housing applications, long-term housing programs, etc.)",
    "Population Health Education (cancer related awareness, screenings, prevention info, etc.)",
    "Primary Care (dental, vision, physicals, chronic care visits, etc.)",
    "SOAR (SSI/SSDI related disability paperwork, documentation support, etc.)",
    "Social Services (housing, food, utilities, clothing, transportation, etc.)",
    "Specialty Care (cardiology, dermatology, GI, orthopedics, etc.)",
    "Substance Use Treatment (detox, rehab, MAT programs, recovery support, etc.)",
    "Urgent Care (same-day visits for sudden illness or minor injury that cannot wait for a scheduled appointment, etc.)",
    "Women's Health (OB-GYN, mammograms, well-woman exams, prenatal care, etc.)"
]

support_categories_clean = [
    "Behavioral Health",
    "Community-Based Preventive Wellness",
    "Coordinated Assessments",
    "Enrollment Assistance",
    "Emergency Department",
    "Nutrition & Cultural Health Education",
    "Pediatrics",
    "Permanent Support Housing",
    "Population Health Education",
    "Primary Care",
    "SOAR",
    "Social Services",
    "Specialty Care",
    "Substance Use Treatment",
    "Urgent Care",
    "Women's Health"
]

# Create mapping dictionary for renaming support items
support_mapping = {
    "Behavioral Health (therapy, counseling, psych services, crisis support, etc.)": "Behavioral Health",
    "Community-Based Preventive Wellness (Movement Is Medicine, fitness programs, health classes, etc.)": "Community-Based Preventive Wellness",
    "Coordinated Assessments (needs assessments, screenings, intake forms, etc.)": "Coordinated Assessments",
    "Enrollment Assistance (MAP, Medicaid, SNAP, Medicare, insurance, etc.)": "Enrollment Assistance",
    "Emergency Department (ER follow-up, discharge help, post-ER coordination, etc.)": "Emergency Department",
    "Nutrition & Cultural Health Education (healthy eating, food demos, SFC programs, etc.)": "Nutrition & Cultural Health Education",
    "Pediatrics (child related exams, immunizations, sick visits, wellness visits, etc.)": "Pediatrics",
    "Permanent Support Housing (PSH related referrals, housing applications, long-term housing programs, etc.)": "Permanent Support Housing",
    "Population Health Education (cancer related awareness, screenings, prevention info, etc.)": "Population Health Education",
    "Primary Care (dental, vision, physicals, chronic care visits, etc.)": "Primary Care",
    "SOAR (SSI/SSDI related disability paperwork, documentation support, etc.)": "SOAR",
    "Social Services (housing, food, utilities, clothing, transportation, etc.)": "Social Services",
    "Specialty Care (cardiology, dermatology, GI, orthopedics, etc.)": "Specialty Care",
    "Substance Use Treatment (detox, rehab, MAT programs, recovery support, etc.)": "Substance Use Treatment",
    "Urgent Care (same-day visits for sudden illness or minor injury that cannot wait for a scheduled appointment, etc.)": "Urgent Care",
    "Women's Health (OB-GYN, mammograms, well-woman exams, prenatal care, etc.)": "Women's Health",
    "MAP Application": "Enrollment Assistance",
    "Primary Care Appointment": "Primary Care",
    "Behavioral Health Appointment": "Behavioral Health",
    "Primary Care Referral": "Primary Care",
    "Specialty Care Referral": "Specialty Care",
    "Behavioral Health Referral": "Behavioral Health",
    "Social Determinant of Health Referral": "Social Services",
    "Dental": "Primary Care",
    "Specialty Care": "Specialty Care",
    "Prescription Coverage": "Enrollment Assistance",
    "Vision Appointment": "Primary Care",
    "Set up Financial Screening": "Enrollment Assistance",
    "Set an appointment for Financial Screening": "Enrollment Assistance",
    "SSI": "SOAR",
    "Dental and Mental": "Primary Care",
    "Housing and other services for her and her autistic son": "Permanent Support Housing",
    "Social Determinant of Health Referral,": "Social Services",
    "homeless resources": "Social Services",
    "coordinated assessment with Sunrise": "Coordinated Assessments",
    "Food bank": "Social Services",
    "Re-Entry": "Social Services"
}

# Counter to count all support types mentioned
counter = Counter()

# Around line 897, modify the splitting logic:

for entry in df['Support']:
    standardized_entry = str(entry).replace(' but', ', ')
    items = [i.strip() for i in re.split(pattern, standardized_entry) if i.strip()]
    for item in items:
        # Apply mapping first
        item = support_mapping.get(item, item)
        # Strip parenthetical descriptions - keep only text before the opening parenthesis
        clean_item = re.sub(r'\s*\(.*?\)\s*', '', item).strip()
        if clean_item:  # Only count if there's content after stripping
            counter[clean_item] += 1

# Create DataFrame from counter
df_support = pd.DataFrame(counter.items(), columns=['Support', 'Count']).sort_values(by='Count', ascending=False)

# print("Support Value counts After Split: \n", df_support)

df['Support'] = (
    df['Support']
        .astype(str)
            .str.strip()
            .replace({
                "" : "",
            })
    )

support_bar=px.bar(
    df_support,
    x='Support',
    y='Count',
    color='Support',
    text='Count',
).update_layout(
    title=dict(
        text='Type of Coordination Provided',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=0,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        title=dict(
            # text=None,
            text="Type of Coordination",
            font=dict(size=16),  # Font size for the title
        ),
        showticklabels=False  # Hide x-tick labels
    ),
    yaxis=dict(
        title=dict(
            text='Count',
            font=dict(size=16),  # Font size for the title
        ),
    ),
    legend=dict(
        # title='Support',
        title_text='',
        orientation="v",  # Vertical legend
        x=1.05,  # Position legend to the right
        y=1,  # Position legend at the top
        xanchor="left",  # Anchor legend to the left
        yanchor="top",  # Anchor legend to the top
        visible=True
    ),
    hovermode='closest', # Display only one hover label per trace
    bargap=0.08,  # Reduce the space between bars
    bargroupgap=0,  # Reduce space between individual bars in groups
).update_traces(
    textposition='outside',
    hovertemplate='<b>Support:</b>: %{label}<br><b>Count</b>: %{y}<extra></extra>'
)

# Support Pie Chart
support_pie = px.pie(
    df_support,
    names='Support',
    values='Count',
).update_layout(
    title=dict(
        text='Ratio of Coordination Services Provided',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    rotation=90,
    # textinfo='value+percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label}</b>: %{value}<extra></extra>'
)

# ------------------------ Individuals' Status (New vs. Returning) --------------------- #

# # "Individual's Status:" dataframe:
df_status = df['Status'].value_counts().reset_index(name='Count')

# Status Bar Chart
status_bar=px.bar(
    df_status,
    x='Status',
    y='Count',
    color='Status',
    text='Count',
).update_layout(
    title=dict(
        text='New vs. Returning Clients',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=0,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        title=dict(
            # text=None,
            text="Status",
            font=dict(size=16),  # Font size for the title
        ),
        showticklabels=True  # Hide x-tick labels
    ),
    yaxis=dict(
        title=dict(
            text='Count',
            font=dict(size=16),  # Font size for the title
        ),
    ),
    legend=dict(
        # title='Support',
        title_text='',
        orientation="v",  # Vertical legend
        x=1.05,  # Position legend to the right
        y=1,  # Position legend at the top
        xanchor="left",  # Anchor legend to the left
        yanchor="top",  # Anchor legend to the top
        # visible=True
        visible=False
    ),
    hovermode='closest', # Display only one hover label per trace
    bargap=0.08,  # Reduce the space between bars
    bargroupgap=0,  # Reduce space between individual bars in groups
).update_traces(
    textposition='auto',
    hovertemplate='<b>Status:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>'
)

# Status Pie Chart
status_pie=px.pie(
    df_status,
    names="Status",
    values='Count'  # Specify the values parameter
).update_layout(
    title=dict(
        text='Ratio of New vs. Returning',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    rotation=-90,
    # textinfo='value+percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label} Status</b>: %{value}<extra></extra>',
)

# ----------------------- Housing Status ------------------------ #

df['Housing'] = (
    df['Housing']
    .str.strip()
    .replace({
        "" : "N/A",
    })
)

df_housing = df['Housing'].value_counts().reset_index(name='Count')
# print("", df_housing)

# Housing Bar Chart
housing_bar=px.bar(
    df_housing,
    x='Housing',
    y='Count',
    color='Housing',
    text='Count',
).update_layout(
    title=dict(
        text='Housing Status Distribution',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=0,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        showticklabels=False,  # Hide x-tick labels
        title=dict(
            text=None,
            # text="Housing",
        ),
    ),
    yaxis=dict(
        title=dict(
            text=None
        )
    ),
    legend=dict(
        title=''
    ),
    bargap=0.08,
    showlegend=True,
)

# Housing Pie Chart
housing_pie=px.pie(
    df_housing,
    names='Housing',
    values='Count',
    # title='Race/Ethnicity'
    title='Ratio of Housing Status',
).update_layout(
    title=dict(
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    rotation=-90,
    # textinfo='value+percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label} Housing</b>: %{value}<extra></extra>',
)

# ----------------------- Income Level ------------------------ #

# print("Income Unique Before:", df['Income'].unique())

df['Income'] = (
    df['Income']
    .str.strip()
    .replace({
        0 : "N/A",
        "$0" : "N/A",
        "" : "N/A",
        "Unknown" : "N/A",
        "unknown" : "N/A",
        "?" : "N/A",
    })
)

# "Income Level" dataframe:
df_income = df['Income'].value_counts().reset_index(name='Count')
# print("Income Value Counts:", df_income)

# Income Bar Chart
income_bar=px.bar(
    df_income,
    x='Income',
    y='Count',
    color='Income',
    text='Count',
).update_layout(
    title=dict(
        text='Income Level Distribution',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=0,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        showticklabels=False,  # Hide x-tick labels
        title=dict(
            text=None,
            # text="Income Level",
        ),
    ),
    yaxis=dict(
        title=dict(
            text=None
        )
    ),
    legend=dict(
        title=''
    ),
    bargap=0.08,
    showlegend=True,
)

# Income Pie Chart
income_pie=px.pie(
    df_income,
    names='Income',
    values='Count',
    # title='Race/Ethnicity'
    title='Ratio of Income Level',
).update_layout(
    title=dict(
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    rotation=-90,
    # textinfo='value+percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label} Income</b>: %{value}<extra></extra>',
)

# ----------------------- Person Filling Out This Form ------------------------ #

# print("Person Unique Before: \n", df["Person"].unique().tolist())

person_unique = [
    'Dominique Street',
    'Dr Larry Wallace Jr',
    'Eric Roberts',
    'Eric roberts',
    'EricRoberts',
    'Jaqueline Oviedo',
    'Kimberly Holiday',
    'Larry Wallace Jr',
    'Michael Lambert',
    'Michael Lambert ',
    'Rishit Yokananth',
    'Sonya Hosey',
    'Toya Craney',
    'Tramisha Pete',
    'Viviana Varela',
]

df['Person'] = (
    df['Person']
    .str.strip()
    .replace({
        'Dominique': 'Dominique Street',
        'Jaqueline Ovieod': 'Jaqueline Oviedo',
        'Eric roberts': 'Eric Roberts',
        'EricRoberts': 'Eric Roberts',
        'Dr Larry Wallace Jr': 'Larry Wallace Jr',
        'Sonya': 'Sonya Hosey',
        })
    )

counter = Counter()

for entry in df['Person']:
    items = [i.strip() for i in str(entry).split(",")]
    for item in items:
        if item:  # Only count non-empty items
            counter[item] += 1

df_person = pd.DataFrame(counter.items(), columns=['Person', 'Count']).sort_values(by='Count', ascending=False)

# # Groupby Person submitting this form:
# df_person = df['Person'].value_counts().reset_index(name='Count')
# print('Person Submitting: \n', person_submitting)

# Person Submitting Bar Chart
person_bar=px.bar(
    df_person,
    x='Person',
    y='Count',
    color='Person',
    text='Count',
).update_layout(
    title=dict(
        text='People Submitting Forms',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
            )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    xaxis=dict(
        tickangle=0,  # Rotate x-axis labels for better readability
        tickfont=dict(size=16),  # Adjust font size for the tick labels
        title=dict(
            # text=None,
            text="Name",
            font=dict(size=16),  # Font size for the title
        ),
        showticklabels=False  # Hide x-tick labels
    ),
    yaxis=dict(
        title=dict(
            text='Count',
            font=dict(size=16),  # Font size for the title
        ),
    ),
    legend=dict(
        # title='Support',
        title_text='',
        orientation="v",  # Vertical legend
        x=1.05,  # Position legend to the right
        y=1,  # Position legend at the top
        xanchor="left",  # Anchor legend to the left
        yanchor="top",  # Anchor legend to the top
        # visible=False
        visible=True
    ),
    hovermode='closest', # Display only one hover label per trace
    bargap=0.08,  # Reduce the space between bars
    bargroupgap=0,  # Reduce space between individual bars in groups
).update_traces(
    textposition='outside',
    hovertemplate='<b>Name:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>'
)

# Person Submitting Pie Chart
person_pie=px.pie(
    df_person,
    names="Person",
    values='Count'  # Specify the values parameter
).update_layout(
    title=dict(
        text='Ratio of People Submitting Forms',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    )
).update_traces(
    rotation=140,
    # textinfo='value+percent',
    texttemplate='%{value}<br>(%{percent:.1%})',
    hovertemplate='<b>%{label} Status</b>: %{value}<extra></extra>',
)

# ---------------------- Zip 2 --------------------- #

# Clean and filter ZIP codes
df['ZIP2'] = df['ZIP Code:'].astype(str).str.strip()

# Define invalid/null values to exclude
invalid_zip_values = [
    'Texas', 'Unhoused', 'UNHOUSED', 'UnKnown', 'Unknown', 'uknown',
    'Unknown ', 'NA', 'nan', 'NaN', 'None', '5126364511', '', ' '
]

# Filter out invalid ZIP codes - only keep numeric values
valid_zip_mask = (
    df['ZIP2'].str.isnumeric() & 
    ~df['ZIP2'].isin(invalid_zip_values)
)

# Create filtered dataframe with only valid ZIP codes
df_zip_filtered = df[valid_zip_mask].copy()

# Create value count dataframe for the bar chart (only valid zips)
df_z = df_zip_filtered['ZIP2'].value_counts().reset_index(name='Count')
df_z.columns = ['ZIP2', 'Count']

df_z['Percentage'] = (df_z['Count'] / df_z['Count'].sum()) * 100
df_z['text_label'] = df_z['Count'].astype(str) + ' (' + df_z['Percentage'].round(1).astype(str) + '%)'

zip_fig =px.bar(
    df_z,
    x='Count',
    y='ZIP2',
    color='ZIP2',
    text='text_label',
    orientation='h'
).update_layout(
    title='Number of Clients by Zip Code',
    xaxis_title='Residents',
    yaxis_title='Zip Code',
    title_x=0.5,
    font=dict(
        family='Calibri',
        size=17,
        color='black'
    ),
    yaxis=dict(
        tickangle=0
    ),
    legend=dict(
        title='ZIP Code',
        orientation="v",
        x=1.05,
        xanchor="left",
        y=1,
        yanchor="top"
    ),
).update_traces(
    textposition='auto',
    textfont=dict(size=30),
    textangle=0,
    hovertemplate='<b>ZIP Code</b>: %{y}<br><b>Count</b>: %{x}<extra></extra>'
)

zip_pie = px.pie(
    df_z,
    names='ZIP2',
    values='Count',
    color_discrete_sequence=px.colors.qualitative.Safe
).update_layout(
    title=dict(
        text='Ratio of ZIP Code Distribution',
        x=0.5, 
        font=dict(
            size=21,
            family='Calibri',
            color='black',
        )
    ),
    font=dict(
        family='Calibri',
        size=16,
        color='black'
    ),
    legend_title='ZIP Code'
).update_traces(
    rotation=90,
    texttemplate='%{value}<br>(%{percent:.1%})',
    textfont_size=16,
    hovertemplate='<b>ZIP Code</b>: %{label}<br><b>Count</b>: %{value}<br><b>Percent</b>: %{percent}<extra></extra>'
)

# -----------------------------------------------------------------------------

# Get the distinct values in column

# distinct_service = df['What service did/did not complete?'].unique()
# print('Distinct:\n', distinct_service)

# =============================== Folium ========================== #

# empty_strings = df[df['ZIP Code:'].str.strip() == ""]
# # print("Empty strings: \n", empty_strings.iloc[:, 10:12])

# # Filter df to exclued all rows where there is no value for "ZIP Code:"
# df = df[df['ZIP Code:'].str.strip() != ""]

# mode_value = df['ZIP Code:'].mode()[0]
# df['ZIP Code:'] = df['ZIP Code:'].fillna(mode_value)

# # print("ZIP value counts:", df['ZIP Code:'].value_counts())
# # print("Zip Unique Before: \n", df['ZIP Code:'].unique().tolist())

# # Check for non-numeric values in the 'ZIP Code:' column
# # print("ZIP non-numeric values:", df[~df['ZIP Code:'].str.isnumeric()]['ZIP Code:'].unique())

# df['ZIP Code:'] = df['ZIP Code:'].astype(str).str.strip()

# df['ZIP Code:'] = (
#     df['ZIP Code:']
#     .astype(str).str.strip()
#         .replace({
#             'Texas': mode_value,
#             'Unhoused': mode_value,
#             'unknown': mode_value,
#             'Unknown': mode_value,
#             'UnKnown': mode_value,
#             'uknown': mode_value,
#             'NA': mode_value,
#             "": mode_value,
#             'nan': mode_value
# }))

# df['ZIP Code:'] = df['ZIP Code:'].where(df['ZIP Code:'].str.isdigit(), mode_value)
# df['ZIP Code:'] = df['ZIP Code:'].astype(int)

# df_zip = df['ZIP Code:'].value_counts().reset_index(name='Residents')
# # df_zip['ZIP Code:'] = df_zip['index'].astype(int)
# df_zip['Residents'] = df_zip['Residents'].astype(int)
# # df_zip.drop('index', axis=1, inplace=True)

# # print("Zip Unique After: \n", df['ZIP Code:'].unique().tolist())

# # print(df_zip.head())

# # Create a folium map
# m = folium.Map([30.2672, -97.7431], zoom_start=10)

# # Add different tile sets
# folium.TileLayer('OpenStreetMap', attr='© OpenStreetMap contributors').add_to(m)
# folium.TileLayer('Stamen Terrain', attr='Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL.').add_to(m)
# folium.TileLayer('Stamen Toner', attr='Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL.').add_to(m)
# folium.TileLayer('Stamen Watercolor', attr='Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL.').add_to(m)
# folium.TileLayer('CartoDB positron', attr='Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL.').add_to(m)
# folium.TileLayer('CartoDB dark_matter', attr='Map tiles by CartoDB, under CC BY 3.0. Data by OpenStreetMap, under ODbL.').add_to(m)

# # Available map styles
# map_styles = {
#     'OpenStreetMap': {
#         'tiles': 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
#         'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
#     },
#     'Stamen Terrain': {
#         'tiles': 'https://stamen-tiles.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg',
#         'attribution': 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under ODbL.'
#     },
#     'Stamen Toner': {
#         'tiles': 'https://stamen-tiles.a.ssl.fastly.net/toner/{z}/{x}/{y}.png',
#         'attribution': 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under ODbL.'
#     },
#     'Stamen Watercolor': {
#         'tiles': 'https://stamen-tiles.a.ssl.fastly.net/watercolor/{z}/{x}/{y}.jpg',
#         'attribution': 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under ODbL.'
#     },
#     'CartoDB positron': {
#         'tiles': 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
#         'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
#     },
#     'CartoDB dark_matter': {
#         'tiles': 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
#         'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
#     },
#     'ESRI Imagery': {
#         'tiles': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
#         'attribution': 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
#     }
# }

# # Add tile layers to the map
# for style, info in map_styles.items():
#     folium.TileLayer(tiles=info['tiles'], attr=info['attribution'], name=style).add_to(m)

# # Select a style
# # selected_style = 'OpenStreetMap'
# # selected_style = 'Stamen Terrain'
# # selected_style = 'Stamen Toner'
# # selected_style = 'Stamen Watercolor'
# selected_style = 'CartoDB positron'
# # selected_style = 'CartoDB dark_matter'
# # selected_style = 'ESRI Imagery'

# # Apply the selected style
# if selected_style in map_styles:
#     style_info = map_styles[selected_style]
#     # print(f"Selected style: {selected_style}")
#     folium.TileLayer(
#         tiles=style_info['tiles'],
#         attr=style_info['attribution'],
#         name=selected_style
#     ).add_to(m)
# else:
#     print(f"Selected style '{selected_style}' is not in the map styles dictionary.")
#      # Fallback to a default style
#     folium.TileLayer('OpenStreetMap').add_to(m)
    
# geolocator = Nominatim(user_agent="your_app_name", timeout=10)

# # Function to get coordinates from zip code
# # def get_coordinates(zip_code):
# #     geolocator = Nominatim(user_agent="response_q4_2024.py", timeout=10) # Add a timeout parameter to prevent long waits
# #     location = geolocator.geocode({"postalcode": zip_code, "country": "USA"})
# #     if location:
# #         return location.latitude, location.longitude
# #     else:
# #         print(f"Could not find coordinates for zip code: {zip_code}")
# #         return None, None
    
# def get_coordinates(zip_code):
#     for _ in range(3):  # Retry up to 3 times
#         try:
#             location = geolocator.geocode({"postalcode": zip_code, "country": "USA"})
#             if location:
#                 return location.latitude, location.longitude
#         except GeocoderTimedOut:
#             time.sleep(2)  # Wait before retrying
#     return None, None  # Return None if all retries fail

# # Apply function to dataframe to get coordinates
# df_zip['Latitude'], df_zip['Longitude'] = zip(*df_zip['ZIP Code:'].apply(get_coordinates))

# # Filter out rows with NaN coordinates
# df_zip = df_zip.dropna(subset=['Latitude', 'Longitude'])
# # print(df_zip.head())
# # print(df_zip[['Zip Code', 'Latitude', 'Longitude']].head())
# # print(df_zip.isnull().sum())

# # instantiate a feature group for the incidents in the dataframe
# incidents = folium.map.FeatureGroup()

# for index, row in df_zip.iterrows():
#     lat, lng = row['Latitude'], row['Longitude']

#     if pd.notna(lat) and pd.notna(lng):  
#         incidents.add_child(# Check if both latitude and longitude are not NaN
#         folium.vector_layers.CircleMarker(
#             location=[lat, lng],
#             radius=row['Residents'] * 1.2,  # Adjust the multiplication factor to scale the circle size as needed,
#             color='blue',
#             fill=True,
#             fill_color='blue',
#             fill_opacity=0.4
#         ))

# # add pop-up text to each marker on the map
# latitudes = list(df_zip['Latitude'])
# longitudes = list(df_zip['Longitude'])

# # labels = list(df_zip[['Zip Code', 'Residents_In_Zip_Code']])
# labels = df_zip.apply(lambda row: f"ZIP Code: {row['ZIP Code:']}, Patients: {row['Residents']}", axis=1)

# for lat, lng, label in zip(latitudes, longitudes, labels):
#     if pd.notna(lat) and pd.notna(lng):
#         folium.Marker([lat, lng], popup=label).add_to(m)
 
# formatter = "function(num) {return L.Util.formatNum(num, 5);};"
# mouse_position = MousePosition(
#     position='topright',
#     separator=' Long: ',
#     empty_string='NaN',
#     lng_first=False,
#     num_digits=20,
#     prefix='Lat:',
#     lat_formatter=formatter,
#     lng_formatter=formatter,
# )

# m.add_child(mouse_position)

# # add incidents to map
# m.add_child(incidents)

# map_path = 'zip_code_map.html'
# map_file = os.path.join(script_dir, map_path)
# m.save(map_file)
# map_html = open(map_file, 'r').read()

# ========================== DataFrame Table ========================== #

df = df.sort_values('Date of Activity', ascending=True)

# create a display index column and prepare table data/columns
# reset index to ensure contiguous numbering after any filtering/sorting upstream
df_indexed = df.reset_index(drop=True).copy()
# Insert '#' as the first column (1-based row numbers)
df_indexed.insert(0, '#', df_indexed.index + 1)

# Convert to records for DataTable
data = df_indexed.to_dict('records')
columns = [{"name": col, "id": col} for col in df_indexed.columns]

# -------------------------------------------------- #

# print("Locations: \n", df['Location'].unique().tolist())

def create_location_dataframes_with_support_tables(df, location_list):
    """
    Creates filtered dataframes for each location and support type tables with split logic
    
    Parameters:
    df: Main dataframe
    location_list: List of location names to filter by
    
    Returns:
    Dictionary with location dataframes, support tables, and all necessary variables for Dash
    """
    location_data = {}
    location_dataframes = {}  # Store DataFrames separately
    
    for location in location_list:
        # Create safe variable name
        safe_name = location.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        
        # Filter dataframe for this location
        df_location = df[df['Location'] == location]
        
        # Store DataFrame separately
        location_dataframes[safe_name] = df_location
        
        # Create support counts with SPLIT logic (like your September file)
        counter = Counter()
        
        for entry in df_location['Support']:
            # Split by comma and clean each item
            items = [i.strip() for i in str(entry).split(",") if i.strip()]
            for item in items:
                if item:  # Only count non-empty items
                    counter[item] += 1
        
        # Create DataFrame from counter
        df_support = pd.DataFrame(counter.items(), columns=['Type of Support', 'Count']).sort_values(by='Count', ascending=False)
        
        # Create indexed version for the table
        df_support_indexed = df_support.reset_index(drop=True).copy()
        df_support_indexed.insert(0, '#', df_support_indexed.index + 1)
        data_support = df_support_indexed.to_dict('records')
        columns_support = [{"name": col, "id": col} for col in df_support_indexed.columns]
        
        # Calculate sum of support counts instead of dataframe length
        support_count_sum = df_support['Count'].sum() if not df_support.empty else 0
        
        # Store only JSON-serializable data
        location_data[safe_name] = {
            'length': support_count_sum,  # Now this is the sum of support counts
            'original_name': location,
            'data_support': data_support,
            'columns_support': columns_support
        }
    
    return location_data, location_dataframes

# The rest of your code remains the same, but now:
# bmhc_len = sum of all support counts for Black Men's Health Clinic
# downtown_cc_len = sum of all support counts for Downtown Austin Community Court
# etc.

# This means your table titles will now show:
# "Black Men's Health Clinic Support Types (45)" - where 45 is the total count of all support types provided
# instead of showing the number of different support types or number of client visits

# Updated usage:
location_unique = [
    "Black Men's Health Clinic",
    'Downtown Austin Community Court', 
    'South Bridge',
    'Sunrise Navigation Homeless Center', 
    'Phone Call', 
    'Community First Village'
]

# Get both the JSON-serializable data and the DataFrames
location_results, location_dfs = create_location_dataframes_with_support_tables(df, location_unique)

# Extract individual dataframes from the separate dictionary
df_bmhc = location_dfs['black_mens_health_clinic']
df_downtown_cc = location_dfs['downtown_austin_community_court']
df_south_bridge = location_dfs['south_bridge']
df_sunrise = location_dfs['sunrise_navigation_homeless_center']
df_phone_call = location_dfs['phone_call']
df_community_first = location_dfs['community_first_village']

# Extract lengths for table titles
bmhc_len = location_results['black_mens_health_clinic']['length']
downtown_cc_len = location_results['downtown_austin_community_court']['length']
south_bridge_len = location_results['south_bridge']['length']
sunrise_len = location_results['sunrise_navigation_homeless_center']['length']
phone_call_len = location_results['phone_call']['length']
community_first_len = location_results['community_first_village']['length']

# Extract support table data for Dash tables
data_bmhc_support = location_results['black_mens_health_clinic']['data_support']
columns_bmhc_support = location_results['black_mens_health_clinic']['columns_support']

data_downtown_cc_support = location_results['downtown_austin_community_court']['data_support']
columns_downtown_cc_support = location_results['downtown_austin_community_court']['columns_support']

data_south_bridge_support = location_results['south_bridge']['data_support']
columns_south_bridge_support = location_results['south_bridge']['columns_support']

data_sunrise_support = location_results['sunrise_navigation_homeless_center']['data_support']
columns_sunrise_support = location_results['sunrise_navigation_homeless_center']['columns_support']

data_phone_call_support = location_results['phone_call']['data_support']
columns_phone_call_support = location_results['phone_call']['columns_support']

data_community_first_support = location_results['community_first_village']['data_support']
columns_community_first_support = location_results['community_first_village']['columns_support']

# ------------------------------------------------ #

# Create location support summary table that groups by location
df_location_support = (
    df.groupby('Location')
    .agg({
        'Support': ['count', lambda x: ', '.join(sorted(set(x)))]  # Count and unique support types
    })
    .reset_index()
)

# Flatten the multi-level column names
df_location_support.columns = ['Location', 'Count', 'Support Types']

# Sort by count in descending order
df_location_support = df_location_support.sort_values(by='Count', ascending=False)

# Create indexed version for the table
df_location_support_indexed = df_location_support.reset_index(drop=True).copy()
df_location_support_indexed.insert(0, '#', df_location_support_indexed.index + 1)
data_location_support = df_location_support_indexed.to_dict('records')
columns_location_support = [{"name": col, "id": col} for col in df_location_support_indexed.columns]

# Print verification
# for key, data in location_results.items():
#     print(f"{data['original_name']}: {data['length']}")

# # Print verification
# for key, data in location_results.items():
#     print(f"{data['original_name']}: {data['length']}")

# Create location support summary table that groups by location
df_location_support = (
    df.groupby('Location')
    .agg({
        'Support': ['count', lambda x: ', '.join(sorted(set(x)))]  # Count and unique support types
    })
    .reset_index()
)

# Flatten the multi-level column names
df_location_support.columns = ['Location', 'Count', 'Support Types']

# Sort by count in descending order
df_location_support = df_location_support.sort_values(by='Count', ascending=False)

# Create indexed version for the table
df_location_support_indexed = df_location_support.reset_index(drop=True).copy()
df_location_support_indexed.insert(0, '#', df_location_support_indexed.index + 1)
data_location_support = df_location_support_indexed.to_dict('records')
columns_location_support = [{"name": col, "id": col} for col in df_location_support_indexed.columns]

# ---------------------------------------------- #

df_main = df.sort_values('Date of Activity', ascending=True)

# create a display index column and prepare table data/columns
# reset index to ensure contiguous numbering after any filtering/sorting upstream
df_main_indexed = df_main.reset_index(drop=True).copy()
# Insert '#' as the first column (1-based row numbers)
df_main_indexed.insert(0, '#', df_main_indexed.index + 1)

# Convert to records for DataTable
data_main_navigation = df_main_indexed.to_dict('records')
columns_main_navigation = [{"name": col, "id": col} for col in df_main_indexed.columns]

# ============================== Dash Application ========================== #

app = dash.Dash(__name__)
server= app.server

app.layout = html.Div(
    children=[ 
        html.Div(
            className='divv', 
            children=[ 
                html.H1(
                    'Client Navigation Report', 
                    className='title'),
                html.H1(
                    f'{report_month} {report_year}', 
                    className='title2'),
                html.Div(
                    className='btn-box', 
                    children=[
                        html.A(
                            'Repo',
                            href=f'https://github.com/CxLos/Nav_{report_month}_{report_year}',
                            className='btn'
                        ),
                    ]
                ),
            ]
        ),  

# ============================ Rollups ========================== #

# ROW 1
html.Div(
    className='rollup-row',
    children=[
        
        html.Div(
            className='rollup-box-tl',
            children=[
                html.Div(
                    className='title-box',
                    children=[
                        html.H3(
                            className='rollup-title',
                            children=[f'{report_month} Clients Served']
                        ),
                    ]
                ),

                html.Div(
                    className='circle-box',
                    children=[
                        html.Div(
                            className='circle-1',
                            children=[
                                html.H1(
                                className='rollup-number',
                                children=[clients_served]
                                ),
                            ]
                        )
                    ],
                ),
            ]
        ),
        html.Div(
            className='rollup-box-tr',
            children=[
                html.Div(
                    className='title-box',
                    children=[
                        html.H3(
                            className='rollup-title',
                            children=[f'{report_month} Navigation Hours']
                        ),
                    ]
                ),
                html.Div(
                    className='circle-box',
                    children=[
                        html.Div(
                            className='circle-2',
                            children=[
                                html.H1(
                                className='rollup-number',
                                children=[df_duration]
                                ),
                            ]
                        )
                    ],
                ),
            ]
        ),
    ]
),

html.Div(
    className='rollup-row',
    children=[
        html.Div(
            className='rollup-box-bl',
            children=[
                html.Div(
                    className='title-box',
                    children=[
                        html.H3(
                            className='rollup-title',
                            children=[f'{report_month} Travel Hours']
                        ),
                    ]
                ),

                html.Div(
                    className='circle-box',
                    children=[
                        html.Div(
                            className='circle-3',
                            children=[
                                html.H1(
                                className='rollup-number',
                                children=[travel_time]
                                ),
                            ]
                        )
                    ],
                ),
            ]
        ),
        html.Div(
            className='rollup-box-br',
            children=[
                html.Div(
                    className='title-box',
                    children=[
                        html.H3(
                            className='rollup-title',
                            children=['Placeholder']
                        ),
                    ]
                ),
                html.Div(
                    className='circle-box',
                    children=[
                        html.Div(
                            className='circle-4',
                            children=[
                                html.H1(
                                className='rollup-number',
                                children=['-']
                                ),
                            ]
                        )
                    ],
                ),
            ]
        ),
    ]
),

# ============================ Visuals ========================== #

html.Div(
    className='graph-container',
    children=[
        
        html.H1(
            className='visuals-text',
            children='Visuals'
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=race_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=race_pie
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=gender_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=gender_pie
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=age_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=age_pie
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=insurance_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=insurance_pie
                        )
                    ]
                ),
            ]
        ),
        
        # Breadcrumb navigation
        html.Div(
            className='location-breadcrumb',
            id='location-breadcrumb',
            style={

            },
            children=[
                html.Button(
                    '🏠 All Locations',
                    className='bread-button',
                    id='location-home-btn',
                    n_clicks=0,
                    style={
                        'fontFamily': 'Segoe UI, Tahoma, sans-serif',
                        'fontSize': '16px'
                    }
                )
            ]
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='location-drill-chart',
                            className='graph',
                            figure=location_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=location_pie
                        )
                    ]
                ),
            ]
        ),
        
        # Store for drill-down state
        dcc.Store(id='location-drill-state', data={'level': 0, 'selected_location': None}),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=support_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=support_pie
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=status_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=status_pie
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=housing_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=housing_pie
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=income_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=income_pie
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='graph-row',
            children=[
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=person_bar
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            className='graph',
                            figure=person_pie
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='zip-row',
            children=[
                html.Div(
                    className='wide-box',
                    children=[
                        dcc.Graph(
                            className='zip-graph',
                            figure=zip_fig
                        )
                    ]
                ),
            ]
        ),
        
        # html.Div(
        #     className='graph-row',
        #     children=[
        #         html.Div(
        #             className='wide-box',
        #             children=[
        #                 dcc.Graph(
        #                     className='zip-graph',
        #                     figure=zip_pie
        #                 )
        #             ]
        #         ),
        #     ]
        # ),

        # html.Div(
        #     className='folium-row',
        #     children=[
        #         html.Div(
        #             className='folium-box',
        #             children=[
        #                 html.H1(
        #                     'Visitors by Zip Code Map', 
        #                     className='zip'
        #                 ),
        #                 html.Iframe(
        #                     className='folium',
        #                     id='folium-map',
        #                     srcDoc=map_html
        #                 )
        #             ]
        #         ),
        #     ]
        # ),
    ]
),

# ============================ Data Table ========================== #

    html.Div(
        className='data-row',
        children=[
            html.Div(
                className='data-box',
                children=[
                    html.H1(
                        className='data-title',
                        children='Navigation Table'
                    ),
                    dash_table.DataTable(
                        id='applications-table',
                        data=data_main_navigation, 
                        columns=columns_main_navigation, 
                        page_size=10,
                        sort_action='native',
                        filter_action='native',
                        row_selectable='multi',
                        style_table={
                            'overflowX': 'auto',
                            # 'border': '3px solid #000',
                            # 'borderRadius': '0px'
                        },
                        style_cell={
                            'textAlign': 'left',
                            'minWidth': '100px', 
                            'whiteSpace': 'normal'
                        },
                        style_header={
                            'textAlign': 'center', 
                            'fontWeight': 'bold',
                            'backgroundColor': '#34A853', 
                            'color': 'white'
                        },
                        style_data={
                            'whiteSpace': 'normal',
                            'height': 'auto',
                        },
                        style_cell_conditional=[
                            # index column: narrow & centered
                            {
                                "if": {"column_id": "#"},
                                "width": "60px",
                                "minWidth": "60px",
                                "maxWidth": "60px",
                                "textAlign": "center",
                            },
                            {
                                "if": {"column_id": "Timestamp"},
                                "width": "100px",
                                "minWidth": "100px",
                                "maxWidth": "200px",
                                "textAlign": "center",
                            },
                            {
                                "if": {"column_id": "Date of Activity"},
                                "width": "160px",
                                "minWidth": "160px",
                                "maxWidth": "160px",
                                "textAlign": "center",
                            },
                            {
                                "if": {"column_id": "Description"},
                                "width": "400px",
                                "minWidth": "400px",
                                "maxWidth": "400px",
                                "textAlign": "left",
                            },
                        ]

                    ),
                ]
            ),
            
            # Black Men's Health Clinic Support Table
            # html.Div(
            #     className='data-box',
            #     children=[
            #         html.H1(
            #             className='data-title',
            #             children=f"Black Men's Health Clinic Support Types ({bmhc_len})"
            #         ),
            #         dash_table.DataTable(
            #             id='bmhc-support-table',
            #             data=data_bmhc_support,
            #             columns=columns_bmhc_support,
            #             page_size=10,
            #             sort_action='native',
            #             filter_action='native',
            #             row_selectable='multi',
            #             style_table={
            #                 'overflowX': 'auto',
            #             },
            #             style_cell={
            #                 'textAlign': 'left',
            #                 'minWidth': '100px', 
            #                 'whiteSpace': 'normal'
            #             },
            #             style_header={
            #                 'textAlign': 'center', 
            #                 'fontWeight': 'bold',
            #                 'backgroundColor': '#34A853', 
            #                 'color': 'white'
            #             },
            #             style_data={
            #                 'whiteSpace': 'normal',
            #                 'height': 'auto',
            #             },
            #             style_cell_conditional=[
            #                 {'if': {'column_id': '#'},
            #                 'width': '20px', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
            #                 {'if': {'column_id': 'Type of Support'},
            #                 'width': '300px', 'minWidth': '300px', 'maxWidth': '400px', 'textAlign': 'left'},
            #                 {'if': {'column_id': 'Count'},
            #                 'width': '100px', 'minWidth': '100px', 'maxWidth': '100px', 'textAlign': 'center'},
            #             ]
            #         ),
            #     ]
            # ),
            
            # # Downtown Austin Community Court Support Table
            # html.Div(
            #     className='data-box',
            #     children=[
            #         html.H1(
            #             className='data-title',
            #             children=f"Downtown Austin Community Court Support Types ({downtown_cc_len})"
            #         ),
            #         dash_table.DataTable(
            #             id='downtown-cc-support-table',
            #             data=data_downtown_cc_support,
            #             columns=columns_downtown_cc_support,
            #             page_size=10,
            #             sort_action='native',
            #             filter_action='native',
            #             row_selectable='multi',
            #             style_table={
            #                 'overflowX': 'auto',
            #             },
            #             style_cell={
            #                 'textAlign': 'left',
            #                 'minWidth': '100px', 
            #                 'whiteSpace': 'normal'
            #             },
            #             style_header={
            #                 'textAlign': 'center', 
            #                 'fontWeight': 'bold',
            #                 'backgroundColor': '#34A853', 
            #                 'color': 'white'
            #             },
            #             style_data={
            #                 'whiteSpace': 'normal',
            #                 'height': 'auto',
            #             },
            #             style_cell_conditional=[
            #                 {'if': {'column_id': '#'},
            #                 'width': '20px', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
            #                 {'if': {'column_id': 'Type of Support'},
            #                 'width': '300px', 'minWidth': '300px', 'maxWidth': '400px', 'textAlign': 'left'},
            #                 {'if': {'column_id': 'Count'},
            #                 'width': '100px', 'minWidth': '100px', 'maxWidth': '100px', 'textAlign': 'center'},
            #             ]
            #         ),
            #     ]
            # ),
            
            # # South Bridge Support Table
            # html.Div(
            #     className='data-box',
            #     children=[
            #         html.H1(
            #             className='data-title',
            #             children=f"South Bridge Support Types ({south_bridge_len})"
            #         ),
            #         dash_table.DataTable(
            #             id='south-bridge-support-table',
            #             data=data_south_bridge_support,
            #             columns=columns_south_bridge_support,
            #             page_size=10,
            #             sort_action='native',
            #             filter_action='native',
            #             row_selectable='multi',
            #             style_table={
            #                 'overflowX': 'auto',
            #             },
            #             style_cell={
            #                 'textAlign': 'left',
            #                 'minWidth': '100px', 
            #                 'whiteSpace': 'normal'
            #             },
            #             style_header={
            #                 'textAlign': 'center', 
            #                 'fontWeight': 'bold',
            #                 'backgroundColor': '#34A853', 
            #                 'color': 'white'
            #             },
            #             style_data={
            #                 'whiteSpace': 'normal',
            #                 'height': 'auto',
            #             },
            #             style_cell_conditional=[
            #                 {'if': {'column_id': '#'},
            #                 'width': '20px', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
            #                 {'if': {'column_id': 'Type of Support'},
            #                 'width': '300px', 'minWidth': '300px', 'maxWidth': '400px', 'textAlign': 'left'},
            #                 {'if': {'column_id': 'Count'},
            #                 'width': '100px', 'minWidth': '100px', 'maxWidth': '100px', 'textAlign': 'center'},
            #             ] # pyright: ignore[reportArgumentType]
            #         ),
            #     ]
            # ),
            
            # # Sunrise Navigation Homeless Center Support Table
            # html.Div(
            #     className='data-box',
            #     children=[
            #         html.H1(
            #             className='data-title',
            #             children=f"Sunrise Navigation Homeless Center Support Types ({sunrise_len})"
            #         ),
            #         dash_table.DataTable(
            #             id='sunrise-support-table',
            #             data=data_sunrise_support,
            #             columns=columns_sunrise_support,
            #             page_size=10,
            #             sort_action='native',
            #             filter_action='native',
            #             row_selectable='multi',
            #             style_table={
            #                 'overflowX': 'auto',
            #             },
            #             style_cell={
            #                 'textAlign': 'left',
            #                 'minWidth': '100px', 
            #                 'whiteSpace': 'normal'
            #             },
            #             style_header={
            #                 'textAlign': 'center', 
            #                 'fontWeight': 'bold',
            #                 'backgroundColor': '#34A853', 
            #                 'color': 'white'
            #             },
            #             style_data={
            #                 'whiteSpace': 'normal',
            #                 'height': 'auto',
            #             },
            #             style_cell_conditional=[
            #                 {'if': {'column_id': '#'},
            #                 'width': '20px', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
            #                 {'if': {'column_id': 'Type of Support'},
            #                 'width': '300px', 'minWidth': '300px', 'maxWidth': '400px', 'textAlign': 'left'},
            #                 {'if': {'column_id': 'Count'},
            #                 'width': '100px', 'minWidth': '100px', 'maxWidth': '100px', 'textAlign': 'center'},
            #             ]
            #         ),
            #     ]
            # ),
            
            # # Phone Call Support Table
            # html.Div(
            #     className='data-box',
            #     children=[
            #         html.H1(
            #             className='data-title',
            #             children=f"Phone Call Support Types ({phone_call_len})"
            #         ),
            #         dash_table.DataTable(
            #             id='phone-call-support-table',
            #             data=data_phone_call_support,
            #             columns=columns_phone_call_support,
            #             page_size=10,
            #             sort_action='native',
            #             filter_action='native',
            #             row_selectable='multi',
            #             style_table={
            #                 'overflowX': 'auto',
            #             },
            #             style_cell={
            #                 'textAlign': 'left',
            #                 'minWidth': '100px', 
            #                 'whiteSpace': 'normal'
            #             },
            #             style_header={
            #                 'textAlign': 'center', 
            #                 'fontWeight': 'bold',
            #                 'backgroundColor': '#34A853', 
            #                 'color': 'white'
            #             },
            #             style_data={
            #                 'whiteSpace': 'normal',
            #                 'height': 'auto',
            #             },
            #             style_cell_conditional=[
            #                 {'if': {'column_id': '#'},
            #                 'width': '20px', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
            #                 {'if': {'column_id': 'Type of Support'},
            #                 'width': '300px', 'minWidth': '300px', 'maxWidth': '400px', 'textAlign': 'left'},
            #                 {'if': {'column_id': 'Count'},
            #                 'width': '100px', 'minWidth': '100px', 'maxWidth': '100px', 'textAlign': 'center'},
            #             ]
            #         ),
            #     ]
            # ),
            
            # # Community First Village Support Table
            # html.Div(
            #     className='data-box',
            #     children=[
            #         html.H1(
            #             className='data-title',
            #             children=f"Community First Village Support Types ({community_first_len})"
            #         ),
            #         dash_table.DataTable(
            #             id='community-first-support-table',
            #             data=data_community_first_support,
            #             columns=columns_community_first_support,
            #             page_size=10,
            #             sort_action='native',
            #             filter_action='native',
            #             row_selectable='multi',
            #             style_table={
            #                 'overflowX': 'auto',
            #             },
            #             style_cell={
            #                 'textAlign': 'left',
            #                 'minWidth': '100px', 
            #                 'whiteSpace': 'normal'
            #             },
            #             style_header={
            #                 'textAlign': 'center', 
            #                 'fontWeight': 'bold',
            #                 'backgroundColor': '#34A853', 
            #                 'color': 'white'
            #             },
            #             style_data={
            #                 'whiteSpace': 'normal',
            #                 'height': 'auto',
            #             },
            #             style_cell_conditional=[
            #                 {'if': {'column_id': '#'},
            #                 'width': '20px', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
            #                 {'if': {'column_id': 'Type of Support'},
            #                 'width': '300px', 'minWidth': '300px', 'maxWidth': '400px', 'textAlign': 'left'},
            #                 {'if': {'column_id': 'Count'},
            #                 'width': '100px', 'minWidth': '100px', 'maxWidth': '100px', 'textAlign': 'center'},
            #             ]
            #         ),
            #     ]
            # ),
            
            # # Location Support Summary Table
            # html.Div(
            #     className='data-box',
            #     children=[
            #         html.H1(
            #             className='data-title',
            #             children='Location Support Summary'
            #         ),
            #         dash_table.DataTable(
            #             id='applications-table',
            #             data=data_location_support,
            #             columns=columns_location_support,
            #             page_size=10,
            #             sort_action='native',
            #             filter_action='native',
            #             row_selectable='multi',
            #             style_table={
            #                 'overflowX': 'auto',
            #             },
            #             style_cell={
            #                 'textAlign': 'left',
            #                 'minWidth': '100px', 
            #                 'whiteSpace': 'normal'
            #             },
            #             style_header={
            #                 'textAlign': 'center', 
            #                 'fontWeight': 'bold',
            #                 'backgroundColor': '#34A853', 
            #                 'color': 'white'
            #             },
            #             style_data={
            #                 'whiteSpace': 'normal',
            #                 'height': 'auto',
            #             },
            #             style_cell_conditional=[
            #                 {'if': {'column_id': '#'},
            #                 'width': '20px', 'minWidth': '60px', 'maxWidth': '60px', 'textAlign': 'center'},
            #                 {'if': {'column_id': 'Location'},
            #                 'width': '200px', 'minWidth': '200px', 'maxWidth': '250px', 'textAlign': 'left'},
            #                 {'if': {'column_id': 'Count'},
            #                 'width': '100px', 'minWidth': '100px', 'maxWidth': '100px', 'textAlign': 'center'},
            #                 {'if': {'column_id': 'Support Provided'},
            #                 'width': '400px', 'minWidth': '400px', 'maxWidth': '600px', 'textAlign': 'left'},
            #             ]
            #         ),
            #     ]
            # ),
        ]
    ),
])

# ======================== Location Drill-Down Callback ======================== #

@app.callback(
    [Output('location-drill-chart', 'figure'),
     Output('location-drill-state', 'data'),
     Output('location-breadcrumb', 'children')],
    [Input('location-drill-chart', 'clickData'),
     Input('location-home-btn', 'n_clicks')],
    [State('location-drill-state', 'data')]
)
def location_drill_navigation(clickData, home_clicks, state):
    """
    Handle drill-down navigation for location charts
    - Level 0: Show all locations
    - Level 1: Show support types for selected location
    """
    ctx = callback_context.triggered[0]['prop_id'] if callback_context.triggered else None
    
    # Handle back to home button
    if ctx == 'location-home-btn.n_clicks' and home_clicks > 0:
        state['level'] = 0
        state['selected_location'] = None
    
    # Handle drill-down click
    elif clickData and ctx == 'location-drill-chart.clickData':
        if state['level'] == 0:
            # Drill down to support types for clicked location
            clicked_location = clickData['points'][0]['x']
            state['selected_location'] = clicked_location
            state['level'] = 1
    
    # Generate chart based on current level
    if state['level'] == 0:
        # Level 0: Show all locations (original chart)
        fig = px.bar(
            df_location,
            x="Location",
            y='Count',
            color="Location",
            text='Count',
        ).update_layout(
            title=dict(
                text='Outreach/ Locations Encountered (Click to drill down)',
                x=0.5, 
                font=dict(size=21, family='Calibri', color='black')
            ),
            font=dict(family='Calibri', size=16, color='black'),
            xaxis=dict(
                tickangle=-20,
                tickfont=dict(size=16),
                title=dict(text="Location", font=dict(size=16)),
                showticklabels=False
            ),
            yaxis=dict(
                title=dict(text='Count', font=dict(size=16)),
            ),
            legend=dict(
                title='',
                orientation="v",
                x=1.05,
                y=1,
                xanchor="left",
                yanchor="top",
            ),
            hovermode='closest',
            bargap=0.08,
            bargroupgap=0,
        ).update_traces(
            textposition=None,
            hovertemplate='<b>Location:</b> %{x}<br><b>Count</b>: %{y}<extra></extra>'
        )
        
        # Breadcrumb for home
        breadcrumb = [
            html.Button(
                '🏠 All Locations',
                id='location-home-btn',
                n_clicks=0,
                style={
                    'border': 'none',
                    'background': 'none',
                    'color': '#007bff',
                    'cursor': 'pointer',
                    'fontSize': '16px',
                    'fontWeight': 'bold'
                }
            )
        ]
        
    else:
        # Level 1: Show support types for selected location
        selected_loc = state['selected_location']
        df_filtered = df[df['Location'] == selected_loc]
        
        counter = Counter()
        for entry in df_filtered['Support']:
            standardized_entry = str(entry).replace(' and ', ', ')
            items = [i.strip() for i in re.split(pattern, standardized_entry) if i.strip()]
            for item in items:
                # Strip parenthetical descriptions - keep only text before the opening parenthesis
                clean_item = re.sub(r'\s*\(.*?\)\s*', '', item).strip()
                if clean_item:  # Only count if there's content after stripping
                    counter[clean_item] += 1

        df_support_filtered = pd.DataFrame(
            counter.items(),
            columns=['Support', 'Count']
        ).sort_values(by='Count', ascending=False)

        
        fig = px.bar(
            df_support_filtered,
            x='Support',
            y='Count',
            color='Support',
            text='Count',
        ).update_layout(
            title=dict(
                text=f'Support Types at {selected_loc}',
                x=0.5,
                font=dict(size=21, family='Calibri', color='black')
            ),
            font=dict(family='Calibri', size=16, color='black'),
            xaxis=dict(
                tickangle=-20,
                tickfont=dict(size=16),
                title=dict(text="Support Type", font=dict(size=16)),
                showticklabels=False
            ),
            yaxis=dict(
                title=dict(text='Count', font=dict(size=16)),
            ),
            legend=dict(
                title='',
                orientation="v",
                x=1.05,
                y=1,
                xanchor="left",
                yanchor="top",
            ),
            hovermode='closest',
            bargap=0.08,
        ).update_traces(
            textposition='outside',
            hovertemplate='<b>Support:</b> %{x}<br><b>Count</b>: %{y}<extra></extra>'
        )
        
        # Breadcrumb showing path
        breadcrumb = [
            html.Button(
                '🏠 All Locations',
                id='location-home-btn',
                n_clicks=0,
                style={
                    'border': 'none',
                    'background': 'none',
                    'color': '#007bff',
                    'cursor': 'pointer',
                    'fontSize': '16px',
                    'fontWeight': 'bold'
                }
            ),
            html.Span(' > ', style={'margin': '0 10px', 'color': '#6c757d'}),
            html.Span(selected_loc, style={'fontWeight': 'bold', 'color': '#495057'})
        ]
    
    return fig, state, breadcrumb

# ============================================================================== #

print(f"Serving Flask app '{current_file}'! 🚀")

if __name__ == '__main__':
    app.run(debug=
                   True)
                #    False)
                
# ----------------------------------------------- Updated Database --------------------------------------

# updated_path = f'data/Navigation_{report_month}_{report_year}.xlsx'
# data_path = os.path.join(script_dir, updated_path)
# sheet_name=f'{report_month} {report_year}'

# with pd.ExcelWriter(data_path, engine='xlsxwriter') as writer:
#     df.to_excel(
#             writer, 
#             sheet_name=sheet_name, 
#             startrow=1, 
#             index=False
#         )

#     # Access the workbook and each worksheet
#     workbook = writer.book
#     sheet1 = writer.sheets[sheet_name]
    
#     # Define the header format
#     header_format = workbook.add_format({
#         'bold': True, 
#         'font_size': 16, 
#         'align': 'center', 
#         'valign': 'vcenter',
#         'border': 1, 
#         'font_color': 'black', 
#         'bg_color': '#B7B7B7',
#     })
    
#     # Set column A (Name) to be left-aligned, and B-E to be right-aligned
#     left_align_format = workbook.add_format({
#         'align': 'left',  # Left-align for column A
#         'valign': 'vcenter',  # Vertically center
#         'border': 0  # No border for individual cells
#     })

#     right_align_format = workbook.add_format({
#         'align': 'right',  # Right-align for columns B-E
#         'valign': 'vcenter',  # Vertically center
#         'border': 0  # No border for individual cells
#     })
    
#     # Create border around the entire table
#     border_format = workbook.add_format({
#         'border': 1,  # Add border to all sides
#         'border_color': 'black',  # Set border color to black
#         'align': 'center',  # Center-align text
#         'valign': 'vcenter',  # Vertically center text
#         'font_size': 12,  # Set font size
#         'font_color': 'black',  # Set font color to black
#         'bg_color': '#FFFFFF'  # Set background color to white
#     })

#     # Merge and format the first row (A1:E1) for each sheet
#     sheet1.merge_range('A1:AB1', f'Client Navigation Report {current_month} {report_year}', header_format)

#     # Set column alignment and width
#     # sheet1.set_column('A:A', 20, left_align_format)  

#     print(f"Navigation Excel file saved to {data_path}")

# -------------------------------------------- KILL PORT ---------------------------------------------------

# netstat -ano | findstr :8050
# taskkill /PID 24772 /F
# npx kill-port 8050


# ---------------------------------------------- Host Application -------------------------------------------

# 1. pip freeze > requirements.txt
# 2. add this to procfile: 'web: gunicorn impact_11_2024:server'
# 3. heroku login
# 4. heroku create
# 5. git push heroku main

# Create venv 
# virtualenv venv 
# source venv/bin/activate # uses the virtualenv

# Update PIP Setup Tools:
# pip install --upgrade pip setuptools

# Install all dependencies in the requirements file:
# pip install -r requirements.txt

# Check dependency tree:
# pipdeptree
# pip show package-name

# Remove
# pypiwin32
# pywin32
# jupytercore

# ----------------------------------------------------

# Name must start with a letter, end with a letter or digit and can only contain lowercase letters, digits, and dashes.

# Heroku Setup:
# heroku login
# heroku create nav-jul-2025
# heroku git:remote -a nav-jul-2025
# git remote set-url heroku git@heroku.com:nav-jan-2025.git
# git push heroku main

# Clear Heroku Cache:
# heroku plugins:install heroku-repo
# heroku repo:purge_cache -a nav-nov-2024

# Set buildpack for heroku
# heroku buildpacks:set heroku/python

# Heatmap Colorscale colors -----------------------------------------------------------------------------

#   ['aggrnyl', 'agsunset', 'algae', 'amp', 'armyrose', 'balance',
            #  'blackbody', 'bluered', 'blues', 'blugrn', 'bluyl', 'brbg',
            #  'brwnyl', 'bugn', 'bupu', 'burg', 'burgyl', 'cividis', 'curl',
            #  'darkmint', 'deep', 'delta', 'dense', 'earth', 'edge', 'electric',
            #  'emrld', 'fall', 'geyser', 'gnbu', 'gray', 'greens', 'greys',
            #  'haline', 'hot', 'hsv', 'ice', 'icefire', 'inferno', 'jet',
            #  'magenta', 'magma', 'matter', 'mint', 'mrybm', 'mygbm', 'oranges',
            #  'orrd', 'oryel', 'oxy', 'peach', 'phase', 'picnic', 'pinkyl',
            #  'piyg', 'plasma', 'plotly3', 'portland', 'prgn', 'pubu', 'pubugn',
            #  'puor', 'purd', 'purp', 'purples', 'purpor', 'rainbow', 'rdbu',
            #  'rdgy', 'rdpu', 'rdylbu', 'rdylgn', 'redor', 'reds', 'solar',
            #  'spectral', 'speed', 'sunset', 'sunsetdark', 'teal', 'tealgrn',
            #  'tealrose', 'tempo', 'temps', 'thermal', 'tropic', 'turbid',
            #  'turbo', 'twilight', 'viridis', 'ylgn', 'ylgnbu', 'ylorbr',
            #  'ylorrd'].

# rm -rf ~$bmhc_data_2024_cleaned.xlsx
# rm -rf ~$bmhc_data_2024.xlsx
# rm -rf ~$bmhc_q4_2024_cleaned2.xlsx