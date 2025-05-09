import streamlit as st
import pandas as pd
import os

# Set page config first
st.set_page_config(page_title="Adopter Dashboard", layout="wide")

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
    pet = pets_df[pets_df["pet_id"] == pet_id].iloc[0]
    shelter = shelters_df[shelters_df["name"] == pet["sheltername"]].iloc[0]
    phone = shelter["phone"]
    formatted_phone = f"+{phone[:3]} {phone[3:]}"
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
    return f"{pets_df[pets_df['pet_id'] == pet_id].iloc[0]['name']} has been skipped."

# Delete adopter account
def delete_adopter_account(adopter_id):
    global adopters_df
    adopters_df = adopters_df[adopters_df["adopter_id"] != adopter_id]
    save_data()
    return "Adopter account deleted successfully"

# Adopter dashboard
st.sidebar.title("Dog Shelter Adoption Platform")

# Logout button styling
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

# Display image
if os.path.exists("pics/f2.jpg"):
    st множествоimage("pics/f2.jpg", caption="Loving Homes", width=300)
else:
    st.warning("Image f2.jpg not found. Please ensure it is in the pics/ directory.")

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
                    if pet.get("image_path") and os.path.exists(pet["image_path"]):
                        st.image(pet["image_path"], caption=pet["name"], width=300)
                    else:
                        st.write("No image available")
                with col2:
                    st.write(f"{pet['name']} ({pet['species']}, {pet['breed']}, {pet['gender']}, Age: {pet['age']})")
                    col_like, col_skip = st.columns(2)
                    with col_like:
                        if st.button(f"Like {pet['name']}", key=f"like_{pet['pet_id']}"):
                            message = like_pet(user["adopter_id"], pet["pet_id"])
                            st.session_state.show_contact_message = True
                            st.session_state.contact_message = message
                            st.session_state.recommendation_index += 1
                    with col_skip:
                        if st.button(f"Skip {pet['name']}", key=f"skip_{pet['pet_id']}"):
                            message = skip_pet(user["adopter_id"], pet["pet_id"])
                            st.session_state.recommendation_index += 1
                            st.info(message)
            else:
                st.success(st.session_state.contact_message)
                if st.button("Review other pets"):
                    st.session_state.show_contact_message = False

    elif option == "View Liked Pets":
        st.subheader("Liked Pets")
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
                            phone = shelter["phone"]
                            formatted_phone = f"+{phone[:3]} {phone[3:]}"
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                if pet.get("image_path") and os.path.exists(pet["image_path"]):
                                    st.image(pet["image_path"], caption=pet["name"], width=300)
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