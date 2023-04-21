from dotenv import load_dotenv
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import mysql.connector
import psycopg2
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import os
import plotly
import plotly.graph_objs as go
import plotly.express as px

load_dotenv("./src/kpi_app/.env.local")

db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database="serlo",
    charset="latin1",
)


def cached(func):
    cache = dict()

    def return_func(arg):
        if arg in cache:
            return cache[arg]
        else:
            result = func(arg)
            cache[arg] = result
            return result

    return return_func


def query(sql):
    c = db.cursor()
    c.execute(sql)

    return c.fetchall()


def querySingleton(sql):
    return [x[0] for x in query(sql)]


@cached
def getParent(termId):
    return querySingleton(
        """
        select parent_id from term_taxonomy where id = %s;
    """
        % termId
    )[0]


def getTermName(termId):
    return querySingleton(
        """
        select term.name from term_taxonomy
        join term on term.id = term_taxonomy.term_id
        where term_taxonomy.id = %s;
    """
        % termId
    )[0]


@cached
def getSubject(termId):
    if int(termId) in [
        79733,
        81317,
        20852,
        87814,
        87827,
        85477,
        87860,
        75049,
        76750,
        87496,
        75678,
        91252,
        91253,
    ]:
        return "Prüfungsbereich Mathematik"
    if int(termId) in [106082]:
        return getTermName(termId)

    parent = getParent(termId)
    grandparent = getParent(parent)

    if parent == 106081:
        return getTermName(termId)

    return getSubject(parent) if grandparent != None else getTermName(termId)


@cached
def getSubjectFromUuid(uuid):
    taxonomyTerms = querySingleton(
        f"""
        select term_taxonomy_id from term_taxonomy_entity
        where term_taxonomy_entity.entity_id  = {uuid};
    """
    )

    if len(taxonomyTerms) > 0:
        return getSubject(taxonomyTerms[0])

    parents = querySingleton(
        f"""
        select parent_id from entity_link
        where entity_link.child_id  = {uuid};
    """
    )

    if len(parents) > 0:
        return getSubjectFromUuid(parents[0])

    return None


def read_event_log_edits():
    df = pd.read_sql(
        """
        select event_log.id, event_log.actor_id, event_log.date, user.username, event_parameter_uuid.uuid_id from event_log
        join user on user.id = event_log.actor_id
        join event_parameter on event_parameter.log_id = event_log.id
        join event_parameter_uuid on event_parameter_uuid.event_parameter_id = event_parameter.id
        where event_log.event_id = 5
        and year(event_log.date) > 2018
        and user.username != "Legacy"
    """,
        db,
    )
    df.set_index("id", inplace=True)
    df.rename(columns={"uuid_id": "uuid"}, inplace=True)
    df["subject"] = df["uuid"].map(getSubjectFromUuid)
    return df


event_log_edits = read_event_log_edits()

# Connect to the database
user_db = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    database="kratos",
)


# Define a function to execute SQL queries
def user_query(sql):
    cursor = user_db.cursor()
    cursor.execute(sql)
    return cursor.fetchall()


# Execute the SQL query to select the desired columns from the "identities" table
results = user_query(
    "SELECT traits ->> 'username', (metadata_public ->> 'legacy_id')::int, traits ->> 'interest' FROM identities;"
)

# Convert the results to a pandas dataframe
df = pd.DataFrame(results, columns=["username", "legacy_id", "interest"])


# Führe den Join durch und speichere das Ergebnis in einer neuen Variablen
merged_df_edits = pd.merge(
    event_log_edits, df, left_on="actor_id", right_on="legacy_id"
)
merged_df_edits = merged_df_edits.drop(["legacy_id", "username_y"], axis=1)
merged_df_edits = merged_df_edits.rename(columns={"username_x": "username"})
merged_df_edits


def Anzahl_Autorinnen(
    days=90, edits=10, week=0, year=0, days2=0, interest="all", subject="all"
):
    lower_date = pd.Timestamp.today() - pd.Timedelta(
        days=days + days2 + week * 7 + year * 365
    )
    upper_date = pd.Timestamp.today() - pd.Timedelta(days=days2 + week * 7 + year * 365)

    df2 = merged_df_edits[
        (lower_date < merged_df_edits["date"]) & (upper_date > merged_df_edits["date"])
    ]

    if interest == "teacher":
        df2 = df2.loc[df2["interest"].isin(["teacher"])]
    elif interest == "no teachers":
        df2 = df2.loc[df2["interest"].isin([""])]

    if subject != "all":
        df2 = df2.loc[df2["subject"].isin([subject])]

    df2 = df2.reset_index()
    df3 = df2.groupby(by=["actor_id", "username"], as_index=False).count()
    # Delete all authors under baseline
    df4 = df3
    df4["isActive"] = df4["uuid"].apply(lambda x: 1 if x >= edits else 0)

    return df4[df4.isActive == 1].actor_id.count()


def Anzahl_aller_Bearbeitungen(
    days=90, week=0, year=0, days2=0, interest="all", subject="all"
):
    lower_date = pd.Timestamp.today() - pd.Timedelta(
        days=days + days2 + week * 7 + year * 365
    )
    upper_date = pd.Timestamp.today() - pd.Timedelta(days=days2 + week * 7 + year * 365)

    df2 = merged_df_edits[
        (lower_date < merged_df_edits["date"]) & (upper_date > merged_df_edits["date"])
    ]

    if interest == "teacher":
        df2 = df2.loc[df2["interest"].isin(["teacher"])]
    elif interest == "no teachers":
        df2 = df2.loc[df2["interest"].isin([""])]

    if subject != "all":
        df2 = df2.loc[df2["subject"].isin([subject])]

    df2 = df2.reset_index()

    return df2.actor_id.count()


def one_year_dates(days=365, year=0):
    lower_date = pd.Timestamp.today() - pd.Timedelta(days=days + year * 365)
    upper_date = pd.Timestamp.today() - pd.Timedelta(days=year * 365)

    one_year_dates = []
    current_date = lower_date + relativedelta(days=1)

    while current_date <= upper_date:
        one_year_dates.append(current_date)
        current_date += relativedelta(days=1)

    return one_year_dates


def new_range(days=365):
    return list(reversed(range(days)))


def read_event_log_contents():
    df = pd.read_sql(
        """
        select event_log.id, event_log.actor_id, event_log.date, user.username from event_log
        join user on user.id = event_log.actor_id
        where event_log.event_id = 4
        and year(event_log.date) > 2018
        and user.username != "Legacy"
    """,
        db,
    )
    return df


event_log_contents = read_event_log_contents()


merged_df_contents = pd.merge(
    event_log_contents, df, left_on="actor_id", right_on="legacy_id"
)
merged_df_contents = merged_df_contents.drop(["legacy_id", "username_y"], axis=1)
merged_df_contents = merged_df_contents.rename(columns={"username_x": "username"})
merged_df_contents


def Anzahl_erstellter_Inhalte(days=90, week=0, year=0, days2=0, interest="all"):
    lower_date = pd.Timestamp.today() - pd.Timedelta(
        days=days + days2 + week * 7 + year * 365
    )
    upper_date = pd.Timestamp.today() - pd.Timedelta(days=days2 + week * 7 + year * 365)

    df2 = merged_df_contents[
        (lower_date < merged_df_contents["date"])
        & (upper_date > merged_df_contents["date"])
    ]

    if interest == "teacher":
        df2 = df2.loc[df2["interest"].isin(["teacher"])]
    elif interest == "no teachers":
        df2 = df2.loc[df2["interest"].isin([""])]

    df2 = df2.reset_index()

    return df2.actor_id.count()


external_stylesheets = [
    "https://codepen.io/chriddyp/pen/bWLwgP.css",
    dbc.themes.BOOTSTRAP,
]
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://use.fontawesome.com/releases/v5.7.2/css/all.css",
    ],
    title="Serlo KPI Dashboard",
)

# CSS-Stile definieren
header_style = {"font-size": "54px", "color": "black", "text-align": "center"}
Überschrift = html.H1("Serlo KPI dashboard", style=header_style)

# Header


image_url = (
    "https://de.serlo.org/_assets/img/serlo-logo.svg"  # Hier Ihre Bild-URL angeben
)
image_style = {
    "height": "100px",
    "width": "100px",
    "margin-right": "20px",
}  # Hier die Größe des Bildes festlegen

# Dropdown menus

# 1
dropdown_options = [
    {"label": "edits > 1: alle Autor*innen", "value": 1},
    {"label": "edits > 10: aktive Autor*innen", "value": 10},
    {"label": "edits > 100: sehr aktive Autor*innen", "value": 100},
]
# dropdown = dcc.Dropdown(id="edit-selector", options=dropdown_options, value=1, placeholder="# edits")

header_style = {
    "display": "flex",
    "flex-direction": "row",
    "align-items": "center",
    "justify-content": "space-between",
}
dropdown_style = {"flex-grow": "1", "margin-left": "10px", "width": "300px"}

# 2
drop_options = [
    {"label": "alle", "value": "all"},
    {"label": "Lehrer*innen", "value": "teacher"},
    {"label": "keine Lehrer*innen", "value": "no teachers"},
]

# 3
liste = [subject for subject in merged_df_edits["subject"].unique()]
new_list = list(filter(None, liste))
subject_options = [{"label": subject, "value": subject} for subject in new_list]
subject_options.insert(0, {"label": "alle", "value": "all"})

header = html.Div(
    children=[
        html.Img(src=image_url, style=image_style),
        dcc.Dropdown(
            id="edit-selector",
            options=dropdown_options,
            value=1,
            className="edit-selector",
            style=dropdown_style,
            placeholder="# edits",
        ),
        dcc.Dropdown(
            id="interest-selector",
            options=drop_options,
            value="all",
            className="edit-selector",
            style=dropdown_style,
            placeholder="Lehrer*in ?",
        ),
        dcc.Dropdown(
            id="subject-selector",
            options=subject_options,
            value="all",
            style=dropdown_style,
            placeholder="Fach",
        ),
    ],
    style=header_style,
)


# KPIs


def create_card(title, content1, content2):
    sign = ""
    if content1 > content2:
        sign = "+"

    relative_change = round((content1 - content2) * 100 / content2)

    color = "black"
    if content1 > content2:
        color = "#229954"
    if content2 > content1:
        color = "#A93226"

    card = dbc.Card(
        dbc.CardBody(
            [
                html.H4(title, className="card-title", style={"text-align": "center"}),
                html.Br(),
                html.Br(),
                html.H2(
                    content1,
                    className="card-subtitle",
                    style={
                        "font-size": "54px",
                        "font-weight": "bold",
                        "text-align": "center",
                    },
                ),
                html.Br(),
                html.Br(),
                html.P(
                    [
                        f"letztes Jahr: {content2} ",
                        html.Span(
                            f"({sign}{relative_change}%)", style={"color": color}
                        ),
                    ],
                    style={"text-align": "center", "font-size": "34px"},
                ),
            ]
        ),
        className="rounded",  # Ändere die Kartenform auf abgerundete Kante
        color="#D6EAF8",
    )
    return card


def create_card_Autorinnen(edits=10, interest="all", subject="all"):
    var_1 = Anzahl_Autorinnen(
        days=90,
        edits=edits,
        week=0,
        year=0,
        days2=0,
        interest=interest,
        subject=subject,
    )
    var_2 = Anzahl_Autorinnen(
        days=90,
        edits=edits,
        week=0,
        year=1,
        days2=0,
        interest=interest,
        subject=subject,
    )

    sign = ""
    if var_1 > var_2:
        sign = "+"

    relative_change = round((var_1 - var_2) * 100 / var_2)

    color = "black"
    if var_1 > var_2:
        color = "#229954"
    if var_2 > var_1:
        color = "#A93226"

    title = "alle Autor*innen"
    if edits == 10:
        title = "aktive Autor*innen (edits > 10)"
    if edits == 100:
        title = "sehr aktive Autor*innen (edits > 100)"

    card = dbc.Card(
        dbc.CardBody(
            [
                html.H4(title, className="card-title", style={"text-align": "center"}),
                html.Br(),
                html.Br(),
                html.H2(
                    var_1,
                    className="card-subtitle",
                    style={
                        "font-size": "54px",
                        "font-weight": "bold",
                        "text-align": "center",
                    },
                ),
                html.Br(),
                html.Br(),
                html.P(
                    [
                        f"letztes Jahr: {var_2} ",
                        html.Span(
                            f"({sign}{relative_change}%)", style={"color": color}
                        ),
                    ],
                    style={"text-align": "center", "font-size": "34px"},
                )
                # ''', style={"text-align": "center", "font-size": "24px"}))
            ]
        ),
        className="rounded",  # Ändere die Kartenform auf abgerundete Kante
        color="#D6EAF8",
    )
    return card


# def create_card_Bearbeitungen(interest="all", subject="all"):
#     var_1 = Anzahl_aller_Bearbeitungen(days=90, week=0, year=0, days2=0, interest=interest, subject=subject)
#     var_2 = Anzahl_aller_Bearbeitungen(days=90, week=0, year=1, days2=0, interest=interest, subject=subject)
#
#     sign = ""
#     if var_1 > var_2:
#         sign = "+"
#
#     relative_change = round((var_1 - var_2) * 100 / var_2)
#
#     color = "black"
#     if var_1 > var_2:
#         color = "#229954"
#     if var_2 > var_1:
#         color = "#A93226"
#
#     title = "alle Autor*innen"
#     if edits == 10:
#         title = "aktive Autor*innen (edits > 10)"
#     if edits == 100:
#         title = "sehr aktive Autor*innen (edits > 100)"
#
#     card = dbc.Card(
#         dbc.CardBody([
#
#             html.H4(title, className="card-title", style={"text-align": "center"}),
#             html.Br(),
#             html.Br(),
#             html.H2(var_1, className="card-subtitle",
#                     style={"font-size": "54px", "font-weight": "bold", "text-align": "center"}),
#             html.Br(),
#             html.Br(),
#
#             html.P(
#                 [
#                     f"letztes Jahr: {var_2} ",
#                     html.Span(f"({sign}{relative_change}%)", style={"color": color})
#                 ],
#                 style={"text-align": "center", "font-size": "34px"}
#             )
#
#             # ''', style={"text-align": "center", "font-size": "24px"}))
#         ]
#         ),
#
#         className="rounded",  # Ändere die Kartenform auf abgerundete Kante
#         color='#D6EAF8'
#
#     )
#     return (card)


card1 = html.Div(id="card-output_1")

card2 = html.Div(id="card-output_2")

card3 = html.Div(id="card-output_3")


# card1 = create_card("Autor*innen", Anzahl_Autorinnen(days=90, edits=10, week=0, year=0, days2=0),
# Anzahl_Autorinnen(days=90, edits=10, week=0, year=1, days2=0))

# card2 = create_card("Bearbeitungen", Anzahl_aller_Bearbeitungen(days=90, week=0, year=0, days2=0),
# Anzahl_aller_Bearbeitungen(days=90, week=0, year=1, days2=0))


# card3 = create_card("erstellte Inhalte", Anzahl_erstellter_Inhalte(days=90, week=0, year=0, days2=0),
# Anzahl_erstellter_Inhalte(days=90, week=0, year=1, days2=0))

# Card Callbacks


@app.callback(
    Output("card-output_1", "children"),
    [
        Input("edit-selector", "value"),
        Input("interest-selector", "value"),
        Input("subject-selector", "value"),
    ],
)
def update_card_1(edit_selector_value, interest_selector_value, subject_selector_value):
    card = create_card_Autorinnen(
        edit_selector_value, interest_selector_value, subject_selector_value
    )
    return card


@app.callback(
    Output("card-output_2", "children"),
    [Input("interest-selector", "value"), Input("subject-selector", "value")],
)
def update_card_2(var_1, var_2):
    card = create_card(
        "Bearbeitungen",
        Anzahl_aller_Bearbeitungen(
            days=90, week=0, year=0, days2=0, interest=var_1, subject=var_2
        ),
        Anzahl_aller_Bearbeitungen(
            days=90, week=0, year=1, days2=0, interest=var_1, subject=var_2
        ),
    )
    return card


@app.callback(
    Output("card-output_3", "children"), [Input("interest-selector", "value")]
)
def update_card_3(var):
    card = create_card(
        "erstellte Inhalte",
        Anzahl_erstellter_Inhalte(days=90, week=0, year=0, days2=0, interest=var),
        Anzahl_erstellter_Inhalte(days=90, week=0, year=1, days2=0, interest=var),
    )
    return card


KPI_Row = dbc.Row(
    [
        dbc.Col(id="card1", children=[card1], md=4),
        dbc.Col(id="card2", children=[card2], md=4),
        dbc.Col(id="card3", children=[card3], md=4),
    ]
)

# Graphs


# fig2 = px.line(x=one_year_dates(days=365), y=[Anzahl_aller_Bearbeitungen(days2=i) for i in new_range(days=365)],
# title='Bearbeitungen / 90 Tage')

# fig3 = px.line(x=one_year_dates(days=365), y=[Anzahl_erstellter_Inhalte(days2=i) for i in new_range(days=365)],
# title='erstellte Inhalte / 90 Tage')

# fig2.update_layout(plot_bgcolor='#ECF2FF', paper_bgcolor='#ECF2FF')
# fig3.update_layout(plot_bgcolor='#ECF2FF', paper_bgcolor='#ECF2FF')

graph1 = dcc.Graph(id="graph_1")

graph2 = dcc.Graph(id="graph_2")

graph3 = dcc.Graph(id="graph_3")


def create_figure_Autorinnen(edits=10, interest="all", subject="all"):
    figure = px.line(
        x=one_year_dates(days=365),
        y=[
            Anzahl_Autorinnen(days2=i, edits=edits, interest=interest, subject=subject)
            for i in new_range(days=365)
        ],
        title="Autor*Innen / 90 Tage",
    )
    figure.update_layout(plot_bgcolor="#ECF2FF", paper_bgcolor="#ECF2FF")
    return figure


@app.callback(
    Output("graph_1", "figure"),
    [
        Input("edit-selector", "value"),
        Input("interest-selector", "value"),
        Input("subject-selector", "value"),
    ],
)
def update_figure(var_1, var_2, var_3):
    figure = create_figure_Autorinnen(var_1, var_2, var_3)

    return figure


def create_figure_Bearbeitungen(interest="all", subject="all"):
    figure = px.line(
        x=one_year_dates(days=365),
        y=[
            Anzahl_aller_Bearbeitungen(days2=i, interest=interest, subject=subject)
            for i in new_range(days=365)
        ],
        title="Bearbeitungen / 90 Tage",
    )
    figure.update_layout(plot_bgcolor="#ECF2FF", paper_bgcolor="#ECF2FF")
    return figure


@app.callback(
    Output("graph_2", "figure"),
    [Input("interest-selector", "value"), Input("subject-selector", "value")],
)
def update_figure(var_1, var_2):
    figure = create_figure_Bearbeitungen(var_1, var_2)

    return figure


def create_figure_Inhalte(interest="all"):
    figure = px.line(x=one_year_dates(days=365),
                     y=[Anzahl_erstellter_Inhalte(days2=i, interest=interest)
                        for i in new_range(days=365)],
                     title='erstellte Inhalte / 90 Tage')
    figure.update_layout(plot_bgcolor='#ECF2FF', paper_bgcolor='#ECF2FF')
    return figure


@app.callback(
    Output('graph_3', 'figure'),
    [Input("interest-selector", 'value')]
)
def update_figure(var):
    figure = create_figure_Inhalte(var)

    return figure


graph_Row = dbc.Row([dbc.Col(graph1, md=4), dbc.Col(graph2, md=4), dbc.Col(graph3, md=4)])

app.layout = html.Div(

    [header, KPI_Row, graph_Row],

    style={'backgroundColor': 'white'}
    # style={'backgroundColor':'#F7C8E0'}

)


# Run the app
if __name__ == '__main__':
    app.run_server()