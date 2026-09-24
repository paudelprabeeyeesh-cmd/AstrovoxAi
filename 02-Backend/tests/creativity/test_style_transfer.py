from creativity.style_transfer import StyleTransfer, StyleProfile, StyledText


class TestStyleTransfer:
    def test_transfer_returns_styled_text(self):
        st = StyleTransfer()
        result = st.transfer("The quick brown fox jumps.", target_style="formal")
        assert isinstance(result, StyledText)
        assert result.style == "formal"

    def test_shakespearean_style(self):
        st = StyleTransfer()
        result = st.transfer("The quick brown fox jumps.", target_style="shakespearean")
        assert result.style == "shakespearean"
        assert len(result.text) > 0

    def test_casual_style(self):
        st = StyleTransfer()
        result = st.transfer("The quick brown fox jumps.", target_style="casual")
        assert result.style == "casual"

    def test_match_score_range(self):
        st = StyleTransfer()
        result = st.transfer("hello world", target_style="poetic")
        assert 0.0 <= result.match_score <= 1.0

    def test_unknown_style_defaults(self):
        st = StyleTransfer()
        result = st.transfer("text", target_style="unknown")
        assert result.style == "unknown"
        assert len(result.text) > 0

    def test_deterministic_with_seed(self):
        st_a = StyleTransfer(seed=7)
        st_b = StyleTransfer(seed=7)
        r_a = st_a.transfer("sample input text here", target_style="noir")
        r_b = st_b.transfer("sample input text here", target_style="noir")
        assert r_a.text == r_b.text
