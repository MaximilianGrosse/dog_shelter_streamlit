import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import uuid
from googleapiclient.http import MediaIoBaseUpload
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load credentials and initialize Google Sheets and Drive clients
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials_info = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    gc = gspread.authorize(credentials)
    drive_service = build("drive", "v3", credentials=credentials)
except Exception as e:
    logger.error(f"Failed to load credentials: {e}")
    st.error(f"Error loading Google API credentials: {e}")
    st.stop()

# Load data from Google Sheets
def load_data():
    try:
        pets_df = pd.DataFrame(gc.open_by_key(st.secrets["gcp"]["sheets_pets_id"]).sheet1.get_all_records())
        adopters_df = pd.DataFrame(gc.open_by_key(st.secrets["gcp"]["sheets_adopters_id"]).sheet1.get_all_records())
        shelters_df = pd.DataFrame(gc.open_by_key(st.secrets["gcp"]["sheets_shelters_id"]).sheet1.get_all_records())
        return pets_df, adopters_df, shelters_df
    except Exception as e:
        logger.error(f"Failed to load data from Google Sheets: {e}")
        st.error(f"Error loading data from Google Sheets: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

pets_df, adopters_df, shelters_df = load_data()

# Save data to Google Sheets
def save_data():
    global pets_df, adopters_df, shelters_df
    try:
        gc.open_by_key(st.secrets["gcp"]["sheets_pets_id"]).sheet1.update([pets_df.columns.values.tolist()] + pets_df.values.tolist())
        gc.open_by_key(st.secrets["gcp"]["sheets_adopters_id"]).sheet1.update([adopters_df.columns.values.tolist()] + adopters_df.values.tolist())
        gc.open_by_key(st.secrets["gcp"]["sheets_shelters_id"]).sheet1.update([shelters_df.columns.values.tolist()] + shelters_df.values.tolist())
        # Reload data to reflect changes
        pets_df, adopters_df, shelters_df = load_data()
    except Exception as e:
        logger.error(f"Failed to save data to Google Sheets: {e}")
        st.error(f"Error saving data to Google Sheets: {e}")

# Get image URL from Google Drive
def get_image_url(file_id):
    return f"https://drive.google.com/uc?id={file_id}"

# Upload photo to Google Drive
def upload_photo(pet_id, file):
    try:
        if file is not None:
            file_metadata = {"name": f"{pet_id}.jpg", "parents": [st.secrets["gcp"]["drive_folder_id"]]}
            media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype="image/jpeg")
            file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
            return file.get("id")
        return None
    except Exception as e:
        logger.error(f"Failed to upload photo to Google Drive: {e}")
        st.error(f"Error uploading photo to Google Drive: {e}")
        return None

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
    pets_df.loc[pet_idx, data.keys()] = data.values()
    save_data()

# Sidebar navigation
st.sidebar.markdown("## Dog Shelter Adoption Platform")
st.sidebar.markdown("### Navigation")
st.page_link("app.py", label="Login/Registration")
st.page_link("pages/Adopter_Dashboard.py", label="Adopter Dashboard")
st.page_link("pages/Shelter_Dashboard.py", label="Shelter Dashboard")

# Main content
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
        age = st.number_input("Age", min_value=0.0, step=0.1)
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
                file_id = upload_photo(data["pet_id"], uploaded_file)
                if file_id:
                    pet_idx = pets_df.index[pets_df["pet_id"] == data["pet_id"]].tolist()[0]
                    pets_df.at[pet_idx, "image_path"] = f"{data['pet_id']}.jpg"
                    save_data()
            st.success("Pet added successfully!")

    # Edit pet
    with st.expander("Edit Pet"):
        pet_id = st.selectbox("Select Pet", pets_df[pets_df["sheltername"] == shelter["name"]]["pet_id"])
        if pet_id:
            pet = pets_df[pets_df["pet_id"] == pet_id].iloc[0]
            breed = st.text_input("Breed", value=pet["breed"])
            age = st.number_input("Age", min_value=0.0, step=0.1, value=float(pet["age"]))
            if st.button("Save Changes"):
                edit_pet(pet_id, {"breed": breed, "age": age})
                st.success("Pet updated successfully!")