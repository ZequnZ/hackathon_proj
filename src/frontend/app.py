import dash
from dash import Input, Output, State, dcc, html

# Initialize the Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H2("Chat with your Dataset", style={"textAlign": "center", "marginTop": "40px"}),
    dcc.Store(id="chat-history", data=[]),
    html.Div(id="chat-window", style={
        "height": "400px", "overflowY": "auto", "border": "1px solid #ccc", "padding": "10px", "marginBottom": "10px", "background": "#fafafa", "maxWidth": "600px", "margin": "0 auto"
    }),
    html.Div([
        dcc.Input(id="user-input", placeholder="Type your message...", type="text", value="", style={"width": "80%", "padding": "10px", "borderRadius": "8px", "border": "1px solid #ccc"}, autoFocus=True),
        html.Button("Send", id="send-btn", n_clicks=0, style={"width": "18%", "marginLeft": "2%", "padding": "10px", "borderRadius": "8px", "background": "#1976d2", "color": "white", "border": "none"})
    ], style={"display": "flex", "maxWidth": "600px", "margin": "0 auto 40px auto"}),
], style={"maxWidth": "700px", "margin": "0 auto"})

@app.callback(
    Output("chat-history", "data"),
    Output("user-input", "value"),
    Input("send-btn", "n_clicks"),
    State("user-input", "value"),
    State("chat-history", "data"),
    prevent_initial_call=True
)
def update_chat(n_clicks, user_msg, history):
    """Updates the user-input element and chat history when the user sends a message.
    This function is triggered when the user clicks the "Send" button.
    It appends the user's message to the chat history and clears the user-input textbox.
    """
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
    # "chat-history" is the ID of the dcc.Store component that holds the chat history
    # "data" is the property that holds the chat messages
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
