"""Unit tests for UI components and F1 theme."""

import sys
from importlib import import_module
from unittest.mock import MagicMock, patch

import pytest

# Import components module directly without going through __init__.py
components = import_module("src.ui.components")
F1Theme = components.F1Theme
apply_f1_theme = components.apply_f1_theme


class TestF1Theme:
    """Test F1Theme configuration model."""

    def test_f1_theme_default_values(self):
        """Test F1Theme initializes with correct default values."""
        theme = F1Theme()

        # Test primary colors
        assert theme.f1_red == "#E10600"
        assert theme.black == "#0e1117"
        assert theme.dark_gray == "#1e2130"
        assert theme.white == "#FFFFFF"

        # Test spacing
        assert theme.spacing_xs == "4px"
        assert theme.spacing_sm == "8px"
        assert theme.spacing_md == "16px"
        assert theme.spacing_lg == "24px"
        assert theme.spacing_xl == "32px"

        # Test border radius
        assert theme.radius_sm == "4px"
        assert theme.radius_md == "8px"
        assert theme.radius_lg == "12px"

        # Test transitions
        assert theme.transition_fast == "150ms ease"
        assert theme.transition_normal == "200ms ease"
        assert theme.transition_slow == "300ms ease"

    def test_f1_theme_custom_values(self):
        """Test F1Theme accepts custom values."""
        theme = F1Theme(
            f1_red="#FF0000", spacing_md="20px", transition_fast="100ms ease"
        )

        assert theme.f1_red == "#FF0000"
        assert theme.spacing_md == "20px"
        assert theme.transition_fast == "100ms ease"

    def test_f1_theme_model_dump(self):
        """Test F1Theme can be serialized."""
        theme = F1Theme()
        theme_dict = theme.model_dump()

        assert isinstance(theme_dict, dict)
        assert "f1_red" in theme_dict
        assert "spacing_md" in theme_dict
        assert theme_dict["f1_red"] == "#E10600"


class TestApplyF1Theme:
    """Test apply_f1_theme CSS injection function."""

    @patch("src.ui.components.st")
    def test_apply_f1_theme_injects_css(self, mock_st):
        """Test that apply_f1_theme injects CSS via st.markdown."""
        # Setup mock session state
        mock_st.session_state = {}

        # Call function
        apply_f1_theme()

        # Verify st.markdown was called with CSS
        mock_st.markdown.assert_called_once()
        call_args = mock_st.markdown.call_args

        # Check that CSS was injected
        css_content = call_args[0][0]
        assert "<style>" in css_content
        assert "</style>" in css_content
        assert "#E10600" in css_content  # F1 red color
        assert "unsafe_allow_html" in call_args[1]
        assert call_args[1]["unsafe_allow_html"] is True

    @patch("src.ui.components.st")
    def test_apply_f1_theme_sets_session_flag(self, mock_st):
        """Test that apply_f1_theme sets css_injected flag."""
        # Setup mock session state
        mock_st.session_state = {}

        # Call function
        apply_f1_theme()

        # Verify flag was set
        assert "css_injected" in mock_st.session_state
        assert mock_st.session_state["css_injected"] is True

    @patch("src.ui.components.st")
    def test_apply_f1_theme_only_injects_once(self, mock_st):
        """Test that CSS is only injected once per session."""
        # Setup mock session state with flag already set
        mock_st.session_state = {"css_injected": True}

        # Call function
        apply_f1_theme()

        # Verify st.markdown was NOT called
        mock_st.markdown.assert_not_called()

    @patch("src.ui.components.st")
    def test_apply_f1_theme_includes_responsive_css(self, mock_st):
        """Test that responsive CSS is included."""
        mock_st.session_state = {}

        apply_f1_theme()

        css_content = mock_st.markdown.call_args[0][0]

        # Check for responsive media queries
        assert "@media (max-width: 768px)" in css_content
        assert "@media (max-width: 480px)" in css_content

    @patch("src.ui.components.st")
    def test_apply_f1_theme_includes_accessibility_css(self, mock_st):
        """Test that accessibility CSS is included."""
        mock_st.session_state = {}

        apply_f1_theme()

        css_content = mock_st.markdown.call_args[0][0]

        # Check for accessibility features
        assert "focus-visible" in css_content
        assert "outline:" in css_content

    @patch("src.ui.components.st")
    def test_apply_f1_theme_includes_animations(self, mock_st):
        """Test that animation CSS is included."""
        mock_st.session_state = {}

        apply_f1_theme()

        css_content = mock_st.markdown.call_args[0][0]

        # Check for animations
        assert "@keyframes fadeIn" in css_content
        assert "@keyframes slideIn" in css_content
        assert "animation:" in css_content

    @patch("src.ui.components.st")
    def test_apply_f1_theme_includes_component_styles(self, mock_st):
        """Test that all component styles are included."""
        mock_st.session_state = {}

        apply_f1_theme()

        css_content = mock_st.markdown.call_args[0][0]

        # Check for various component styles
        assert ".stButton" in css_content
        assert ".stChatMessage" in css_content
        assert ".stTextInput" in css_content
        assert ".stSlider" in css_content
        assert ".streamlit-expanderHeader" in css_content
        assert ".welcome-hero" in css_content

    @patch("src.ui.components.st")
    def test_apply_f1_theme_includes_centered_layout(self, mock_st):
        """Test that centered layout CSS with 800px max-width is included."""
        mock_st.session_state = {}

        apply_f1_theme()

        css_content = mock_st.markdown.call_args[0][0]

        # Check for centered layout styles
        assert ".main .block-container" in css_content
        assert "max-width: 800px" in css_content
        assert "padding-top:" in css_content
        assert "padding-left:" in css_content
        assert "padding-right:" in css_content


class TestRecommendationPrompt:
    """Test RecommendationPrompt model."""

    def test_recommendation_prompt_creation(self):
        """Test RecommendationPrompt model can be created with valid data."""
        RecommendationPrompt = components.RecommendationPrompt

        prompt = RecommendationPrompt(
            icon="🏆",
            text="Who is leading the championship?",
            category="standings",
            query="Who is currently leading the Formula 1 World Championship?",
        )

        assert prompt.icon == "🏆"
        assert prompt.text == "Who is leading the championship?"
        assert prompt.category == "standings"
        assert (
            prompt.query == "Who is currently leading the Formula 1 World Championship?"
        )

    def test_recommendation_prompt_categories(self):
        """Test RecommendationPrompt accepts all valid categories."""
        RecommendationPrompt = components.RecommendationPrompt

        valid_categories = ["standings", "results", "prediction", "historical"]

        for category in valid_categories:
            prompt = RecommendationPrompt(
                icon="🏁", text="Test prompt", category=category, query="Test query"
            )
            assert prompt.category == category


class TestExecutePrompt:
    """Test execute_prompt function."""

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_execute_prompt_adds_message_to_history(self, mock_logger, mock_st):
        """Test that execute_prompt adds user message to session state."""
        execute_prompt = components.execute_prompt

        # Setup mock session state
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Execute prompt
        query = "Who is leading the championship?"
        execute_prompt(query)

        # Verify message was added
        assert len(mock_st.session_state["messages"]) == 1
        message = mock_st.session_state["messages"][0]
        assert message["role"] == "user"
        assert message["content"] == query
        assert "timestamp" in message

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_execute_prompt_sets_execution_flag(self, mock_logger, mock_st):
        """Test that execute_prompt sets prompt_executed flag."""
        execute_prompt = components.execute_prompt

        # Setup mock session state
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Execute prompt
        execute_prompt("Test query")

        # Verify flag was set
        assert mock_st.session_state["prompt_executed"] is True

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_execute_prompt_triggers_rerun(self, mock_logger, mock_st):
        """Test that execute_prompt triggers st.rerun()."""
        execute_prompt = components.execute_prompt

        # Setup mock session state
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Execute prompt
        execute_prompt("Test query")

        # Verify rerun was called
        mock_st.rerun.assert_called_once()

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_execute_prompt_logs_execution(self, mock_logger, mock_st):
        """Test that execute_prompt logs the execution."""
        execute_prompt = components.execute_prompt

        # Setup mock session state
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Execute prompt
        query = "Test query"
        execute_prompt(query)

        # Verify logging
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "recommendation_prompt_executed"
        assert call_args[1]["query"] == query
        assert call_args[1]["session_id"] == "test-session-123"


class TestRenderRecommendationPrompts:
    """Test render_recommendation_prompts component."""

    @patch("src.ui.components.st")
    def test_render_recommendation_prompts_displays_four_prompts(self, mock_st):
        """Test that render_recommendation_prompts displays 4 prompts."""
        render_recommendation_prompts = components.render_recommendation_prompts

        # Setup mock button to not trigger
        mock_st.button.return_value = False

        # Call function
        render_recommendation_prompts()

        # Verify 4 buttons were created
        assert mock_st.button.call_count == 4

    @patch("src.ui.components.st")
    def test_render_recommendation_prompts_uses_grid_layout(self, mock_st):
        """Test that prompts are displayed in 2x2 grid using st.columns()."""
        render_recommendation_prompts = components.render_recommendation_prompts

        # Setup mock
        mock_st.button.return_value = False

        # Call function
        render_recommendation_prompts()

        # Verify st.columns was called twice (for 2 rows)
        assert mock_st.columns.call_count == 2

        # Verify columns were called with 2 columns each time
        for call in mock_st.columns.call_args_list:
            assert call[0][0] == 2

    @patch("src.ui.components.st")
    def test_render_recommendation_prompts_covers_all_categories(self, mock_st):
        """Test that prompts cover standings, results, prediction, and historical."""
        render_recommendation_prompts = components.render_recommendation_prompts

        # Setup mock
        mock_st.button.return_value = False

        # Call function
        render_recommendation_prompts()

        # Get all button texts
        button_texts = [call[0][0] for call in mock_st.button.call_args_list]
        combined_text = " ".join(button_texts)

        # Verify diverse categories are covered
        assert (
            "championship" in combined_text.lower()
            or "leading" in combined_text.lower()
        )
        assert "race" in combined_text.lower()
        assert "predict" in combined_text.lower()
        assert (
            "hamilton" in combined_text.lower()
            or "career" in combined_text.lower()
            or "stats" in combined_text.lower()
        )

    @patch("src.ui.components.st")
    def test_render_recommendation_prompts_buttons_have_icons(self, mock_st):
        """Test that all prompt buttons include emoji icons."""
        render_recommendation_prompts = components.render_recommendation_prompts

        # Setup mock
        mock_st.button.return_value = False

        # Call function
        render_recommendation_prompts()

        # Get all button texts
        button_texts = [call[0][0] for call in mock_st.button.call_args_list]

        # Verify all buttons have emoji icons (contain emoji characters)
        for text in button_texts:
            # Check that text starts with an emoji (non-ASCII character)
            assert any(ord(char) > 127 for char in text[:5])

    @patch("src.ui.components.st")
    @patch("src.ui.components.execute_prompt")
    def test_render_recommendation_prompts_executes_on_click(
        self, mock_execute, mock_st
    ):
        """Test that clicking a prompt button executes the query."""
        render_recommendation_prompts = components.render_recommendation_prompts

        # Setup mock to simulate button click on first button
        mock_st.button.side_effect = [True, False, False, False]

        # Call function
        render_recommendation_prompts()

        # Verify execute_prompt was called
        mock_execute.assert_called_once()


class TestRenderWelcomeScreen:
    """Test render_welcome_screen component."""

    @patch("src.ui.components.st")
    @patch("src.ui.components.render_recommendation_prompts")
    def test_render_welcome_screen_displays_hero_section(
        self, mock_render_prompts, mock_st
    ):
        """Test that welcome screen renders hero section with title and tagline."""
        # Import function
        render_welcome_screen = components.render_welcome_screen

        # Call function
        render_welcome_screen()

        # Verify st.markdown was called
        assert mock_st.markdown.call_count >= 2

        # Get all markdown calls
        markdown_calls = [call[0][0] for call in mock_st.markdown.call_args_list]
        combined_content = " ".join(markdown_calls)

        # Check for hero section elements
        assert "🏎️ ChatFormula1" in combined_content
        assert "Your AI-powered Formula 1 expert assistant" in combined_content
        assert "welcome-hero" in combined_content

    @patch("src.ui.components.st")
    @patch("src.ui.components.render_recommendation_prompts")
    def test_render_welcome_screen_displays_description(
        self, mock_render_prompts, mock_st
    ):
        """Test that welcome screen renders description of capabilities."""
        render_welcome_screen = components.render_welcome_screen

        render_welcome_screen()

        # Get all markdown calls
        markdown_calls = [call[0][0] for call in mock_st.markdown.call_args_list]
        combined_content = " ".join(markdown_calls)

        # Check for description content
        assert "F1 standings" in combined_content or "race results" in combined_content
        assert "AI" in combined_content

    @patch("src.ui.components.st")
    @patch("src.ui.components.render_recommendation_prompts")
    def test_render_welcome_screen_uses_flexbox_centering(
        self, mock_render_prompts, mock_st
    ):
        """Test that welcome screen uses flexbox for vertical centering."""
        render_welcome_screen = components.render_welcome_screen

        render_welcome_screen()

        # Get all markdown calls
        markdown_calls = [call[0][0] for call in mock_st.markdown.call_args_list]
        combined_content = " ".join(markdown_calls)

        # Check for flexbox CSS properties
        assert "display: flex" in combined_content
        assert "flex-direction: column" in combined_content
        assert "justify-content: center" in combined_content
        assert "align-items: center" in combined_content

    @patch("src.ui.components.st")
    @patch("src.ui.components.render_recommendation_prompts")
    def test_render_welcome_screen_uses_unsafe_html(self, mock_render_prompts, mock_st):
        """Test that welcome screen uses unsafe_allow_html for custom styling."""
        render_welcome_screen = components.render_welcome_screen

        render_welcome_screen()

        # Check that all markdown calls use unsafe_allow_html=True
        for call in mock_st.markdown.call_args_list:
            assert call[1].get("unsafe_allow_html") is True

    @patch("src.ui.components.st")
    @patch("src.ui.components.render_recommendation_prompts")
    def test_render_welcome_screen_includes_recommendation_prompts(
        self, mock_render_prompts, mock_st
    ):
        """Test that welcome screen calls render_recommendation_prompts."""
        render_welcome_screen = components.render_welcome_screen

        render_welcome_screen()

        # Verify render_recommendation_prompts was called
        mock_render_prompts.assert_called_once()


class TestWelcomeScreenTransition:
    """Test welcome screen to chat transition functionality."""

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_execute_prompt_hides_welcome_screen(self, mock_logger, mock_st):
        """Test that executing a prompt adds message which hides welcome screen."""
        execute_prompt = components.execute_prompt

        # Setup mock session state with empty messages (welcome screen visible)
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Execute prompt
        query = "Who is leading the championship?"
        execute_prompt(query)

        # Verify message was added (which will hide welcome screen on next render)
        assert len(mock_st.session_state["messages"]) == 1
        assert mock_st.session_state["messages"][0]["role"] == "user"
        assert mock_st.session_state["messages"][0]["content"] == query

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_execute_prompt_triggers_agent_processing(self, mock_logger, mock_st):
        """Test that executing a prompt sets flag to trigger agent processing."""
        execute_prompt = components.execute_prompt

        # Setup mock session state
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Execute prompt
        execute_prompt("Test query")

        # Verify prompt_executed flag was set (triggers agent processing)
        assert mock_st.session_state["prompt_executed"] is True

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_execute_prompt_triggers_ui_rerun(self, mock_logger, mock_st):
        """Test that executing a prompt triggers rerun for smooth transition."""
        execute_prompt = components.execute_prompt

        # Setup mock session state
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Execute prompt
        execute_prompt("Test query")

        # Verify rerun was called (enables smooth transition)
        mock_st.rerun.assert_called_once()

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_message_history_not_empty_after_prompt(self, mock_logger, mock_st):
        """Test that message history is not empty after prompt execution."""
        execute_prompt = components.execute_prompt

        # Setup mock session state with empty messages
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Verify messages is empty initially
        assert len(mock_st.session_state["messages"]) == 0

        # Execute prompt
        execute_prompt("Test query")

        # Verify messages is no longer empty (welcome screen will be hidden)
        assert len(mock_st.session_state["messages"]) > 0

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_execute_prompt_includes_timestamp(self, mock_logger, mock_st):
        """Test that executed prompt message includes timestamp."""
        execute_prompt = components.execute_prompt

        # Setup mock session state
        mock_st.session_state = {"messages": [], "session_id": "test-session-123"}

        # Execute prompt
        execute_prompt("Test query")

        # Verify message has timestamp
        message = mock_st.session_state["messages"][0]
        assert "timestamp" in message
        assert message["timestamp"] is not None


class TestRenderAboutModal:
    """Test render_about_modal component."""

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_render_about_modal_displays_when_flag_set(self, mock_logger, mock_st):
        """Test that about modal displays when show_about flag is True."""
        render_about_modal = components.render_about_modal

        # Setup mock session state with show_about flag
        mock_st.session_state = {"show_about": True}

        # Mock the dialog decorator to capture the inner function
        dialog_func = None

        def mock_dialog(title):
            def decorator(func):
                nonlocal dialog_func
                dialog_func = func
                return func

            return decorator

        mock_st.dialog = mock_dialog

        # Call function
        render_about_modal()

        # Verify dialog function was created
        assert dialog_func is not None

        # Verify show_about flag was reset
        assert mock_st.session_state["show_about"] is False

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_render_about_modal_not_displayed_when_flag_false(
        self, mock_logger, mock_st
    ):
        """Test that about modal does not display when show_about flag is False."""
        render_about_modal = components.render_about_modal

        # Setup mock session state with show_about flag False
        mock_st.session_state = {"show_about": False}

        # Track if dialog was called
        dialog_called = False

        def mock_dialog(title):
            def decorator(func):
                nonlocal dialog_called
                dialog_called = True
                return func

            return decorator

        mock_st.dialog = mock_dialog

        # Call function
        render_about_modal()

        # Verify dialog was not shown (flag remains False)
        assert mock_st.session_state["show_about"] is False

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_render_about_modal_includes_project_description(
        self, mock_logger, mock_st
    ):
        """Test that about modal includes project description."""
        render_about_modal = components.render_about_modal

        # Setup mock
        mock_st.session_state = {"show_about": True}

        # Capture markdown calls
        markdown_calls = []
        mock_st.markdown = MagicMock(
            side_effect=lambda *args, **kwargs: markdown_calls.append(args[0])
        )

        # Mock dialog decorator
        dialog_func = None

        def mock_dialog(title):
            def decorator(func):
                nonlocal dialog_func
                dialog_func = func
                return func

            return decorator

        mock_st.dialog = mock_dialog

        # Call function
        render_about_modal()

        # Execute the dialog function to capture content
        if dialog_func:
            dialog_func()

        # Verify project description is present
        combined_content = " ".join(markdown_calls)
        assert "ChatFormula1" in combined_content
        assert "AI-powered" in combined_content or "Formula 1" in combined_content

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_render_about_modal_includes_features_list(self, mock_logger, mock_st):
        """Test that about modal includes features list."""
        render_about_modal = components.render_about_modal

        # Setup mock
        mock_st.session_state = {"show_about": True}

        # Capture markdown calls
        markdown_calls = []
        mock_st.markdown = MagicMock(
            side_effect=lambda *args, **kwargs: markdown_calls.append(args[0])
        )

        # Mock dialog decorator
        dialog_func = None

        def mock_dialog(title):
            def decorator(func):
                nonlocal dialog_func
                dialog_func = func
                return func

            return decorator

        mock_st.dialog = mock_dialog

        # Call function
        render_about_modal()

        # Execute the dialog function
        if dialog_func:
            dialog_func()

        # Verify features are present
        combined_content = " ".join(markdown_calls)
        assert "Features" in combined_content or "features" in combined_content

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_render_about_modal_includes_creator_name(self, mock_logger, mock_st):
        """Test that about modal includes creator name 'Prateek Mulye'."""
        render_about_modal = components.render_about_modal

        # Setup mock
        mock_st.session_state = {"show_about": True}

        # Capture markdown calls
        markdown_calls = []
        mock_st.markdown = MagicMock(
            side_effect=lambda *args, **kwargs: markdown_calls.append(args[0])
        )

        # Mock dialog decorator
        dialog_func = None

        def mock_dialog(title):
            def decorator(func):
                nonlocal dialog_func
                dialog_func = func
                return func

            return decorator

        mock_st.dialog = mock_dialog

        # Call function
        render_about_modal()

        # Execute the dialog function
        if dialog_func:
            dialog_func()

        # Verify creator name is present
        combined_content = " ".join(markdown_calls)
        assert "Prateek Mulye" in combined_content

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_render_about_modal_includes_social_links(self, mock_logger, mock_st):
        """Test that about modal includes LinkedIn and GitHub links."""
        render_about_modal = components.render_about_modal

        # Setup mock
        mock_st.session_state = {"show_about": True}

        # Mock dialog decorator
        dialog_func = None

        def mock_dialog(title):
            def decorator(func):
                nonlocal dialog_func
                dialog_func = func
                return func

            return decorator

        mock_st.dialog = mock_dialog

        # Call function
        render_about_modal()

        # Execute the dialog function
        if dialog_func:
            dialog_func()

        # Verify link_button was called for LinkedIn and GitHub
        assert mock_st.link_button.call_count == 2

        # Get all link_button calls
        link_calls = [call[0] for call in mock_st.link_button.call_args_list]
        link_urls = [call[1] for call in link_calls]

        # Verify LinkedIn and GitHub URLs are present
        assert any("linkedin.com/in/prateekmulye" in url for url in link_urls)
        assert any("github.com/prateekmulye" in url for url in link_urls)

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_render_about_modal_error_handling(self, mock_logger, mock_st):
        """Test that about modal has error handling with fallback display."""
        render_about_modal = components.render_about_modal

        # Setup mock to raise exception
        mock_st.session_state = {"show_about": True}
        mock_st.dialog = MagicMock(side_effect=Exception("Test error"))

        # Call function - should not raise exception
        render_about_modal()

        # Verify error was logged
        mock_logger.error.assert_called_once()

        # Verify fallback error message was displayed
        mock_st.error.assert_called_once()
        assert "Unable to display About modal" in mock_st.error.call_args[0][0]

    @patch("src.ui.components.st")
    @patch("src.ui.components.logger")
    def test_render_about_modal_fallback_includes_creator_info(
        self, mock_logger, mock_st
    ):
        """Test that fallback display includes creator information."""
        render_about_modal = components.render_about_modal

        # Setup mock to raise exception
        mock_st.session_state = {"show_about": True}
        mock_st.dialog = MagicMock(side_effect=Exception("Test error"))

        # Capture markdown calls
        markdown_calls = []
        mock_st.markdown = MagicMock(
            side_effect=lambda *args, **kwargs: markdown_calls.append(args[0])
        )

        # Call function
        render_about_modal()

        # Verify fallback content includes creator info
        combined_content = " ".join(markdown_calls)
        assert "Prateek Mulye" in combined_content
        assert "linkedin.com/in/prateekmulye" in combined_content
        assert "github.com/prateekmulye" in combined_content
