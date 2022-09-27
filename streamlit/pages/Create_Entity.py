import asyncio
import copy
from io import StringIO

import pandas as pd
import spacy_streamlit
import streamlit as st
from godel import GoldenAPI
from godel.schema import CreateEntityInput, StatementInputRecordInput
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import AgGridTheme

st.set_page_config(layout="wide")

st.markdown("# Create Entity")
st.sidebar.markdown("# Create Entity")

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


"# 1. Attempt to Disambiguate Subject"

# Get predicates and templates
predicates = {}
predicates_inverse = {}
for p in goldapi.predicates()["data"]["predicates"]["edges"]:
    p = p["node"]
    predicates[p["name"]] = {"id": p["id"], "objectType": p["objectType"]}
    predicates_inverse[p["id"]] = {"name": p["name"], "objectType": p["objectType"]}
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

    st.write(
        "Specify name of entity you want to create and make sure that it doesn't already exist with initial searching."
    )

    st.write("### Subject")
    data = None

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
            "Potential pre-existing entities", options=subject_search_choices
        )
    else:
        subject_entity_disambiguation = st.selectbox(
            "Potential pre-existing entities",
            options=["No entity found. Continue to create entity."],
        )

    st.write("### Statements")

    st.write(
        "# 2. Create Statements and Minimum Disambiguation Triples(MDTs) for Entity"
    )

    # Specifiy number of predicates and load
    num_predicates = st.number_input("Number of statements you'd like to add", 0, 10)

    statements = []
    object_entity_disambiguation = []
    for npred in range(int(num_predicates)):

        st.write("___")

        st.write(f"### Statement #{npred+1}")

        # Select predicate
        st.write("#### Predicate")
        predicate = st.selectbox(
            "Predicate", options=predicates_df.index, key=f"PREDICATE_{npred}"
        )

        # Select object
        st.write("#### Object")
        # Depending on predicate, provide object options
        object_entity_disambiguation = []
        if predicates_df["objectType"][predicate] == "ENTITY":
            object = st.text_input("Object name", key=f"ENTITY_{npred}")

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
                    "Object Golden entity",
                    options=object_search_choices,
                    key=f"OBJECT_CHOICE_{npred}",
                )
            else:
                object_entity_disambiguation = st.selectbox(
                    "Object Golden entity",
                    options=["No entity found. Entity MUST be created first."],
                    key=f"OBJECT_NONE_{npred}",
                )
        elif predicates_df["objectType"][predicate] == "ANY_URI":
            object = st.text_input("Enter URI", key=f"ANY_URI_{npred}")
        elif predicates_df["objectType"][predicate] == "STRING":
            object = st.text_input("Enter string", key=f"STRING_{npred}")
        else:
            object = st.text_input("Enter", key=f"ELSE_{npred}")

        # Citation
        st.write("#### Citation")
        citation = st.text_input("Citation", key=f"CITATION_{npred}")

        # Create statement record input
        # Case 1: Object entity predicate and it exists
        if len(object_entity_disambiguation) > 1:
            statements.append(
                StatementInputRecordInput(
                    predicate_id=predicates[predicate]["id"],
                    object_entity_id=object_entity_disambiguation[1],
                    citation_urls=[citation] if citation else [],
                    qualifiers=[],
                )
            )
        # Case 2: Non-entity predicate
        else:
            statements.append(
                StatementInputRecordInput(
                    predicate_id=predicates[predicate]["id"],
                    object_value=object,
                    citation_urls=[citation] if citation else [],
                    qualifiers=[],
                )
            )

    "# 3. Entity Preview and Submission"
    st.write("#### Preview of Entity")
    st.write(f"**Subject**:  {subject}")
    col1, col2, col3 = st.columns(3)
    with col1:
        for s in statements:
            col1.metric(
                "Predicate",
                f"{predicates_inverse[s.predicate_id]['name']}({s.predicate_id})",
            )
    with col2:
        for s in statements:
            try:
                col2.metric("Object", s.object_value)
            except:
                col2.metric("Object", f"EntityID: {s.object_entity_id}")
    with col3:
        for s in statements:
            col3.metric("Citation", str(s.citation_urls))

    if st.button("Submit Entity"):
        if statements:
            create_entity_input = CreateEntityInput(name=subject, statements=statements)
            data = goldapi.create_entity(create_entity_input=create_entity_input)
        else:
            data = None

        try:
            entity_id = data["data"]["createEntity"]["entity"]["id"]
            st.write(f"https://dapp.golden.xyz/entity/{entity_id}")
            data
        except:
            st.write("Invalid or no submission yet, check error message")
            st.write(f"Data message return {data}")
