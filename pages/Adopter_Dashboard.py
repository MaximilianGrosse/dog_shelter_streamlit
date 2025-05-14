import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import logging
import time


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if "user" not in st.session_state:
    st.session_state.user = None
if "user_type" not in st.session_state:
    st.session_state.user_type = None

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
        time.sleep(3)  # Increase delay to 3 seconds to avoid rate limits
        sheets = {
            "pets": gc.open_by_key(st.secrets["gcp"]["sheets_pets_id"]).sheet1,
            "adopters": gc.open_by_key(st.secrets["gcp"]["sheets_adopters_id"]).sheet1,
            "shelters": gc.open_by_key(st.secrets["gcp"]["sheets_shelters_id"]).sheet1
        }
        
        # Fetch data with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                pets_df = pd.DataFrame(sheets["pets"].get_all_records())
                adopters_df = pd.DataFrame(sheets["adopters"].get_all_records())
                shelters_df = pd.DataFrame(sheets["shelters"].get_all_records())
                break  # Success, exit retry loop
            except gspread.exceptions.APIError as api_err:
                if api_err.response.get('error', {}).get('code') == 429:  # Rate limit
                    logger.warning(f"Rate limit hit on attempt {attempt + 1}, retrying...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                    if attempt == max_retries - 1:
                        raise api_err
                else:
                    raise api_err
        
        # Validate column existence (reverted header logging as requested)
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

# Get image URL from Google Drive
def get_image_url(file_id):
    return f"https://drive.google.com/uc?id={file_id}"

# Get image URL by searching for the file name in the Drive folder (for user-uploaded pet photos)
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

# Matching function
def calculate_match(adopter, pet):
    score = 0
    if adopter["pref_species"] == pet["species"]:
        score += 0.3
    if adopter["pref_gender"] in [pet["gender"], "Any"]:
        score += 0.1
    activity_levels = {"High": 3, "Medium": 2, "Low": 1}
    if activity_levels.get(adopter["activity_level"], 0) >= activity_levels.get(pet["activity_level"], 0):
        score += 0.2
    if adopter["allergy_friendly"] == "Yes" and pet["allergy_friendly"] == "Yes":
        score += 0.2
    space_suitable = False
    apartment_size = float(adopter["apartment_size"]) if adopter["apartment_size"] and str(adopter["apartment_size"]).strip() else 0
    if pet["activity_level"] == "Low" or (adopter["house"] == "Yes" or adopter["garden"] == "Yes") or apartment_size >= 50:
        space_suitable = True
    if space_suitable and not pet["special_needs"]:
        score += 0.2
    return score

# Get recommendations
def get_recommendations(adopter_id):
    global adopters_df, pets_df
    adopter = adopters_df[adopters_df["adopter_id"] == adopter_id].iloc[0]
    liked_pets = []
    skipped_pets = []
    if isinstance(adopter.get("liked_pets"), str) and adopter["liked_pets"].strip():
        liked_pets = adopter["liked_pets"].split(",")
    if isinstance(adopter.get("skipped_pets"), str) and adopter["skipped_pets"].strip():
        skipped_pets = adopter["skipped_pets"].split(",")
    excluded_pets = liked_pets + skipped_pets
    scores = []
    for _, pet in pets_df.iterrows():
        if pet["pet_id"] not in excluded_pets:
            score = calculate_match(adopter, pet)
            scores.append((pet["pet_id"], score))
    scores.sort(key=lambda x: x[1], reverse=True)
    top_pets = [pets_df[pets_df["pet_id"] == pet_id].iloc[0] for pet_id, _ in scores[:5]]
    return top_pets

# Like a pet
def like_pet(adopter_id, pet_id):
    global adopters_df
    adopter_idx = adopters_df.index[adopters_df["adopter_id"] == adopter_id].tolist()[0]
    current_likes = adopters_df.at[adopter_idx, "liked_pets"]
    likes_list = []
    if isinstance(current_likes, str) and current_likes.strip():
        likes_list = current_likes.split(",")
    if pet_id not in likes_list:
        likes_list.append(pet_id)
        adopters_df.at[adopter_idx, "liked_pets"] = ",".join(likes_list)
    save_data()
    # Update session state user
    st.session_state.user = adopters_df.iloc[adopter_idx].to_dict()
    pet = pets_df[pets_df["pet_id"] == pet_id].iloc[0]
    shelter = shelters_df[shelters_df["name"] == pet["sheltername"]].iloc[0]
    phone = str(shelter["phone"]).strip() if shelter["phone"] and str(shelter["phone"]).strip() else "Not provided"
    if phone and phone != "Not provided" and len(phone) >= 3 and phone.isdigit():
        formatted_phone = f"+{phone[:3]} {phone[3:]}"
    else:
        formatted_phone = phone
    return f"{pet['name']} was liked by you. The contact information of the shelter located in {shelter['address']} is phone number {formatted_phone} and email {shelter['email']}. Please don't hesitate to contact them!"

# Skip a pet
def skip_pet(adopter_id, pet_id):
    global adopters_df
    adopter_idx = adopters_df.index[adopters_df["adopter_id"] == adopter_id].tolist()[0]
    current_skips = adopters_df.at[adopter_idx, "skipped_pets"]
    skips_list = []
    if isinstance(current_skips, str) and current_skips.strip():
        skips_list = current_skips.split(",")
    if pet_id not in skips_list:
        skips_list.append(pet_id)
        adopters_df.at[adopter_idx, "skipped_pets"] = ",".join(skips_list)
    save_data()
    # Update session state user
    st.session_state.user = adopters_df.iloc[adopter_idx].to_dict()
    return f"{pets_df[pets_df['pet_id'] == pet_id].iloc[0]['name']} has been skipped."

# Delete adopter account
def delete_adopter_account(adopter_id):
    global adopters_df
    adopters_df = adopters_df[adopters_df["adopter_id"] != adopter_id]
    save_data()
    return "Adopter account deleted successfully"

# Sidebar navigation
st.sidebar.markdown("## Dog Shelter Adoption Platform")
st.sidebar.markdown("### Navigation")
st.page_link("app.py", label="Login/Registration")
st.page_link("pages/Adopter_Dashboard.py", label="Adopter Dashboard")
st.page_link("pages/Shelter_Dashboard.py", label="Shelter Dashboard")

# Styling
st.markdown("""
    <style>
    .logout-button {
        background-color: red;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 4px;
        vertical-align: middle;
    }
    .pet-description {
        margin-left: 20px;
    }
    .button-container {
        margin-top: 10px;
        margin-left: 20px;
    }
    .image-column {
        margin-right: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Header with title and logout button
col1, col2 = st.columns([4, 1])
with col1:
    st.title("Adopter Dashboard")
with col2:
    if st.button("Logout", key="logout_button"):
        st.session_state.user = None
        st.session_state.user_type = None
        st.switch_page("app.py")

st.markdown("### Join Our Pet Adoption Community! 🐾")
st.markdown("Find your furry friend or help pets find loving homes with our platform! ❤️")

# Display image from pics folder
st.image("pics/f2.jpg", caption="Loving Homes", width=300)

if st.session_state.user is None or st.session_state.user_type != "Adopter":
    st.error("Please log in as an Adopter.")
    st.markdown("[Go to Login/Registration](./)")
else:
    user = st.session_state.user
    st.subheader(f"Welcome, {user['name']}")

    # Initialize session state for recommendation index
    if "recommendation_index" not in st.session_state:
        st.session_state.recommendation_index = 0
    if "show_contact_message" not in st.session_state:
        st.session_state.show_contact_message = False
    if "contact_message" not in st.session_state:
        st.session_state.contact_message = ""

    # Menu
    option = st.selectbox("Choose an action", ["View Recommended Pets", "View Liked Pets", "Delete Account"])

    if option == "View Recommended Pets":
        st.subheader("Recommended Pets")
        pets_df, adopters_df, shelters_df = load_data()
        recommendations = get_recommendations(user["adopter_id"])
        
        if not recommendations:
            st.info("No more pets to recommend.")
        elif st.session_state.recommendation_index >= len(recommendations):
            st.info("No more pets to recommend.")
        else:
            if not st.session_state.show_contact_message:
                pet = recommendations[st.session_state.recommendation_index]
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.markdown("<div class='image-column'>", unsafe_allow_html=True)
                    image_path = pet.get("image_path", "")
                    if image_path:
                        drive_url = get_drive_image_url("f2.jpg")
                        if drive_url:
                            st.image(drive_url, caption="Loving Homes", width=300)
                        else:
                            st.warning("Image f2.jpg not found in Google Drive. Ensure it is uploaded to the PetImages folder.")
                    else:
                        st.write("No image available")
                    st.markdown(f"<div class='pet-description'>{pet['name']} ({pet['species']}, {pet['breed']}, {pet['gender']}, Age: {pet['age']})</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                with col2:
                    with st.container():
                        st.markdown("<div class='button-container'>", unsafe_allow_html=True)
                        col_like, col_skip = st.columns(2)
                        with col_like:
                            if st.button(f"Like {pet['name']}", key=f"like_{pet['pet_id']}"):
                                message = like_pet(user["adopter_id"], pet["pet_id"])
                                st.session_state.show_contact_message = True
                                st.session_state.contact_message = message
                                st.session_state.recommendation_index += 1
                                st.rerun()
                        with col_skip:
                            if st.button(f"Skip {pet['name']}", key=f"skip_{pet['pet_id']}"):
                                message = skip_pet(user["adopter_id"], pet["pet_id"])
                                st.session_state.recommendation_index += 1
                                st.info(message)
                                st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.success(st.session_state.contact_message)
                if st.button("Review other pets"):
                    st.session_state.show_contact_message = False
                    st.rerun()

    elif option == "View Liked Pets":
        st.subheader("Liked Pets")
        pets_df, adopters_df, shelters_df = load_data()
        # Refresh user from adopters_df to ensure latest data
        user = adopters_df[adopters_df["adopter_id"] == user["adopter_id"]].iloc[0]
        st.session_state.user = user.to_dict()
        liked_pets = []
        if isinstance(user.get("liked_pets"), str) and user["liked_pets"].strip():
            liked_pets = user["liked_pets"].split(",")
        if not liked_pets or liked_pets == [""]:
            st.info("No liked pets yet.")
        else:
            for pet_id in liked_pets:
                if pet_id:
                    pet_data = pets_df[pets_df["pet_id"] == pet_id]
                    if not pet_data.empty:
                        pet = pet_data.iloc[0]
                        shelter_data = shelters_df[shelters_df["name"] == pet["sheltername"]]
                        if not shelter_data.empty:
                            shelter = shelter_data.iloc[0]
                            phone = str(shelter["phone"]).strip() if shelter["phone"] and str(shelter["phone"]).strip() else "Not provided"
                            if phone and phone != "Not provided" and len(phone) >= 3 and phone.isdigit():
                                formatted_phone = f"+{phone[:3]} {phone[3:]}"
                            else:
                                formatted_phone = phone
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                image_path = pet.get("image_path", "")
                                if image_path:
                                    drive_url = get_drive_image_url(image_path)
                                    if drive_url:
                                        st.image(drive_url, caption=pet["name"], width=300)
                                    else:
                                        st.write("No image available")
                                else:
                                    st.write("No image available")
                            with col2:
                                st.write(f"**{pet['name']}** ({pet['species']}, {pet['breed']}, {pet['gender']}, Age: {pet['age']})")
                                st.write(f"**Shelter**: {shelter['name']}")
                                st.write(f"**Address**: {shelter['address']}")
                                st.write(f"**Phone**: {formatted_phone}")
                                st.write(f"**Email**: {shelter['email']}")
                    else:
                        st.warning(f"Pet with ID {pet_id} no longer available.")
                else:
                    st.warning("Invalid pet ID in liked pets.")

    elif option == "Delete Account":
        st.subheader("Delete Account")
        if st.button("Confirm Deletion"):
            message = delete_adopter_account(user["adopter_id"])
            st.success(message)
            st.session_state.user = None
            st.session_state.user_type = None
            st.switch_page("app.py")