
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import itertools
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, dash_table, callback, Patch
from base64 import b64encode


app = Dash(__name__)

sum_file = f'/data/sum_file.csv'
df = pd.read_csv(sum_file)
df.drop(columns=['Unnamed: 0'], inplace=True)

op = [{'label': i, 'value': i} for i in df.columns]
fig = px.box(df, x='model', y='auc_prob', color='gen')

# buffer = io.StringIO()
# app.to_html(buffer)

# html_bytes = buffer.getvalue().encode()
# encoded = b64encode(html_bytes).decode()

app.layout = html.Div([
    # html.H4("AUC by configuration"),
    html.Div([
        html.H4("AUC by configuration"),
        html.P("Filter by:"),
        dcc.Checklist(
            id='filter-by', 
            options=[{'label': i, 'value': i} for i in ["subset", "gen", "model"]], 
            value=[], 
            inline=True
        ),
        dcc.Dropdown(id='filter-options', options=[], multi=False),
    # ]),
    # html.Div([
        html.P("x-axis:"),
        dcc.Dropdown(
            id='x-axis', 
            options=op,
            value='model', 
         #   inline=True
        ),
        html.P("y-axis:"),
        dcc.Dropdown(
            id='y-axis', 
            options=op, 
            value='auc_prob', 
        ),
        html.P("color:"),
        dcc.Dropdown(
            id='color', 
            options=op, 
            value='gen', 
        )
    ], style={'padding': 10, 'flex': 1}),
    html.Div([
        dash_table.DataTable(id='table', data=df.to_dict('records'), page_size=5, style_table={'overflowX': 'auto'}),
        dcc.Graph(id="graph", figure=fig)
    ])
], style={'display': 'flex', 'flexDirection': 'row'})

@app.callback(
    Output("filter-options", "options"),
    Input("filter-by", "value")
)
def update_filter_options(filter_by):
    if filter_by:
       filter_options=np.unique(df[filter_by])
       return filter_options
    else:
        return []

@app.callback(
    Output("table", "data"), 
    Output("graph", "figure"), 
    Input("x-axis", "value"), 
    Input("y-axis", "value"),
    Input("color", "value"),
    Input("filter-by", "value"),
    Input("filter-options", "value")
)
def update_output(x, y, color, filter_by, filter_value):
    if filter_value:
        patched_fig = Patch()
        filter_value=str(filter_value)
        filter_by= filter_by[0]
        # Filter rows where the selected column equals the selected value
        filtered_df = df[df[filter_by] == filter_value]
        patched_fig = px.box(data_frame=filtered_df, x=x, y=y, color=color)
        return filtered_df.to_dict('records'), patched_fig
    else:
        fig = px.box(data_frame=df, x=x, y=y, color=color)

    # Return the data for the table and the figure
        return df.to_dict('records'), fig

if __name__ == '__main__':
    app.run_server(debug=True, port=4000)
