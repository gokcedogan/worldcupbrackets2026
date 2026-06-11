import json
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="2026 World Cup Bracket",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ 2026 World Cup Bracket App")

# -----------------------------
# Basic setup
# -----------------------------

SAVE_DIR = Path("saved_brackets")
SAVE_DIR.mkdir(exist_ok=True)

users = ["Gokce", "Jack"]

user = st.sidebar.selectbox(
    "Who is filling out the bracket?",
    users
)

st.sidebar.write(f"Current bracket: **{user}**")

groups = {
    "Group A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "Group B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "Group C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "Group D": ["United States", "Paraguay", "Australia", "Turkey"],
    "Group E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "Group F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "Group G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "Group H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "Group I": ["France", "Senegal", "Iraq", "Norway"],
    "Group J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "Group K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "Group L": ["England", "Croatia", "Ghana", "Panama"],
}

group_letters = {
    "Group A": "A",
    "Group B": "B",
    "Group C": "C",
    "Group D": "D",
    "Group E": "E",
    "Group F": "F",
    "Group G": "G",
    "Group H": "H",
    "Group I": "I",
    "Group J": "J",
    "Group K": "K",
    "Group L": "L",
}

# FIFA Round of 32 fixed slots
round32_template = [
    ("M73", "2A", "2B"),
    ("M74", "1E", "3A/B/C/D/F"),
    ("M75", "1F", "2C"),
    ("M76", "1C", "2F"),
    ("M77", "1I", "3C/D/F/G/H"),
    ("M78", "2E", "2I"),
    ("M79", "1A", "3C/E/F/H/I"),
    ("M80", "1L", "3E/H/I/J/K"),
    ("M81", "1D", "3B/E/F/I/J"),
    ("M82", "1G", "3A/E/H/I/J"),
    ("M83", "2K", "2L"),
    ("M84", "1H", "2J"),
    ("M85", "1B", "3E/F/G/I/J"),
    ("M86", "1J", "2H"),
    ("M87", "1K", "3D/E/I/J/L"),
    ("M88", "2D", "2G"),
]

round16_template = [
    ("M89", "Winner M74", "Winner M77"),
    ("M90", "Winner M73", "Winner M75"),
    ("M91", "Winner M76", "Winner M78"),
    ("M92", "Winner M79", "Winner M80"),
    ("M93", "Winner M83", "Winner M84"),
    ("M94", "Winner M81", "Winner M82"),
    ("M95", "Winner M86", "Winner M88"),
    ("M96", "Winner M85", "Winner M87"),
]

quarter_template = [
    ("M97", "Winner M90", "Winner M93"),
    ("M98", "Winner M89", "Winner M91"),
    ("M99", "Winner M92", "Winner M94"),
    ("M100", "Winner M95", "Winner M96"),
]

semi_template = [
    ("M101", "Winner M97", "Winner M98"),
    ("M102", "Winner M99", "Winner M100"),
]

final_template = [
    ("M104", "Winner M101", "Winner M102"),
]


# -----------------------------
# Helper functions
# -----------------------------

def save_bracket(username, data):
    file_path = SAVE_DIR / f"{username.lower()}_bracket.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_bracket(username):
    file_path = SAVE_DIR / f"{username.lower()}_bracket.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_saved_group_pick(saved_data, group_name, position):
    try:
        return saved_data["group_stage"][group_name][position]
    except KeyError:
        return ""


def get_saved_value(saved_data, section, key, default=""):
    try:
        return saved_data[section][key]
    except KeyError:
        return default


def group_result_lookup(group_picks):
    """
    Creates labels like:
    1A = winner of Group A
    2A = runner-up of Group A
    3A = third-place team of Group A
    """
    lookup = {}

    for group_name, picks in group_picks.items():
        letter = group_letters[group_name]

        lookup[f"1{letter}"] = picks.get("1st", "")
        lookup[f"2{letter}"] = picks.get("2nd", "")
        lookup[f"3{letter}"] = picks.get("3rd", "")
        lookup[f"4{letter}"] = picks.get("4th", "")

    return lookup


def resolve_slot(slot, lookup, third_place_assignments=None):
    """
    Turns a bracket slot like 1A or 2B into the selected team name.
    For third-place slots like 3A/B/C/D/F, use the manually assigned third-place team.
    """
    if third_place_assignments is None:
        third_place_assignments = {}

    if slot.startswith("Winner "):
        return slot

    if slot in lookup:
        return lookup[slot]

    if slot.startswith("3"):
        return third_place_assignments.get(slot, "")

    return slot


def pick_winner(match_id, team1, team2, saved_data, section):
    options = [""]

    if team1:
        options.append(team1)

    if team2 and team2 != team1:
        options.append(team2)

    saved_pick = get_saved_value(saved_data, section, match_id)

    if saved_pick and saved_pick not in options:
        options.append(saved_pick)

    default_index = options.index(saved_pick) if saved_pick in options else 0

    winner = st.selectbox(
        f"{match_id}: {team1 or 'TBD'} vs {team2 or 'TBD'}",
        options,
        index=default_index,
        key=f"{user}_{section}_{match_id}"
    )

    return winner


saved_data = load_bracket(user)

# -----------------------------
# Tabs
# -----------------------------

tab_group, tab_knockout, tab_compare = st.tabs(
    ["Group Stage", "Knockout Stage", "View / Compare"]
)

# -----------------------------
# Group stage tab
# -----------------------------

with tab_group:
    st.header("Group Stage Predictions")
    st.write("For each group, rank the teams from 1st to 4th.")

    group_picks = {}

    for group_name, teams in groups.items():
        st.subheader(group_name)

        group_picks[group_name] = {}

        available_teams = teams.copy()

        for position in ["1st", "2nd", "3rd", "4th"]:
            saved_pick = get_saved_group_pick(saved_data, group_name, position)

            options = [""] + available_teams

            if saved_pick and saved_pick not in options:
                options.append(saved_pick)

            default_index = options.index(saved_pick) if saved_pick in options else 0

            pick = st.selectbox(
                f"{group_name} - {position} place",
                options,
                index=default_index,
                key=f"{user}_{group_name}_{position}"
            )

            group_picks[group_name][position] = pick

            if pick in available_teams:
                available_teams.remove(pick)

        st.caption("Teams in this group: " + ", ".join(teams))

    bracket_data = {
        "user": user,
        "group_stage": group_picks,
        "third_place_qualifiers": saved_data.get("third_place_qualifiers", []),
        "third_place_assignments": saved_data.get("third_place_assignments", {}),
        "round32": saved_data.get("round32", {}),
        "round16": saved_data.get("round16", {}),
        "quarterfinals": saved_data.get("quarterfinals", {}),
        "semifinals": saved_data.get("semifinals", {}),
        "final": saved_data.get("final", {}),
    }

    if st.button("💾 Save Group Stage"):
        save_bracket(user, bracket_data)
        st.success(f"{user}'s group-stage picks have been saved!")

# -----------------------------
# Knockout stage tab
# -----------------------------

with tab_knockout:
    st.header("Knockout Stage")

    if not saved_data.get("group_stage"):
        st.warning("Please save your group-stage picks first.")
    else:
        saved_group_picks = saved_data["group_stage"]
        lookup = group_result_lookup(saved_group_picks)

        st.subheader("Step 1: Choose the 8 third-place teams that advance")

        third_place_options = []

        for group_name in groups.keys():
            letter = group_letters[group_name]
            third_team = lookup.get(f"3{letter}", "")

            if third_team:
                third_place_options.append(f"3{letter}: {third_team}")

        saved_third_qualifiers = saved_data.get("third_place_qualifiers", [])

        third_place_qualifiers = st.multiselect(
            "Pick exactly 8 third-place teams",
            third_place_options,
            default=saved_third_qualifiers,
            max_selections=8,
            key=f"{user}_third_place_qualifiers"
        )

        if len(third_place_qualifiers) < 8:
            st.info("Pick 8 third-place teams before completing all Round of 32 third-place slots.")
        elif len(third_place_qualifiers) == 8:
            st.success("You selected 8 third-place teams.")

        third_place_team_by_group = {}

        for item in third_place_qualifiers:
            group_code = item.split(":")[0]
            team_name = item.split(": ", 1)[1]
            third_place_team_by_group[group_code] = team_name

        st.subheader("Step 2: Assign third-place teams to FIFA-eligible Round of 32 slots")

        st.caption(
            "Some Round of 32 slots can only receive third-place teams from certain groups. "
            "For example, one slot is 3A/B/C/D/F, meaning a qualified third-place team from one of those groups."
        )

        third_place_assignments = {}

        third_slots = sorted(
            list({slot for _, a, b in round32_template for slot in [a, b] if slot.startswith("3")})
        )

        for slot in third_slots:
            eligible_letters = slot[1:].split("/")
            eligible_codes = [f"3{letter}" for letter in eligible_letters]

            eligible_teams = [
                third_place_team_by_group[code]
                for code in eligible_codes
                if code in third_place_team_by_group
            ]

            saved_assignment = get_saved_value(
                saved_data,
                "third_place_assignments",
                slot,
                default=""
            )

            options = [""] + eligible_teams

            if saved_assignment and saved_assignment not in options:
                options.append(saved_assignment)

            default_index = options.index(saved_assignment) if saved_assignment in options else 0

            third_place_assignments[slot] = st.selectbox(
                f"{slot}",
                options,
                index=default_index,
                key=f"{user}_assign_{slot}"
            )

        st.divider()
        st.subheader("Round of 32")

        round32_winners = {}

        for match_id, slot1, slot2 in round32_template:
            team1 = resolve_slot(slot1, lookup, third_place_assignments)
            team2 = resolve_slot(slot2, lookup, third_place_assignments)

            round32_winners[match_id] = pick_winner(
                match_id,
                team1,
                team2,
                saved_data,
                "round32"
            )

        st.divider()
        st.subheader("Round of 16")

        round16_winners = {}

        for match_id, slot1, slot2 in round16_template:
            previous_match_1 = slot1.replace("Winner ", "")
            previous_match_2 = slot2.replace("Winner ", "")

            team1 = round32_winners.get(previous_match_1, "")
            team2 = round32_winners.get(previous_match_2, "")

            round16_winners[match_id] = pick_winner(
                match_id,
                team1,
                team2,
                saved_data,
                "round16"
            )

        st.divider()
        st.subheader("Quarterfinals")

        quarter_winners = {}

        for match_id, slot1, slot2 in quarter_template:
            previous_match_1 = slot1.replace("Winner ", "")
            previous_match_2 = slot2.replace("Winner ", "")

            team1 = round16_winners.get(previous_match_1, "")
            team2 = round16_winners.get(previous_match_2, "")

            quarter_winners[match_id] = pick_winner(
                match_id,
                team1,
                team2,
                saved_data,
                "quarterfinals"
            )

        st.divider()
        st.subheader("Semifinals")

        semi_winners = {}

        for match_id, slot1, slot2 in semi_template:
            previous_match_1 = slot1.replace("Winner ", "")
            previous_match_2 = slot2.replace("Winner ", "")

            team1 = quarter_winners.get(previous_match_1, "")
            team2 = quarter_winners.get(previous_match_2, "")

            semi_winners[match_id] = pick_winner(
                match_id,
                team1,
                team2,
                saved_data,
                "semifinals"
            )

        st.divider()
        st.subheader("Final")

        final_winners = {}

        for match_id, slot1, slot2 in final_template:
            previous_match_1 = slot1.replace("Winner ", "")
            previous_match_2 = slot2.replace("Winner ", "")

            team1 = semi_winners.get(previous_match_1, "")
            team2 = semi_winners.get(previous_match_2, "")

            final_winners[match_id] = pick_winner(
                match_id,
                team1,
                team2,
                saved_data,
                "final"
            )

        champion = final_winners.get("M104", "")

        if champion:
            st.success(f"🏆 Predicted Champion: {champion}")

        full_bracket_data = {
            "user": user,
            "group_stage": saved_group_picks,
            "third_place_qualifiers": third_place_qualifiers,
            "third_place_assignments": third_place_assignments,
            "round32": round32_winners,
            "round16": round16_winners,
            "quarterfinals": quarter_winners,
            "semifinals": semi_winners,
            "final": final_winners,
            "champion": champion,
        }

        if st.button("💾 Save Full Bracket"):
            save_bracket(user, full_bracket_data)
            st.success(f"{user}'s full bracket has been saved!")

# -----------------------------
# View / compare tab
# -----------------------------

with tab_compare:
    st.header("View Saved Brackets")

    selected_view_user = st.selectbox(
        "Whose saved bracket do you want to view?",
        users,
        key="view_saved_user"
    )

    view_data = load_bracket(selected_view_user)

    if view_data:
        st.json(view_data)
    else:
        st.info(f"No saved bracket yet for {selected_view_user}.")

    st.divider()
    st.header("Quick Champion Comparison")

    col1, col2 = st.columns(2)

    with col1:
        gokce_data = load_bracket("Gokce")
        st.subheader("Gokce")
        st.write(gokce_data.get("champion", "No champion saved yet."))

    with col2:
        boyfriend_data = load_bracket("Jack")
        st.subheader("Jack")
        st.write(boyfriend_data.get("champion", "No champion saved yet."))