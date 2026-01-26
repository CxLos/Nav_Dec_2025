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

# ============================== Data Loading Function ========================== #

def load_data_for_month(month_name, year=2025):
    """Load and process navigation data for a specific month or full year"""

    data = pd.DataFrame(client.open_by_url(sheet_url).sheet1.get_all_records())
    df_loaded = data.copy()
    
    # Trim leading and trailing whitespaces from column names
    df_loaded.columns = df_loaded.columns.str.strip()
    
    # Convert month name to integer
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Filter df where 'Date of Activity' is in selected month or full year
    df_loaded["Date of Activity"] = pd.to_datetime(df_loaded["Date of Activity"], errors='coerce')
    
    # Handle full year option (e.g., '2025')
    if month_name == '2025':
        df_loaded = df_loaded[df_loaded['Date of Activity'].dt.year == year]  # type: ignore
        int_month = None  # No specific month
    else:
        int_month = month_map.get(month_name, 12)
        df_loaded = df_loaded[(df_loaded['Date of Activity'].dt.month == int_month) & (df_loaded['Date of Activity'].dt.year == year)]  # type: ignore
    
    # Sort df from oldest to newest
    df_loaded = df_loaded.sort_values(by='Date of Activity', ascending=True)
    
    return df_loaded, month_name, year, int_month

# Load default month 
df, report_month, report_year, int_month = load_data_for_month('January', 2025)

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

# ----------------------------------------------------
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

# ================================== Data Cleaning ================================== #

# Income Level

# print("Income Unique Before:", df['Income'].unique())

income_unique = [
    'Unknown', 'Under 25,000', '', 0, '$0', '25,000 - 49,999', 'unknown', '?'
]

df['Income'] = df['Income'].replace({
    '': 'N/A',
    '$0': 'Unknown',
    'Unknown': 'N/A',
    'unknown': 'N/A',
    '?': 'N/A',
    0: 'N/A',
    '': '',
})

# ========================== SPREADSHEET COMPARISON ========================== #

# Load second spreadsheet for comparison
sheet_url_2 = "https://docs.google.com/spreadsheets/d/1GWnQrLptjkgg8CR1G8OpYaCHZMmW5xOzg0kFtPCkxKw/edit?gid=0#gid=0"
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

# =========================== Initial Empty Figures =========================== #

# Create empty figures for initial load
empty_fig = go.Figure()
empty_fig.update_layout(title=dict(text='Please Select a Month', x=0.5, font=dict(size=20)))

# ========================== DataFrame Table ========================== #

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
                    f'Client Navigation Report {report_year}', 
                    className='title'),
                html.H1(
                    id='month-subtitle',
                    children='', 
                    className='title2'),
                html.Div(
                    className='dropdown-container',
                    children=[
                        html.Label('', style={'marginRight': '10px', 'fontWeight': 'bold'}),
                        dcc.Dropdown(
                            id='month-dropdown',
                            className='month-dropdown',
                            options=[
                                {'label': '2025 (Full Year)', 'value': '2025'},
                                {'label': 'January', 'value': 'January'},
                                {'label': 'February', 'value': 'February'},
                                {'label': 'March', 'value': 'March'},
                                {'label': 'April', 'value': 'April'},
                                {'label': 'May', 'value': 'May'},
                                {'label': 'June', 'value': 'June'},
                                {'label': 'July', 'value': 'July'},
                                {'label': 'August', 'value': 'August'},
                                {'label': 'September', 'value': 'September'},
                                {'label': 'October', 'value': 'October'},
                                {'label': 'November', 'value': 'November'},
                                {'label': 'December', 'value': 'December'},
                            ],
                            value=None,
                            placeholder='Select month',
                            clearable=False,
                            style={
                                'width': '150px',
                                'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Calibri, Arial, sans-serif',
                                # 'backgroundColor': 'rgb(250, 242, 127)',
                                # 'border': '3px solid rgb(240, 208, 0)',
                                # 'borderRadius': '50px'
                            }
                        ),
                    ],
                    style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'margin': '20px 0'}
                ),
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
                            id='clients-served-title',
                            className='rollup-title',
                            children=['Clients Served']
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
                                id='clients-served-number',
                                className='rollup-number',
                                children=['-']
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
                            id='nav-hours-title',
                            className='rollup-title',
                            children=['Navigation Hours']
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
                                id='nav-hours-number',
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
                            id='travel-hours-title',
                            className='rollup-title',
                            children=['Travel Hours']
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
                                id='travel-hours-number',
                                className='rollup-number',
                                children=['-']
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
                            id='race-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='race-pie',
                            className='graph',
                            figure=empty_fig
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
                            id='gender-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='gender-pie',
                            className='graph',
                            figure=empty_fig
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
                            id='age-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='age-pie',
                            className='graph',
                            figure=empty_fig
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
                            id='insurance-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='insurance-pie',
                            className='graph',
                            figure=empty_fig
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
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='location-pie',
                            className='graph',
                            figure=empty_fig
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
                            id='support-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='support-pie',
                            className='graph',
                            figure=empty_fig
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
                            id='status-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='status-pie',
                            className='graph',
                            figure=empty_fig
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
                            id='housing-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='housing-pie',
                            className='graph',
                            figure=empty_fig
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
                            id='income-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='income-pie',
                            className='graph',
                            figure=empty_fig
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
                            id='person-bar',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
                html.Div(
                    className='graph-box',
                    children=[
                        dcc.Graph(
                            id='person-pie',
                            className='graph',
                            figure=empty_fig
                        )
                    ]
                ),
            ]
        ),
        
        html.Div(
            className='zip-row',
            children=[
                html.Div(
                    className='zip-box',
                    children=[
                        dcc.Graph(
                            id='zip-graph',
                            className='zip-graph',
                            figure=empty_fig
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
        ]
    ),
])

# ======================== Month Selection Callback ======================== #

@app.callback(
    [
        Output('month-subtitle', 'children'),
        Output('clients-served-title', 'children'),
        Output('clients-served-number', 'children'),
        Output('nav-hours-title', 'children'),
        Output('nav-hours-number', 'children'),
        Output('travel-hours-title', 'children'),
        Output('travel-hours-number', 'children'),
        Output('race-bar', 'figure'),
        Output('race-pie', 'figure'),
        Output('gender-bar', 'figure'),
        Output('gender-pie', 'figure'),
        Output('age-bar', 'figure'),
        Output('age-pie', 'figure'),
        Output('insurance-bar', 'figure'),
        Output('insurance-pie', 'figure'),
        Output('location-drill-chart', 'figure'),
        Output('location-pie', 'figure'),
        Output('support-bar', 'figure'),
        Output('support-pie', 'figure'),
        Output('status-bar', 'figure'),
        Output('status-pie', 'figure'),
        Output('housing-bar', 'figure'),
        Output('housing-pie', 'figure'),
        Output('income-bar', 'figure'),
        Output('income-pie', 'figure'),
        Output('person-bar', 'figure'),
        Output('person-pie', 'figure'),
        Output('zip-graph', 'figure'),
    ],
    [Input('month-dropdown', 'value')],
    prevent_initial_call=True
)
def update_month_data(selected_month):
    """Update all dashboard components based on selected month"""
    
    # Handle None (no selection yet)
    if selected_month is None:
        return dash.no_update

    try:
        print(f"🔄 Callback triggered for month: {selected_month}")
        
        # Load data for selected month
        df_month, month_name, year, int_month = load_data_for_month(selected_month, 2025)
        
    except Exception as e:
        print(f"❌ ERROR in callback: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return empty/error state
        return (
            f"Error: {selected_month}",
            "Error loading data",
            '-',
            "Error loading data",
            '-',
            "Error loading data",
            '-',
            *[empty_fig] * 22,  # All graph outputs (11 pairs of charts)
        )
    
    # Load data for selected month
    df_month, month_name, year, int_month = load_data_for_month(selected_month, 2025)
    
    # Strip whitespace from columns
    df_month.columns = df_month.columns.str.strip()
    
    # Strip whitespace from string entries
    for col in df_month.select_dtypes(include='object').columns:
        df_month[col] = df_month[col].map(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Create Full Name column
    df_month['Full Name'] = df_month["Individual's First Name:"].astype(str) + " " + df_month["Individual's Last Name:"].astype(str)
    
    # Data preprocessing (same as original)
    df_month['HMIS SPID Number:'] = df_month['HMIS SPID Number:'].fillna(-1)
    df_month['MAP Card Number'] = df_month['MAP Card Number'].fillna(-1)
    
    # Debug: Print column names before rename
    # print(f"📋 Columns BEFORE rename: {df_month.columns.tolist()[:10]}...")  # First 10 columns
    
    df_month.rename(
        columns={
            "Activity Duration (minutes):" : "Activity Duration",
            "Location Encountered:" : "Location",
            "Type of Coordination/Navigation Provided:" : "Support",
            "Individual's Insurance Status:" : "Insurance",
            "Individual's Status:" : "Status",
            'Person submitting this form:' : 'Person',
            'Total travel time (minutes):' : 'Travel',
            'County:' : 'County',
            'Race / Ethnicity:' : 'Ethnicity',  # Fixed: added spaces around slash
            'Gender:' : 'Gender',
            'Age:' : 'Age',
            'Housing Status' : 'Housing',
            'Income Level' : 'Income'
        },
        inplace=True
    )
    
    # Debug: Print column names to see what we have
    # print(f"📋 Available columns after rename: {df_month.columns.tolist()}")
    
    # Calculate metrics
    clients_served = str(len(df_month))
    df_duration = round(df_month['Activity Duration'].sum()/60)
    
    # Travel Time Calculation
    df_month['Travel'] = (df_month['Travel'].astype(str).str.strip().replace({'The Bumgalows': '0'}))
    df_month['Travel'] = pd.to_numeric(df_month['Travel'], errors='coerce').fillna(0)
    travel_time = round(df_month['Travel'].sum() / 60)
    
    # Race/Ethnicity Processing
    df_month['Ethnicity'] = (df_month['Ethnicity'].astype(str).str.strip().replace({
        "Hispanic/Latino": "Hispanic/ Latino",
        "White": "White/ European Ancestry",
        "White/ European Ancestry": "White / Caucasian",
        "Group search": "N/A",
    }))
    df_race = df_month['Ethnicity'].value_counts().reset_index(name='Count')
    
    race_bar = px.bar(df_race, x='Ethnicity', y='Count', color='Ethnicity', text='Count').update_layout(
        title=dict(text=f'{month_name} Race Distribution Bar Chart', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black'),
        xaxis=dict(tickangle=-20, tickfont=dict(size=16), showticklabels=False, title=dict(text="Race/ Ethnicity", font=dict(size=16))),
        yaxis=dict(title=dict(text='Count', font=dict(size=16))),
        legend=dict(title='', orientation="v", x=1.05, y=1, xanchor="left", yanchor="top", visible=True),
        hovermode='closest', bargap=0.07, bargroupgap=0
    ).update_traces(textposition='auto', hovertemplate='<b>Race:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>')
    
    race_pie = px.pie(df_race, names='Ethnicity', values='Count').update_layout(
        title=dict(text=f'{month_name} Race Distribution Ratio', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black')
    ).update_traces(texttemplate='%{value}<br>(%{percent:.1%})', hovertemplate='<b>%{label}</b>: %{value}<extra></extra>')
    
    # Gender Processing
    df_month['Gender'] = (df_month['Gender'].astype(str).str.strip().replace({"Group search": "N/A"}))
    df_gender = df_month['Gender'].value_counts().reset_index(name='Count')
    
    gender_bar = px.bar(df_gender, x='Gender', y='Count', color='Gender', text='Count').update_layout(
        title=dict(text=f'{month_name} Sex Distribution Bar Chart', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black'),
        xaxis=dict(tickangle=0, tickfont=dict(size=16), title=dict(text="Gender", font=dict(size=16))),
        yaxis=dict(title=dict(text='Count', font=dict(size=16))),
        legend=dict(title='', orientation="v", x=1.05, y=1, xanchor="left", yanchor="top", visible=False),
        hovermode='closest', bargap=0.07, bargroupgap=0
    ).update_traces(textposition='auto', hovertemplate='<b>Gender</b>: %{label}<br><b>Count</b>: %{y}<extra></extra>')
    
    gender_pie = px.pie(df_month, names='Gender').update_layout(
        title=dict(text=f'{month_name} Patient Visits by Sex', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black')
    ).update_traces(texttemplate='%{value}<br>(%{percent:.1%})', hovertemplate='<b>%{label} Visits</b>: %{value}<extra></extra>')
    
    # Age Processing
    def random_date(start, end):
        return start + timedelta(days=np.random.randint(0, (end - start).days))
    
    start_date = datetime(1950, 1, 1)
    end_date = datetime(2000, 12, 31)
    
    df_month['Individual\'s Date of Birth:'] = pd.to_datetime(df_month['Individual\'s Date of Birth:'], errors='coerce')
    df_month['Individual\'s Date of Birth:'] = df_month['Individual\'s Date of Birth:'].apply(
        lambda x: random_date(start_date, end_date) if pd.isna(x) else x
    )
    df_month['Client Age'] = pd.to_datetime('today').year - df_month['Individual\'s Date of Birth:'].dt.year
    df_month['Client Age'] = df_month['Client Age'].apply(lambda x: "N/A" if x < 0 else x)
    
    def categorize_age(age):
        if age == "N/A": return "N/A"
        elif 10 <= age <= 19: return '10-19'
        elif 20 <= age <= 29: return '20-29'
        elif 30 <= age <= 39: return '30-39'
        elif 40 <= age <= 49: return '40-49'
        elif 50 <= age <= 59: return '50-59'
        elif 60 <= age <= 69: return '60-69'
        elif 70 <= age <= 79: return '70-79'
        else: return '80+'
    
    df_month['Age_Group'] = df_month['Client Age'].apply(categorize_age)
    df_decades = df_month.groupby('Age_Group', observed=True).size().reset_index(name='Patient_Visits')
    
    age_order = ['10-19', '20-29', '30-39', '40-49', '50-59', '60-69', '70-79', '80+']
    df_decades['Age_Group'] = pd.Categorical(df_decades['Age_Group'], categories=age_order, ordered=True)
    df_decades = df_decades.sort_values('Age_Group')
    
    age_bar = px.bar(df_decades, x='Age_Group', y='Patient_Visits', color='Age_Group', text='Patient_Visits').update_layout(
        title=dict(text=f'{month_name} Client Age Distribution', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black'),
        xaxis=dict(tickangle=0, tickfont=dict(size=16), title=dict(text="Age Group", font=dict(size=16))),
        yaxis=dict(title=dict(text='Number of Visits', font=dict(size=16))),
        legend=dict(title_text='', orientation="v", x=1.05, y=1, xanchor="left", yanchor="top", visible=False),
        hovermode='closest', bargap=0.08, bargroupgap=0
    ).update_traces(textposition='auto', hovertemplate='<b>Age:</b>: %{label}<br><b>Count</b>: %{y}<extra></extra>')
    
    age_pie = px.pie(df_decades, names='Age_Group', values='Patient_Visits').update_layout(
        title=dict(text=f'{month_name} Client Age Distribution Ratio', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black')
    ).update_traces(rotation=190, texttemplate='%{value}<br>(%{percent:.1%})', hovertemplate='<b>%{label}</b>: %{value}<extra></extra>')
    
    # Insurance Processing
    df_month["Insurance"] = (df_month["Insurance"].str.strip().replace({
        '': 'Unknown', 'unknown': 'Unknown', 'Just got it!!!': 'Private Insurance',
        'Medicare': 'Medicaid', 'NONE': 'None', 'Map 000': 'MAP 100',
        '30 Day 100': '30 DAY 100', '30 DAY100': '30 DAY 100', '30DAY 100': '30 DAY 100',
    }))
    df_insurance = df_month.groupby("Insurance").size().reset_index(name='Count')
    
    insurance_bar = px.bar(df_insurance, x="Insurance", y='Count', color="Insurance", text='Count').update_layout(
        title=dict(text=f'{month_name} Insurance Status Bar Chart', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black'),
        xaxis=dict(tickangle=-20, tickfont=dict(size=16), showticklabels=False, title=dict(text="Insurance", font=dict(size=16))),
        yaxis=dict(title=dict(text='Count', font=dict(size=16))),
        legend=dict(title='Insurance', orientation="v", x=1.05, y=1, xanchor="left", yanchor="top", visible=True),
        hovermode='closest', bargap=0.08, bargroupgap=0
    ).update_traces(textposition='auto', hovertemplate='<b>Insurance:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>')
    
    insurance_pie = px.pie(df_insurance, names="Insurance", values='Count').update_layout(
        title=dict(text=f'{month_name} Insurance Status Ratio', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black')
    ).update_traces(rotation=100, texttemplate='%{value}<br>(%{percent:.1%})', hovertemplate='<b>%{label}</b>: %{value}<extra></extra>')
    
    # Location Processing
    df_month['Location'] = (df_month['Location'].str.strip().replace({"": "N/A"}))
    df_location = df_month['Location'].value_counts().reset_index(name='Count')
    
    location_bar = px.bar(df_location, x="Location", y='Count', color="Location", text='Count').update_layout(
        title=dict(text=f'{month_name} Outreach/ Locations Encountered (Click to drill down)', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black'),
        xaxis=dict(tickangle=-20, tickfont=dict(size=16), title=dict(text="Location", font=dict(size=16)), showticklabels=False),
        yaxis=dict(title=dict(text='Count', font=dict(size=16))),
        legend=dict(title='', orientation="v", x=1.05, y=1, xanchor="left", yanchor="top"),
        hovermode='closest', bargap=0.08, bargroupgap=0
    ).update_traces(textposition=None, hovertemplate='<b>Location:</b> %{x}<br><b>Count</b>: %{y}<extra></extra>')
    
    location_pie = px.pie(df_location, names="Location", values='Count').update_layout(
        title=dict(text=f'{month_name} Location Breakdown', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black')
    ).update_traces(rotation=200, texttemplate='%{value}<br>(%{percent:.1%})', hovertemplate='<b>%{label}</b>: %{value}<extra></extra>')
    
    # Support Processing
    counter = Counter()
    for entry in df_month['Support']:
        standardized_entry = str(entry).replace(' and ', ', ')
        items = [i.strip() for i in re.split(pattern, standardized_entry) if i.strip()]
        for item in items:
            clean_item = re.sub(r'\s*\(.*?\)\s*', '', item).strip()
            if clean_item:
                counter[clean_item] += 1
    
    df_support = pd.DataFrame(counter.items(), columns=['Support', 'Count']).sort_values(by='Count', ascending=False)
    
    support_bar = px.bar(df_support, x='Support', y='Count', color='Support', text='Count').update_layout(
        title=dict(text=f'{month_name} Coordination Services Provided', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black'),
        xaxis=dict(tickangle=-20, tickfont=dict(size=16), title=dict(text="Coordination Service", font=dict(size=16)), showticklabels=False),
        yaxis=dict(title=dict(text='Count', font=dict(size=16))),
        legend=dict(title='', orientation="v", x=1.05, y=1, xanchor="left", yanchor="top"),
        hovermode='closest', bargap=0.08
    ).update_traces(textposition='outside', hovertemplate='<b>Support:</b> %{x}<br><b>Count</b>: %{y}<extra></extra>')
    
    support_pie = px.pie(df_support, names='Support', values='Count').update_layout(
        title=dict(text=f'{month_name} Coordination Services Breakdown', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black')
    ).update_traces(rotation=195, texttemplate='%{value}<br>(%{percent:.1%})', hovertemplate='<b>%{label}</b>: %{value}<extra></extra>')
    
    # Status Processing
    df_month['Status'] = (df_month['Status'].str.strip().replace({"": "N/A", "Group search": "N/A"}))
    df_status = df_month['Status'].value_counts().reset_index(name='Count')
    
    status_bar = px.bar(df_status, x="Status", y='Count', color="Status", text='Count').update_layout(
        title=dict(text=f'{month_name} Client Status Distribution', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black'),
        xaxis=dict(tickangle=-20, tickfont=dict(size=16), showticklabels=False, title=dict(text="Status", font=dict(size=16))),
        yaxis=dict(title=dict(text='Count', font=dict(size=16))),
        legend=dict(title='Status', orientation="v", x=1.05, y=1, xanchor="left", yanchor="top", visible=True),
        hovermode='closest', bargap=0.08, bargroupgap=0
    ).update_traces(textposition='auto', hovertemplate='<b>Status:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>')
    
    status_pie = px.pie(df_status, names="Status", values='Count').update_layout(
        title=dict(text=f'{month_name} Client Status Ratio', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black')
    ).update_traces(rotation=100, texttemplate='%{value}<br>(%{percent:.1%})', hovertemplate='<b>%{label}</b>: %{value}<extra></extra>')
    
    # Housing Status Processing
    df_month['Housing'] = (
        df_month['Housing']
        .str.strip()
        .replace({
            "" : "N/A",
        })
    )
    
    df_housing = df_month['Housing'].value_counts().reset_index(name='Count')
    
    housing_bar = px.bar(
        df_housing,
        x='Housing',
        y='Count',
        color='Housing',
        text='Count',
    ).update_layout(
        title=dict(
            text=f'{month_name} Housing Status Distribution',
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
            tickangle=0,
            tickfont=dict(size=16),
            showticklabels=False,
            title=dict(text=None),
        ),
        yaxis=dict(
            title=dict(text=None)
        ),
        legend=dict(title=''),
        bargap=0.08,
        showlegend=True,
    )
    
    housing_pie = px.pie(
        df_housing,
        names='Housing',
        values='Count',
        title=f'Ratio of {month_name} Housing Status',
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
        texttemplate='%{value}<br>(%{percent:.1%})',
        hovertemplate='<b>%{label} Housing</b>: %{value}<extra></extra>',
    )
    
    # Income Level Processing
    df_month['Income'] = (
        df_month['Income']
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
    
    df_income = df_month['Income'].value_counts().reset_index(name='Count')
    # print("Income Unique Before:", df_income['Income'].unique())

    income_unique = [

    ]
    
    income_bar = px.bar(
        df_income,
        x='Income',
        y='Count',
        color='Income',
        text='Count',
    ).update_layout(
        title=dict(
            text=f'{month_name} Income Level Distribution',
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
            tickangle=0,
            tickfont=dict(size=16),
            showticklabels=False,
            title=dict(text=None),
        ),
        yaxis=dict(
            title=dict(text=None)
        ),
        legend=dict(title=''),
        bargap=0.08,
        showlegend=True,
    )
    
    income_pie = px.pie(
        df_income,
        names='Income',
        values='Count',
        title=f'Ratio of {month_name} Income Level',
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
        texttemplate='%{value}<br>(%{percent:.1%})',
        hovertemplate='<b>%{label} Income</b>: %{value}<extra></extra>',
    )
    
    # Person Processing
    df_person = df_month['Person'].value_counts().reset_index(name='Count')
    
    person_bar = px.bar(df_person, x='Person', y='Count', color='Person', text='Count').update_layout(
        title=dict(text='Navigator Distribution', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black'),
        xaxis=dict(tickangle=-20, tickfont=dict(size=16), showticklabels=False, title=dict(text="Navigator", font=dict(size=16))),
        yaxis=dict(title=dict(text='Count', font=dict(size=16))),
        legend=dict(title='', orientation="v", x=1.05, y=1, xanchor="left", yanchor="top", visible=True),
        hovermode='closest', bargap=0.08, bargroupgap=0
    ).update_traces(textposition='auto', hovertemplate='<b>Navigator:</b> %{label}<br><b>Count</b>: %{y}<extra></extra>')
    
    person_pie = px.pie(df_person, names='Person', values='Count').update_layout(
        title=dict(text='Navigator Distribution Ratio', x=0.5, font=dict(size=21, family='Calibri', color='black')),
        font=dict(family='Calibri', size=16, color='black')
    ).update_traces(rotation=100, texttemplate='%{value}<br>(%{percent:.1%})', hovertemplate='<b>%{label}</b>: %{value}<extra></extra>')
    
    # Zip Code Processing
    df_month['ZIP2'] = df_month['ZIP Code:'].astype(str).str.strip()
    
    # Define invalid/null values to exclude
    invalid_zip_values = [
        'Texas', 'Unhoused', 'UNHOUSED', 'UnKnown', 'Unknown', 'uknown',
        'Unknown ', 'NA', 'nan', 'NaN', 'None', '5126364511', '', ' '
    ]
    
    # Filter out invalid ZIP codes - only keep numeric values
    valid_zip_mask = (
        df_month['ZIP2'].str.isnumeric() & 
        ~df_month['ZIP2'].isin(invalid_zip_values)
    )
    
    # Create filtered dataframe with only valid ZIP codes
    df_zip_filtered = df_month[valid_zip_mask].copy()
    
    # Create value count dataframe for the bar chart (only valid zips)
    df_z = df_zip_filtered['ZIP2'].value_counts().reset_index(name='Count')
    df_z.columns = ['ZIP2', 'Count']
    
    df_z['Percentage'] = (df_z['Count'] / df_z['Count'].sum()) * 100
    df_z['text_label'] = df_z['Count'].astype(str) + ' (' + df_z['Percentage'].round(1).astype(str) + '%)'
    
    zip_fig = px.bar(
        df_z,
        x='Count',
        y='ZIP2',
        color='ZIP2',
        text='text_label',
        orientation='h'
    ).update_layout(
        title=f'Number of {month_name} Clients by Zip Code',
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
    
    # Return all updated values
    return (
        f'{month_name}',
        f'{month_name} Clients Served',
        clients_served,
        f'{month_name} Navigation Hours',
        df_duration,
        f'{month_name} Travel Hours',
        travel_time,
        race_bar, race_pie,
        gender_bar, gender_pie,
        age_bar, age_pie,
        insurance_bar, insurance_pie,
        location_bar, location_pie,
        support_bar, support_pie,
        status_bar, status_pie,
        housing_bar, housing_pie,
        income_bar, income_pie,
        person_bar, person_pie,
        zip_fig
    )

# ======================== Location Drill-Down Callback ======================== #

@app.callback(
    [Output('location-drill-chart', 'figure', allow_duplicate=True),
     Output('location-drill-state', 'data'),
     Output('location-breadcrumb', 'children')],
    [Input('location-drill-chart', 'clickData'),
     Input('location-home-btn', 'n_clicks')],
    [State('location-drill-state', 'data')],
    prevent_initial_call=True
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
                text=f'Coordination Services Provided at {selected_loc}',
                x=0.5,
                font=dict(size=21, family='Calibri', color='black')
            ),
            font=dict(family='Calibri', size=16, color='black'),
            xaxis=dict(
                tickangle=-20,
                tickfont=dict(size=16),
                title=dict(text="Coordination Service", font=dict(size=16)),
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
#     sheet1.merge_range('A1:AE1', f'Client Navigation Report {report_month} {report_year}', header_format)

#     # Set column alignment and width
#     # sheet1.set_column('A:A', 20, left_align_format)  

#     print(f"Navigation Excel file saved to {data_path}")

# --------------------------- KILL PORT ---------------------------------

# netstat -ano | findstr :8050
# taskkill /PID 24772 /F
# npx kill-port 8050


# ------------------------------ Host Application ------------------------------

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