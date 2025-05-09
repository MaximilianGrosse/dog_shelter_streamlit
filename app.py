import streamlit as st
import pandas as pd
import uuid
import os

# Set page config first
st.set_page_config(page_title="Login/Registration", layout="wide")

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.user_type = None

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

# Register user
def register_user(user_type, data):
    global adopters_df, shelters_df
    data["username"] = data["username"].lower()
    if user_type == "Adopter":
        if data["username"] in adopters_df["username"].values:
            return False, "Username already exists"
        data["adopter_id"] = f"ADOP{uuid.uuid4().hex[:6].upper()}"
        data["liked_pets"] = ""
        adopters_df = pd.concat([adopters_df, pd.DataFrame([data])], ignore_index=True)
    else:  # Shelter
        if data["username"] in shelters_df["username"].values:
            return False, "Username already exists"
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
        else:
            st.write(f"Debug: Adopter username '{username}' not found or password incorrect.")
    else:  # Shelter
        user = shelters_df[(shelters_df["username"] == username) & (shelters_df["password"] == password)]
        if not user.empty:
            return True, user.iloc[0]
        else:
            st.write(f"Debug: Shelter username '{username}' not found or password incorrect.")
    return False, "Invalid credentials"

# Main app
st.sidebar.title("Dog Shelter Adoption Platform")

st.title("Dog Shelter Adoption Platform")
st.markdown("### Join Our Pet Adoption Community! 🐾")
st.markdown("Find your furry friend or help pets find loving homes with our platform! ❤️")

# Display image
if os.path.exists("pics/f1.jpg"):
    st.image("pics/f1.jpg", caption="Happy Pets", use_column_width=True)
else:
    st.warning("Image f1.jpg not found. Please ensure it is in the pics/ directory.")

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
                st.session_state.user = result
                st.session_state.user_type = user_type
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
                    data[field] = st.selectbox("Preferred Species", ["Dog", "Cat", "Turtle", "Rabbit", "Hamster"], key=f"reg_{field}")
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
                data[field] = st.text_input(field.capitalize(), key=f"reg_{field}")
        if st.button("Register"):
            success, message = register_user(user_type, data)
            if success:
                st.success(message)
            else:
                st.error(message)