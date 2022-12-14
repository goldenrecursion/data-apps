import asyncio
import copy
from io import StringIO
import requests

import pandas as pd
import spacy
import en_core_web_md
import spacy_streamlit
import streamlit as st
from godel import GoldenAPI
from godel.schema import CreateStatementInput
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode

from helper import get_text_from_website

nlp = en_core_web_md.load()

st.set_page_config(layout="wide")

st.markdown("# Text to Triples")
st.sidebar.markdown("# Text to Triples")


########################
##### Introduction #####
########################

st.write("## Introduction")
st.markdown(
    """
The Text to Triples demo shows an example of how you can extract entities and relationships from unstructured text
with the aid of pre-trained ML/NLP models provided by Spacy's Named Entity Recognition(NER) pipelines.

Checkout spacy's documentation on named entity recognition at https://spacy.io/usage/linguistic-features#named-entities

Extract and submit triples from text with the following process:

1. Extract Text Content from Website 
    - Submit the URL of a website page containing relevant text materials
    - We'll use Spacy to help you extract entities from unstructured text
    - Entity labels consist of:
        - PERSON: People, including fictional
        - NORP: Nationalities or religious or political groups
        - FACILITY: Buildings, airports, highways, bridges, etc.
        - ORGANIZATION: Companies, agencies, institutions, etc.
        - GPE: Countries, cities, states
        - LOCATION: Non-GPE locations, mountain ranges, bodies of water
        - PRODUCT: Vehicles, weapons, foods, etc. (Not services)
        - EVENT: Named hurricanes, battles, wars, sports events, etc.
        - WORK OF ART: Titles of books, songs, etc.
        - LAW: Named documents made into laws 
        - LANGUAGE: Any named language
        - DATE: Absolute or relative dates or periods
        - CARDINAL: Numerals that do not fall under another type
        - MONEY: Monetary values, including unit
        - ORDINAL: "first", "second", etc. 
        - PERCENT: Percentage, including "%"
        - QUANTITY: Measurements, as of weight or distance
        - TIME: Times smaller than a day

2. Create Statements
    - Create additional statements from triples you find in the text

3. Confirm Triple Submission
    - Confirm the statement is correct
    - Submit with the GraphQL API
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


#########################
##### Spacy and Web #####
#########################
st.write("### 1. Enter a website to extract entities and potential relationships")

url = st.text_input("")

meta, content = get_text_from_website(url)
all_text = meta + content

doc = nlp(all_text)

for ent in doc.ents:
    print(ent.text, ent.start_char, ent.end_char, ent.label_)

labels = set([ent.label_ for ent in doc.ents])
if labels:
    spacy_streamlit.visualize_ner(doc, labels=labels)

############################
##### Create Statement #####
############################
st.write("### 2. Create Statement")

with st.container():

    st.write(
        "Specify name of entity you want to create a statement for."
    )

    st.write("#### Subject")

    # Get entity text options
    subject_entity_choices = list(
        filter(lambda x: x.label_ == "ORG" or x.label_ == "PERSON", doc.ents)
    )
    subject_entity_choices = set([span.text for span in subject_entity_choices])
    subject = st.selectbox("Subject", options=subject_entity_choices)

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
    st.write("#### Predicate")
    predicate = st.selectbox("Predicate", options=sorted(predicates_df.index))

    # Select object
    st.write("#### Object")
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
    elif predicates_df["objectType"][predicate] == "DATE":
        object = st.text_input("Enter date DD-MM-YYYY")
    else:
        object = st.text_input("Enter")

    # Citation
    st.write("#### Citation")
    citation = st.text_input("Citation", url)

################################
##### Statement Submission #####
################################
    "### 3. Triple Preview and Submission"
    st.write("#### Preview of Triple")
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
