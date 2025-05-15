import streamlit as st
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize session state
if "user_data" not in st.session_state:
    st.session_state.user_data = None
if "recommendation_index" not in st.session_state:
    st.session_state.recommendation_index = 0
if "recommended_pets" not in st.session_state:
    st.session_state.recommended_pets = []
if "skipped_pets" not in st.session_state:
    st.session_state.skipped_pets = []

# GitHub repository details (replace 'yourusername' with your actual GitHub username)
GITHUB_USERNAME = "yourusername"  # Replace with your GitHub username
REPO_NAME = "dog_shelter_streamlit"
BRANCH = "main"
CSV_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/{BRANCH}/pets.csv"
IMAGE_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{REPO_NAME}/{BRANCH}/"

# Load pet data from GitHub
def load_pets():
    try:
        pets_df = pd.read_csv(CSV_URL)
        required_columns = ["pet_id", "species", "breed", "gender", "name", "activity_level", "age", "allergy_friendly"]
        if pets_df.empty or not all(col in pets_df.columns for col in required_columns):
            logger.error("Pets DataFrame is empty or missing required columns")
            st.error("Pet data is missing or malformed. Please check the pets.csv file on GitHub.")
            return pd.DataFrame()
        logger.info(f"Successfully loaded pets data with {len(pets_df)} rows")
        return pets_df
    except Exception as e:
        logger.error(f"Failed to load pets data from GitHub: {str(e)}")
        st.error(f"Error loading pet data from GitHub: {str(e)}")
        return pd.DataFrame()

pets_df = load_pets()

# Calculate match score between user and pet
def calculate_match(user_data, pet):
    score = 0
    if user_data["pref_species"] == pet["species"]:
        score += 0.3
    if user_data["pref_gender"] in [pet["gender"], "Any"]:
        score += 0.1
    activity_levels = {"High": 3, "Medium": 2, "Low": 1}
    if activity_levels.get(user_data["activity_level"], 0) >= activity_levels.get(pet["activity_level"], 0):
        score += 0.2
    if user_data["allergy_friendly"] == "Yes" and pet["allergy_friendly"] == "Yes":
        score += 0.2
    space_suitable = False
    apartment_size = float(user_data["apartment_size"]) if user_data["apartment_size"] and str(user_data["apartment_size"]).strip() else 0
    if pet["activity_level"] == "Low" or (user_data["house"] == "Yes" or user_data["garden"] == "Yes") or apartment_size >= 50:
        space_suitable = True
    if space_suitable and not pet.get("special_needs", ""):
        score += 0.2
    return score

# Get pet recommendations
def get_recommendations(user_data):
    scores = []
    skipped_pets = st.session_state.skipped_pets
    for _, pet in pets_df.iterrows():
        if pet["pet_id"] not in skipped_pets:
            score = calculate_match(user_data, pet)
            scores.append((pet["pet_id"], score))
    scores.sort(key=lambda x: x[1], reverse=True)
    recommended_pets = [pets_df[pets_df["pet_id"] == pet_id].iloc[0] for pet_id, _ in scores]
    return recommended_pets

# Main app
st.title("🐾 Dog Shelter Adoption Platform")
st.markdown("""
### Welcome to Our Pet Adoption Community!
Our mission is to connect loving homes with adorable pets in need. By sharing a bit about yourself, you can help us find the perfect furry friend for you! Together, we can make a difference—one happy pet at a time. ❤️
""")

# User input form
if st.session_state.user_data is None:
    st.subheader("Tell Us About Yourself")
    with st.form(key="user_form"):
        name = st.text_input("Name")
        country = st.text_input("Country")
        age = st.selectbox("Age", list(range(18, 100)))
        pref_species = st.selectbox("Preferred Species", pets_df["species"].unique() if not pets_df.empty else ["Dog", "Cat", "Rabbit", "Turtle", "Hamster"])
        pref_gender = st.selectbox("Preferred Gender", ["Male", "Female", "Any"])
        house = st.selectbox("Do you live in a house?", ["Yes", "No"])
        garden = st.selectbox("Do you have a garden?", ["Yes", "No"])
        activity_level = st.selectbox("Activity Level", ["High", "Medium", "Low"])
        allergy_friendly = st.selectbox("Need an allergy-friendly pet?", ["Yes", "No"])
        apartment_size = st.number_input("Apartment Size (in sqm)", min_value=0, step=1)
        submit_button = st.form_submit_button(label="Find My Pet!")

        if submit_button:
            if not name or not country:
                st.error("Please fill in all required fields (Name and Country).")
            else:
                st.session_state.user_data = {
                    "name": name,
                    "country": country,
                    "age": age,
                    "pref_species": pref_species,
                    "pref_gender": pref_gender,
                    "house": house,
                    "garden": garden,
                    "activity_level": activity_level,
                    "allergy_friendly": allergy_friendly,
                    "apartment_size": apartment_size
                }
                st.session_state.recommended_pets = get_recommendations(st.session_state.user_data)
                st.session_state.recommendation_index = 0
                st.session_state.skipped_pets = []
                st.rerun()

# Display recommendations
if st.session_state.user_data is not None:
    st.subheader(f"Recommended Pets for {st.session_state.user_data['name']}")
    
    if not pets_df.empty:
        recommendations = st.session_state.recommended_pets
        if st.session_state.recommendation_index >= len(recommendations):
            st.info("Thank you for visiting! We've run out of pets to recommend. Please check back later for new pets in need of a loving home. 🐶🐱")
        else:
            pet = recommendations[st.session_state.recommendation_index]
            col1, col2 = st.columns([1, 3])
            with col1:
                image_path = pet.get("image_path", "")
                if image_path:
                    image_url = f"{IMAGE_BASE_URL}{image_path}"
                    st.image(image_url, caption=pet["name"], width=300)
                else:
                    st.write("No image available")
            with col2:
                st.markdown(f"**{pet['name']}** ({pet['species']}, {pet['breed']}, {pet['gender']}, Age: {pet['age']})")
                st.write(f"**Shelter**: {pet['sheltername']}")
                st.write(f"**Activity Level**: {pet['activity_level']}")
                st.write(f"**Allergy Friendly**: {pet['allergy_friendly']}")
                st.write(f"**Time in Shelter**: {pet.get('time_in_shelter', 'N/A')}")
                st.write(f"**Current Disability**: {pet.get('disability_current', 'None')}")
                st.write(f"**Past Disability**: {pet.get('disability_past', 'None')}")
                st.write(f"**Special Needs**: {pet.get('special_needs', 'None')}")
                col_like, col_skip = st.columns(2)
                with col_like:
                    if st.button(f"Choose {pet['name']}", key=f"choose_{pet['pet_id']}"):
                        st.success(f"Congratulations! You've chosen {pet['name']} as your new furry friend! 🥳 Please contact {pet['sheltername']} to proceed with the adoption.")
                        st.stop()
                with col_skip:
                    if st.button(f"Skip {pet['name']}", key=f"skip_{pet['pet_id']}"):
                        st.session_state.skipped_pets.append(pet["pet_id"])
                        st.session_state.recommendation_index += 1
                        st.rerun()
    else:
        st.info("Thank you for visiting! We currently have no pets to recommend. Please check back later for new pets in need of a loving home. 🐶🐱")