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

########################
##### Introduction #####
########################

st.write("## Introduction")
st.markdown(
    """
In order to create an entity in Golden's protocol, you'll need to got through the following processes:

1. Disambiguate Subject
    - You'll need to confirm that the subject does not already exist
    - This prevents and duplicates and potential penalities
    - If unable to disambiguate, you can create your entity subject

2. Select Template and Create Statements
    - Minimum Disambiguation Triples (MDTs) are required
    - MDTs includes templates via the "Is a" predicate
    - Create additional MDT statements dependant on your template statement

3. Confirm Entity Submission
    - Confirm the entity statements are correct
    - Submit by creating entity with the GraphQL API
"""
)


#########################
##### API and Setup #####
#########################
st.write("### 0. Authenticate with JSON Web Token (JWT) ")

st.write(
    "You can retrieve this from your profile page here: https://dapp.golden.xyz/profile"
)

jwt_token = st.text_input("JWT:", "")

st.write("## Get Started")

if jwt_token:
    goldapi = GoldenAPI(jwt_token=jwt_token)
else:
    goldapi = GoldenAPI()

# Retrieve predicate and template data
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


################################
##### Disambiguate Subject #####
################################
st.write("### 1. Disambiguate Subject")

with st.container():

    st.write(
        "Specify name of entity you want to create and make sure that it doesn't already exist with initial searching."
    )

    st.write("#### Subject")
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

    ##############################
    ##### Template Statement #####
    ##############################

    # All statements to be added
    statements = []

    st.write("### 2. Select Template Subject")

    template_entity = st.selectbox(
        "'Is a' Templates",
        sorted(templates_df.index),
    )
    template_entity_id = templates_df.entityId[template_entity]

    # Add "Is a" template statement
    statements.append(
        StatementInputRecordInput(
            predicate_id=predicates["Is a"]["id"],
            object_entity_id=template_entity_id,
            citation_urls=[],
            qualifiers=[],
        )
    )

    # Add "Name predicate"
    statements.append(
        StatementInputRecordInput(
            predicate_id=predicates["Name"]["id"],
            object_value=subject,
            citation_urls=[],
            qualifiers=[],
        )
    )

    ###############################
    ##### MDTs and Statements #####
    ###############################

    st.write(
        "### 3. Create Minimum Disambiguation Triples(MDTs) and Statements for Entity"
    )

    st.write(
        "Please first refer to our Protocol Schema at https://dapp.golden.xyz/schema before selecting your statements."
    )
    st.write(
        "Additional information on MDTs can be found here https://docs.golden.xyz/protocol/concepts/minimum-disambiguation-triple-requirements-mdt"
    )

    st.write("#### Statements")
    # Specifiy number of predicates and load
    num_predicates = st.number_input("Number of statements you'd like to add", 0, 10)

    object_entity_disambiguation = []
    for npred in range(int(num_predicates)):

        st.write("___")

        st.write(f"#### Statement #{npred+1}")

        # Select predicate
        st.write("##### Predicate")
        predicate = st.selectbox(
            "Predicate", options=sorted(predicates_df.index), key=f"PREDICATE_{npred}"
        )

        # Select object
        st.write("##### Object")
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
        st.write("##### Citation")
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

    #########################################
    ##### Entity Preview and Submission #####
    #########################################

    st.write("### 4. Entity Preview and Submission")
    st.write("##### Preview of Entity")
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
            create_entity_input = CreateEntityInput(statements=statements)
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
