import streamlit as st
import pandas as pd
import uuid
import os
from PIL import Image

# Set page config first
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

# Breed lists
BREEDS = {
    "Dog": ["Labrador", "Golden Retriever", "German Wyrd", "Beagle", "Bulldog", "Poodle", "Husky", "Chihuahua", "Dachshund", "Boxer", "Rottweiler", "Shih Tzu", "Doberman", "Corgi", "Great Dane"],
    "Cat": ["Siamese", "Persian", "Maine Coon", "Tabby", "Bengal", "Ragdoll", "Abyssinian", "Sphynx", "British Shorthair", "Scottish Fold", "Burmese", "Oriental", "Norwegian Forest", "Devon Rex", "Manx"],
    "Rabbit": ["Lop", "Netherland Dwarf", "Lionhead", "Angora", "Flemish Giant", "Rex", "Mini Lop", "Dutch", "Himalayan", "Chinchilla"],
    "Turtle": ["Red-Eared Slider", "Box Turtle", "Hermann’s", "Russian", "Slider", "Painted Turtle", "Map Turtle", "Musk Turtle"],
    "Hamster": ["Syrian", "Roborovski", "Dwarf", "Golden", "Campbell’s", "Chinese", "Winter White"]
}

# Add pet
def add_pet(shelter_id, pet_data, image_file=None):
    global pets_df
    pet_data["pet_id"] = f"PET{uuid.uuid4().hex[:6].upper()}"
    shelter = shelters_df[shelters_df["shelter_id"] == shelter_id].iloc[0]
    pet_data["sheltername"] = shelter["name"]
    if image_file:
        image_path = f"pet_pics/{pet_data['pet_id']}.jpg"
        os.makedirs("pet_pics", exist_ok=True)
        # Convert and save as JPG
        img = Image.open(image_file)
        img.convert("RGB").save(image_path, "JPEG")
        pet_data["image_path"] = image_path
    else:
        pet_data["image_path"] = ""
    pets_df = pd.concat([pets_df, pd.DataFrame([pet_data])], ignore_index=True)
    save_data()
    return "Pet added successfully"

# Edit pet
def edit_pet(pet_id, pet_data, image_file=None):
    global pets_df
    pet_idx = pets_df.index[pets_df["pet_id"] == pet_id].tolist()[0]
    if image_file:
        image_path = f"pet_pics/{pet_id}.jpg"
        os.makedirs("pet_pics", exist_ok=True)
        # Convert and save as JPG
        img = Image.open(image_file)
        img.convert("RGB").save(image_path, "JPEG")
        pet_data["image_path"] = image_path
    elif "image_path" not in pet_data:
        pet_data["image_path"] = pets_df.at[pet_idx, "image_path"]
    for key, value in pet_data.items():
        pets_df.at[pet_idx, key] = value
    save_data()
    return "Pet updated successfully"

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
    st.title("Shelter Dashboard")
with col2:
    if st.button("Logout", key="logout_button"):
        st.session_state.user = None
        st.session_state.user_type = None
        st.switch_page("app.py")

st.markdown("### Join Our Pet Adoption Community! 🐾")
st.markdown("Find your furry friend or help pets find loving homes with our platform! ❤️")

# Display image
if os.path.exists("pics/f3.jpg"):
    st.image("pics/f3.jpg", caption="Shelter Heroes", width=300)
else:
    st.warning("Image f3.jpg not found. Please ensure it is in the pics/ directory.")

if st.session_state.user is None or st.session_state.user_type != "Shelter":
    st.error("Please log in as a Shelter.")
    st.markdown("[Go to Login/Registration](./)")
else:
    user = st.session_state.user
    st.subheader(f"Welcome, {user['name']}")

    # Menu
    option = st.selectbox("Choose an action", ["Add New Pet", "View My Pets", "Edit Pet", "Delete Account"])

    if option == "Add New Pet":
        st.subheader("Add New Pet")
        pet_data = {}
        default_species = ["Dog", "Cat", "Rabbit", "Turtle", "Hamster"]
        use_custom_species = st.checkbox("Add custom species", key="custom_species")
        if use_custom_species:
            pet_data["species"] = st.text_input("Custom Species", key="pet_species")
        else:
            pet_data["species"] = st.selectbox("Species", default_species, key="pet_species")
        
        # Breed search and selection
        if pet_data["species"] in BREEDS:
            breed_search = st.text_input("Search Breed", key="breed_search")
            breed_options = [b for b in BREEDS[pet_data["species"]] if breed_search.lower() in b.lower()] or BREEDS[pet_data["species"]]
            pet_data["breed"] = st.selectbox("Breed", breed_options, key="pet_breed")
        else:
            pet_data["breed"] = st.text_input("Breed", key="pet_breed")
        
        pet_data["gender"] = st.selectbox("Gender", ["Male", "Female"], key="pet_gender")
        pet_data["name"] = st.text_input("Name", key="pet_name")
        pet_data["activity_level"] = st.selectbox("Activity Level", ["High", "Medium", "Low"], key="pet_activity_level")
        age_options = list(range(0, 15)) + ["15+"]
        pet_data["age"] = st.selectbox("Age", age_options, key="pet_age")
        pet_data["allergy_friendly"] = st.selectbox("Allergy Friendly", ["Yes", "No"], key="pet_allergy_friendly")
        pet_data["time_in_shelter"] = st.selectbox("Time in Shelter", ["< 1 year", "1-2 years", "2+ years"], key="pet_time_in_shelter")
        pet_data["disability_current"] = st.text_input("Disability Current", key="pet_disability_current")
        pet_data["disability_past"] = st.text_input("Disability Past", key="pet_disability_past")
        pet_data["special_needs"] = st.text_input("Special Needs", key="pet_special_needs")
        
        image_file = st.file_uploader("Upload Pet Image (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"], key="pet_image")
        
        if st.button("Add Pet"):
            message = add_pet(user["shelter_id"], pet_data, image_file)
            st.success(message)

    elif option == "View My Pets":
        st.subheader("My Pets")
        shelter_pets = pets_df[pets_df["sheltername"] == user["name"]]
        if shelter_pets.empty:
            st.write("No pets added yet.")
        else:
            for _, pet in shelter_pets.iterrows():
                col1, col2 = st.columns([1, 3])
                with col1:
                    if pet.get("image_path") and os.path.exists(pet["image_path"]):
                        st.image(pet["image_path"], caption=pet["name"], width=300)
                    else:
                        st.write("No image available")
                with col2:
                    st.write(f"{pet['name']} ({pet['species']}, {pet['breed']})")

    elif option == "Edit Pet":
        st.subheader("Edit Pet")
        shelter_pets = pets_df[pets_df["sheltername"] == user["name"]]
        if shelter_pets.empty:
            st.write("No pets available to edit.")
        else:
            pet_options = [f"{pet['name']} ({pet['species']}, {pet['breed']})" for _, pet in shelter_pets.iterrows()]
            selected_pet = st.selectbox("Select Pet to Edit", pet_options, key="edit_pet_select")
            pet_id = shelter_pets.iloc[pet_options.index(selected_pet)]["pet_id"]
            pet = shelter_pets[shelter_pets["pet_id"] == pet_id].iloc[0]
            
            pet_data = {}
            default_species = ["Dog", "Cat", "Rabbit", "Turtle", "Hamster"]
            use_custom_species = st.checkbox("Add custom species", key="edit_custom_species")
            if use_custom_species:
                pet_data["species"] = st.text_input("Custom Species", value=pet["species"], key="edit_pet_species")
            else:
                species_options = default_species + [pet["species"]] if pet["species"] not in default_species else default_species
                pet_data["species"] = st.selectbox("Species", species_options, index=species_options.index(pet["species"]), key="edit_pet_species")
            
            if pet_data["species"] in BREEDS:
                breed_search = st.text_input("Search Breed", key="edit_breed_search")
                breed_options = [b for b in BREEDS[pet_data["species"]] if breed_search.lower() in b.lower()] or BREEDS[pet_data["species"]]
                pet_data["breed"] = st.selectbox("Breed", breed_options, index=breed_options.index(pet["breed"]) if pet["breed"] in breed_options else 0, key="edit_pet_breed")
            else:
                pet_data["breed"] = st.text_input("Breed", value=pet["breed"], key="edit_pet_breed")
            
            pet_data["gender"] = st.selectbox("Gender", ["Male", "Female"], index=["Male", "Female"].index(pet["gender"]), key="edit_pet_gender")
            pet_data["name"] = st.text_input("Name", value=pet["name"], key="edit_pet_name")
            pet_data["activity_level"] = st.selectbox("Activity Level", ["High", "Medium", "Low"], index=["High", "Medium", "Low"].index(pet["activity_level"]), key="edit_pet_activity_level")
            age_options = list(range(0, 15)) + ["15+"]
            pet_data["age"] = st.selectbox("Age", age_options, index=age_options.index(pet["age"]) if pet["age"] in age_options else len(age_options)-1, key="edit_pet_age")
            pet_data["allergy_friendly"] = st.selectbox("Allergy Friendly", ["Yes", "No"], index=["Yes", "No"].index(pet["allergy_friendly"]), key="edit_pet_allergy_friendly")
            pet_data["time_in_shelter"] = st.selectbox("Time in Shelter", ["< 1 year", "1-2 years", "2+ years"], index=["< 1 year", "1-2 years", "2+ years"].index(pet["time_in_shelter"]), key="edit_pet_time_in_shelter")
            pet_data["disability_current"] = st.text_input("Disability Current", value=pet["disability_current"], key="edit_pet_disability_current")
            pet_data["disability_past"] = st.text_input("Disability Past", value=pet["disability_past"], key="edit_pet_disability_past")
            pet_data["special_needs"] = st.text_input("Special Needs", value=pet["special_needs"], key="edit_pet_special_needs")
            
            image_file = st.file_uploader("Upload New Pet Image (JPG, JPEG, PNG)", type=["jpg", "jpeg", "png"], key="edit_pet_image")
            
            if st.button("Update Pet"):
                message = edit_pet(pet_id, pet_data, image_file)
                st.success(message)

    elif option == "Delete Account":
        st.subheader("Delete Account")
        if st.button("Confirm Deletion"):
            message = delete_shelter_account(user["shelter_id"])
            st.success(message)
            st.session_state.user = None
            st.session_state.user_type = None
            st.switch_page("app.py")