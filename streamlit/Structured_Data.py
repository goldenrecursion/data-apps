from io import StringIO

import pandas as pd
import streamlit as st
from godel import GoldenAPI
from godel.schema import (
    CreateEntityInput,
    QualifierInputRecordInput,
    StatementInputRecordInput,
)
from st_aggrid import (
    AgGrid,
    DataReturnMode,
    GridOptionsBuilder,
    GridUpdateMode,
    AgGridTheme,
)
from st_aggrid.shared import AgGridTheme

st.set_page_config(layout="wide")

st.markdown("# Data Table Import")
st.sidebar.markdown("# Data Table Import")


"# 0. Add your API key"
api_key = st.text_input("API Key", "")

# API
if api_key:
    goldapi = GoldenAPI(jwt_token=api_key)
else:
    goldapi = GoldenAPI()

"# 1. Upload your data"
"This currently works best for single row -> single subject entity ingest"

uploaded_file = st.file_uploader("Upload CSVs and data tables here.")

df = pd.DataFrame([])

if uploaded_file:
    # Can be used wherever a "file-like" object is accepted:
    try:
        dataframe = pd.read_csv(uploaded_file)
    except:
        pass

    gb = GridOptionsBuilder.from_dataframe(dataframe)
    gb.configure_pagination(paginationAutoPageSize=True)  # Add pagination
    gb.configure_side_bar()  # Add a sidebar
    gb.configure_default_column(editable=True)
    gridOptions = gb.build()

    grid_response = AgGrid(
        dataframe,
        gridOptions=gridOptions,
        data_return_mode="AS_INPUT",
        update_mode="MODEL_CHANGED",
        fit_columns_on_grid_load=False,
        theme=AgGridTheme.STREAMLIT,
        enable_enterprise_modules=True,
        height=350,
        width="100%",
        reload_data=True,
    )

    data = grid_response["data"]
    df = pd.DataFrame(data)
    df = df[:10]


"# 2. Specify Triples"

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

"### a. Pick a subject column and specify its template"
# Iterate through columns and assign one of [None, "Subject", "Predicate"]
# Should only be one subject
columns = df.columns
subject_col = st.selectbox("Pick the subject column", list(columns))
subject_template = st.selectbox(
    "Pick the template for the subject", list(templates_df.index)
)


"### b. Specify a predicate field for each column"
"None will specify a column's variables a null and do nothing"
triple_col_map = {}
for i, col in enumerate(columns):
    # skip subject col
    if col == subject_col:
        continue

    plist = list(predicates_df.index)
    if col in predicates_df.index:
        pred_list = [col] + plist
    else:
        pred_list = [None] + plist

    triple_col_map[col] = st.selectbox(
        f"Predicate for {col}", pred_list, key=f"{i},{col}"
    )

"# 3 Submit subject entity and triples"

triple_col_map = {k: v for k, v in triple_col_map.items() if v is not None}

"Triple to predicate mapping"
triple_col_map

selected_columns = [subject_col] + list(triple_col_map.keys())

if len(df):
    ingest_df = df[selected_columns]
else:
    ingest_df = df

# ingest_df
# subject_col
# subject_template

create_entity_inputs = []

for i in range(len(ingest_df)):
    name = ingest_df[subject_col][i]

    # Add template
    statement_input_record_inputs = []

    statement_input_record_inputs.append(
        StatementInputRecordInput(
            predicate_id=predicates["Is a"]["id"],
            object_value=templates["Company"]["entityId"],
            citation_urls=[],
            qualifiers=[],
        )
    )

    # Add predicates
    for pred_col, pred_name in triple_col_map.items():
        object_value = ingest_df[pred_col][i]
        # delimiter
        if ", " in object_value:
            object_values = object_value.split(", ")
        else:
            object_values = [object_value]
        for object_value in object_values:
            statement_input_record_inputs.append(
                StatementInputRecordInput(
                    predicate_id=predicates[pred_name]["id"],
                    object_value=object_value,
                    citation_urls=[],
                    qualifiers=[],
                )
            )
    # Create Entity Input
    create_entity_input = CreateEntityInput(
        name=name, statements=statement_input_record_inputs
    )
    create_entity_inputs.append(create_entity_input)

created_data = []

if st.button("Submit Entities and Triples"):
    progress_bar = st.progress(0)
    len_entity_inputs = len(create_entity_inputs)
    for i, create_entity_input in enumerate(create_entity_inputs):
        try:
            progress_bar.progress((i + 1) / len_entity_inputs)
        except:
            print(i)
            print(len_entity_inputs)
        data = goldapi.create_entity(input=create_entity_input.__to_json_value__())
        created_data.append(data)
else:
    pass

### Submitted entities

created_data_df = pd.DataFrame(
    [d["data"]["createEntity"]["entity"] for d in created_data]
)
created_data_df
