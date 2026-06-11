import json
from datetime import datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="2026 World Cup Bracket",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ 2026 World Cup Bracket App")

# -----------------------------
# Basic setup
# -----------------------------

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
# Google Sheets functions
# -----------------------------

@st.cache_resource
def get_google_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )

    client = gspread.authorize(credentials)
    spreadsheet_name = st.secrets["gcp_service_account"]["spreadsheet_name"]

    sheet = client.open(spreadsheet_name).sheet1
    return sheet


def save_bracket(username, data):
    sheet = get_google_sheet()

    all_records = sheet.get_all_records()
    row_to_update = None

    for index, record in enumerate(all_records, start=2):
        if record.get("user") == username:
            row_to_update = index
            break

    bracket_json = json.dumps(data, ensure_ascii=False)
    last_saved = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row_values = [username, bracket_json, last_saved]

    if row_to_update:
        sheet.update(f"A{row_to_update}:C{row_to_update}", [row_values])
    else:
        sheet.append_row(row_values)


def load_bracket(username):
    try:
        sheet = get_google_sheet()
        all_records = sheet.get_all_records()

        for record in all_records:
            if record.get("user") == username:
                bracket_json = record.get("bracket_json", "")

                if bracket_json:
                    return json.loads(bracket_json)

        return {}

    except Exception as e:
        st.error(f"Could not load bracket from Google Sheets: {e}")
        return {}


# -----------------------------
# Helper functions
# -----------------------------

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
    lookup = {}

    for group_name, picks in group_picks.items():
        letter = group_letters[group_name]

        lookup[f"1{letter}"] = picks.get("1st", "")
        lookup[f"2{letter}"] = picks.get("2nd", "")
        lookup[f"3{letter}"] = picks.get("3rd", "")
        lookup[f"4{letter}"] = picks.get("4th", "")

    return lookup


def resolve_slot(slot, lookup, third_place_assignments=None):
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


def bracket_table(section_data):
    rows = []

    for match_id, winner in section_data.items():
        rows.append({
            "Match": match_id,
            "Winner": winner
        })

    return rows


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
        "champion": saved_data.get("champion", ""),
    }

    if st.button("💾 Save Group Stage"):
        try:
            save_bracket(user, bracket_data)
            st.success(f"{user}'s group-stage picks have been saved to Google Sheets!")
        except Exception as e:
            st.error(f"Could not save to Google Sheets: {e}")


# -----------------------------
# Knockout stage tab
# -----------------------------

with tab_knockout:
    st.header("Knockout Stage")

    current_group_picks = group_picks

    missing_picks = []

    for group_name, picks in current_group_picks.items():
        for position in ["1st", "2nd", "3rd", "4th"]:
            if not picks.get(position):
                missing_picks.append(f"{group_name} - {position}")

    if missing_picks:
        st.warning("Please complete all group-stage rankings before moving to the knockout stage.")
        with st.expander("Missing picks"):
            for item in missing_picks:
                st.write(item)
    else:
        lookup = group_result_lookup(current_group_picks)

        st.subheader("Step 1: Choose the 8 third-place teams that advance")

        third_place_options = []

        for group_name in groups.keys():
            letter = group_letters[group_name]
            third_team = lookup.get(f"3{letter}", "")

            if third_team:
                third_place_options.append(f"3{letter}: {third_team}")

        saved_third_qualifiers = saved_data.get("third_place_qualifiers", [])

        saved_third_qualifiers = [
            item for item in saved_third_qualifiers
            if item in third_place_options
        ]

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

        st.subheader("Step 2: Assign third-place teams to eligible Round of 32 slots")

        st.caption(
            "Some Round of 32 slots can only receive third-place teams from certain groups. "
            "For example, 3A/B/C/D/F means a qualified third-place team from one of those groups."
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

            if saved_assignment not in eligible_teams:
                saved_assignment = ""

            options = [""] + eligible_teams
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
            "group_stage": current_group_picks,
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
            try:
                save_bracket(user, full_bracket_data)
                st.success(f"{user}'s full bracket has been saved to Google Sheets!")
            except Exception as e:
                st.error(f"Could not save to Google Sheets: {e}")


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

    if not view_data:
        st.info(f"No saved bracket yet for {selected_view_user}.")
    else:
        st.subheader(f"{selected_view_user}'s Group Stage Picks")

        group_rows = []

        for group_name, picks in view_data.get("group_stage", {}).items():
            group_rows.append({
                "Group": group_name,
                "1st": picks.get("1st", ""),
                "2nd": picks.get("2nd", ""),
                "3rd": picks.get("3rd", ""),
                "4th": picks.get("4th", "")
            })

        if group_rows:
            st.dataframe(group_rows, use_container_width=True, hide_index=True)

        st.subheader("Third-Place Qualifiers")

        third_rows = []

        for item in view_data.get("third_place_qualifiers", []):
            third_rows.append({
                "Qualified third-place team": item
            })

        if third_rows:
            st.dataframe(third_rows, use_container_width=True, hide_index=True)
        else:
            st.info("No third-place qualifiers saved yet.")

        st.subheader("Third-Place Slot Assignments")

        assignment_rows = []

        for slot, team in view_data.get("third_place_assignments", {}).items():
            assignment_rows.append({
                "Slot": slot,
                "Team": team
            })

        if assignment_rows:
            st.dataframe(assignment_rows, use_container_width=True, hide_index=True)

        st.subheader("Knockout Stage Picks")

        knockout_sections = {
            "Round of 32": "round32",
            "Round of 16": "round16",
            "Quarterfinals": "quarterfinals",
            "Semifinals": "semifinals",
            "Final": "final"
        }

        for display_name, section_key in knockout_sections.items():
            section_data = view_data.get(section_key, {})

            if section_data:
                st.markdown(f"### {display_name}")
                st.dataframe(
                    bracket_table(section_data),
                    use_container_width=True,
                    hide_index=True
                )

        champion = view_data.get("champion", "")

        if champion:
            st.success(f"🏆 Champion: {champion}")

    st.divider()
    st.header("Quick Champion Comparison")

    col1, col2 = st.columns(2)

    with col1:
        gokce_data = load_bracket("Gokce")
        st.subheader("Gokce")
        st.write(gokce_data.get("champion", "No champion saved yet."))

    with col2:
        jack_data = load_bracket("Jack")
        st.subheader("Jack")
        st.write(jack_data.get("champion", "No champion saved yet."))
