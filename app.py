import streamlit as st
import pandas as pd
import pyarrow.parquet as pq
import os
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import seaborn as sns

st.title("Player Journey Visualization Tool")
uploaded_file = st.file_uploader(
    "Upload player_data.zip",
    type="zip"
)

# ---------------- LOAD DATA ----------------

def load_all_data(folder):
    frames = []

    for root, dirs, files in os.walk(folder):
        for f in files:
            path = os.path.join(root, f)

            try:
                table = pq.read_table(path)
                df = table.to_pandas()
                frames.append(df)
            except:
                continue

    return pd.concat(frames, ignore_index=True)


if uploaded_file is not None:

    import zipfile
    import tempfile

    temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    df = load_all_data(temp_dir)

else:
    st.warning("Please upload the player_data.zip file to continue.")
    st.stop()

# decode events
df["event"] = df["event"].apply(
    lambda x: x.decode("utf-8") if isinstance(x, bytes) else x
)

# identify bots
df["is_bot"] = df["user_id"].str.isnumeric()


# ---------------- UI CONTROLS ----------------

st.header("Match Controls")

player_type = st.selectbox(
    "Player Type",
    ["All", "Humans", "Bots"]
)

if player_type == "Humans":
    filtered_df = df[df["is_bot"] == False]

elif player_type == "Bots":
    filtered_df = df[df["is_bot"] == True]

else:
    filtered_df = df


match_select = st.selectbox(
    "Select Match",
    filtered_df["match_id"].unique()
)

match_df = filtered_df[filtered_df["match_id"] == match_select]


# ---------------- TIMELINE ----------------

match_df["time_seconds"] = (
    match_df["ts"] - match_df["ts"].min()
).dt.total_seconds()

min_time = float(match_df["time_seconds"].min())
max_time = float(match_df["time_seconds"].max())

if min_time < max_time:

    time_slider = st.slider(
        "Match Timeline (seconds)",
        min_value=min_time,
        max_value=max_time,
        value=max_time
    )

    match_df = match_df[match_df["time_seconds"] <= time_slider]

else:
    st.write("This match has no timeline variation.")


# filter events based on player type
if player_type == "Humans":
    match_df = match_df[~match_df["event"].str.contains("Bot")]

elif player_type == "Bots":
    match_df = match_df[match_df["event"].str.contains("Bot")]


# ---------------- MAP SETUP ----------------

map_select = match_df["map_id"].iloc[0]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

map_images = {
    "AmbroseValley": os.path.join(BASE_DIR,"minimaps","AmbroseValley_Minimap.png"),
    "GrandRift": os.path.join(BASE_DIR,"minimaps","GrandRift_Minimap.png"),
    "Lockdown": os.path.join(BASE_DIR,"minimaps","Lockdown_Minimap.jpg")
}

MAP_CONFIG = {
    "AmbroseValley": {"scale":900,"origin_x":-370,"origin_z":-473},
    "GrandRift": {"scale":581,"origin_x":-290,"origin_z":-290},
    "Lockdown": {"scale":1000,"origin_x":-500,"origin_z":-500}
}


def world_to_pixel(x,z,map_id):

    config = MAP_CONFIG[map_id]

    u = (x - config["origin_x"]) / config["scale"]
    v = (z - config["origin_z"]) / config["scale"]

    px = u * 1024
    py = (1 - v) * 1024

    return px, py


match_df["px"], match_df["py"] = zip(*match_df.apply(
    lambda r: world_to_pixel(r["x"], r["z"], r["map_id"]),
    axis=1
))


# ---------------- MAP VISUALIZATION ----------------

st.header("Map Visualization")

img = mpimg.imread(map_images[map_select])

fig, ax = plt.subplots(figsize=(7,7))

ax.imshow(img, extent=[0,1024,1024,0])


# movement
movement = match_df[match_df["event"].isin(["Position","BotPosition"])]

ax.scatter(
    movement["px"],
    movement["py"],
    c="green",
    s=15,
    alpha=0.6,
    label="Movement"
)

# loot
loot = match_df[match_df["event"]=="Loot"]

ax.scatter(
    loot["px"],
    loot["py"],
    c="yellow",
    s=80,
    edgecolors="black",
    label="Loot"
)

# kills
kills = match_df[match_df["event"].isin(["Kill","BotKill"])]

ax.scatter(
    kills["px"],
    kills["py"],
    c="red",
    s=100,
    edgecolors="black",
    label="Kill"
)

# deaths
deaths = match_df[match_df["event"].isin(["Killed","BotKilled"])]

ax.scatter(
    deaths["px"],
    deaths["py"],
    c="purple",
    s=100,
    edgecolors="black",
    label="Death"
)

# storm
storm = match_df[match_df["event"]=="KilledByStorm"]

ax.scatter(
    storm["px"],
    storm["py"],
    c="blue",
    s=120,
    edgecolors="black",
    label="Storm Death"
)

ax.legend()

ax.set_xlim(0,1024)
ax.set_ylim(1024,0)

st.pyplot(fig)


# ---------------- TRAFFIC HEATMAP ----------------

st.header("Traffic Heatmap")

fig2, ax2 = plt.subplots(figsize=(7,7))

ax2.imshow(img, extent=[0,1024,1024,0])

sns.kdeplot(
    x=movement["px"],
    y=movement["py"],
    cmap="Reds",
    fill=True,
    alpha=0.8,
    bw_adjust=0.3,
    levels=100,
    ax=ax2
)

ax2.set_xlim(0,1024)
ax2.set_ylim(1024,0)


st.pyplot(fig2)
