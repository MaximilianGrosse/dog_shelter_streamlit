import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import uuid
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.user_type = None

# Load credentials from secrets and initialize Google Sheets client
try:
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Load the service account credentials directly from st.secrets
    credentials_info = st.secrets["gcp_service_account"]
    credentials = Credentials.from_service_account_info(credentials_info, scopes=scopes)
    gc = gspread.authorize(credentials)
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

# Register user
def register_user(user_type, data):
    global adopters_df, shelters_df
    data["username"] = data["username"].lower()
    if user_type == "Adopter":
        if data["username"] in adopters_df["username"].values:
            return False, "Username already exists"
        data["adopter_id"] = f"ADOP{uuid.uuid4().hex[:6].upper()}"
        data["liked_pets"] = ""
        data["skipped_pets"] = ""
        adopters_df = pd.concat([adopters_df, pd.DataFrame([data])], ignore_index=True)
    else:  # Shelter
        if data["username"] in shelters_df["username"].values:
            return False, "Username already exists"
        phone = data["phone"].replace("+", "").replace(" ", "")
        if not phone.isdigit() or len(phone) < 10:
            return False, "Phone number must be at least 10 digits and contain only numbers"
        data["phone"] = phone
        data["shelter_id"] = f"SHEL{uuid.uuid4().hex[:6].upper()}"
        shelters_df = pd.concat([shelters_df, pd.DataFrame([data])], ignore_index=True)
    save_data()
    return True, "Registration successful"

# Login user
def login_user(user_type, username, password):
    global adopters_df, shelters_df
    username = username.lower()
    if user_type == "Adopter":
        user = adopters_df[(adopters_df["username"] == username) & (adopters_df["password"] == password)]
        if not user.empty:
            return True, user.iloc[0]
    else:  # Shelter
        user = shelters_df[(shelters_df["username"] == username) & (shelters_df["password"] == password)]
        if not user.empty:
            return True, user.iloc[0]
    return False, "Invalid credentials"

# Sidebar navigation
st.sidebar.markdown("## Dog Shelter Adoption Platform")
st.sidebar.markdown("### Navigation")
st.page_link("app.py", label="Login/Registration")
st.page_link("pages/Adopter_Dashboard.py", label="Adopter Dashboard")
st.page_link("pages/Shelter_Dashboard.py", label="Shelter Dashboard")

# Main app
st.title("Dog Shelter Adoption Platform")
st.markdown("### Join Our Pet Adoption Community! 🐾")
st.markdown("Find your furry friend or help pets find loving homes with our platform! ❤️")

# Split layout: left for form, right for image
col1, col2 = st.columns([1, 1])

with col1:
    # If logged in, redirect to dashboard
    if st.session_state.user is not None:
        if st.session_state.user_type == "Adopter":
            st.switch_page("pages/Adopter_Dashboard.py")
        else:
            st.switch_page("pages/Shelter_Dashboard.py")
    else:
        # User type selection
        user_type = st.radio("User Type", ["Adopter", "Shelter"])

        # Tabs for Login/Register
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.subheader(f"{user_type} Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                success, result = login_user(user_type, username, password)
                if success:
                    st.session_state.user = result.to_dict()
                    st.session_state.user_type = user_type
                    save_data()
                    st.success("Login successful! Redirecting to dashboard...")
                    if user_type == "Adopter":
                        st.switch_page("pages/Adopter_Dashboard.py")
                    else:
                        st.switch_page("pages/Shelter_Dashboard.py")
                else:
                    st.error(result)

        with tab2:
            st.subheader(f"{user_type} Registration")
            fields = {
                "Adopter": ["name", "country", "age", "pref_species", "pref_gender", "house", "garden", "activity_level", "allergy_friendly", "apartment_size", "username", "password"],
                "Shelter": ["name", "address", "email", "phone", "username", "password"]
            }
            data = {}
            for field in fields[user_type]:
                if user_type == "Adopter":
                    if field == "pref_species":
                        species_list = list(pets_df["species"].unique()) if not pets_df.empty else ["Dog", "Cat", "Rabbit", "Turtle", "Hamster"]
                        data[field] = st.selectbox("Preferred Species", species_list, key=f"reg_{field}")
                    elif field == "age":
                        data[field] = st.selectbox("Age", list(range(18, 100)), key=f"reg_{field}")
                    elif field == "pref_gender":
                        data[field] = st.selectbox("Preferred Gender", ["Male", "Female"], key=f"reg_{field}")
                    elif field == "house":
                        data[field] = st.selectbox("House", ["Yes", "No"], key=f"reg_{field}")
                    elif field == "garden":
                        data[field] = st.selectbox("Garden", ["Yes", "No"], key=f"reg_{field}")
                    elif field == "allergy_friendly":
                        data[field] = st.selectbox("Allergy Friendly", ["Yes", "No"], key=f"reg_{field}")
                    elif field == "activity_level":
                        data[field] = st.selectbox("Activity Level", ["High", "Medium", "Low"], key=f"reg_{field}")
                    elif field == "apartment_size":
                        data[field] = st.number_input("Apartment Size in qm", min_value=0, step=1, key=f"reg_{field}")
                    else:
                        data[field] = st.text_input(field.capitalize(), key=f"reg_{field}")
                else:  # Shelter
                    if field == "phone":
                        data[field] = st.text_input("Phone (at least 10 digits, numbers only)", key=f"reg_{field}")
                    else:
                        data[field] = st.text_input(field.capitalize(), key=f"reg_{field}")
            if st.button("Register"):
                success, message = register_user(user_type, data)
                if success:
                    st.session_state.user = data
                    st.session_state.user_type = user_type
                    save_data()
                    st.success(message + " Redirecting to dashboard...")
                    if user_type == "Adopter":
                        st.switch_page("pages/Adopter_Dashboard.py")
                    else:
                        st.switch_page("pages/Shelter_Dashboard.py")
                else:
                    st.error(message)

with col2:
    # Display image (replace with your actual f1.jpg file ID from Google Drive)
    f1_file_id = "your-f1-jpg-file-id"  # Replace with actual file ID
    st.image(f"https://drive.google.com/uc?id={f1_file_id}", caption="Happy Pets", width=300)