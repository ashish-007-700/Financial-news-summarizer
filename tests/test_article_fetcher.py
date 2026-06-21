from ingestion.article_fetcher import html_to_text


def test_html_to_text_extracts_readable_paragraphs():
    html = """
    <html>
      <body>
        <script>ignore_me()</script>
        <p>Apple reported revenue of $90 billion for the quarter, beating analyst estimates.</p>
        <p>Shares rose 3% after management raised guidance for the next quarter.</p>
      </body>
    </html>
    """

    text = html_to_text(html)

    assert "$90 billion" in text
    assert "3%" in text
    assert "ignore_me" not in text

