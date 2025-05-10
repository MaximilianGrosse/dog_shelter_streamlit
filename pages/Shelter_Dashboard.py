import streamlit as st
import pandas as pd
import os
import uuid

# Set page config
st.set_page_config(page_title="Shelter Dashboard", layout="wide")

# Load CSVs
@st.cache_data
def load_data():
    if os.path.exists("pets.csv"):
        pets_df = pd.read_csv("pets.csv")
    else:
        pets_df = pd.DataFrame(columns=["pet_id", "species", "breed", "gender", "name", "sheltername", "activity_level", "age", "allergy_friendly", "time_in_shelter", "disability_current", "disability_past", "special_needs", "image_path"])
    
    if os.path.exists("adopters.csv"):
        adopters_df = pd.read_csv("adopters.csv")
    else:
        adopters_df = pd.DataFrame(columns=["adopter_id", "name", "country", "age", "pref_species", "pref_gender", "house", "garden", "activity_level", "allergy_friendly", "apartment_size", "username", "password", "liked_pets", "skipped_pets"])
    
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
def add_pet(data, shelter_id):
    global pets_df
    data["pet_id"] = f"PET{uuid.uuid4().hex[:6].upper()}"
    data["sheltername"] = shelters_df[shelters_df["shelter_id"] == shelter_id].iloc[0]["name"]
    pets_df = pd.concat([pets_df, pd.DataFrame([data])], ignore_index=True)
    save_data()

# Edit pet
def edit_pet(pet_id, data):
    global pets_df
    pet_idx = pets_df.index[pets_df["pet_id"] == pet_id].tolist()[0]
    pets_df.at[pet_idx, data.keys()] = data.values()
    save_data()

# Upload photo
def upload_photo(pet_id, file):
    global pets_df
    if file is not None:
        file_path = f"pet_pics/{pet_id}.jpg"
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        pet_idx = pets_df.index[pets_df["pet_id"] == pet_id].tolist()[0]
        pets_df.at[pet_idx, "image_path"] = file_path
        save_data()

# Sidebar navigation
st.sidebar.markdown("## Dog Shelter Adoption Platform")
st.sidebar.markdown("### Navigation")
st.page_link("app.py", label="Login/Registration")
st.page_link("pages/Adopter_Dashboard.py", label="Adopter Dashboard")
st.page_link("pages/Shelter_Dashboard.py", label="Shelter Dashboard")

# Main content (simplified, assuming prior context)
st.title("Shelter Dashboard")

if st.session_state.user is None or st.session_state.user_type != "Shelter":
    st.error("Please log in as a Shelter.")
    st.markdown("[Go to Login/Registration](./)")
else:
    shelter = st.session_state.user
    st.subheader(f"Welcome, {shelter['name']}")

    # Add pet form
    with st.expander("Add New Pet"):
        species = st.selectbox("Species", ["Dog", "Cat", "Rabbit", "Turtle", "Hamster"])
        breed = st.text_input("Breed")
        gender = st.selectbox("Gender", ["Male", "Female"])
        name = st.text_input("Name")
        activity_level = st.selectbox("Activity Level", ["High", "Medium", "Low"])
        age = st.number_input("Age", min_value=0, step=0.1)
        allergy_friendly = st.selectbox("Allergy Friendly", ["Yes", "No"])
        time_in_shelter = st.selectbox("Time in Shelter", ["< 1 year", "1-2 years", "2+ years"])
        disability_current = st.text_input("Current Disability")
        disability_past = st.text_input("Past Disability")
        special_needs = st.text_input("Special Needs")
        uploaded_file = st.file_uploader("Upload Pet Photo (JPG/JPEG/PNG)", type=["jpg", "jpeg", "png"])
        if st.button("Add Pet"):
            data = {
                "species": species, "breed": breed, "gender": gender, "name": name,
                "activity_level": activity_level, "age": age, "allergy_friendly": allergy_friendly,
                "time_in_shelter": time_in_shelter, "disability_current": disability_current,
                "disability_past": disability_past, "special_needs": special_needs
            }
            add_pet(data, shelter["shelter_id"])
            if uploaded_file:
                upload_photo(data["pet_id"], uploaded_file)
            st.success("Pet added successfully!")

    # Edit pet (simplified)
    with st.expander("Edit Pet"):
        pet_id = st.selectbox("Select Pet", pets_df[pets_df["sheltername"] == shelter["name"]]["pet_id"])
        if pet_id:
            pet = pets_df[pets_df["pet_id"] == pet_id].iloc[0]
            breed = st.text_input("Breed", value=pet["breed"])
            age = st.number_input("Age", min_value=0, step=0.1, value=pet["age"])
            if st.button("Save Changes"):
                edit_pet(pet_id, {"breed": breed, "age": age})
                st.success("Pet updated successfully!")