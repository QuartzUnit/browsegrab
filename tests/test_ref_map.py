"""Tests for browsegrab.dom.ref_map — ref ID assignment and role classification."""

from browsegrab.dom.ref_map import INTERACTIVE_ROLES, LANDMARK_ROLES, RefMap


class TestAssign:
    """Tests for RefMap.assign()."""

    def test_assign_sequential_ref_ids(self):
        rm = RefMap()
        e1 = rm.assign("button", "Submit")
        e2 = rm.assign("link", "Home")
        e3 = rm.assign("textbox", "Search")
        assert e1.ref == "e1"
        assert e2.ref == "e2"
        assert e3.ref == "e3"

    def test_assign_stores_role_and_name(self):
        rm = RefMap()
        e = rm.assign("button", "Submit")
        assert e.role == "button"
        assert e.name == "Submit"

    def test_assign_passes_optional_attrs(self):
        rm = RefMap()
        e = rm.assign(
            "textbox",
            "Email",
            tag="input",
            value="test@x.com",
            level=0,
            focused=True,
            checked=None,
            expanded=True,
            selector="#email",
        )
        assert e.tag == "input"
        assert e.value == "test@x.com"
        assert e.focused is True
        assert e.expanded is True
        assert e.selector == "#email"

    def test_assign_increments_count(self):
        rm = RefMap()
        assert rm.count == 0
        rm.assign("button", "A")
        assert rm.count == 1
        rm.assign("link", "B")
        assert rm.count == 2


class TestGet:
    """Tests for RefMap.get()."""

    def test_get_returns_correct_element(self):
        rm = RefMap()
        rm.assign("button", "Submit")
        e2 = rm.assign("link", "Home")
        result = rm.get("e2")
        assert result is e2
        assert result.name == "Home"

    def test_get_returns_none_for_unknown_ref(self):
        rm = RefMap()
        rm.assign("button", "Submit")
        assert rm.get("e99") is None

    def test_get_returns_none_on_empty_map(self):
        rm = RefMap()
        assert rm.get("e1") is None


class TestAllElements:
    """Tests for RefMap.all_elements()."""

    def test_all_elements_returns_in_order(self):
        rm = RefMap()
        rm.assign("button", "A")
        rm.assign("link", "B")
        rm.assign("textbox", "C")
        elements = rm.all_elements()
        assert len(elements) == 3
        assert [e.name for e in elements] == ["A", "B", "C"]

    def test_all_elements_empty(self):
        rm = RefMap()
        assert rm.all_elements() == []


class TestClear:
    """Tests for RefMap.clear()."""

    def test_clear_resets_counter_and_elements(self):
        rm = RefMap()
        rm.assign("button", "A")
        rm.assign("link", "B")
        assert rm.count == 2

        rm.clear()
        assert rm.count == 0
        assert rm.all_elements() == []

        # Counter resets — next assignment starts at e1 again
        e = rm.assign("textbox", "New")
        assert e.ref == "e1"


class TestRoleClassification:
    """Tests for is_interactive, is_landmark, should_include."""

    def test_is_interactive_true_for_all_interactive_roles(self):
        rm = RefMap()
        for role in INTERACTIVE_ROLES:
            assert rm.is_interactive(role) is True, f"Expected {role} to be interactive"

    def test_is_interactive_false_for_landmark(self):
        rm = RefMap()
        assert rm.is_interactive("heading") is False
        assert rm.is_interactive("navigation") is False

    def test_is_interactive_false_for_unknown(self):
        rm = RefMap()
        assert rm.is_interactive("paragraph") is False
        assert rm.is_interactive("") is False

    def test_is_landmark_true_for_all_landmark_roles(self):
        rm = RefMap()
        for role in LANDMARK_ROLES:
            assert rm.is_landmark(role) is True, f"Expected {role} to be landmark"

    def test_is_landmark_false_for_interactive(self):
        rm = RefMap()
        assert rm.is_landmark("button") is False

    def test_should_include_for_interactive(self):
        rm = RefMap()
        assert rm.should_include("button") is True
        assert rm.should_include("link") is True

    def test_should_include_for_landmark(self):
        rm = RefMap()
        assert rm.should_include("heading") is True
        assert rm.should_include("main") is True

    def test_should_include_false_for_unrelated_roles(self):
        rm = RefMap()
        assert rm.should_include("paragraph") is False
        assert rm.should_include("img") is False
        assert rm.should_include("") is False
