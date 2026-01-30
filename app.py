
import streamlit as st
import pandas as pd
import plotly.express as px

from helper import (
    supv_view_cols,
    split_comma_values,
    pad_leading_zeros,
    format_name,
    comply_map,
    comply_map_verbose,
    pivot_cols,
)


# Get the current credentials

st.set_page_config(layout="wide")
st.title("Compliance Dashboard")

st.caption('Welcome!')


@st.cache_data
def load_data():
    df = pd.read_csv("MMECH/sample_data/compliance_extract_example.csv", index_col="Unnamed: 0")
    df["ID"] = pad_leading_zeros(df["ID"])
    df["Supv ID"]=df["Supv ID"].astype(str)
    return df

df = load_data()


# Sidebar or main input for user ID
user_id = st.text_input("🔐 Enter your User ID to access your employees' compliance info:")

if user_id:
    filtered_df = df[df["Supv ID"] == str(user_id)]

    if not filtered_df.empty:
        supv_name = filtered_df['Supv Name'].iloc[0]

        # Get unique IDs & Units for this supervisor
        # === New panel for multi‑filter (scrollable with Select All/Clear All) ===
        st.sidebar.markdown("### 🔎 Filter Employees")
        
        # Get unique IDs & Units for this supervisor
        available_ids = sorted(filtered_df['ID'].unique())
        available_units = sorted(filtered_df['Unit'].dropna().unique())
        available_depts = sorted(filtered_df['Dept Name'].dropna().unique())
        
        # --- Employee IDs as a scrollable checkbox grid ---
        id_state_key = f"id_table_{user_id}"
        
        # Initialize/sync selection table in session_state
        id_df_current = pd.DataFrame({"ID": available_ids})
        if id_state_key not in st.session_state:
            # Default: all selected
            st.session_state[id_state_key] = id_df_current.assign(Selected=True)
        else:
            # Merge to keep prior choices, default new IDs to True
            prev = st.session_state[id_state_key][["ID", "Selected"]]
            merged = id_df_current.merge(prev, on="ID", how="left")
            merged["Selected"] = merged["Selected"].fillna(True)
            st.session_state[id_state_key] = merged
        
        # Select All / Clear All controls
        c1, c2 = st.sidebar.columns(2)
        with c1:
            if st.button("Select All", use_container_width=True, key=f"btn_all_{user_id}"):
                st.session_state[id_state_key]["Selected"] = True
        with c2:
            if st.button("Clear All", use_container_width=True, key=f"btn_none_{user_id}"):
                st.session_state[id_state_key]["Selected"] = False
                
                
        
        # Scrollable checkbox table
        edited_id_table = st.sidebar.data_editor(
            st.session_state[id_state_key],
            hide_index=True,
            use_container_width=True,
            height=150,  # adjust to taste
            column_config={
                "Selected": st.column_config.CheckboxColumn("Selected", help="Toggle employee visibility"),
                "ID": st.column_config.TextColumn("Employee ID", disabled=True),
            },
            key=f"de_ids_{user_id}",
        )
        # Persist edits
        st.session_state[id_state_key] = edited_id_table
        selected_ids = edited_id_table.loc[edited_id_table["Selected"], "ID"].tolist()
        
        
                    
        # --- Units picker (keeps multiselect, adds All/None buttons and proper state) ---
        units_state_key = f"units_{user_id}"
        if units_state_key not in st.session_state:
            st.session_state[units_state_key] = available_units

        depts_state_key = f"depts_{user_id}"
        if depts_state_key not in st.session_state:
            st.session_state[depts_state_key] = available_depts
                
        selected_units = st.sidebar.multiselect(
            "Select Unit(s):",
            options=available_units,
            default=None,  # default is driven by session_state via key
            key=units_state_key,
        )

        selected_depts = st.sidebar.multiselect(
            "Select Department(s):",
            options=available_depts,
            default=None,  # default is driven by session_state via key
            key=depts_state_key,
        )

        
        # Apply filters
        filtered_df = filtered_df[
            filtered_df['ID'].isin(selected_ids) &
            filtered_df['Unit'].isin(selected_units) &
            filtered_df['Dept Name'].isin(selected_depts)
        ]

        
        mask = df["ID"].isin(selected_ids)
        if selected_units:
            mask &= df["Unit"].isin(selected_units)
        if selected_depts:
            mask &= df["Dept Name"].isin(selected_depts)
        
        filtered_df = filtered_df[mask]


        if filtered_df.empty:
            st.info('There is no data available based on selections.')
            st.stop()


        # === Display filtered data ===
        st.text(f"Compliance Details for Supervisor: {supv_name}")
        st.dataframe(filtered_df[supv_view_cols], use_container_width=True)

        # === Sunburst logic ===
        
        data = {supv_name: {}}
        for category, (name_col, date_col) in comply_map.items():
            cat_dict = {}
            split_df = split_comma_values(filtered_df, name_col, date_col)
            
            if split_df.empty:
                continue

            for emp, emp_df in split_df.groupby('Name'):
                name_values = emp_df[name_col].dropna().unique().tolist()
    
                if name_values:
                    emp_dict = {}
                    for name_val in name_values:
                        if date_col:
                            dates = emp_df.loc[emp_df[name_col] == name_val, date_col].dropna().unique().tolist()
                            emp_dict[name_val] = dates if dates else None
                        else:
                            emp_dict[name_val] = None
                    cat_dict[emp] = emp_dict
            if cat_dict:
                data[supv_name][category] = cat_dict

        records = []
        for supv, categories in data.items():
            for category, employees in categories.items():
                for emp, names in employees.items():
                    for name_val, dates in names.items():
                        if dates:
                            for date_val in dates:
                                records.append([supv, category, emp, str(name_val), str(date_val)])
                        else:
                            records.append([supv, category, emp, str(name_val)])

        max_depth = max(len(r) for r in records)
        for r in records:
            while len(r) < max_depth:
                r.append(None)

        cols = ['Supervisor', 'Category', 'Employee', 'Name', 'Date'][:max_depth]
        df_hier = pd.DataFrame(records, columns=cols)
        df_hier['Count'] = 1

        fig = px.sunburst(
            df_hier,
            path=cols,
            values='Count',
            color='Category',
            color_discrete_sequence=px.colors.qualitative.Set2,
            branchvalues='total',
            title="Sunburst Chart"
        )
        fig.update_layout(
            height=900,
            width=900
        )

        st.plotly_chart(fig,use_container_width=True)
    else:
        st.warning("No data found for this ID. Please check and try again.")

    
    # Dictionary keyed by employee -> list of task strings
    employee_tasks = {}
    
    for category, (name_col, date_col) in comply_map_verbose.items():
        split_df = split_comma_values(filtered_df, name_col, date_col)
    
        for _, row in split_df.iterrows():
            emp_name = format_name(row["Name"])
            item_name = row[name_col]
            item_date = row[date_col] if date_col else None
    
            if not pd.notna(item_name):
                continue
    
            item_str = str(item_name)
    
            # Special case: "does not exist"
            if "does not exist" in item_str.lower():
                task_text = f"{item_str}"
            else:
                if category == "Checklist":
                    task_text = f"is due for checklist item '{item_str}'" + (f" which expires {item_date}" if pd.notna(item_date) else "")
                elif category == "Courses":
                    task_text = f"must complete course '{item_str}'" + (f" by {item_date}" if pd.notna(item_date) else "")
                elif category == "Licenses":
                    task_text = f"needs to renew license/certification '{item_str}'" + (f" by {item_date}" if pd.notna(item_date) else "")
                elif category == "Meals":
                    task_text = f"has a recorded meal issue: {item_str}"
    
            # Add to the employee's list
            employee_tasks.setdefault(emp_name, []).append(task_text)
    
    st.subheader("📝 Employee To‑Do List")
    for emp_name, tasks in employee_tasks.items():
        st.markdown(f"**{emp_name}**")
        for t in tasks:
            st.write(f"- {t}")


    # Let user pick pivot dimension
    x_axis_choice = st.selectbox(
        "Select Pivot Field",
        pivot_cols,
        index=0
    )
    
    # Build a category-level dataset per chosen X-axis
    records_bar = []
    for category, (name_col, date_col) in comply_map.items():
        split_df = split_comma_values(filtered_df, name_col, date_col)
        if split_df.empty:
            continue
        for _, row in split_df.iterrows():
            records_bar.append({
                x_axis_choice: row[x_axis_choice],
                "Category": category,
                "ID": row["ID"]
            })
    
    df_bar = pd.DataFrame(records_bar)
    
    # Count unique IDs per group
    pivot_df = (
        df_bar.groupby([x_axis_choice, "Category"])["ID"]
        .nunique()
        .reset_index(name="Count")
    )

    fig_bar = px.bar(
    pivot_df,
    x=x_axis_choice,
    y="Count",
    color="Category",
    text="Count",
    barmode="stack",
    color_discrete_sequence=px.colors.qualitative.Set2,
    title=f"Compliance Counts by {x_axis_choice}"
    )
    
    fig_bar.update_layout(
        autosize=True
    )
    
    st.plotly_chart(fig_bar,use_container_width=True)






    
