"""Launch from the repository root: chainlit run chainlit_app.py -w."""

# Importing the frontend registers its Chainlit lifecycle handlers.
from frontend.chainlit_app import handle_message, start_chat

from frontend.team_api import register_routes
register_routes()
