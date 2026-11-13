"""Candidate adapter uses the actual Tk button and its confirmation dialog."""
def invoke_review_ui(app):
    if app.review_button.instate(['disabled']):
        raise AssertionError('Review UI unexpectedly disabled')
    app.review_button.invoke()
