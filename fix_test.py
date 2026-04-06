import re

with open('tests/test_ui_components.py', 'r') as f:
    content = f.read()

# Fix TestRenderAboutModal object attribute setting issue
content = re.sub(
    r'mock_st\.session_state = \{"show_about": True, "css_injected": True, "messages": \[\]\}',
    r'mock_st.session_state = {"show_about": True}\n        mock_st.session_state.__setattr__ = lambda self, key, value: self.__setitem__(key, value)\n        mock_st.session_state.__getattr__ = lambda self, key: self.get(key)',
    content
)

content = re.sub(
    r'mock_st\.session_state = \{"show_about": False, "css_injected": True, "messages": \[\]\}',
    r'mock_st.session_state = {"show_about": False}\n        mock_st.session_state.__setattr__ = lambda self, key, value: self.__setitem__(key, value)\n        mock_st.session_state.__getattr__ = lambda self, key: self.get(key)',
    content
)

with open('tests/test_ui_components.py', 'w') as f:
    f.write(content)
