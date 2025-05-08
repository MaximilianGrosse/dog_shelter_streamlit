import streamlit as st
import pandas as pd
import os

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
    apartment_size = float(adopter["apartment_size"]) if adopter["apartment_size"] and adopter["apartment_size"].strip() else 0
    if pet["activity_level"] == "Low" or (adopter["house"] == "Yes" or adopter["garden"] == "Yes") or apartment_size >= 50:
        space_suitable = True
    if space_suitable and not pet["special_needs"]:
        score += 0.2
    return score

# Get recommendations
def get_recommendations(adopter_id):
    global adopters_df, pets_df
    adopter = adopters_df[adopters_df["adopter_id"] == adopter_id].iloc[0]
    scores = []
    for _, pet in pets_df.iterrows():
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
    if current_likes:
        likes_list = current_likes.split(",")
        if pet_id not in likes_list:
            likes_list.append(pet_id)
            adopters_df.at[adopter_idx, "liked_pets"] = ",".join(likes_list)
    else:
        adopters_df.at[adopter_idx, "liked_pets"] = pet_id
    save_data()
    pet = pets_df[pets_df["pet_id"] == pet_id].iloc[0]
    shelter = shelters_df[shelters_df["name"] == pet["sheltername"]].iloc[0]
    return f"Shelter Contact:\nName: {shelter['name']}\nEmail: {shelter['email']}\nPhone: {shelter['phone']}"

# Delete adopter account
def delete_adopter_account(adopter_id):
    global adopters_df
    adopters_df = adopters_df[adopters_df["adopter_id"] != adopter_id]
    save_data()
    return "Adopter account deleted successfully"

# Adopter dashboard
st.title("Adopter Dashboard")
if st.session_state.user is None or st.session_state.user_type != "Adopter":
    st.error("Please log in as an Adopter.")
    st.markdown("[Go to Login](./)")
else:
    user = st.session_state.user
    st.subheader(f"Welcome, {user['name']}")

    # Menu
    option = st.selectbox("Choose an action", ["View Recommended Pets", "View Liked Pets", "Delete Account"])

    if option == "View Recommended Pets":
        st.subheader("Recommended Pets")
        recommendations = get_recommendations(user["adopter_id"])
        for pet in recommendations:
            st.write(f"{pet['name']} ({pet['species']}, {pet['breed']}, {pet['gender']}, Age: {pet['age']})")
            if st.button(f"Like {pet['name']}", key=pet["pet_id"]):
                st.success(like_pet(user["adopter_id"], pet["pet_id"]))

    elif option == "View Liked Pets":
        st.subheader("Liked Pets")
        liked_pets = user["liked_pets"].split(",") if user["liked_pets"] else []
        if not liked_pets or liked_pets == [""]:
            st.write("No liked pets yet.")
        else:
            for pet_id in liked_pets:
                if pet_id:
                    pet = pets_df[pets_df["pet_id"] == pet_id].iloc[0]
                    st.write(f"{pet['name']} ({pet['species']}, {pet['breed']})")

    elif option == "Delete Account":
        st.subheader("Delete Account")
        if st.button("Confirm Deletion"):
            message = delete_adopter_account(user["adopter_id"])
            st.success(message)
            st.session_state.user = None
            st.session_state.user_type = None
            st.rerun()

    if st.button("Logout"):
        st.session_state.user = None
        st.session_state.user_type = None
        st.rerun()