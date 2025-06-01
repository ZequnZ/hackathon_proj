import dash
import requests
from dash import Input, Output, State, dcc, html

# Google Fonts import for modern look
FONT_URL = "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap"

# Initialize the Dash app
app = dash.Dash(__name__)

app.layout = html.Div(
    [
        # Google Fonts link
        html.Link(rel="stylesheet", href=FONT_URL),
        html.H2(
            "Chat with your Dataset",
            style={
                "textAlign": "center",
                "marginTop": "40px",
                "fontFamily": "Inter, sans-serif",
                "fontWeight": 600,
                "fontSize": "2.2rem",
                "color": "#222",
            },
        ),
        dcc.Store(id="chat-history", data=[]),
        dcc.Store(id="all-messages", data=[]),
        html.Div(
            id="chat-window",
            style={
                "height": "420px",
                "overflowY": "auto",
                "border": "none",
                "boxShadow": "0 4px 24px rgba(0,0,0,0.08)",
                "padding": "24px 18px",
                "marginBottom": "18px",
                "background": "linear-gradient(135deg, #f8fafc 0%, #e9f0f7 100%)",
                "maxWidth": "800px",
                "margin": "0 auto",
                "borderRadius": "18px",
                "fontFamily": "Inter, sans-serif",
            },
        ),
        html.Div(
            [
                dcc.Input(
                    id="user-input",
                    placeholder="Type your message...",
                    type="text",
                    value="",
                    style={
                        "width": "80%",
                        "padding": "14px 16px",
                        "borderRadius": "12px 0 0 12px",
                        "border": "1px solid #d1d5db",
                        "fontSize": "1rem",
                        "fontFamily": "Inter, sans-serif",
                        "outline": "none",
                        "background": "#fff",
                    },
                    autoFocus=True,
                ),
                html.Button(
                    "Send",
                    id="send-btn",
                    n_clicks=0,
                    style={
                        "width": "20%",
                        "padding": "14px 0",
                        "borderRadius": "0 12px 12px 0",
                        "background": "#2563eb",
                        "color": "white",
                        "border": "none",
                        "fontWeight": 600,
                        "fontSize": "1rem",
                        "fontFamily": "Inter, sans-serif",
                        "cursor": "pointer",
                        "transition": "background 0.2s",
                    },
                ),
            ],
            style={
                "display": "flex",
                "maxWidth": "760px",
                "margin": "0 auto 36px auto",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.04)",
                "borderRadius": "12px",
                "background": "#f1f5f9",
            },
        ),
    ],
    style={
        "maxWidth": "900px",
        "margin": "0 auto",
        "fontFamily": "Inter, sans-serif",
        "background": "#f3f6fa",
        "minHeight": "100vh",
        "paddingBottom": "40px",
    },
)


@app.callback(
    Output("chat-history", "data"),
    Output("user-input", "value"),
    Output("all-messages", "data"),  # Add output for all_messages
    Input("send-btn", "n_clicks"),
    Input("user-input", "n_submit"),  # Trigger on Enter key
    State("user-input", "value"),
    State("chat-history", "data"),
    State("all-messages", "data"),  # Add state for all_messages
    prevent_initial_call=True,
)
def update_chat(n_clicks, n_submit, user_msg, history, all_messages):  # noqa: C901
    """Updates the user-input element and chat history when the user sends a message.
    This function is triggered when the user clicks the "Send" button.
    It appends the user's message to the chat history and clears the user-input textbox.
    Persists all_messages from backend in dcc.Store.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, "", dash.no_update
    if not user_msg or user_msg.strip() == "":
        return dash.no_update, "", dash.no_update
    history = history or []
    history.append({"type": "user", "content": user_msg})

    all_messages.append({"type": "user", "content": user_msg})
    try:
        payload = {
            "messages": all_messages,
            "result": "string",
            "visual_created": False,
            "follow_up_question": "string",
        }
        response = requests.post(
            "http://127.0.0.1:8002/chat/ask_agent",
            json=payload,
            timeout=60,
        )
        valid_response_keys = [
            "type",
            "content",
            "tool_calls",
            "tool_call_id",
        ]
        if response.status_code == 200:
            last_message = response.json().get("result", "(No response from backend)")
            all_messages = response.json()["messages"]
            encoded_image = response.json().get("visualization_image", None)
            html_img_tag = f'<img src="data:image/png;base64,{encoded_image}" />'
            follow_up_question = response.json().get("follow_up_question", None)
            new_messages = []
            for msg in all_messages:
                if msg["type"] == "system":
                    continue
                new_msg = {}
                for valid_key in valid_response_keys:
                    if valid_key in msg:
                        new_msg[valid_key] = msg[valid_key]

                new_messages.append(new_msg)

            all_messages = new_messages

            history.append({"type": "ai", "content": last_message})
            if encoded_image:
                history.append(
                    {
                        "type": "ai",
                        "content": html_img_tag,
                        "visualization_image": encoded_image,
                    }
                )
            if follow_up_question:
                history.append(
                    {
                        "type": "ai",
                        "content": f"<b>Follow-up questions:</b><br/>{follow_up_question}",
                        "follow_up_question": follow_up_question,
                    }
                )
                all_messages.append(
                    {
                        "type": "ai",
                        "content": html_img_tag,
                        "visualization_image": encoded_image,
                    }
                )
        else:
            last_message = f"(Backend error: {response.status_code})"
            all_messages = dash.no_update
            history.append({"type": "ai", "content": last_message})
    except Exception as e:
        last_message = f"(Backend error: {str(e)})"
        all_messages = dash.no_update
        history.append({"type": "ai", "content": last_message})

    return history, "", all_messages


@app.callback(
    Output("chat-window", "children"),
    # "chat-history" is the ID of the dcc.Store component that holds the chat history
    # "data" is the property that holds the chat messages
    Input("chat-history", "data"),
)
def render_chat(history):
    if not history:
        return html.Div(
            "No messages yet. Start the conversation!",
            style={
                "color": "#888",
                "fontStyle": "italic",
                "textAlign": "center",
                "marginTop": "120px",
                "fontSize": "1.1rem",
            },
        )
    messages = []
    for msg in history:
        is_user = msg["type"] == "user"
        align = "right" if is_user else "left"
        color = "#2563eb" if is_user else "#f1f5f9"
        text_color = "#fff" if is_user else "#222"
        bubble_style = {
            "background": color,
            "color": text_color,
            "padding": "12px 18px",
            "borderRadius": "16px",
            "maxWidth": "70%",
            "display": "inline-block",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.04)",
            "fontSize": "1rem",
            "fontFamily": "Inter, sans-serif",
            "margin": "2px 0",
        }
        wrapper_style = {
            "textAlign": align,
            "margin": "12px 0",
            "display": "flex",
            "justifyContent": "flex-end" if is_user else "flex-start",
        }
        messages.append(
            html.Div(
                dcc.Markdown(
                    msg["content"], dangerously_allow_html=True, style=bubble_style
                ),
                style=wrapper_style,
            )
        )

    return messages


if __name__ == "__main__":
    app.run(debug=True)
