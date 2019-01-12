import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import pymysql
import plotly.graph_objs as go
from dash.dependencies import Input, Output

#Set external stylesheet
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

#Set up connection to db
db = pymysql.connect(host="localhost", user="testUser", passwd="BorrisBulletDodger", db="allItems", charset='utf8')
cursor = db.cursor()

#Store data in dataframe
try:
    sql = "SELECT * FROM motorcycles WHERE adExpiry IS NOT NULL"# AND displacement = 300"
    df = pd.read_sql(sql, db)
    print(df)
finally:
    db.close()






app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    dcc.Graph(
        id='graph1',
        figure={
            'data': [go.Scatter(
                x=df['kms'],
                y=df['price'],
                mode='markers',
                marker={
                    'size': 15,
                    'opacity': 0.5,
                }
            )]
        }
    )
])


if __name__ == '__main__':
    app.run_server(debug=True)