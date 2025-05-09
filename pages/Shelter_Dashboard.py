import streamlit as st
import pandas as pd
import uuid
import os

# Set page config first
st.set_page_config(page_title="Shelter Dashboard", layout="wide")

# Load CSVs
@st.cache_data
def load_data():
    if os.path.exists("pets.csv"):
        pets_df = pd.read_csv("pets.csv")
    else:
        pets_df = pd.DataFrame(columns=["pet_id", "species", "breed", "gender", "name", "sheltername", "activity_level", "age", "allergy_friendly", "time_in_shelter", "disability_current", "disability_past", "special_needs"])
    
    if os.path.exists("adopters.csv"):
        adopters_df = pd.read_csv("adopters.csv")
    else:
        adopters_df = pd.DataFrame(columns=["adopter_id", "name", "country", "age", "pref_species", "pref_gender", "house", "garden", "activity_level", "allergy_friendly", "apartment_size", "username", "password", "liked_pets"])
    
    if os.path.exists("shelters.csv"):
        shelters_df = pd.read_csv("shelters.csv")
    else:
        shelters_df = pd.DataFrame(columns=["shelter_id", "name", "address", "email", "phone", "username", "password"])
    
    return pets_df, adopters_df, shelters_df

pets_df, adopters_df, shelters_df = load_data()

# Save CSVs
def save_data():
    global pets_df, adopters_df, shelters_df
    pets_df.to_csv("pets.csv", index=False)
    adopters_df.to_csv("adopters.csv", index=False)
    shelters_df.to_csv("shelters.csv", index=False)

# Add pet
def add_pet(shelter_id, pet_data):
    global pets_df
    pet_data["pet_id"] = f"PET{uuid.uuid4().hex[:6].upper()}"
    shelter = shelters_df[shelters_df["shelter_id"] == shelter_id].iloc[0]
    pet_data["sheltername"] = shelter["name"]
    pets_df = pd.concat([pets_df, pd.DataFrame([pet_data])], ignore_index=True)
    save_data()
    return "Pet added successfully"

# Delete shelter account
def delete_shelter_account(shelter_id):
    global pets_df, shelters_df
    shelter = shelters_df[shelters_df["shelter_id"] == shelter_id].iloc[0]
    pets_df = pets_df[pets_df["sheltername"] != shelter["name"]]
    shelters_df = shelters_df[shelters_df["shelter_id"] != shelter_id]
    save_data()
    return "Shelter account and associated pets deleted successfully"

# Shelter dashboard
st.sidebar.title("Dog Shelter Adoption Platform")
st.sidebar.markdown("Navigate:")

st.title("Shelter Dashboard")
st.markdown("### Join Our Pet Adoption Community! 🐾")
st.markdown("Find your furry friend or help pets find loving homes with our platform! ❤️")

# Display images
if os.path.exists("pics/f1.png") and os.path.exists("pics/f2.png"):
    col1, col2 = st.columns(2)
    with col1:
        st.image("pics/f1.png", caption="Happy Pets", use_column_width=True)
    with col2:
        st.image("pics/f2.png", caption="Loving Homes", use_column_width=True)
else:
    st.warning("Images not found. Please ensure pics/f1.png and pics/f2.png are in the repository.")

if st.session_state.user is None or st.session_state.user_type != "Shelter":
    st.error("Please log in as a Shelter.")
    st.markdown("[Go to Login/Registration](./)")
else:
    user = st.session_state.user
    st.subheader(f"Welcome, {user['name']}")

    # Menu
    option = st.selectbox("Choose an action", ["Add New Pet", "View My Pets", "Delete Account"])

    if option == "Add New Pet":
        st.subheader("Add New Pet")
        pet_data = {}
        fields = ["species", "breed", "gender", "name", "activity_level", "age", "allergy_friendly", "time_in_shelter", "disability_current", "disability_past", "special_needs"]
        for field in fields:
            if field == "allergy_friendly":
                pet_data[field] = st.selectbox("Allergy Friendly", ["Yes", "No"], key=f"pet_{field}")
            elif field == "activity_level":
                pet_data[field] = st.selectbox("Activity Level", ["High", "Medium", "Low"], key=f"pet_{field}")
            else:
                pet_data[field] = st.text_input(field.capitalize(), key=f"pet_{field}")
        if st.button("Add Pet"):
            message = add_pet(user["shelter_id"], pet_data)
            st.success(message)

    elif option == "View My Pets":
        st.subheader("My Pets")
        shelter_pets = pets_df[pets_df["sheltername"] == user["name"]]
        if shelter_pets.empty:
            st.write("No pets added yet.")
        else:
            for _, pet in shelter_pets.iterrows():
                st.write(f"{pet['name']} ({pet['species']}, {pet['breed']})")

    elif option == "Delete Account":
        st.subheader("Delete Account")
        if st.button("Confirm Deletion"):
            message = delete_shelter_account(user["shelter_id"])
            st.success(message)
            st.session_state.user = None
            st.session_state.user_type = None
            st.rerun()

    if st.button("Logout"):
        st.session_state.user = None
        st.session_state.user_type = None
        st.rerun()