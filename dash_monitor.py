import pandas as pd

def get_logs():
    logs = pd.read_csv("log_mania.csv", names=["input","user","timestamp"], parse_dates=["timestamp"])
    logs.loc[logs["input"].str.contains("%%javascript"),"language"]="javascript"
    logs.loc[~logs["input"].str.contains("%%javascript"),"language"]="python"
    return logs

logs=get_logs()

import ast
def bag_to_trees(logs):
    bag_of_words = logs.input.values

    trees = []
    for cell in bag_of_words:
        try:
            trees += [ast.parse(cell)]
        except SyntaxError:
            pass
    return trees
trees = bag_to_trees(logs)

class Analyzer(ast.NodeVisitor):
    def __init__(self):
        self.stats = {"import": [], "from": []}

    def visit_Import(self, node):
        for alias in node.names:
            self.stats["import"].append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            self.stats["from"].append(alias.name)
        self.generic_visit(node)
def get_stats(logs):     
    analyzer = Analyzer()
    trees = bag_to_trees(logs)
    [analyzer.visit(tree) for tree in trees]
    stats = analyzer.stats
    return stats
stats = get_stats(logs)

import plotly.express as px

def log_fig(logs):
    fig = px.line(logs, x="timestamp", hover_name="input", title="How I Made This Notebook", template="presentation", color="language")
    fig.update_traces(mode='markers+lines')
    return fig

def get_memory():
    memory = pd.read_csv("memory.csv", names=["timestamp","rss"], parse_dates=["timestamp"])
    memory["MB"] = memory.rss/1000**2
    memory["GB"] = memory.MB/1000
    memory["momentum"] = memory.GB.diff().fillna(0)
    memory["speed"] = memory.momentum.abs().shift(-1).fillna(0)
    return memory
memory = get_memory()

def mem_fig(memory):
    mem_fig = px.scatter(memory, x="timestamp", y="GB", color="speed", color_continuous_scale=px.colors.diverging.Spectral,template="presentation", title="Memory Lately")
    return mem_fig

from plotly.subplots import make_subplots
def combined_plot(plot1,plot2):
    combined = make_subplots(specs=[[{"secondary_y": True}]]).update_layout(template="presentation", title="Notebook Profile").update_coloraxes(colorscale="spectral")
    combined.add_traces(plot1.data, secondary_ys=[True,True]).add_trace(plot2.data[0])
    return combined

import dash
import dash_core_components as dcc
import dash_html_components as html

app = dash.Dash("")
app.title = "Notebook Stats"

app.layout = html.Div([
    html.H1(app.title),
    html.Div([
        dcc.Graph(
            figure=combined_plot(log_fig(logs),mem_fig(memory)),
            id="historical-profile"
        ),
        html.H3(
            f"Total Cell Executions: {logs.count()[0]}",
            id="total-executions"
        ),
        html.H3(
            f"Ticks: 0",
            id="ticks"
        )
    ]),
    dcc.Interval(
        id="interval-component",
        interval=5*1000, # in milliseconds
    )
])

from dash.dependencies import Input, Output
@app.callback([
    Output("historical-profile", "figure"),
    Output("total-executions", "children"),
    Output("ticks", "children")
],
    [Input("interval-component", "n_intervals")])
def update_info(n_intervals):
    print(n_intervals)
    logs, memory = get_logs(), get_memory()

    fig = combined_plot(log_fig(logs),mem_fig(memory))
    fig['layout']['uirevision'] = 'some-constant'

    return [fig , f"Total Cell Executions:{logs.count()[0]}", f"Ticks: {n_intervals}"]

app.run_server()