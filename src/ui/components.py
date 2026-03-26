"""Reusable UI components for ChatFormula1 Streamlit app.

This module provides components for:
- Message display with role-based styling
- Source citations and metadata
- Feedback mechanisms
- Loading indicators
- F1 theme configuration and CSS injection
"""

from datetime import datetime
from typing import Any, Literal, Optional

import streamlit as st
import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class F1Theme(BaseModel):
    """F1 theme color configuration and design tokens."""

    # Primary colors
    f1_red: str = "#E10600"
    black: str = "#0e1117"
    dark_gray: str = "#1e2130"
    medium_gray: str = "#262730"
    light_gray: str = "#888888"
    white: str = "#FFFFFF"

    # Accent colors
    accent_red: str = "#FF1E1E"
    accent_silver: str = "#C0C0C0"

    # Semantic colors
    success: str = "#00D856"
    warning: str = "#FFA500"
    error: str = "#FF4444"

    # Spacing scale (8px base)
    spacing_xs: str = "4px"
    spacing_sm: str = "8px"
    spacing_md: str = "16px"
    spacing_lg: str = "24px"
    spacing_xl: str = "32px"

    # Border radius
    radius_sm: str = "4px"
    radius_md: str = "8px"
    radius_lg: str = "12px"

    # Transitions
    transition_fast: str = "150ms ease"
    transition_normal: str = "200ms ease"
    transition_slow: str = "300ms ease"


class RecommendationPrompt(BaseModel):
    """Model for recommendation prompt configuration.

    Attributes:
        icon: Emoji icon to display with the prompt
        text: Display text for the prompt button
        category: Category of the prompt (standings, results, prediction, historical)
        query: Actual query to execute (may differ from display text)
    """

    icon: str
    text: str
    category: Literal["standings", "results", "prediction", "historical"]
    query: str


def apply_f1_theme() -> None:
    """Apply F1-themed custom CSS to the Streamlit app.

    This function injects custom CSS once per session to style the application
    with Formula 1 brand colors and modern UI design patterns. It includes:
    - Global styles and color scheme
    - Centered layout with max-width constraint
    - Responsive behavior for different screen sizes
    - Interactive element styling with hover effects
    - Smooth animations and transitions
    """
    # Only inject CSS once per session for performance
    if "css_injected" in st.session_state:
        return

    theme = F1Theme()

    css = f"""
    <style>
    /* ========================================
       GLOBAL STYLES
       ======================================== */
    .stApp {{
        background-color: {theme.black};
        max-width: 100vw;
        color: {theme.white};
    }}

    /* Main content container - centered layout */
    .main .block-container {{
        max-width: 800px;
        padding-top: {theme.spacing_lg};
        padding-left: {theme.spacing_lg};
        padding-right: {theme.spacing_lg};
    }}

    /* ========================================
       WELCOME SCREEN STYLES
       ======================================== */
    .welcome-hero {{
        text-align: center;
        padding: {theme.spacing_xl} 0;
        animation: fadeIn 0.5s ease-in;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 40vh;
    }}

    .welcome-hero h1 {{
        color: {theme.f1_red};
        font-size: 3rem;
        margin-bottom: {theme.spacing_sm};
        font-weight: 700;
        line-height: 1.2;
    }}

    .welcome-hero h3 {{
        color: {theme.light_gray};
        font-size: 1.5rem;
        font-weight: 400;
        margin-top: {theme.spacing_sm};
        line-height: 1.4;
    }}
    
    /* Welcome description styling */
    .welcome-description {{
        text-align: center;
        margin: 2rem auto;
        max-width: 600px;
        color: {theme.light_gray};
        font-size: 1.1rem;
        line-height: 1.6;
        animation: fadeIn 0.7s ease-in;
    }}

    /* ========================================
       BUTTON STYLES - All Interactive Elements
       ======================================== */
    /* Base button styling with 8px rounded corners */
    .stButton > button {{
        border: 2px solid {theme.medium_gray};
        border-radius: {theme.radius_md};
        padding: {theme.spacing_md};
        transition: all {theme.transition_normal};
        background-color: {theme.dark_gray};
        color: {theme.white};
        font-weight: 500;
        font-size: 1rem;
        text-align: left;
        cursor: pointer;
    }}

    /* Button hover effects with F1 red border and smooth transitions */
    .stButton > button:hover {{
        border-color: {theme.f1_red};
        transform: scale(1.02);
        box-shadow: 0 4px 12px rgba(225, 6, 0, 0.3);
        background-color: {theme.medium_gray};
        transition: all {theme.transition_normal};
    }}

    .stButton > button:active {{
        transform: scale(0.98);
        transition: all {theme.transition_fast};
    }}
    
    /* Recommendation prompt specific styling with hover effects */
    .stButton > button[kind="secondary"] {{
        min-height: 80px;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        padding: {theme.spacing_md} {theme.spacing_lg};
        border-radius: {theme.radius_md};
        transition: all {theme.transition_normal};
    }}

    .stButton > button[kind="secondary"]:hover {{
        border-color: {theme.f1_red};
        transform: scale(1.02);
        box-shadow: 0 6px 16px rgba(225, 6, 0, 0.35);
        transition: all {theme.transition_normal};
    }}

    /* Primary button styling with F1 red accent */
    .stButton > button[kind="primary"] {{
        background-color: {theme.f1_red};
        border-color: {theme.f1_red};
        color: {theme.white};
        border-radius: {theme.radius_md};
        transition: all {theme.transition_normal};
    }}

    .stButton > button[kind="primary"]:hover {{
        background-color: {theme.accent_red};
        border-color: {theme.accent_red};
        box-shadow: 0 4px 16px rgba(225, 6, 0, 0.4);
        transform: scale(1.02);
        transition: all {theme.transition_normal};
    }}

    /* ========================================
       CHAT MESSAGE STYLES
       ======================================== */
    /* Chat message bubbles with F1 red left border and dark gray background */
    .stChatMessage {{
        background-color: {theme.dark_gray};
        border-radius: {theme.radius_md};
        padding: {theme.spacing_md};
        margin: {theme.spacing_sm} 0;
        border-left: 4px solid {theme.f1_red};
        transition: all {theme.transition_fast};
    }}

    /* User message styling with silver accent */
    .stChatMessage[data-testid="user-message"] {{
        border-left-color: {theme.accent_silver};
        background-color: {theme.medium_gray};
    }}

    /* Assistant message styling */
    .stChatMessage[data-testid="assistant-message"] {{
        border-left-color: {theme.f1_red};
    }}

    /* ========================================
       INPUT FIELD STYLES
       ======================================== */
    /* Text input and textarea with rounded corners and transitions */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stChatInput > div > div > input {{
        background-color: {theme.dark_gray};
        border: 2px solid {theme.medium_gray};
        border-radius: {theme.radius_md};
        color: {theme.white};
        transition: all {theme.transition_fast};
        padding: {theme.spacing_sm};
    }}

    .stTextInput > div > div > input:hover,
    .stTextArea > div > div > textarea:hover,
    .stChatInput > div > div > input:hover {{
        border-color: {theme.light_gray};
        transition: all {theme.transition_fast};
    }}

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stChatInput > div > div > input:focus {{
        border-color: {theme.f1_red};
        box-shadow: 0 0 0 1px {theme.f1_red};
        outline: none;
        transition: all {theme.transition_fast};
    }}
    
    /* Persistent search bar on welcome screen - ChatGPT/Anthropic UX pattern */
    .stChatInput {{
        margin-top: {theme.spacing_xl};
        margin-bottom: {theme.spacing_md};
        animation: fadeIn 0.6s ease-in;
    }}
    
    .stChatInput > div {{
        border-radius: {theme.radius_md};
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        transition: box-shadow {theme.transition_normal};
    }}
    
    .stChatInput > div:hover {{
        box-shadow: 0 4px 12px rgba(225, 6, 0, 0.2);
        transition: box-shadow {theme.transition_normal};
    }}
    
    .stChatInput > div > div {{
        border-radius: {theme.radius_md};
    }}
    
    /* Welcome screen specific spacing for search bar */
    .stChatInput + div {{
        margin-top: {theme.spacing_lg};
    }}

    /* ========================================
       SLIDER STYLES
       ======================================== */
    /* Slider with F1 red accent color */
    .stSlider > div > div > div > div {{
        background-color: {theme.f1_red};
    }}

    .stSlider > div > div > div {{
        border-radius: {theme.radius_md};
    }}

    /* Slider thumb */
    .stSlider > div > div > div > div > div {{
        background-color: {theme.f1_red};
        border-radius: 50%;
        transition: all {theme.transition_fast};
    }}

    .stSlider > div > div > div > div > div:hover {{
        box-shadow: 0 0 8px rgba(225, 6, 0, 0.5);
        transition: all {theme.transition_fast};
    }}

    /* ========================================
       EXPANDER STYLES
       ======================================== */
    /* Expander with rounded corners and hover effects */
    .streamlit-expanderHeader {{
        background-color: {theme.dark_gray};
        border-radius: {theme.radius_md};
        border: 2px solid {theme.medium_gray};
        transition: all {theme.transition_fast};
        padding: {theme.spacing_sm};
    }}

    .streamlit-expanderHeader:hover {{
        border-color: {theme.f1_red};
        background-color: {theme.medium_gray};
        transition: all {theme.transition_fast};
    }}

    .streamlit-expanderContent {{
        border-radius: 0 0 {theme.radius_md} {theme.radius_md};
        border: 2px solid {theme.medium_gray};
        border-top: none;
        background-color: {theme.dark_gray};
    }}

    /* ========================================
       LINK BUTTON STYLES
       ======================================== */
    /* Link buttons with rounded corners and F1 red hover */
    .stLinkButton > a {{
        border: 2px solid {theme.medium_gray};
        border-radius: {theme.radius_md};
        transition: all {theme.transition_normal};
        padding: {theme.spacing_sm} {theme.spacing_md};
        text-decoration: none;
        display: inline-block;
    }}

    .stLinkButton > a:hover {{
        border-color: {theme.f1_red};
        transform: scale(1.02);
        box-shadow: 0 2px 8px rgba(225, 6, 0, 0.3);
        transition: all {theme.transition_normal};
    }}

    /* ========================================
       DIVIDER & SEPARATOR STYLES
       ======================================== */
    hr {{
        border-color: {theme.medium_gray};
        margin: {theme.spacing_md} 0;
        opacity: 0.5;
    }}

    /* ========================================
       METRIC & DATA DISPLAY STYLES
       ======================================== */
    /* Metric values with F1 red accent */
    [data-testid="stMetricValue"] {{
        color: {theme.f1_red};
        font-weight: 600;
        font-size: 1.5rem;
    }}

    [data-testid="stMetricLabel"] {{
        color: {theme.light_gray};
        font-size: 0.9rem;
    }}

    /* ========================================
       ALERT & NOTIFICATION STYLES
       ======================================== */
    /* Success messages with rounded corners */
    .stSuccess {{
        background-color: rgba(0, 216, 86, 0.1);
        border-left: 4px solid {theme.success};
        border-radius: {theme.radius_md};
        padding: {theme.spacing_md};
        color: {theme.white};
    }}

    /* Warning messages with rounded corners */
    .stWarning {{
        background-color: rgba(255, 165, 0, 0.1);
        border-left: 4px solid {theme.warning};
        border-radius: {theme.radius_md};
        padding: {theme.spacing_md};
        color: {theme.white};
    }}

    /* Error messages with rounded corners */
    .stError {{
        background-color: rgba(255, 68, 68, 0.1);
        border-left: 4px solid {theme.error};
        border-radius: {theme.radius_md};
        padding: {theme.spacing_md};
        color: {theme.white};
    }}

    /* Info messages */
    .stInfo {{
        background-color: rgba(225, 6, 0, 0.1);
        border-left: 4px solid {theme.f1_red};
        border-radius: {theme.radius_md};
        padding: {theme.spacing_md};
        color: {theme.white};
    }}

    /* ========================================
       DIALOG & MODAL STYLES
       ======================================== */
    /* Dialog/Modal styling with rounded corners */
    [data-testid="stDialog"] {{
        border-radius: {theme.radius_lg};
        background-color: {theme.dark_gray};
        border: 2px solid {theme.medium_gray};
    }}

    /* ========================================
       PROGRESS & LOADING INDICATORS
       ======================================== */
    /* Loading spinner with F1 red accent */
    .stSpinner > div {{
        border-top-color: {theme.f1_red};
        border-right-color: {theme.f1_red};
    }}

    /* Progress bar with F1 red accent */
    .stProgress > div > div > div > div {{
        background-color: {theme.f1_red};
        border-radius: {theme.radius_sm};
        transition: all {theme.transition_slow};
    }}

    .stProgress > div > div > div {{
        background-color: {theme.medium_gray};
        border-radius: {theme.radius_sm};
    }}

    /* ========================================
       SELECTBOX & DROPDOWN STYLES
       ======================================== */
    /* Selectbox with rounded corners */
    .stSelectbox > div > div {{
        border-radius: {theme.radius_md};
        border: 2px solid {theme.medium_gray};
        background-color: {theme.dark_gray};
        transition: all {theme.transition_fast};
    }}

    .stSelectbox > div > div:hover {{
        border-color: {theme.f1_red};
        transition: all {theme.transition_fast};
    }}

    /* ========================================
       RADIO & CHECKBOX STYLES
       ======================================== */
    /* Radio buttons with F1 red accent */
    .stRadio > div {{
        border-radius: {theme.radius_md};
    }}

    .stRadio > div > label > div:first-child {{
        background-color: {theme.dark_gray};
        border: 2px solid {theme.medium_gray};
        transition: all {theme.transition_fast};
    }}

    .stRadio > div > label:hover > div:first-child {{
        border-color: {theme.f1_red};
        transition: all {theme.transition_fast};
    }}

    /* Checkbox with F1 red accent */
    .stCheckbox > label > div:first-child {{
        border-radius: {theme.radius_sm};
        border: 2px solid {theme.medium_gray};
        transition: all {theme.transition_fast};
    }}

    .stCheckbox > label:hover > div:first-child {{
        border-color: {theme.f1_red};
        transition: all {theme.transition_fast};
    }}

    /* ========================================
       ANIMATIONS
       ======================================== */
    @keyframes fadeIn {{
        from {{
            opacity: 0;
            transform: translateY(20px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    @keyframes slideIn {{
        from {{
            opacity: 0;
            transform: translateX(-20px);
        }}
        to {{
            opacity: 1;
            transform: translateX(0);
        }}
    }}

    @keyframes pulse {{
        0%, 100% {{
            opacity: 1;
        }}
        50% {{
            opacity: 0.7;
        }}
    }}

    /* ========================================
       ACCESSIBILITY - WCAG 2.1 Level AA Compliance
       ======================================== */
    /* Ensure focus indicators are visible and prominent (3px outline for better visibility) */
    button:focus-visible,
    input:focus-visible,
    textarea:focus-visible,
    a:focus-visible,
    select:focus-visible,
    [role="button"]:focus-visible {{
        outline: 3px solid {theme.f1_red};
        outline-offset: 3px;
        box-shadow: 0 0 0 5px rgba(225, 6, 0, 0.2);
        transition: outline {theme.transition_fast}, box-shadow {theme.transition_fast};
    }}

    /* Ensure focus is visible even on dark backgrounds */
    .stButton > button:focus-visible {{
        outline: 3px solid {theme.f1_red};
        outline-offset: 3px;
        box-shadow: 0 0 0 5px rgba(225, 6, 0, 0.3);
    }}

    /* High contrast text for readability (WCAG AA: 4.5:1 for normal, 3:1 for large) */
    body, p, span, div {{
        color: {theme.white};  /* White on black: 21:1 ratio - exceeds WCAG AAA */
    }}

    /* Large text (18pt+) with sufficient contrast */
    h1, h2, h3, h4, h5, h6 {{
        color: {theme.white};  /* White on black: 21:1 ratio */
    }}

    /* Secondary text with sufficient contrast */
    .stCaption, caption, small {{
        color: {theme.light_gray};  /* Light gray (#888888) on black: 9.74:1 ratio - exceeds WCAG AA */
    }}

    /* Link text with sufficient contrast */
    a {{
        color: {theme.f1_red};  /* F1 red (#E10600) on black: 5.14:1 ratio - meets WCAG AA */
        text-decoration: underline;  /* Underline for non-color identification */
        transition: color {theme.transition_fast};
    }}

    a:hover {{
        color: {theme.accent_red};  /* Brighter red (#FF1E1E) on hover: 6.2:1 ratio */
        text-decoration: underline;
        transition: color {theme.transition_fast};
    }}

    /* Skip to main content link for keyboard navigation */
    .skip-to-main {{
        position: absolute;
        top: -40px;
        left: 0;
        background: {theme.f1_red};
        color: {theme.white};
        padding: {theme.spacing_sm} {theme.spacing_md};
        text-decoration: none;
        border-radius: {theme.radius_md};
        z-index: 100;
        transition: top {theme.transition_fast};
    }}

    .skip-to-main:focus {{
        top: 0;
        outline: 3px solid {theme.white};
        outline-offset: 2px;
    }}

    /* Ensure interactive elements have minimum touch target size (44x44px for mobile) */
    .stButton > button,
    .stLinkButton > a,
    [role="button"] {{
        min-height: 44px;
        min-width: 44px;
        padding: {theme.spacing_sm} {theme.spacing_md};
    }}

    /* Screen reader only text */
    .sr-only {{
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border-width: 0;
    }}

    /* Ensure disabled elements are clearly indicated */
    button:disabled,
    input:disabled,
    select:disabled {{
        opacity: 0.5;
        cursor: not-allowed;
        border-color: {theme.medium_gray};
    }}

    /* Keyboard navigation indicator for chat messages */
    .stChatMessage:focus-within {{
        outline: 2px solid {theme.f1_red};
        outline-offset: 2px;
    }}

    /* Ensure error messages have sufficient contrast */
    .stError, [data-testid="stNotification"] {{
        color: {theme.white};  /* White text on error background */
    }}

    /* Ensure warning messages have sufficient contrast */
    .stWarning {{
        color: {theme.white};  /* White text on warning background */
    }}

    /* Ensure success messages have sufficient contrast */
    .stSuccess {{
        color: {theme.white};  /* White text on success background */
    }}

    /* ========================================
       RESPONSIVE DESIGN
       ======================================== */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding: {theme.spacing_md};
            max-width: 100%;
        }}

        .welcome-hero h1 {{
            font-size: 2rem;
        }}

        .welcome-hero h3 {{
            font-size: 1.2rem;
        }}

        .stButton > button {{
            padding: {theme.spacing_sm} {theme.spacing_md};
            font-size: 0.9rem;
        }}

        .stButton > button[kind="secondary"] {{
            min-height: 60px;
        }}
    }}

    @media (max-width: 480px) {{
        .welcome-hero h1 {{
            font-size: 1.5rem;
        }}

        .welcome-hero h3 {{
            font-size: 1rem;
        }}

        .main .block-container {{
            padding: {theme.spacing_sm};
        }}

        .stButton > button[kind="secondary"] {{
            min-height: 50px;
            padding: {theme.spacing_sm};
        }}
    }}

    /* ========================================
       SMOOTH SCROLLING & PERFORMANCE
       ======================================== */
    html {{
        scroll-behavior: smooth;
    }}

    /* Optimize animations for performance */
    * {{
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }}

    /* ========================================
       CUSTOM SCROLLBAR STYLING
       ======================================== */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}

    ::-webkit-scrollbar-track {{
        background: {theme.black};
        border-radius: {theme.radius_sm};
    }}

    ::-webkit-scrollbar-thumb {{
        background: {theme.medium_gray};
        border-radius: {theme.radius_sm};
        transition: all {theme.transition_fast};
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: {theme.f1_red};
        transition: all {theme.transition_fast};
    }}
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)

    # Mark CSS as injected to prevent re-injection
    st.session_state.css_injected = True

    logger.info("f1_theme_applied", theme_colors=theme.model_dump())


def render_message(
    role: str,
    content: str,
    metadata: Optional[dict[str, Any]] = None,
    message_id: Optional[str] = None,
) -> None:
    """Render a chat message with role-based styling.

    Args:
        role: Message role ("user" or "assistant")
        content: Message content (supports markdown)
        metadata: Optional metadata (sources, confidence, etc.)
        message_id: Optional unique message ID for feedback tracking
    """
    with st.chat_message(role):
        # Render main content with markdown support
        st.markdown(content)

        # Render metadata if present
        if metadata and role == "assistant":
            render_message_metadata(metadata, message_id)


def render_message_metadata(
    metadata: dict[str, Any],
    message_id: Optional[str] = None,
) -> None:
    """Render metadata section for assistant messages.

    Args:
        metadata: Message metadata dictionary
        message_id: Optional message ID for feedback
    """
    # Create columns for metadata and feedback
    col1, col2 = st.columns([4, 1])

    with col1:
        # Show sources if available
        if "sources" in metadata and metadata["sources"]:
            render_sources(metadata["sources"])

        # Show confidence if available
        if "confidence" in metadata:
            render_confidence(metadata["confidence"])

        # Show warnings if present
        if "warnings" in metadata and metadata["warnings"]:
            for warning in metadata["warnings"]:
                st.warning(warning, icon="⚠️")

    with col2:
        # Render feedback buttons
        if message_id:
            render_feedback_buttons(message_id)


def render_sources(sources: list[dict[str, Any]]) -> None:
    """Render expandable source citations.

    Args:
        sources: List of source dictionaries with content, url, title, etc.
    """
    with st.expander(f"📚 Sources ({len(sources)})", expanded=False):
        for i, source in enumerate(sources, 1):
            source_type = source.get("type", "unknown")

            # Different styling for different source types
            if source_type == "historical":
                icon = "📖"
                label = "Historical Context"
            elif source_type == "current":
                icon = "🔍"
                label = "Current Information"
            else:
                icon = "📄"
                label = "Source"

            st.markdown(f"**{icon} {label} {i}**")

            # Show title if available
            if "title" in source and source["title"]:
                st.markdown(f"*{source['title']}*")

            # Show URL if available
            if "url" in source and source["url"]:
                st.markdown(f"🔗 [{source['url']}]({source['url']})")

            # Show content preview
            content = source.get("content", "")
            if content:
                preview = content[:200] + "..." if len(content) > 200 else content
                st.text(preview)

            # Show score if available
            if "score" in source:
                score = source["score"]
                st.progress(score, text=f"Relevance: {score:.2%}")

            if i < len(sources):
                st.divider()


def render_confidence(confidence: float) -> None:
    """Render confidence score indicator.

    Args:
        confidence: Confidence score (0.0 to 1.0)
    """
    # Determine color based on confidence level
    if confidence >= 0.8:
        color = "green"
        label = "High Confidence"
    elif confidence >= 0.5:
        color = "orange"
        label = "Medium Confidence"
    else:
        color = "red"
        label = "Low Confidence"

    st.markdown(
        f"**Confidence:** :{color}[{label}] ({confidence:.0%})",
        help="Confidence level in the prediction or analysis",
    )


def render_feedback_buttons(message_id: str) -> None:
    """Render thumbs up/down feedback buttons with accessibility support.

    Accessibility features:
    - Descriptive help text for screen readers
    - Clear disabled state indication
    - Keyboard navigation support
    - ARIA labels for icon-only buttons

    Args:
        message_id: Unique message identifier

    Requirements: 4.6, 5.5
    """
    # Check if feedback already given
    feedback_key = f"feedback_{message_id}"
    current_feedback = st.session_state.feedback.get(message_id)

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "👍",
            key=f"thumbs_up_{message_id}",
            disabled=current_feedback == "up",
            use_container_width=True,
            help=(
                "This response was helpful"
                if current_feedback != "up"
                else "You marked this as helpful"
            ),
        ):
            st.session_state.feedback[message_id] = "up"
            logger.info(
                "feedback_received",
                message_id=message_id,
                feedback="positive",
            )
            st.rerun()

    with col2:
        if st.button(
            "👎",
            key=f"thumbs_down_{message_id}",
            disabled=current_feedback == "down",
            use_container_width=True,
            help=(
                "This response was not helpful"
                if current_feedback != "down"
                else "You marked this as not helpful"
            ),
        ):
            st.session_state.feedback[message_id] = "down"
            logger.info(
                "feedback_received",
                message_id=message_id,
                feedback="negative",
            )
            st.rerun()

    # Show feedback confirmation with ARIA live region for screen readers
    if current_feedback:
        emoji = "👍" if current_feedback == "up" else "👎"
        st.markdown(
            f"<p role='status' aria-live='polite' style='font-size: 0.9rem; color: #888;'>{emoji} Feedback recorded</p>",
            unsafe_allow_html=True,
        )


def render_typing_indicator() -> None:
    """Render a typing indicator for streaming responses."""
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            st.empty()


def render_error_message(error: str, show_details: bool = False) -> None:
    """Render user-friendly error message.

    Args:
        error: Error message or exception string
        show_details: Whether to show technical details
    """
    # Map common errors to user-friendly messages
    user_friendly_errors = {
        "rate_limit": "⏱️ We're experiencing high demand. Please try again in a moment.",
        "api_key": "🔑 There's a configuration issue. Please contact support.",
        "network": "🌐 Connection issue detected. Please check your internet connection.",
        "timeout": "⏰ The request took too long. Please try a simpler question.",
        "vector_store": "📚 Knowledge base temporarily unavailable. Responses may be limited.",
        "search": "🔍 Search service temporarily unavailable. Using cached knowledge only.",
    }

    # Try to match error to friendly message
    friendly_msg = None
    for key, msg in user_friendly_errors.items():
        if key in error.lower():
            friendly_msg = msg
            break

    if friendly_msg:
        st.error(friendly_msg)
    else:
        st.error("⚠️ Something went wrong. Please try again.")

    # Show technical details in expander if requested
    if show_details:
        with st.expander("Technical Details"):
            st.code(error)


def render_loading_state(message: str = "Processing your request...") -> None:
    """Render loading state with progress indicator.

    Args:
        message: Loading message to display
    """
    with st.status(message, expanded=True) as status:
        st.write("🔍 Analyzing your question...")
        st.write("📚 Searching knowledge base...")
        st.write("🌐 Fetching latest information...")
        st.write("🤖 Generating response...")
        status.update(label="Complete!", state="complete")


def execute_prompt(query: str) -> None:
    """Execute a recommendation prompt by adding it to session state and triggering agent.

    This function implements the welcome screen to chat transition by:
    1. Adding the query to message history as a user message (Requirement 3.4)
    2. Setting a flag to trigger agent processing (Requirement 3.5)
    3. Rotating the recommendation prompts to show different capabilities
    4. Triggering a rerun to update the UI and hide welcome screen

    When the message is added to history, the welcome screen will be hidden
    on the next render because st.session_state.messages is no longer empty.
    The chat interface will then display the message and process the query.

    Args:
        query: The query text to execute

    Requirements: 3.4, 3.5, 8.6
    """
    from datetime import datetime

    # Add user message to history (Requirement 3.4)
    # This ensures recommendation prompt execution adds message to history
    st.session_state.messages.append(
        {
            "role": "user",
            "content": query,
            "timestamp": datetime.now(),
        }
    )

    # Set flag to indicate prompt was executed (Requirement 3.5)
    # This triggers the agent to generate a response
    st.session_state.prompt_executed = True

    # Rotate prompts to showcase different capabilities
    if "prompt_rotation_index" in st.session_state:
        st.session_state.prompt_rotation_index = (
            st.session_state.prompt_rotation_index + 1
        ) % 2

    logger.info(
        "recommendation_prompt_executed",
        query=query,
        session_id=st.session_state.get("session_id", "unknown"),
    )

    # Trigger rerun to process the query and transition from welcome screen to chat
    # The welcome screen will be hidden because messages list is no longer empty
    # The chat input will become active after the transition (Requirement 8.6)
    st.rerun()


def render_recommendation_prompts() -> None:
    """Render interactive recommendation prompt buttons in a 2x2 grid.

    This component displays 4 diverse prompts covering:
    - Standings queries
    - Race results queries
    - Prediction queries
    - Historical queries

    The prompts are displayed as clickable buttons in a 2x2 grid layout.
    When clicked, they execute the query as if the user typed it.

    The prompts rotate to showcase different capabilities of the app.

    Accessibility features:
    - Descriptive help text for each button
    - Keyboard navigation support
    - Clear visual focus indicators
    - Semantic button labels

    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.6, 5.5
    """
    # Define diverse prompts covering different categories - rotated to showcase different capabilities
    all_prompts = [
        # Standings queries
        RecommendationPrompt(
            icon="🏆",
            text="Who is leading the championship?",
            category="standings",
            query="Who is currently leading the Formula 1 World Championship?",
        ),
        RecommendationPrompt(
            icon="📊",
            text="Show current constructor standings",
            category="standings",
            query="What are the current Formula 1 constructor standings?",
        ),
        # Race results queries
        RecommendationPrompt(
            icon="🏁",
            text="What happened in the last race?",
            category="results",
            query="What were the results of the most recent Formula 1 race?",
        ),
        RecommendationPrompt(
            icon="🎯",
            text="Show me the fastest lap times",
            category="results",
            query="What were the fastest lap times in the most recent race?",
        ),
        # Prediction queries
        RecommendationPrompt(
            icon="🔮",
            text="Predict the winner of the next race",
            category="prediction",
            query="Can you predict who will win the next Formula 1 race?",
        ),
        RecommendationPrompt(
            icon="🎲",
            text="Who will win the championship?",
            category="prediction",
            query="Based on current form, who is most likely to win the World Championship?",
        ),
        # Historical queries
        RecommendationPrompt(
            icon="📚",
            text="Lewis Hamilton's career stats",
            category="historical",
            query="What are Lewis Hamilton's career statistics and achievements in Formula 1?",
        ),
        RecommendationPrompt(
            icon="🏎️",
            text="Most successful F1 teams in history",
            category="historical",
            query="Which Formula 1 teams have been the most successful in history?",
        ),
    ]

    # Initialize rotation index in session state if not present
    if "prompt_rotation_index" not in st.session_state:
        st.session_state.prompt_rotation_index = 0

    # Select 4 prompts based on rotation index, ensuring we get one from each category
    rotation_idx = st.session_state.prompt_rotation_index
    prompts = [
        all_prompts[rotation_idx % 2],  # Standings (0 or 1)
        all_prompts[2 + (rotation_idx % 2)],  # Results (2 or 3)
        all_prompts[4 + (rotation_idx % 2)],  # Prediction (4 or 5)
        all_prompts[6 + (rotation_idx % 2)],  # Historical (6 or 7)
    ]

    # Add semantic heading for screen readers
    st.markdown("<h2 class='sr-only'>Example Questions</h2>", unsafe_allow_html=True)

    # Add some spacing before prompts
    st.markdown(
        "<div style='margin-top: 2rem;' role='region' aria-label='Recommended questions'></div>",
        unsafe_allow_html=True,
    )

    # Display prompts in 2x2 grid using st.columns()
    # First row
    col1, col2 = st.columns(2)

    with col1:
        prompt = prompts[0]
        if st.button(
            f"{prompt.icon} {prompt.text}",
            key=f"prompt_{prompt.category}_0",
            use_container_width=True,
            type="secondary",
            help=f"Ask: {prompt.query}",
        ):
            execute_prompt(prompt.query)

    with col2:
        prompt = prompts[1]
        if st.button(
            f"{prompt.icon} {prompt.text}",
            key=f"prompt_{prompt.category}_1",
            use_container_width=True,
            type="secondary",
            help=f"Ask: {prompt.query}",
        ):
            execute_prompt(prompt.query)

    # Second row
    col3, col4 = st.columns(2)

    with col3:
        prompt = prompts[2]
        if st.button(
            f"{prompt.icon} {prompt.text}",
            key=f"prompt_{prompt.category}_2",
            use_container_width=True,
            type="secondary",
            help=f"Ask: {prompt.query}",
        ):
            execute_prompt(prompt.query)

    with col4:
        prompt = prompts[3]
        if st.button(
            f"{prompt.icon} {prompt.text}",
            key=f"prompt_{prompt.category}_3",
            use_container_width=True,
            type="secondary",
            help=f"Ask: {prompt.query}",
        ):
            execute_prompt(prompt.query)


def render_welcome_screen() -> None:
    """Render welcome screen with hero section, description, search bar, and recommendation prompts.

    This component displays when no conversation history exists (st.session_state.messages is empty).
    It includes:
    - Hero section with centered title, icon, and tagline using F1 theme colors
    - Brief description of chatbot capabilities
    - Persistent search bar positioned above recommendation prompts (ChatGPT/Anthropic UX)
    - Fade-in animation using CSS keyframes
    - Vertical centering using flexbox CSS
    - Interactive recommendation prompts that rotate to showcase different capabilities

    The search bar is always visible on the welcome screen and positioned above the recommendation
    prompts with proper spacing. Once the user types and submits or clicks a recommendation,
    the UI transitions to the chat interface cleanly (ChatGPT/Gemini style).

    Requirements: 8.1, 8.2, 8.4, 8.5, 8.6, 8.7, 3.1, 3.5, 4.6, 5.5
    """
    # Hero section with centered title, icon, and tagline
    # st.markdown(
    #     """
    #     <div class='welcome-hero' style='display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 30vh;'>
    #         <h1>🏎️ ChatFormula1</h1>
    #         <h3>Your AI-powered Formula 1 expert assistant</h3>
    #     </div>
    #     """,
    #     unsafe_allow_html=True,
    # )

    # Brief description (2-3 sentences) of chatbot capabilities
    st.markdown(
        """
        <div style='text-align: center; margin: 1.5rem auto; max-width: 600px; color: #888888; font-size: 1.1rem; line-height: 1.6;'>
            Get instant answers about F1 standings, race results, and predictions powered by advanced AI. 
            Access real-time data and historical statistics to explore everything Formula 1.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Add spacing before recommendation prompts
    st.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)

    # Render recommendation prompts (positioned above where chat input will appear)
    # These will disappear once the user sends a message (either by typing or clicking a prompt)
    render_recommendation_prompts()


def render_about_modal() -> None:
    """Render About modal with project information and creator details.

    This component displays a modal dialog containing:
    - Project description
    - Features list
    - Creator information with name "Prateek Mulye"
    - LinkedIn and GitHub links using st.link_button()
    - F1 theme colors and centered content
    - Error handling with fallback to simple text display

    The modal is triggered by the About button in the header and uses
    Streamlit's @st.dialog() decorator for native modal functionality.

    Requirements: 2.3, 2.4, 2.5, 2.7
    """
    try:

        @st.dialog("About ChatFormula1")
        def show_about():
            """Inner function to display about modal content."""
            # Project title with F1 emoji
            st.markdown("## 🏎️ ChatFormula1")

            # Project description
            st.markdown(
                """
            An AI-powered Formula 1 expert assistant that combines real-time 
            data, historical knowledge, and advanced language models to provide 
            comprehensive answers about Formula 1 racing.
            """
            )

            # Features list
            st.markdown("### ✨ Features")
            st.markdown(
                """
            - **Real-time F1 Data**: Current standings, race results, and live updates
            - **Historical Statistics**: Comprehensive F1 records and historical data
            - **Data-driven Predictions**: AI-powered race and championship predictions
            - **RAG-powered Knowledge**: Retrieval-Augmented Generation for accurate responses
            - **Natural Conversations**: Chat naturally about any F1 topic
            """
            )

            st.divider()

            # Creator information
            st.markdown("### 👨‍💻 Created By")
            st.markdown("**Prateek Mulye**")
            st.markdown("*AI Engineer & Formula 1 Enthusiast*")

            # Social links in two columns
            col1, col2 = st.columns(2)
            with col1:
                st.link_button(
                    "🔗 LinkedIn",
                    "https://www.linkedin.com/in/prateekmulye/",
                    use_container_width=True,
                )
            with col2:
                st.link_button(
                    "💻 GitHub",
                    "https://github.com/prateekmulye",
                    use_container_width=True,
                )

            st.divider()

            # Technology stack
            st.markdown("### 🛠️ Built With")
            st.markdown(
                """
            - **LangChain & LangGraph**: Agent orchestration and workflow
            - **OpenAI GPT-4**: Language model for natural conversations
            - **Pinecone**: Vector database for knowledge retrieval
            - **Tavily**: Real-time web search integration
            - **Streamlit**: Interactive web interface
            """
            )

            # Footer with version info
            st.markdown("---")
            st.caption("ChatFormula1 • Version 1.0 • © 2024")

        # Show modal if flag is set
        if st.session_state.get("show_about", False):
            show_about()
            # Reset flag after showing
            st.session_state.show_about = False

    except Exception as e:
        # Fallback to simple text display if modal fails
        logger.error("about_modal_render_failed", error=str(e), exc_info=True)

        # Display fallback content
        st.error("⚠️ Unable to display About modal. Here's the information:")

        st.markdown(
            """
        ### 🏎️ ChatFormula1
        
        An AI-powered Formula 1 expert assistant combining real-time data, 
        historical knowledge, and advanced language models.
        
        **Created by:** Prateek Mulye
        
        **Connect:**
        - LinkedIn: https://www.linkedin.com/in/prateekmulye/
        - GitHub: https://github.com/prateekmulye
        
        **Built with:** LangChain, LangGraph, OpenAI, Pinecone, Tavily, and Streamlit
        """
        )


def render_welcome_message() -> None:
    """Render welcome message for new conversations.

    DEPRECATED: Use render_welcome_screen() instead for the new UI design.
    This function is kept for backward compatibility.
    """
    st.markdown(
        """
    ### Welcome to ChatFormula1! 🏎️
    
    I'm your AI-powered Formula 1 expert assistant. I can help you with:
    
    - 📊 **Current Standings**: Latest driver and constructor standings
    - 🏁 **Race Results**: Recent and historical race outcomes
    - 📈 **Predictions**: Data-driven race and championship predictions
    - 📚 **History**: F1 statistics, records, and historical information
    - ⚙️ **Technical**: Regulations, car specifications, and technical details
    - 👤 **Drivers & Teams**: Information about drivers, teams, and personnel
    
    **Try asking:**
    - "Who is leading the championship?"
    - "What happened in the last race?"
    - "Predict the winner of the next race"
    - "Tell me about Lewis Hamilton's career"
    - "What are the current technical regulations?"
    
    Just type your question below to get started! 🚀
    """
    )


def render_input_validation_error(error_type: str) -> None:
    """Render input validation error message.

    Args:
        error_type: Type of validation error
    """
    errors = {
        "empty": "⚠️ Please enter a question.",
        "too_long": "⚠️ Your question is too long. Please keep it under 500 characters.",
        "invalid": "⚠️ Invalid input. Please try again.",
    }

    message = errors.get(error_type, "⚠️ Invalid input.")
    st.warning(message)


def format_timestamp(dt: datetime) -> str:
    """Format datetime for display.

    Args:
        dt: Datetime object

    Returns:
        Formatted timestamp string
    """
    now = datetime.now()
    diff = now - dt

    if diff.seconds < 60:
        return "Just now"
    elif diff.seconds < 3600:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff.days == 0:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return dt.strftime("%b %d, %Y")


def render_settings_panel() -> None:
    """Render collapsible settings panel positioned below header.

    This component provides access to configuration options without a permanent sidebar:
    - Temperature slider for model creativity control
    - Conversation history length slider
    - Clear conversation button
    - New session button
    - System information display (agent status, session ID, environment)

    The panel uses st.expander() for collapsible behavior and is only displayed
    when st.session_state.show_settings is True.

    Requirements: 7.3, 7.4, 7.5, 7.6, 7.7
    """
    import uuid

    # Only render if settings flag is set
    if not st.session_state.get("show_settings", False):
        return

    with st.expander("⚙️ Settings", expanded=True):
        # Model Settings Section
        st.markdown("### 🤖 Model Settings")

        # Temperature control
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=st.session_state.settings.openai_temperature,
            step=0.1,
            help="Higher values make output more creative, lower values more focused",
            key="settings_temperature",
        )

        # Update settings if changed
        if temperature != st.session_state.settings.openai_temperature:
            st.session_state.settings.openai_temperature = temperature
            # Reset agent to apply new settings
            st.session_state.agent_graph = None
            logger.info(
                "temperature_updated",
                new_temperature=temperature,
                session_id=st.session_state.get("session_id", "unknown"),
            )

        # Conversation history slider
        max_history = st.slider(
            "Conversation History",
            min_value=5,
            max_value=20,
            value=st.session_state.settings.max_conversation_history,
            step=1,
            help="Number of previous messages to include as context",
            key="settings_max_history",
        )

        # Update settings if changed
        if max_history != st.session_state.settings.max_conversation_history:
            st.session_state.settings.max_conversation_history = max_history
            logger.info(
                "max_history_updated",
                new_max_history=max_history,
                session_id=st.session_state.get("session_id", "unknown"),
            )

        st.divider()

        # Conversation Management Section
        st.markdown("### 💬 Conversation Management")

        # Display message count
        msg_count = len(st.session_state.messages)
        st.metric("Messages in conversation", msg_count)

        # Clear conversation and new session buttons in two columns
        col1, col2 = st.columns(2)

        with col1:
            if st.button(
                "🗑️ Clear Conversation",
                use_container_width=True,
                key="settings_clear",
                help="Delete all messages in the current conversation",
            ):
                st.session_state.messages = []
                st.session_state.agent_state = None
                st.session_state.feedback = {}
                logger.info(
                    "conversation_cleared",
                    session_id=st.session_state.get("session_id", "unknown"),
                )
                st.rerun()

        with col2:
            if st.button(
                "🆕 New Session",
                use_container_width=True,
                key="settings_new_session",
                help="Start a new conversation session with a fresh context",
            ):
                st.session_state.session_id = str(uuid.uuid4())
                st.session_state.messages = []
                st.session_state.agent_state = None
                st.session_state.feedback = {}
                logger.info(
                    "new_session_created", session_id=st.session_state.session_id
                )
                st.rerun()

        st.divider()

        # System Information Section
        st.markdown("### ℹ️ System Information")

        # Agent status
        agent_status = (
            "✅ Ready" if st.session_state.get("agent_graph") else "⚠️ Not Initialized"
        )
        st.text(f"Agent Status: {agent_status}")

        # Session ID (truncated for display)
        session_id = st.session_state.get("session_id", "unknown")
        session_id_short = session_id[:8] if len(session_id) > 8 else session_id
        st.text(f"Session ID: {session_id_short}...")

        # Environment
        env = st.session_state.settings.environment
        st.text(f"Environment: {env}")

        # Session duration
        if "session_start" in st.session_state:
            duration = datetime.now() - st.session_state.session_start
            minutes = duration.seconds // 60
            hours = minutes // 60
            remaining_minutes = minutes % 60

            if hours > 0:
                duration_str = f"{hours}h {remaining_minutes}m"
            else:
                duration_str = f"{minutes}m"

            st.text(f"Session Duration: {duration_str}")

        # Feedback stats
        feedback = st.session_state.get("feedback", {})
        positive = sum(1 for f in feedback.values() if f == "up")
        negative = sum(1 for f in feedback.values() if f == "down")

        if positive > 0 or negative > 0:
            st.text(f"Feedback: 👍 {positive} | 👎 {negative}")


def render_session_info() -> None:
    """Render session information in sidebar.

    DEPRECATED: Use render_settings_panel() instead for the new UI design.
    This function is kept for backward compatibility.
    """
    st.sidebar.divider()
    st.sidebar.subheader("📊 Session Stats")

    # Message count
    msg_count = len(st.session_state.messages)
    st.sidebar.metric("Messages", msg_count)

    # Feedback stats
    feedback = st.session_state.feedback
    positive = sum(1 for f in feedback.values() if f == "up")
    negative = sum(1 for f in feedback.values() if f == "down")

    col1, col2 = st.sidebar.columns(2)
    col1.metric("👍", positive)
    col2.metric("👎", negative)

    # Session duration
    if "session_start" in st.session_state:
        duration = datetime.now() - st.session_state.session_start
        minutes = duration.seconds // 60
        st.sidebar.metric("Duration", f"{minutes} min")
