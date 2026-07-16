import marimo

__generated_with = "0.23.13"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import io
    from app.core.validators.topic_relevance_llm import TopicRelevanceLLM
    from app.core.validators.pii_remover import PIIRemover
    from guardrails.validators import (
        FailResult,
        PassResult
    )
    from sklearn.metrics import classification_report, confusion_matrix

    return PIIRemover, classification_report, confusion_matrix, io, mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Expected Format of the data
    - query : The text message that you want to run against the validators
    - guardrail_triggered : name of the validators you expect to catch this query. In case of queries that should get caught by multiple validators, you can separate them with a "+" sign. for instance : PII + topic_relevance
    """)
    return


@app.cell
def _(mo):
    file_picker = mo.ui.file(filetypes=[".csv"], label="Select a CSV file")
    file_picker
    return (file_picker,)


@app.cell
def _(file_picker, io, mo, pd):
    if file_picker.value:
        user_df = pd.read_csv(io.BytesIO(file_picker.value[0].contents))
        user_df[["query", "guardrail_triggered"]]
    else:
        user_df = pd.DataFrame(columns=["query", "guardrail_triggered"])
        mo.md("*Please select a CSV file to continue.*")
    return (user_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Calculate PII match
    """)
    return


@app.cell
def _(PIIRemover):
    pii_validator = PIIRemover(
        entity_types=[
            "EMAIL_ADDRESS",
            "PHONE_NUMBER",
            "IN_AADHAAR",
            "PERSON",
            "IN_PAN",
            "LOCATION",
            "IN_VOTER",
            "IN_PASSPORT",
            "IN_VEHICLE_REGISTRATION",
            "URL"],
    )
    return (pii_validator,)


@app.cell
def _(pii_validator):
    _result = pii_validator._validate("hey buddy budgeting kya hota haiii muje asan trike se smjao with examples")
    _result.outcome == "fail"
    return


@app.cell
def _(user_df):
    def actual_label(input):
        return "PII" in input

    user_df["pii_true"] = user_df["guardrail_triggered"].apply(actual_label)
    user_df[["query", "guardrail_triggered" ,"pii_true"]]
    return


@app.cell
def _(pii_validator, user_df):
    def is_pii(message):
        result = pii_validator._validate(message)
        return result.outcome == "fail"

    user_df["pii_pred"] = user_df["query"].apply(is_pii)
    user_df[["query","guardrail_triggered","pii_true","pii_pred"]]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Scores
    """)
    return


@app.cell
def _(classification_report, user_df):
    print(classification_report(user_df["pii_true"], user_df["pii_pred"]))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Confusion Matrix
    """)
    return


@app.cell
def _(confusion_matrix, user_df):
    cm = confusion_matrix(user_df["pii_true"], user_df["pii_pred"])
    tn, fp, fn, tp = cm.ravel()
    print(f"{fn} - {fp} - {tp} - {tn}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## False Negatives
    """)
    return


@app.cell
def _(user_df):
    user_df[(user_df["pii_true"] == True) & (user_df["pii_pred"] == False)][["query"]]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## True Positives
    """)
    return


@app.cell
def _(user_df):
    user_df[(user_df["pii_true"] == True) & (user_df["pii_pred"] == True)][["query"]]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## False Positives
    """)
    return


@app.cell
def _(user_df):
    user_df[(user_df["pii_true"] == False) & (user_df["pii_pred"] == True)][["query"]]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## True Negatives
    """)
    return


@app.cell
def _(user_df):
    user_df[(user_df["pii_true"] == False) & (user_df["pii_pred"] == False)][["query"]]
    return


if __name__ == "__main__":
    app.run()
