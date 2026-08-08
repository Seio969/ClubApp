"""Shared Qt styles for the UI.

Centralize all stylesheet strings and small widget font styles here so the
UI files remain focused on layout and behaviour. Keep these strings simple
and import them where needed.
"""

from __future__ import annotations

from typing import Final

# Main menu stylesheet (moved from MainMenuWidget)
MAIN_MENU_STYLESHEET: Final[str] = r"""
/* Solid black background for the main menu */
#mainMenu {
    background-color: #000000;
}

/* Title and subtitle styling */
#title {
    color: #ffffff;
    letter-spacing: 1px;
    font-family: "SF Pro Display", sans-serif;
}
#subtitle {
    color: #cfe8e6;
    font-size: 14px;
}

/* Buttons: modern rounded gradient with hover/pressed states */
QPushButton {
    color: #000000;
    /* Darker green gradient */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #245c1a, stop:1 #388e3c);
    border: none;
    border-radius: 10px;
    padding: 10px 18px;
}
QPushButton:hover {
    /* Slightly brighter dark green on hover */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2e7031, stop:1 #43a047);
}
QPushButton:pressed {
    /* Even darker green when pressed */
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1b3c13, stop:1 #2e7031);
}
QPushButton:disabled {
    background: #666b75;
    color: #cfcfcf;
}
"""

# Members view stylesheet (moved from MembersMenuView)
MEMBERS_MENU_STYLESHEET: Final[str] = r"""
#membersMenu { background: #fafafa; }
#topBar { background: transparent; }
#viewsLabel { font-weight: 600; margin-right: 6px; }
QPushButton { min-width: 90px; min-height: 28px; }
#backButton { 
    background-color: #f0f0f0; 
    border: 1px solid #ccc; 
    border-radius: 4px; 
    font-weight: bold;
    color: #333;
}
#backButton:hover { 
    background-color: #e0e0e0; 
    border-color: #999; 
}
#backButton:pressed { 
    background-color: #d0d0d0; 
}
/* Results table: white rows with a subtle alternate row color and black text */
#resultsTable {
    background: #ffffff;
    /* Ensure table cell text is black */
    color: #000000;
    /* Qt supports alternatingRowColors when set on the view; this provides the
       alternate row color used when QTableView.setAlternatingRowColors(True) */
    alternate-background-color: #f6f6f6;
}
/* Also make sure individual table items keep black text (normal/alternate) */
#resultsTable QTableView::item {
    color: #000000;
}
/* Make sure header section text is also black */
#resultsTable QHeaderView::section {
    color: #000000;
}
"""

# Small per-widget styles that were previously set inline
TITLE_STYLE: Final[str] = "font-size: 35px; font-weight: 700;"
BUTTON_FONT_STYLE: Final[str] = "font-size: 20px;"
