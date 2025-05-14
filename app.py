import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import uuid
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "user_type" not in st.session_state:
    st.session_state.user_type = None

# Load credentials from secrets and initialize Google Sheets and Drive clients
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
        time.sleep(3)  # Delay to avoid rate limits
        sheets = {
            "pets": gc.open_by_key(st.secrets["gcp"]["sheets_pets_id"]).sheet1,
            "adopters": gc.open_by_key(st.secrets["gcp"]["sheets_adopters_id"]).sheet1,
            "shelters": gc.open_by_key(st.secrets["gcp"]["sheets_shelters_id"]).sheet1
        }
        
        # Fetch data with retry logic and detailed error handling
        max_retries = 3
        dataframes = {}
        for sheet_name in ["pets", "adopters", "shelters"]:
            for attempt in range(max_retries):
                try:
                    # Fetch raw data as a list of lists to inspect
                    raw_data = sheets[sheet_name].get_all_values()
                    if not raw_data:
                        raise ValueError(f"No data found in {sheet_name} sheet")
                    # Convert to DataFrame manually to handle encoding
                    headers = raw_data[0]
                    data = raw_data[1:]
                    df = pd.DataFrame(data, columns=headers)
                    dataframes[sheet_name] = df
                    logger.info(f"Successfully loaded {sheet_name} data with {len(df)} rows")
                    break
                except gspread.exceptions.APIError as api_err:
                    if api_err.response.get('error', {}).get('code') == 429:  # Rate limit
                        logger.warning(f"Rate limit hit for {sheet_name} on attempt {attempt + 1}, retrying...")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        if attempt == max_retries - 1:
                            raise api_err
                    else:
                        raise api_err
                except Exception as e:
                    logger.error(f"Failed to load {sheet_name} data on attempt {attempt + 1}: {str(e)}")
                    if attempt == max_retries - 1:
                        raise e
        
        pets_df = dataframes["pets"]
        adopters_df = dataframes["adopters"]
        shelters_df = dataframes["shelters"]
        
        # Validate column existence
        required_columns = {
            "pets": ["pet_id", "species", "breed", "gender", "name"],
            "adopters": ["adopter_id", "username", "password", "name"],
            "shelters": ["shelter_id", "username", "password", "name"]
        }
        for df_name, df in [("pets", pets_df), ("adopters", adopters_df), ("shelters", shelters_df)]:
            if df.empty or not all(col in df.columns for col in required_columns[df_name]):
                logger.error(f"{df_name.capitalize()} DataFrame is empty or missing columns: {required_columns[df_name]}")
                st.error(f"{df_name.capitalize()} data is missing or malformed. Please check the Google Sheet.")
                return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        logger.info("Data loaded successfully from Google Sheets")
        return pets_df, adopters_df, shelters_df
    except gspread.exceptions.APIError as api_err:
        logger.error(f"API Error loading data from Google Sheets: {api_err.response.get('error', {}).get('message', str(api_err))}")
        st.error(f"API Error loading data from Google Sheets: {api_err.response.get('error', {}).get('message', str(api_err))}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except gspread.exceptions.WorksheetNotFound as wnf_err:
        logger.error(f"Worksheet not found: {str(wnf_err)}")
        st.error(f"Worksheet not found in Google Sheet. Ensure the tab is named 'Sheet1': {str(wnf_err)}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error loading data from Google Sheets: {str(e)}")
        st.error(f"Unexpected error loading data from Google Sheets: {str(e)}")
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

# Get image URL from Google Drive
def get_image_url(file_id):
    return f"https://drive.google.com/uc?id={file_id}"

# Get drive image URL
def get_drive_image_url(image_path):
    try:
        if image_path and "drive.google.com" not in image_path:
            query = f"'{st.secrets['gcp']['drive_folder_id']}' in parents and name = '{image_path}'"
            results = drive_service.files().list(q=query, fields="files(id)").execute()
            files = results.get("files", [])
            return get_image_url(files[0]["id"]) if files else None
        return image_path
    except Exception as e:
        logger.error(f"Failed to get image URL from Google Drive: {e}")
        return None

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
    # Display image from Google Drive
    drive_url = get_drive_image_url("f1.jpg")
    if drive_url:
        st.image(drive_url, caption="Happy Pets", width=300)
    else:
        st.warning("Image f1.jpg not found in Google Drive. Ensure it is uploaded to the PetImages folder.")