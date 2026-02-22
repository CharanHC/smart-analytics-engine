import streamlit as st
import pandas as pd
from engine import run_query, SmartAnalyticsEngine

st.set_page_config(page_title="Smart Analytics Engine", layout="wide")

import base64

def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

bg_img = get_base64("download.jpg")

# Inject Custom CSS
st.markdown(f"""
<style>
    /* Main Background */
    .stApp {{
        background-image: url("data:image/png;base64,{bg_img}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #e0e0e0;
    }}
    
    /* Header styling */
    h1, h2, h3 {{
        color: #ffffff !important;
        font-family: 'Inter', sans-serif;
    }}

    /* Primary and Secondary Buttons */
    div.stButton > button {{
        background: linear-gradient(90deg, #ff8a00, #e52e71);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: transform 0.2s, box-shadow 0.2s;
    }}
    
    div.stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(229, 46, 113, 0.4);
        color: white;
        border: none;
    }}

    /* Download Buttons */
    div.stDownloadButton > button {{
        background: linear-gradient(90deg, #11998e, #38ef7d);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: transform 0.2s, box-shadow 0.2s;
    }}

    div.stDownloadButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(56, 239, 125, 0.4);
        color: white;
        border: none;
    }}

    /* Dataframe background */
    [data-testid="stDataFrame"] {{
        background-color: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 10px;
    }}
</style>
""", unsafe_allow_html=True)

st.title("📊 Smart Analytics Engine")

data_source_opt = st.radio("Choose Data Source", ["Upload Excel File", "Connect to Database"], horizontal=True)

if 'df' not in st.session_state:
    st.session_state['df'] = None
if 'query_result' not in st.session_state:
    st.session_state['query_result'] = None

if data_source_opt == "Upload Excel File":
    uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx", "csv"])
    if uploaded_file:
        if uploaded_file.name.endswith(".csv"):
            st.session_state['df'] = pd.read_csv(uploaded_file)
        else:
            st.session_state['df'] = pd.read_excel(uploaded_file)
    else:
        st.session_state['df'] = None
            
elif data_source_opt == "Connect to Database":
    st.info("Example URI: sqlite:///mydatabase.db or postgresql://user:password@localhost/mydb")
    db_uri = st.text_input("Database URI")
    sql_query = st.text_area("SQL Query (e.g. SELECT * FROM table_name)")
    
    if st.button("Connect & Fetch Data") and db_uri and sql_query:
        try:
            import sqlalchemy as sa
            engine = sa.create_engine(db_uri)
            st.session_state['df'] = pd.read_sql(sql_query, engine)
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")

df = st.session_state['df']

if df is not None:

    # Auto-detect date columns
    for col in df.columns:
        if "date" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col])
            except:
                pass

    st.success("File uploaded successfully!")

    st.subheader("Preview")
    st.dataframe(df.head())

    # Ask question
    st.subheader("Ask AI Question")
    question = st.text_input("Type your question")

    if st.button("Run Query") and question:
        st.session_state['query_result'] = run_query(df, question)
        
    if st.session_state['query_result'] is not None:
        st.subheader("Result")
        st.dataframe(st.session_state['query_result'])

        st.download_button(
            "Download Result",
            st.session_state['query_result'].to_csv(index=False).encode('utf-8'),
            "result.csv",
            key="download_query_result"
        )

    # Dynamic filter
    st.subheader("Filter Data")

    filtered_df = df.copy()

    # Let user pick which columns to filter on
    filter_cols = st.multiselect("Filter dataframe on", df.columns)
    
    for col in filter_cols:
        # Datetime
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            target_date = st.date_input(f"Select date for {col}", value=None)
            if target_date:
                filtered_df = filtered_df[filtered_df[col].dt.date == target_date]
        
        # Categorical / Object / String
        elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            unique_vals = df[col].dropna().unique()
            selected_vals = st.multiselect(f"Select values for {col}", unique_vals)
            if selected_vals:
                filtered_df = filtered_df[filtered_df[col].isin(selected_vals)]
                
        # Numeric
        elif pd.api.types.is_numeric_dtype(df[col]):
            try:
                _min = float(df[col].dropna().min())
                _max = float(df[col].dropna().max())
                
                if _min < _max:
                    selected_range = st.slider(f"Select range for {col}", min_value=_min, max_value=_max, value=(_min, _max))
                    filtered_df = filtered_df[(df[col] >= selected_range[0]) & (df[col] <= selected_range[1])]
                else:
                    st.info(f"Column '{col}' has a constant value of {_min}")
            except Exception:
                st.info(f"Could not filter numeric column '{col}'")

    import io

    st.subheader("Filtered Data")
    display_cols = st.multiselect("Choose columns to display", df.columns, default=df.columns[:5])
    if display_cols:
        final_df = filtered_df[display_cols]
    else:
        final_df = filtered_df

    st.dataframe(final_df)

    download_format = st.radio("Download Format", ["CSV", "Excel"], horizontal=True)

    if download_format == "CSV":
        st.download_button(
            "Download Filtered Data",
            final_df.to_csv(index=False).encode('utf-8'),
            "filtered.csv",
            key="download_filtered_data_csv"
        )
    else:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False, sheet_name='Filtered Data')
        
        st.download_button(
            "Download Filtered Data",
            buffer.getvalue(),
            "filtered.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_filtered_data_excel"
        )

    # Dynamic Dashboard Creation
    st.subheader("📈 Dynamic Dashboard")
    
    # We only show the dashboard if there are columns to plot
    if len(final_df.columns) >= 2:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chart_type = st.selectbox("Chart Type", ["Bar Chart", "Line Chart", "Scatter Plot", "Area Chart"])
        with col2:
            x_axis = st.selectbox("X-Axis (Categorical/Time)", final_df.columns, index=0)
        with col3:
            # Try to default Y-axis to a numeric column if available
            numeric_cols = final_df.select_dtypes(include='number').columns.tolist()
            if numeric_cols and numeric_cols[0] in final_df.columns:
                default_y_index = list(final_df.columns).index(numeric_cols[0])
            elif len(final_df.columns) > 1:
                default_y_index = 1
            else:
                default_y_index = 0
                
            y_axis = st.selectbox("Y-Axis (Numeric)", final_df.columns, index=default_y_index)
            
        st.write(f"Displaying **{chart_type}** for `{y_axis}` over `{x_axis}`")
        
        # Prepare data for plotting (aggregate if necessary depending on the chart)
        # Use streamlit native charts
        if chart_type == "Bar Chart":
            st.bar_chart(final_df, x=x_axis, y=y_axis)
        elif chart_type == "Line Chart":
            st.line_chart(final_df, x=x_axis, y=y_axis)
        elif chart_type == "Scatter Plot":
            st.scatter_chart(final_df, x=x_axis, y=y_axis)
        elif chart_type == "Area Chart":
            st.area_chart(final_df, x=x_axis, y=y_axis)
            
    else:
        st.info("Need at least 2 columns in the dataset to generate a dashboard.")