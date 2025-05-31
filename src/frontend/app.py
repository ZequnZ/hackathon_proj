import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = dbc.Container([
    html.H2("Chat with your Dataset"),
    dcc.Store(id="chat-history", data=[]),
    html.Div(id="chat-window", style={
        "height": "400px", "overflowY": "auto", "border": "1px solid #ccc", "padding": "10px", "marginBottom": "10px"
    }),
    dbc.InputGroup([
        dbc.Input(id="user-input", placeholder="Type your message...", type="text", autoFocus=True),
        dbc.Button("Send", id="send-btn", n_clicks=0, color="primary")
    ]),
], style={"maxWidth": "600px", "marginTop": "40px"})

@app.callback(
    Output("chat-history", "data"),
    Output("user-input", "value"),
    Input("send-btn", "n_clicks"),
    State("user-input", "value"),
    State("chat-history", "data"),
    prevent_initial_call=True
)
def update_chat(n_clicks, user_msg, history):
    if not user_msg or user_msg.strip() == "":
        return dash.no_update, ""
    # Append user message
    history = history or []
    history.append({"role": "user", "content": user_msg})
    # Simulate AI response (replace with backend call as needed)
    ai_response = f"You said: {user_msg} (AI response placeholder)"
    history.append({"role": "ai", "content": ai_response})
    return history, ""

@app.callback(
    Output("chat-window", "children"),
    Input("chat-history", "data")
)
def render_chat(history):
    if not history:
        return html.Div("No messages yet. Start the conversation!")
    messages = []
    for msg in history:
        align = "left" if msg["role"] == "user" else "right"
        color = "#e1f5fe" if msg["role"] == "user" else "#c8e6c9"
        messages.append(
            html.Div([
                html.Span(msg["content"], style={"background": color, "padding": "8px 12px", "borderRadius": "12px"})
            ], style={"textAlign": align, "margin": "8px 0"})
        )
    return messages

if __name__ == "__main__":
    app.run(debug=True)
