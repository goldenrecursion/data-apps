import asyncio
import copy
from io import StringIO

import pandas as pd
import spacy_streamlit
import streamlit as st
from godel import GoldenAPI
from godel.schema import CreateStatementInput
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import AgGridTheme

st.set_page_config(layout="wide")

st.markdown("# Create Triple")
st.sidebar.markdown("# Create Triple")

"# 0. Add your API key"
api_key = st.text_input("API Key", "")

# API
if api_key:
    goldapi = GoldenAPI(jwt_token=api_key)
else:
    goldapi = GoldenAPI()

citation_urls = set()
try:
    entity_edges = entity_data["data"]["entity"]["statementsBySubjectId"]["edges"]
    for e in entity_edges:
        if e["node"]["citationUrl"]:
            citation_urls.add(e["node"]["citationUrl"])
except:
    "Seems like there are no citations"


"# 1. Submit Triple"

# Get predicates and templates
predicates = {}
for p in goldapi.predicates()["data"]["predicates"]["edges"]:
    p = p["node"]
    predicates[p["name"]] = {"id": p["id"], "objectType": p["objectType"]}
predicates_df = pd.DataFrame(predicates).transpose()

templates = {}
for t in goldapi.templates()["data"]["templates"]["edges"]:
    t = t["node"]
    templates[t["entity"]["name"]] = {
        "id": t["id"],
        "entityId": t["entityId"],
        "entityDescription": t["entity"]["description"],
    }
templates_df = pd.DataFrame(templates).transpose()

# Get potential entity subjects from text


with st.container():

    st.write("Specify triples to submit for entities that already exist")

    st.write("### Subject")

    # Get entity text options
    subject = st.text_input("Subject name")
    # Disambiguate entity
    subject_search_results = goldapi.entity_search(subject)
    try:
        subject_search_choices = (
            subject_search_results.get("data", {})
            .get("entityByName", {})
            .get("nodes", [])
        )
    except:
        subject_search_choices = []
    if subject_search_choices:
        subject_search_choices = [(s["name"], s["id"]) for s in subject_search_choices]
        subject_entity_disambiguation = st.selectbox(
            "Subject Golden entity", options=subject_search_choices
        )
    else:
        subject_entity_disambiguation = st.selectbox(
            "Subject Golden entity",
            options=["No entity found. Entity MUST be created first."],
        )

    # Select predicate
    st.write("### Predicate")
    predicate = st.selectbox("Predicate", options=predicates_df.index)

    # Select object
    st.write("### Object")
    # Depending on predicate, provide object options
    object_entity_disambiguation = []
    if predicates_df["objectType"][predicate] == "ENTITY":
        object = st.text_input("Object name")

        # Disambiguate entity
        object_search_results = goldapi.entity_search(object)
        try:
            object_search_choices = (
                object_search_results.get("data", {})
                .get("entityByName", {})
                .get("nodes", [])
            )
        except:
            object_search_choices = []
        if object_search_choices:
            object_search_choices = [
                (s["name"], s["id"]) for s in object_search_choices
            ]
            object_entity_disambiguation = st.selectbox(
                "Object Golden entity", options=object_search_choices
            )
        else:
            object_entity_disambiguation = st.selectbox(
                "Object Golden entity",
                options=["No entity found. Entity MUST be created first."],
            )
    elif predicates_df["objectType"][predicate] == "ANY_URI":
        object = st.text_input("Enter URI")
    elif predicates_df["objectType"][predicate] == "STRING":
        object = st.text_input("Enter string")
    else:
        object = st.text_input("Enter")

    # Citation
    st.write("### Citation")
    citation = st.text_input("Citation")

    "# 2. Triple Preview and Submission"
    st.write("### Preview of Triple")
    col1, col2, col3 = st.columns(3)
    preview_subject = (
        subject_entity_disambiguation[0] if subject_entity_disambiguation else subject
    )
    preview_object = (
        object_entity_disambiguation[0] if object_entity_disambiguation else object
    )
    col1.metric("Subject", preview_subject)
    col2.metric("Predicate", predicate)
    col3.metric("Object", preview_object)
    f"Citation: {citation}"

    if st.button("Submit triple"):
        # Case 1: Both subject and object entities exist so we just create the triple
        if predicates_df["objectType"][predicate] == "ENTITY":
            create_statement_input = CreateStatementInput(
                subject_id=subject_entity_disambiguation[1],
                predicate_id=predicates[predicate]["id"],
                object_entity_id=object_entity_disambiguation[1],
                citation_urls=[citation] if citation else [],
            )
            data = goldapi.create_statement(
                create_statement_input=create_statement_input
            )

        # Case 2: Subject entity exists and object is value
        elif predicates_df["objectType"][predicate] != "ENTITY":
            create_statement_input = CreateStatementInput(
                subject_id=subject_entity_disambiguation[1],
                predicate_id=predicates[predicate]["id"],
                object_value=object,
                citation_urls=[citation] if citation else [],
            )
            data = goldapi.create_statement(
                create_statement_input=create_statement_input
            )
        else:
            data = None

        try:
            entity_id = data["data"]["createStatement"]["statement"]["subject"]["id"]
            st.write(f"https://dapp.golden.xyz/entity/{entity_id}")
            data
        except:
            st.write("Invalid or no submission yet, check error message")
            st.write(f"Data message return:")
            data
